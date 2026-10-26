"""Schedulers receive only immutable public belief, clock, receipts and budgets."""
from dataclasses import dataclass
from typing import Literal, Protocol
from continuum.runtime.dynamics import AnalyticDynamics, State, deadline_urgency

Kind = Literal['wait','observe','think','predict','alert']

@dataclass(frozen=True)
class Action:
    kind: Kind
    reason: str = ''

@dataclass(frozen=True)
class PolicyInput:
    at: float
    horizon: float
    dt: float
    x: float
    v: float
    variance: float
    forecast_variance: float
    last_observation: float | None
    innovation: float | None
    observations_left: int
    inferences_left: int
    observation_limit: int
    public_events: tuple[str, ...]
    deadlines: tuple[float, ...]
    noise_std: float = .08

class Policy(Protocol):
    def decide(self, evidence: PolicyInput) -> tuple[Action, ...]: ...

LABELS = {'periodic':'Fixed period', 'event_deadline':'Event / deadline',
          'original_hybrid':'Original hybrid', 'uncertainty':'Uncertainty aware'}

class Scheduler:
    def __init__(self, name, *, period_scale=1., threshold=.035):
        if name not in LABELS:
            raise ValueError('unknown policy')
        self.name,self.period_scale,self.threshold = name,period_scale,threshold
        self.next_at = 0.
        self.state = State(pressure=.2)
        self.dynamics = AnalyticDynamics()

    def decide(self, e):
        if e.observations_left <= 0 or e.inferences_left <= 0:
            return (Action('wait','budget exhausted'),Action('predict'))
        period = e.horizon / max(1,e.observation_limit) * self.period_scale
        due = e.at + 1e-9 >= self.next_at
        if self.name in ('event_deadline','original_hybrid'):
            due = due or bool(e.public_events) or any(abs(e.at-d)<1e-8 for d in e.deadlines)
        if self.name == 'uncertainty':
            # A declared greedy VOI proxy: expected posterior position variance reduction.
            gain = e.forecast_variance ** 2 / (e.forecast_variance + e.noise_std**2)
            remaining_time = max(e.dt,e.horizon-e.at)
            spacing = remaining_time / max(1,e.observations_left)
            age = float('inf') if e.last_observation is None else e.at-e.last_observation
            due = age >= max(e.dt,.5*spacing) and (gain >= self.threshold or age >= 1.5*spacing)
        if not due:
            return (Action('wait','scheduled sleep'),Action('predict'))
        delay = period
        if self.name in ('event_deadline','original_hybrid'):
            # Same timestamp/event + explicit-deadline structure as runtime C/D.
            future = [d for d in e.deadlines if d > e.at]
            if future:
                delay = min(delay,max(5,min(future)-e.at))
            if self.name == 'original_hybrid':
                self.state = self.dynamics.observe(self.state,e.at,'document.available',1)
                if e.innovation is not None and abs(e.innovation)>2.6:
                    self.state = self.dynamics.observe(self.state,e.at,'memory.conflict',1)
                drive = self.state.pressure + self.state.uncertainty + self.state.staleness + deadline_urgency(e.at,future)
                delay = max(5,min(period,delay*(1+self.state.cooldown)/(1+drive)))
        self.next_at = e.at+delay
        return (Action('observe','scheduler wake'),Action('think','Kalman measurement update'),Action('predict'))
