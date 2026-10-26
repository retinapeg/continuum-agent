"""Opt-in Claude CLI validation on public policy states; no tool effects.

This small fixed-context pilot validates the provider and trigger proposals. It
does not estimate a live scheduler's prediction advantage. A call is a CLI
invocation; internal provider retries and subscription charges are not observed.
"""
from __future__ import annotations

import argparse
from itertools import islice
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time

from continuum.runtime.common import ROOT, canonical, confined, digest, redact, uid, utc
from continuum.runtime.contracts import PROPOSAL, validate
from continuum.runtime.database import Database
from continuum.runtime.providers import CLIProvider, ProviderError


REQUIRED_FLAGS = ('--safe-mode', '--tools', '--strict-mcp-config', '--mcp-config',
                  '--disable-slash-commands', '--no-session-persistence', '--no-chrome',
                  '--permission-mode', '--setting-sources', '--settings', '--output-format',
                  '--verbose', '--include-partial-messages', '--json-schema', '--system-prompt', '--model')


def probe_cli() -> dict:
    """Inspect installed version/help only. Never authenticate or invoke a model."""
    binary = shutil.which('claude')
    receipt = {'kind': 'claude-cli-compatibility', 'utc': utc(), 'inference_calls': 0,
               'authentication_checked': False, 'installed': bool(binary), 'commands': [],
               'live_compatibility': 'unverified: no model inference performed'}
    if not binary:
        return {**receipt, 'status': 'unavailable'}
    env = {key: value for key, value in os.environ.items()
           if key in ('PATH', 'HOME', 'USER', 'LOGNAME', 'SHELL', 'LANG', 'LC_ALL')}
    env.update(DISABLE_AUTOUPDATER='1', DISABLE_NONESSENTIAL_TRAFFIC='1')
    outputs = {}
    for flag in ('--version', '--help'):
        try:
            result = subprocess.run([binary, flag], cwd=ROOT, env=env, capture_output=True,
                                    text=True, timeout=10, check=False)
            outputs[flag] = result.stdout
            receipt['commands'].append({'argv': ['claude', flag], 'exit_code': result.returncode,
                                        'stdout_sha256': digest(result.stdout.encode()),
                                        'stderr': redact(result.stderr[:500])})
            if result.returncode:
                return {**receipt, 'status': 'probe-failed'}
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {**receipt, 'status': 'probe-failed', 'error': type(exc).__name__}
    missing = [flag for flag in REQUIRED_FLAGS if flag not in outputs['--help']]
    return {**receipt, 'version': outputs['--version'].strip(), 'missing_flags': missing,
            'status': 'flags-compatible' if not missing else 'incompatible-flags'}


def public_input(value: dict) -> dict:
    """Only the policy interface can cross the provider boundary, never a world."""
    def exact(data, names):
        if not isinstance(data, dict) or set(data) != set(names):
            raise ValueError('exact public context fields required; world/config fields are forbidden')
    def number(value, optional=False):
        if value is None and optional:
            return
        if type(value) not in (float, int) or not math.isfinite(value):
            raise ValueError('finite numeric public state required')
    exact(value, ('at', 'belief', 'latest_observation', 'budget', 'public_events'))
    data = json.loads(canonical(value))
    number(data['at'])
    exact(data['belief'], ('x', 'v', 'std', 'variance', 'at', 'last_observation', 'innovation'))
    for key, value in data['belief'].items():
        number(value, optional=key in ('last_observation', 'innovation'))
    exact(data['budget'], ('observations_remaining', 'inferences_remaining', 'actions_remaining'))
    if any(type(value) is not int or value < 0 for value in data['budget'].values()):
        raise ValueError('nonnegative integer remaining budgets required')
    observation = data['latest_observation']
    if observation is not None:
        exact(observation, ('time', 'measured_at', 'value', 'noise_std', 'id', 'status'))
        for key in ('time', 'measured_at', 'value', 'noise_std'):
            number(observation[key])
        if any(not isinstance(observation[key], str) or len(observation[key]) > 200 for key in ('id', 'status')):
            raise ValueError('bounded observation ID/status required')
    if not isinstance(data['public_events'], list) or len(data['public_events']) > 30:
        raise ValueError('bounded public events required')
    for event in data['public_events']:
        exact(event, ('at', 'kind'))
        number(event['at'])
        if not isinstance(event['kind'], str) or len(event['kind']) > 200:
            raise ValueError('bounded public event kind required')
    return data


