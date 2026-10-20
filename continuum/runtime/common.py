from __future__ import annotations
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import time
import uuid
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
STATES = ('queued', 'running', 'waiting-for-input', 'waiting-for-approval',
          'succeeded', 'failed', 'cancelled', 'outcome-unknown')


def utc(ts: float | None = None) -> str:
    return datetime.fromtimestamp(time.time() if ts is None else ts, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def uid() -> str:
    return str(uuid.uuid4())


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value) -> str:
    return hashlib.sha256((value if isinstance(value, bytes) else canonical(value).encode())).hexdigest()


def redact(value):
    if isinstance(value, dict):
        return {k: ('[REDACTED]' if re.search(r'(password|api.?key|authorization|secret|access.token)', k, re.I)
                    else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r'(?i)Bearer\s+\S+', 'Bearer [REDACTED]', value)
        value = re.sub(r'\b(?:sk-[A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9]{15,})\b', '[REDACTED]', value)
        value = re.sub(r'(?i)((?:api[_-]?key|password|secret)\s*[:=]\s*)\S+', r'\1[REDACTED]', value)
    return value


def confined(base: Path, relative: str, *, exists=False) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError('relative path required')
    base = base.resolve()
    parts = Path(relative).parts
    if any(p in ('..', '.') for p in parts):
        raise ValueError('path traversal denied')
    candidate = base
    for part in parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise ValueError('symlinks denied')
    resolved = candidate.resolve()
    if not resolved.is_relative_to(base) or (exists and not resolved.is_file()):
        raise ValueError('outside approved scope or absent file')
    return resolved


class FileLock:
    """OS lock ownership, not PID guessing. A stale file does not imply ownership."""
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.file = path.open('a+')
        try:
            fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.file.close()
            raise RuntimeError('another owner holds this lock') from None
        self.file.seek(0)
        self.file.truncate()
        self.file.write(canonical({'pid': os.getpid(), 'owner': uid(), 'at': utc()}))
        self.file.flush()

    def close(self):
        fcntl.flock(self.file, fcntl.LOCK_UN)
        self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class WallClock:
    """Elapsed time is monotonic; restart gaps clamp to [0, one day]."""
    def __init__(self, previous: float | None = None):
        wall = time.time()
        self.gap = 0 if previous is None else min(86400, max(0, wall - previous))
        self.start = wall if previous is None else previous + self.gap
        self.origin = time.monotonic()

    def now(self) -> float:
        return self.start + time.monotonic() - self.origin


class SimClock:
    def __init__(self, at=0.0):
        self.at = float(at)

    def now(self):
        return self.at

    def advance(self, at):
        if at < self.at:
            raise ValueError('clock reversal')
        self.at = float(at)
