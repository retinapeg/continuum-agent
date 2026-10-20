"""Identical action policy; only the decision clock changes across agents."""
from .storage import Store

POLICIES = ('reactive', 'periodic', 'adaptive')
RETRY_INTERVAL = 4
PERIOD = 6


class Agent:
    def __init__(self, policy: str, store: Store):
        if policy not in POLICIES:
            raise ValueError(f"unknown policy: {policy}")
        self.policy = policy
        self.store = store

    def candidates(self, at: int) -> list[str]:
        return [row['id'] for row in self.store.pending(at)
                if row['ready'] <= at and
                (row['last_attempt'] is None or at - row['last_attempt'] >= RETRY_INTERVAL)]

    def next_wake(self, at: int) -> int | None:
        if self.policy == 'reactive':
            return None
        if self.policy == 'periodic':
            return (at // PERIOD + 1) * PERIOD
        state = self.store.checkpoint(at)
        next_at = at + state.idle_interval()
        for row in self.store.pending(at):
            eligible = max(row['ready'], at + 1,
                           (row['last_attempt'] + RETRY_INTERVAL)
                           if row['last_attempt'] is not None else at + 1)
            if eligible <= row['deadline']:
                next_at = min(next_at, eligible)
        return next_at
