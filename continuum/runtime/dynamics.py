"""Hand-designed hybrid dynamics, normalized to [0,1], seconds as time unit."""
from dataclasses import asdict, dataclass
import math
from typing import Protocol


@dataclass(frozen=True)
class State:
    at: float = 0.0
    urgency: float = 0.0
    staleness: float = 0.0
    uncertainty: float = 0.0
    pressure: float = 0.0
    cooldown: float = 0.0

    def to_dict(self):
        return asdict(self)


class StateDynamics(Protocol):
    def evolve(self, state: State, at: float) -> State: ...
    def observe(self, state: State, at: float, kind: str, active_goals: int) -> State: ...


class AnalyticDynamics:
    # Seconds^-1. Memories themselves never decay or disappear here.
    rates = {'urgency': 1/300, 'staleness': 1/180, 'uncertainty': 1/600,
             'pressure': 0.0, 'cooldown': 1/30}
    baselines = {'urgency': 1.0, 'staleness': 1.0, 'uncertainty': 0.0,
                 'pressure': 0.0, 'cooldown': 0.0}

    def evolve(self, state, at):
        delta = at - state.at
        if not math.isfinite(at) or delta < 0:
            raise ValueError('finite monotonic state time required')
        values = {key: self.baselines[key] + (getattr(state, key) - self.baselines[key]) * math.exp(-rate * delta)
                  for key, rate in self.rates.items()}
        return State(at=at, **{k: min(1.0, max(0.0, v)) for k, v in values.items()})

    def observe(self, state, at, kind, active_goals):
        values = self.evolve(state, at).to_dict()
        values['pressure'] = min(1.0, active_goals / 5)
        if kind in ('document.available', 'user.message', 'fact.corrected'):
            values['staleness'] = 0.0
        if kind in ('memory.conflict', 'action.failed'):
            values['uncertainty'] = min(1.0, values['uncertainty'] + 0.5)
        if kind == 'notification.delivered':
            values['cooldown'] = 1.0
        return State(**values)


class DiscreteDynamics(AnalyticDynamics):
    """Declared control: hold features between observations; same event impulses."""
    def evolve(self, state, at):
        if not math.isfinite(at) or at < state.at:
            raise ValueError('finite monotonic state time required')
        return State(**{**state.to_dict(), 'at': at})


def deadline_urgency(at, deadlines):
    return max((1 / (1 + max(0, d - at) / 60) for d in deadlines if d is not None), default=0.0)
