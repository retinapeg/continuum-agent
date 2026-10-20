"""Transactional event ingestion, durable memory, and decision provenance."""
import json
import math
import sqlite3
from dataclasses import asdict
from pathlib import Path
from .model import ContinuousState, Event


class Store:
    def __init__(self, path: str | Path = ":memory:"):
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events(
                id TEXT PRIMARY KEY, at INTEGER NOT NULL, payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS facts(
                key TEXT PRIMARY KEY, value TEXT NOT NULL, observed INTEGER NOT NULL,
                expires INTEGER);
            CREATE TABLE IF NOT EXISTS tasks(
                id TEXT PRIMARY KEY, ready INTEGER NOT NULL, deadline INTEGER NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('pending','done','cancelled')),
                last_attempt INTEGER);
            CREATE TABLE IF NOT EXISTS audit(
                seq INTEGER PRIMARY KEY, at INTEGER NOT NULL,
                kind TEXT NOT NULL, payload TEXT NOT NULL);
        """)
        row = self.db.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
        if row is not None and row[0] != '1':
            self.db.close()
            raise ValueError("unsupported database schema")
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO metadata VALUES ('schema_version','1')")

    def close(self) -> None:
        self.db.close()

    def state(self) -> ContinuousState:
        row = self.db.execute("SELECT value FROM metadata WHERE key='state'").fetchone()
        return ContinuousState(**json.loads(row[0])) if row else ContinuousState()

    def _save_state(self, state: ContinuousState) -> None:
        self.db.execute("INSERT OR REPLACE INTO metadata VALUES ('state', ?)",
                        (json.dumps(asdict(state), sort_keys=True),))

    def ingest(self, event: Event) -> bool:
        """Duplicate delivery is a no-op; conflicting IDs and late events fail closed."""
        payload = json.dumps(asdict(event), sort_keys=True)
        with self.db:
            old = self.db.execute("SELECT payload FROM events WHERE id=?", (event.id,)).fetchone()
            if old:
                if old[0] != payload:
                    raise ValueError("conflicting event ID")
                return False
            state = self.state()
            state.advance(event.at)
            if event.kind == "goal":
                if event.ready > event.deadline:
                    raise ValueError("estimate exceeds deadline")
                self.db.execute("INSERT INTO tasks VALUES (?,?,?,'pending',NULL)",
                                (event.key, event.ready, event.deadline))
            elif event.kind == "cancel":
                self.db.execute("UPDATE tasks SET status='cancelled' WHERE id=? AND status='pending'",
                                (event.key,))
            elif event.kind == "fact":
                self.db.execute("INSERT OR REPLACE INTO facts VALUES (?,?,?,?)",
                                (event.key, event.value, event.at, event.expires))
            else:
                raise ValueError(f"unknown event kind: {event.kind}")
            state.observe(event.at, 1.0 if event.kind == "goal" else 0.1)
            self.db.execute("INSERT INTO events VALUES (?,?,?)", (event.id, event.at, payload))
            self._save_state(state)
        return True

    def recall(self, key: str, at: int) -> tuple[str | None, float]:
        row = self.db.execute("SELECT * FROM facts WHERE key=?", (key,)).fetchone()
        if not row or at < row['observed'] or (row['expires'] is not None and at >= row['expires']):
            return None, 0.0
        return row['value'], math.exp(-0.02 * (at - row['observed']))

    def pending(self, at: int) -> list[sqlite3.Row]:
        return self.db.execute("SELECT * FROM tasks WHERE status='pending' AND deadline>=? ORDER BY deadline,id",
                               (at,)).fetchall()

    def log(self, at: int, kind: str, payload: dict) -> None:
        with self.db:
            state = self.state()
            state.advance(at)
            self._save_state(state)
            self.db.execute("INSERT INTO audit(at,kind,payload) VALUES (?,?,?)",
                            (at, kind, json.dumps(payload, sort_keys=True)))

    def attempt(self, task: str, at: int, success: bool) -> None:
        with self.db:
            state = self.state()
            state.advance(at)
            row = self.db.execute("SELECT status FROM tasks WHERE id=?", (task,)).fetchone()
            if not row or row[0] != 'pending':
                raise ValueError("task is not pending")
            self._save_state(state)
            self.db.execute("UPDATE tasks SET last_attempt=?, status=? WHERE id=?",
                            (at, 'done' if success else 'pending', task))
            self.db.execute("INSERT INTO audit(at,kind,payload) VALUES (?,'action',?)",
                            (at, json.dumps({'task': task, 'success': success}, sort_keys=True)))

    def checkpoint(self, at: int) -> ContinuousState:
        state = self.state()
        state.advance(at)
        with self.db:
            self._save_state(state)
        return state