def _new_directory(directory: Path) -> Path:
    directory = Path(directory)
    if directory.is_absolute():
        try:
            directory = directory.relative_to(ROOT)
        except ValueError:
            raise ValueError('pilot output must stay inside this repository') from None
    target = confined(ROOT, str(directory))
    target.mkdir(parents=True, exist_ok=False)
    return target


def run_pilot(directory: Path, public_contexts, *, opt_in=False,
              model='claude-haiku-4-5-20251001', max_calls=3,
              deadline_seconds=90, call_timeout=25) -> dict:
    """Validate at most six independent public prefixes; preserve every attempt.

    Explicit opt-in is checked before creating files, checking authentication or
    constructing the provider. New directory only; failed trials are not retried.
    The wall deadline signals cancellation; provider process cleanup has its
    existing bounded grace. No candidate tools/actions are ever executed.
    """
    if opt_in is not True:
        raise PermissionError('live Claude inference requires explicit opt_in=True / --opt-in')
    if (type(max_calls) is not int or not 1 <= max_calls <= 6
            or type(deadline_seconds) not in (float, int) or not math.isfinite(deadline_seconds)
            or not 15 <= deadline_seconds <= 180
            or type(call_timeout) not in (float, int) or not math.isfinite(call_timeout)
            or not 5 <= call_timeout <= 60):
        raise ValueError('pilot limits: 1–6 calls, 15–180 seconds total, 5–60 seconds per inference')
    contexts = [public_input(item) for item in islice(public_contexts, max_calls)]
    if not contexts:
        raise ValueError('at least one public policy state required')
    target = _new_directory(directory)
    manifest = {'kind': 'fixed-public-context-live-trigger-validation', 'utc': utc(),
                'mode': 'live-Claude', 'requested_model': model, 'opt_in': True,
                'limits': {'max_calls': max_calls, 'deadline_seconds': deadline_seconds,
                           'call_timeout': call_timeout}, 'public_contexts': contexts,
                'scope': 'next_delay proposals only; no performance comparison or tool effects',
                'api_fallback': False, 'actual_subscription_charge': None}
    (target / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    db = Database(target / 'pilot.sqlite', policy='live-trigger-validation')
    provider = CLIProvider('claude', model, target / 'provider', timeout=call_timeout,
                           max_bytes=1_000_000, max_output_tokens=1000)
    cancel = threading.Event()
    timer = threading.Timer(deadline_seconds, cancel.set)
    timer.daemon = True
    started = time.monotonic()
    timer.start()
    attempts = []
    report = {}
    try:
        for index, state in enumerate(contexts):
            remaining = deadline_seconds - (time.monotonic() - started)
            # Original auth probe has a 15-second bound. Do not start a call
            # without that allowance; the overall timer also cancels slot waits.
            if cancel.is_set() or remaining < 15:
                break
            provider.timeout = min(call_timeout, remaining)
            context = {'experiment_task': (
                'You are validating an observation scheduler for a damped oscillator. '
                'Only the supplied public policy state is available. Recommend the next '
                'observation delay in simulated seconds using next_delay. Return a short '
                'decision summary; leave actions, memory_updates, goal_updates empty and '
                'message.text empty. Do not estimate hidden truth or claim completed work. '
                'State estimation uses a shared classical Kalman filter.'), 'policy_input': state}
            call_id = uid()
            call_started = time.monotonic()
            db.db.execute('INSERT INTO calls VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                          (call_id, 'claude', model, None, 'running', digest(context),
                           None, None, None, None, state['at']))
            db.event('live.call.started', {'call_id': call_id, 'context': context},
                     status='running', provider='claude', requested=model)
            receipt = None
            row = {'index': index, 'call_id': call_id, 'at': state['at'], 'input_hash': digest(context),
                   'requested_model': model, 'status': 'running', 'next_delay': None,
                   'provider_status': 'running', 'known_unsent': False, 'error': None}
            try:
                receipt = provider.propose(context, cancel, lambda event: db.event(
                    'live.provider.progress', event, provider='claude', requested=model, status='running'))
                row['provider_status'] = 'succeeded'
                row.update(proposal=redact(receipt.proposal), output_hash=digest(receipt.proposal))
                validate(PROPOSAL, receipt.proposal)
                proposal = receipt.proposal
                if proposal['actions'] or proposal['memory_updates'] or proposal['goal_updates'] or proposal['message']['text']:
                    raise ValueError('trigger validation accepts only a summary and next_delay; no actions or messages')
                if cancel.is_set():
                    raise ProviderError('pilot wall deadline reached', status='cancelled')
                row.update(status='succeeded', next_delay=proposal['next_delay'],
                           proposal=redact(proposal), output_hash=digest(proposal))
            except Exception as exc:
                if receipt is None:
                    receipt = exc
                    row['provider_status'] = exc.status if isinstance(exc, ProviderError) else 'failed'
                row.update(status=exc.status if isinstance(exc, ProviderError) else 'failed',
                           known_unsent=getattr(exc, 'known_unsent', False), error=redact(str(exc))[:800])
            finally:
                row.update(elapsed=time.monotonic() - call_started,
                           reported_model=getattr(receipt, 'reported_model', None),
                           usage=getattr(receipt, 'usage', None),
                           provider_elapsed=getattr(receipt, 'elapsed', None),
                           output_bytes=getattr(receipt, 'output_bytes', None),
                           terminal_subtype=getattr(receipt, 'terminal_subtype', None))
                # Preserve an interrupted attempt even if KeyboardInterrupt escapes.
                if row['status'] == 'running':
                    row.update(status='outcome-unknown', provider_status='outcome-unknown',
                               error='pilot interrupted before terminal receipt')
                # Authentication/slot/input failures can precede a CLI process.
                # The reused adapter attaches elapsed/output telemetry only after
                # spawning its inference process. Missing evidence stays unknown.
                row['cli_invocation_recorded'] = not row['known_unsent'] and (
                    row['provider_status'] == 'succeeded' or row['provider_elapsed'] is not None
                    or row['output_bytes'] is not None)
                with db.transaction() as tx:
                    tx.execute('UPDATE calls SET status=?,reported_model=?,output_hash=?,usage=?,error=?,elapsed=? WHERE id=?',
                               (row['status'], row['reported_model'], row.get('output_hash'),
                                canonical(row['usage']) if row['usage'] is not None else None,
                                row['error'], row['elapsed'], call_id))
                    db.event('live.call.receipt', row, provider='claude', requested=model,
                             reported=row['reported_model'], status=row['status'], tx=tx)
                attempts.append(row)
                with (target / 'attempts.jsonl').open('a') as handle:
                    handle.write(canonical(row) + '\n')
                    handle.flush()
                    os.fsync(handle.fileno())
            if row['status'] in ('outcome-unknown', 'cancelled'):
                break
    finally:
        timer.cancel()
        report = {'kind': manifest['kind'], 'mode': 'live-Claude', 'requested_model': model,
                  'attempted_calls': len(attempts), 'successful_calls': sum(row['status'] == 'succeeded' for row in attempts),
                  'failed_calls': sum(row['status'] != 'succeeded' for row in attempts),
                  'known_unsent_attempts': sum(row['known_unsent'] for row in attempts),
                  'confirmed_cli_invocations': sum(row['cli_invocation_recorded'] for row in attempts),
                  'successful_cli_invocations': sum(row['cli_invocation_recorded'] and row['provider_status'] == 'succeeded' for row in attempts),
                  'invocation_count_unknown': sum(not row['known_unsent'] and not row['cli_invocation_recorded'] for row in attempts),
                  'unattempted_contexts': len(contexts) - len(attempts),
                  'elapsed_seconds': time.monotonic() - started, 'attempts': attempts,
                  'performance_claim': None, 'actual_subscription_charge': None,
                  'scope': manifest['scope'], 'complete': len(attempts) == len(contexts)}
        (target / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        db.close()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('probe', help='only inspect installed CLI version/help; no authentication or inference')
    pilot = commands.add_parser('pilot', help='bounded live validation; requires explicit opt-in')
    pilot.add_argument('--directory', type=Path, required=True)
    pilot.add_argument('--contexts', type=Path, required=True, help='JSON array of frozen public development contexts')
    pilot.add_argument('--opt-in', action='store_true')
    pilot.add_argument('--model', default='claude-haiku-4-5-20251001')
    pilot.add_argument('--max-calls', type=int, default=3)
    pilot.add_argument('--deadline-seconds', type=float, default=90)
    args = parser.parse_args()
    if args.command == 'probe':
        result = probe_cli()
    else:
        if not args.opt_in:
            parser.error('live inference requires --opt-in')
        source = args.contexts.resolve()
        if not source.is_relative_to(ROOT):
            parser.error('contexts must be inside this repository')
        result = run_pilot(args.directory, json.loads(source.read_text()), opt_in=args.opt_in,
                           model=args.model, max_calls=args.max_calls, deadline_seconds=args.deadline_seconds)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
