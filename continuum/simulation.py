"""Virtual-time environment. Hidden ground truth never enters agent memory."""
from dataclasses import asdict, dataclass
from .agents import Agent, PERIOD
from .model import Scenario
from .storage import Store


@dataclass(frozen=True)
class Result:
    scenario: str
    seed: int
    policy: str
    feasible_goals: int
    completed: int
    completion_rate: float
    memory_accuracy: float
    intervention_precision: float | None
    intervention_recall: float
    latency_mean: float | None
    decisions: int
    attempts: int
    interruptions: int
    cost_units: float

    def to_dict(self) -> dict:
        return asdict(self)


def run(scenario: Scenario, policy: str, db_path: str = ':memory:') -> Result:
    store = Store(db_path)
    try:
        # A benchmark run owns one database; accidental append invalidates results.
        if store.db.execute('SELECT COUNT(*) FROM events').fetchone()[0] or store.db.execute(
                'SELECT COUNT(*) FROM audit').fetchone()[0]:
            raise ValueError('simulation requires an empty database')
        agent = Agent(policy, store)
        truth = {g.id: g for g in scenario.goals}
        events_at: dict[int, list] = {}
        for event in scenario.events:
            events_at.setdefault(event.at, []).append(event)
        facts: dict[str, tuple[str, int | None]] = {}
        wake = PERIOD if policy == 'periodic' else (0 if policy == 'adaptive' else None)
        successes, latencies = set(), []
        decisions = attempts = interruptions = correct = probes = 0
        for at in range(scenario.horizon + 1):
            events = events_at.get(at, [])
            for event in events:
                store.ingest(event)
                if event.kind == 'fact':
                    facts[event.key] = (event.value, event.expires)
            # Observe all facts even while asleep: policy comparison isolates scheduling.
            for key in ('fact-0', 'fact-1', 'fact-2', 'fact-3', 'absent'):
                expected = facts.get(key)
                value = expected[0] if expected and (expected[1] is None or at < expected[1]) else None
                correct += store.recall(key, at)[0] == value
                probes += 1
            due = wake is not None and at >= wake
            triggered = bool(events) and policy in ('reactive', 'adaptive')
            if due or triggered:
                decisions += 1
                candidates = agent.candidates(at)
                store.log(at, 'decision', {'policy': policy, 'timer': due,
                                          'event_trigger': triggered, 'candidates': candidates})
                # One interruption is a user-visible action batch, even if unsuccessful.
                interruptions += bool(candidates)
                for task in candidates:
                    attempts += 1
                    success = truth[task].actionable(at) and task not in successes
                    store.attempt(task, at, success)
                    if success:
                        successes.add(task)
                        latencies.append(at - truth[task].actual_ready)
                wake = agent.next_wake(at)
            elif events and policy == 'periodic':
                pass  # ingestion never changes the fixed periodic clock
        feasible = sum(g.feasible for g in scenario.goals)
        completed = len(successes)
        result = Result(scenario.name, scenario.seed, policy, feasible, completed,
                        completed / feasible if feasible else 1.0, correct / probes,
                        completed / attempts if attempts else None,
                        completed / feasible if feasible else 1.0,
                        sum(latencies) / len(latencies) if latencies else None,
                        decisions, attempts, interruptions,
                        round(len(scenario.events) * 0.01 + decisions * 0.1 + attempts, 4))
        store.checkpoint(scenario.horizon)
        store.log(scenario.horizon, 'result', result.to_dict())
        return result
    finally:
        store.close()
