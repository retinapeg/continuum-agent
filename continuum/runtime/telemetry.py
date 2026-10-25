"""Content-free accounting for provider attempts, separate from proposal effects.

One attempt is one Provider.propose invocation (including a known-unsent failure).
Opaque retries inside a provider CLI are not separately observable attempts.
"""
from collections import Counter
import json
import math
import re
import time
from .common import canonical, redact, uid, utc
from .contracts import PROPOSAL, validate
from .providers import ProviderError

TOKENS = ('uncached_input', 'cached_read', 'cache_creation', 'output', 'other')
FAILURES = frozenset(('provider_error', 'timeout', 'cancelled', 'output_limit',
                      'malformed_response', 'tool_isolation', 'model_mismatch',
                      'cli_exit', 'authentication', 'unavailable', 'input_limit',
                      'quota', 'process_restart', 'proposal_rejected', 'application_error'))
TERMINAL_SUBTYPES = ('success', 'error_during_execution', 'error_max_turns',
                     'error_max_budget_usd', 'error_max_structured_output_retries')


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def identifier(value):
    if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_.:/-]{1,160}', value):
        return redact(value)
    return None


def safe_usage(raw):
    """Allow only measured numbers and recognized metadata; never arbitrary text."""
    if not isinstance(raw, dict):
        return None
    result = {key: raw[key] if number(raw.get(key)) else None
              for key in (*TOKENS, 'api_equivalent_usd', 'charge', 'terminal_cost_usd_reported',
                          'cli_num_turns', 'cli_duration_api_ms', 'calculation_version') if key in raw}
    for key, allowed in {
        'source': ('final_result_usage', 'turn.completed.usage', 'modelUsage_aggregate'),
        'estimate_source': ('modelUsage', 'total_cost_usd'),
        'currency': ('USD',), 'estimate_currency': ('USD',),
    }.items():
        if key in raw:
            result[key] = raw[key] if raw[key] in allowed else None
    result['charge'] = result.get('charge')
    result['charge_reason'] = 'subscription invoice not observed' if result['charge'] is None else None
    result['rate_date'] = None
    if isinstance(raw.get('primary_usage'), dict):
        result['primary_usage'] = {k: v if number(v) else None
                                   for k, v in raw['primary_usage'].items() if k in TOKENS}
    if isinstance(raw.get('per_model_reported'), dict):
        keys = ('inputTokens', 'outputTokens', 'cacheReadInputTokens', 'cacheCreationInputTokens', 'costUSD')
        result['per_model_reported'] = {
            identifier(model): {k: row.get(k) if number(row.get(k)) else None for k in keys}
            for model, row in raw['per_model_reported'].items()
            if identifier(model) and isinstance(row, dict)}
    return result


def failure_code(exc):
    code = getattr(exc, 'failure_code', None)
    if code in FAILURES:
        return code
    return 'provider_error'


def safe_progress(event):
    kind = event.get('type')
    if kind not in ('provider.initialized', 'provider.delta', 'provider.proposal',
                    'provider.cleanup_warning', 'fixture.completed', 'routing.selected', 'routing.known_unsent'):
        return {'type': 'provider.progress'}
    result = {'type': kind}
    for key in ('received_chars', 'attempt_index'):
        if number(event.get(key)):
            result[key] = event[key]
    if kind == 'provider.initialized':
        result['model'] = identifier(event.get('model'))
    if kind == 'provider.cleanup_warning':
        result['descendant_cleanup_verified'] = False
    if kind == 'routing.selected':
        result['chosen'] = {k: identifier(event.get('chosen', {}).get(k)) for k in ('provider', 'model')}
        result['fallback'] = event.get('fallback') is True
    if kind == 'routing.known_unsent':
        code = event.get('failure_code')
        result['failure_code'] = code if code in FAILURES else 'provider_error'
    return result


def initialize(db):
    """Atomic, additive migration; preserve the schema-2 calls table byte-for-byte."""
    if db.get('attempt_schema') not in (None, 1):
        raise ValueError('unsupported attempt schema')
    with db.transaction() as tx:
        tx.execute('''CREATE TABLE IF NOT EXISTS provider_attempts(
          id TEXT PRIMARY KEY, call_id TEXT NOT NULL REFERENCES calls(id), trace_id TEXT NOT NULL,
          attempt_index INTEGER NOT NULL, retry_of TEXT REFERENCES provider_attempts(id),
          provider TEXT NOT NULL, requested_model TEXT, reported_model TEXT,
          status TEXT NOT NULL, failure_code TEXT, known_unsent INTEGER,
          usage TEXT, elapsed REAL, output_bytes INTEGER, terminal_subtype TEXT,
          started_at TEXT NOT NULL, finished_at TEXT, UNIQUE(call_id,attempt_index))''')
        db.set('attempt_schema', 1, tx)


