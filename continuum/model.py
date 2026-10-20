"""Public observations and private environment truth are separate types."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Event:
    id: str
    at: int
    kind: str
    key: str
    value: str = ""
    ready: int = 0
    deadline: int = 0
    expires: int | None = None


@dataclass(frozen=True)
class Goal:
    id: str
    actual_ready: int
    deadline: int
    cancelled_at: int | None = None

    def actionable(self, at: int) -> bool:
        return (self.actual_ready <= at <= self.deadline
                and (self.cancelled_at is None or at < self.cancelled_at))

    @property
    def feasible(self) -> bool:
        return self.actual_ready <= self.deadline and (
            self.cancelled_at is None or self.actual_ready < self.cancelled_at)


@dataclass(frozen=True)
class Scenario:
    name: str
    seed: int
    horizon: int
    events: tuple[Event, ...]
    goals: tuple[Goal, ...]


@dataclass
class ContinuousState:
    """Exact solution to d activation / dt = -decay * activation between events.

    Virtual timestamps may be fractional; simulation observations use integer time.
    Activation controls the adaptive scheduler's maximum idle interval.
    """
    at: float = 0.0
    activation: float = 0.0
    decay: float = 0.15

    def advance(self, at: float) -> None:
        if at < self.at:
            raise ValueError("state time must be monotonic")
        self.activation *= math.exp(-self.decay * (at - self.at))
        self.at = at

    def observe(self, at: float, weight: float) -> None:
        self.advance(at)
        self.activation = min(10.0, self.activation + weight)

    def idle_interval(self) -> int:
        return max(3, math.ceil(12 / (1 + self.activation)))
