"""Five predeclared regimes, seeded locally; no random state shared by agents."""
import random
from .model import Event, Goal, Scenario

REGIMES = ('event_aligned', 'quiet_deadlines', 'wide_windows', 'noisy_stream', 'misleading_estimates')


def generate(name: str, seed: int, horizon: int = 120) -> Scenario:
    if name not in REGIMES:
        raise ValueError(name)
    if horizon < 120:
        raise ValueError("horizon must be at least 120")
    rng = random.Random(seed)
    events, goals = [], []
    for i in range(12):
        created = 2 + i * 8
        estimate = created if name == 'event_aligned' else created + rng.randint(3, 6)
        width = 14 if name == 'wide_windows' else rng.randint(2, 4)
        actual = estimate
        if name == 'misleading_estimates':
            actual = estimate + rng.randint(-2, 6)
        deadline = estimate + width
        cancel = created + 1 if i % 5 == 4 and name != 'event_aligned' else None
        key = f'g{i:02d}'
        goals.append(Goal(key, actual, deadline, cancel))
        events.append(Event(f'goal-{i}', created, 'goal', key, ready=estimate, deadline=deadline))
        if cancel is not None:
            events.append(Event(f'cancel-{i}', cancel, 'cancel', key))
    # Same fact workload except the explicitly noisy regime. Versions and expiry
    # provide independent memory probes, without handing hidden readiness to agents.
    fact_times = range(1, horizon, 1 if name == 'noisy_stream' else 11)
    for i, at in enumerate(fact_times):
        events.append(Event(f'fact-{i}', at, 'fact', f'fact-{i % 4}',
                            value=f'v{i}', expires=at + 9))
    events.sort(key=lambda e: (e.at, e.id))
    return Scenario(name, seed, horizon, tuple(events), tuple(goals))
