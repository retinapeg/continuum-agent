"""Private deterministic world. No policy receives this object or its config."""
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import random


@dataclass(frozen=True)
class Change:
    time: float
    omega: float
    damping: float


@dataclass(frozen=True)
class WorldConfig:
    seed: int = 7
    horizon: float = 120.0
    dt: float = 0.5
    omega: float = 0.8
    damping: float = 0.015
    noise: float = 0.08
    changes: tuple[Change, ...] = ()
    stale: tuple[tuple[float, float, float], ...] = ()
    contradictions: tuple[tuple[float, float, float], ...] = ()

    def __post_init__(self):
        values = (self.horizon, self.dt, self.omega, self.damping, self.noise)
        if not all(math.isfinite(v) for v in values):
            raise ValueError('finite world parameters required')
        if not (1 <= self.horizon <= 600 and .05 <= self.dt <= 1 and self.omega > 0 and self.damping >= 0 and self.noise > 0):
            raise ValueError('world parameters outside bounds')
        if abs(self.horizon / self.dt - round(self.horizon / self.dt)) > 1e-8:
            raise ValueError('horizon must align with grid')
        previous = -1
        for c in self.changes:
            if not all(math.isfinite(v) for v in (c.time, c.omega, c.damping)) or not (0 < c.time < self.horizon and 0 < c.omega <= 4 and 0 <= c.damping <= 1):
                raise ValueError('invalid change')
            if c.time <= previous or abs(c.time/self.dt-round(c.time/self.dt)) > 1e-8:
                raise ValueError('changes must be ordered unique grid times')
            previous = c.time
        for start, end, value in self.stale + self.contradictions:
            if not all(math.isfinite(v) for v in (start,end,value)) or not 0 <= start < end <= self.horizon:
                raise ValueError('invalid sensor fault interval')
        if any(lag <= 0 for _,_,lag in self.stale):
            raise ValueError('stale lag must be positive')

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**{**data, 'changes': tuple(Change(**c) for c in data.get('changes', [])),
                     'stale': tuple(tuple(x) for x in data.get('stale', [])),
                     'contradictions': tuple(tuple(x) for x in data.get('contradictions', []))})


def transition(omega, damping, dt):
    """Exact exp(A dt), A=[[0,1],[-omega²,-2*damping]]."""
    q = omega * omega - damping * damping
    decay = math.exp(-damping * dt)
    if abs(q) < 1e-12:
        c, s = 1.0, dt
    elif q > 0:
        k = math.sqrt(q)
        c, s = math.cos(k * dt), math.sin(k * dt) / k
    else:
        k = math.sqrt(-q)
        c, s = math.cosh(k * dt), math.sinh(k * dt) / k
    return (decay*(c+damping*s), decay*s, -decay*omega*omega*s, decay*(c-damping*s))


def advance(x, v, omega, damping, dt):
    a,b,c,d = transition(omega,damping,dt)
    return a*x+b*v, c*x+d*v


def scenario(name, seed=7, **overrides):
    if name not in ('no_change','change','stale','adversarial'):
        raise ValueError('unknown scenario')
    # Validate requested grid before deriving times, including short episodes.
    base = WorldConfig(seed=seed, **overrides)
    ticks = round(base.horizon / base.dt)

    def grid(fraction):
        return round(round(fraction * ticks) * base.dt, 9)

    def interval(start, end, value):
        first = min(ticks - 1, round(start / 120. * ticks))
        last = min(ticks, max(first + 1, round(end / 120. * ticks)))
        return (round(first * base.dt, 9), round(last * base.dt, 9), value)

    # Seed affects hidden timings as well as noise, never exposed to policy.
    rng = random.Random(seed + 9181)
    if name != 'no_change' and ticks < 3 and 'changes' not in overrides:
        raise ValueError('change scenarios require at least three simulation steps')
    first = max(1, min(ticks - 2, round(rng.uniform(.225, .375) * ticks)))
    second = max(first + 1, min(ticks - 1, round(rng.uniform(.5667, .7333) * ticks)))
    t1, t2 = round(first * base.dt, 9), round(second * base.dt, 9)
    changes = () if name == 'no_change' else (Change(t1,1.25,.012), Change(t2,.55,.025))
    stale = (interval(42.,62.,max(base.dt,grid(.1))),) if name == 'stale' else ()
    contradictions = (interval(50.,57.,1.5),interval(83.,87.,-1.5)) if name == 'adversarial' else ()
    values = {'seed':seed, 'changes':changes, 'stale':stale, 'contradictions':contradictions}
    values.update(overrides)
    return WorldConfig(**values)


class World:
    def __init__(self, config: WorldConfig):
        self.config = config
        self._truth = []
        x,v,omega,damping = 1.,0.,config.omega,config.damping
        changes = {round(c.time/config.dt): c for c in config.changes}
        for tick in range(round(config.horizon/config.dt)+1):
            at = round(tick*config.dt,9)
            if tick in changes:
                omega,damping = changes[tick].omega,changes[tick].damping
            self._truth.append({'time':at,'x':x,'v':v,'omega':omega,'damping':damping})
            x,v = advance(x,v,omega,damping,config.dt)

    def measure(self, tick):
        at = self._truth[tick]['time']
        source_tick = tick
        for start,end,lag in self.config.stale:
            if start <= at < end:
                source_tick = max(0,tick-round(lag/self.config.dt))
        source = self._truth[source_tick]
        # Counterfactual measurement depends on world/time, never call order/policy.
        rng = random.Random(f'{self.config.seed}:sensor:{source_tick}')
        value = source['x'] + rng.gauss(0,self.config.noise)
        for start,end,bias in self.config.contradictions:
            if start <= at < end:
                value += bias
        return {'time':at,'measured_at':source['time'],'value':value,'noise_std':self.config.noise,
                'id':f'observation-{tick}'}

    def truth(self):
        return [dict(row) for row in self._truth]

    @property
    def fingerprint(self):
        return hashlib.sha256(json.dumps(self._truth,sort_keys=True).encode()).hexdigest()