class AttemptLedger:
    def __init__(self, db):
        self.db = db

    def start(self, call_id, trace, provider):
        attempt_id = uid()
        with self.db.transaction() as tx:
            previous = tx.execute('SELECT id,attempt_index FROM provider_attempts WHERE call_id=? '
                                  'ORDER BY attempt_index DESC LIMIT 1', (call_id,)).fetchone()
            index = previous['attempt_index'] + 1 if previous else 0
            retry_of = previous['id'] if previous else None
            tx.execute('INSERT INTO provider_attempts '
                       '(id,call_id,trace_id,attempt_index,retry_of,provider,requested_model,status,started_at) '
                       "VALUES (?,?,?,?,?,?,?,'running',?)",
                       (attempt_id, call_id, trace, index, retry_of, identifier(provider.name) or 'unknown',
                        identifier(provider.model), utc()))
            self.db.event('attempt.started', {'call_id': call_id, 'retry_of': retry_of, 'attempt_index': index},
                          trace=trace, attempt=attempt_id, provider=identifier(provider.name),
                          requested=identifier(provider.model), status='running', tx=tx)
        return attempt_id

    def finish(self, attempt_id, receipt=None, *, status='succeeded', code=None, known_unsent=False):
        usage = safe_usage(getattr(receipt, 'usage', None))
        elapsed, output = getattr(receipt, 'elapsed', None), getattr(receipt, 'output_bytes', None)
        subtype = getattr(receipt, 'terminal_subtype', None)
        subtype = subtype if subtype in TERMINAL_SUBTYPES else None
        with self.db.transaction() as tx:
            row = tx.execute('SELECT * FROM provider_attempts WHERE id=?', (attempt_id,)).fetchone()
            if row is None:
                raise ValueError('unknown attempt')
            if row['status'] != 'running':
                return  # A replayed receipt cannot overwrite or add to a finalized attempt.
            tx.execute('UPDATE provider_attempts SET status=?,failure_code=?,known_unsent=?,usage=?, '
                       'reported_model=?,elapsed=?,output_bytes=?,terminal_subtype=?,finished_at=? WHERE id=?',
                       (status, code, int(known_unsent), canonical(usage) if usage is not None else None,
                        identifier(getattr(receipt, 'reported_model', None)), elapsed if number(elapsed) else None,
                        output if number(output) else None, subtype, utc(), attempt_id))
            self.db.event('attempt.finished', {'call_id': row['call_id'], 'failure_code': code,
                          'known_unsent': known_unsent}, trace=row['trace_id'], attempt=attempt_id,
                          provider=row['provider'], requested=row['requested_model'],
                          reported=identifier(getattr(receipt, 'reported_model', None)), status=status, tx=tx)

    def invoke(self, call_id, trace, provider, context, cancel, progress):
        attempt_id = self.start(call_id, trace, provider)
        start = time.monotonic()
        response = None
        try:
            response = provider.propose(context, cancel, lambda event: progress(event, attempt_id, provider))
            try:
                validate(PROPOSAL, response.proposal)
            except Exception as exc:
                raise ProviderError('invalid structured proposal', failure_code='malformed_response') from exc
        except Exception as exc:
            receipt = response or exc
            if getattr(receipt, 'elapsed', None) is None:
                receipt.elapsed = time.monotonic() - start
            self.finish(attempt_id, receipt, status=getattr(exc, 'status', 'failed'),
                        code=failure_code(exc), known_unsent=getattr(exc, 'known_unsent', False))
            # Retain usage on schema rejection for the compatible logical-call receipt too.
            if response is not None and isinstance(exc, ProviderError):
                exc.usage, exc.reported_model, exc.elapsed = response.usage, response.reported_model, response.elapsed
                exc.output_bytes = response.output_bytes
            raise
        self.finish(attempt_id, response)
        return response


def summarize(db):
    """Read unique attempt rows, never sum event receipts or logical calls again."""
    rows = db.rows('SELECT * FROM provider_attempts')
    legacy = db.rows('SELECT COUNT(*) AS n FROM calls c WHERE NOT EXISTS '
                     '(SELECT 1 FROM provider_attempts a WHERE a.call_id=c.id)')[0]['n']
    usage = [json.loads(r['usage']) if r['usage'] else {} for r in rows]
    categories = {}
    for key in (*TOKENS, 'api_equivalent_usd'):
        values = [u[key] for u in usage if number(u.get(key))]
        categories[key] = {'known_subtotal': sum(values) if values else None,
                           'attempts_with_value': len(values),
                           'complete_total': sum(values) if rows and len(values) == len(rows) and not legacy else None}
    return {'scope': 'Provider.propose attempts; opaque CLI internal retries are not enumerated',
            'attempts': len(rows), 'retries': sum(r['retry_of'] is not None for r in rows),
            'known_unsent': sum(r['known_unsent'] == 1 for r in rows),
            'statuses': dict(Counter(r['status'] for r in rows)),
            'failure_codes': dict(Counter(r['failure_code'] for r in rows if r['failure_code'])),
            'legacy_calls_without_attempts': legacy, 'categories': categories,
            'subscription_charge': None}
