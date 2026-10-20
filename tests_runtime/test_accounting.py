"""Terminal-error and discarded-response accounting; no network/model requests."""
import hashlib
import json
import sys
import threading
from unittest.mock import patch

from test_core import Base
from continuum.runtime.common import canonical
from continuum.runtime.contracts import empty_proposal
from continuum.runtime.providers import CLIProvider, FixtureProvider, ProviderError, Response
from continuum.research.campaign import Budget, _run_campaign, source_manifest


class TerminalAccountingTests(Base):
    def fake_cli(self, terminal):
        provider = CLIProvider('claude', 'test-model', self.path / 'provider')
        events = [
            {'type': 'system', 'subtype': 'init', 'model': 'test-model', 'tools': ['StructuredOutput']},
            {'type': 'assistant', 'message': {'model': 'test-model', 'content': []}},
            {'type': 'result', 'is_error': True, 'subtype': 'error_max_structured_output_retries',
             'errors': ['Controlled fixture failure'], **terminal},
        ]
        output = '\n'.join(json.dumps(e) for e in events) + '\n'
        with patch.object(provider, 'command', return_value=[sys.executable, '-c', f'print({output!r})']):
            with self.assertRaises(ProviderError) as caught:
                provider._propose({}, threading.Event(), lambda event: None)
        return caught.exception

    def test_error_usage_aggregates_auxiliary_once(self):
        err = self.fake_cli({
            'usage': {'input_tokens': 10, 'output_tokens': 20, 'cache_read_input_tokens': 3, 'cache_creation_input_tokens': 4},
            'modelUsage': {
                'test-model': {'inputTokens': 10, 'outputTokens': 20, 'cacheReadInputTokens': 3, 'cacheCreationInputTokens': 4, 'costUSD': .02},
                'auxiliary': {'inputTokens': 2, 'outputTokens': 5, 'cacheReadInputTokens': 0, 'cacheCreationInputTokens': 0, 'costUSD': .01},
            }, 'total_cost_usd': .03, 'num_turns': 5, 'duration_api_ms': 200,
        })
        self.assertEqual(err.status, 'failed')
        self.assertEqual(err.reported_model, 'test-model')
        self.assertEqual(err.usage['uncached_input'], 12)
        self.assertEqual(err.usage['output'], 25)
        self.assertEqual(err.usage['primary_usage']['output'], 20)
        self.assertAlmostEqual(err.usage['api_equivalent_usd'], .03)
        self.assertEqual(err.usage['cli_num_turns'], 5)
        self.assertIsNone(err.usage['charge'])
        self.assertGreater(err.output_bytes, 0)
        self.assertGreaterEqual(err.elapsed, 0)
        self.assertEqual(err.terminal_subtype, 'error_max_structured_output_retries')

    def test_error_aggregate_without_primary_usage(self):
        err = self.fake_cli({'modelUsage': {'test-model': {
            'inputTokens': 2, 'outputTokens': 3, 'cacheReadInputTokens': 4, 'cacheCreationInputTokens': 5, 'costUSD': .01}}})
        self.assertEqual(err.usage['output'], 3)
        self.assertIsNone(err.usage['primary_usage']['output'])

    def test_missing_telemetry_unknown_and_terminal_cost_fallback(self):
        self.assertIsNone(self.fake_cli({}).usage)
        err = self.fake_cli({'total_cost_usd': .05})
        self.assertEqual(err.usage['api_equivalent_usd'], .05)
        self.assertIsNone(err.usage['output'])
        self.assertEqual(err.usage['estimate_source'], 'total_cost_usd')

    def test_failed_runtime_call_persists_available_receipt(self):
        class Failed(FixtureProvider):
            def propose(inner, *args):
                raise ProviderError('Controlled failure', usage={'output': 7, 'api_equivalent_usd': .02},
                                    reported_model='test-model', elapsed=.25, output_bytes=500,
                                    terminal_subtype='error_max_structured_output_retries')
        runtime = self.runtime(Failed()); runtime.goal('Goal'); runtime.tick()
        call = runtime.db.rows('SELECT * FROM calls')[0]
        self.assertEqual(call['status'], 'failed')
        self.assertEqual(json.loads(call['usage'])['output'], 7)
        self.assertEqual(call['reported_model'], 'test-model')
        self.assertEqual(call['elapsed'], .25)
        self.assertEqual(runtime.db.rows('SELECT * FROM operations'), [])
        receipt = runtime.db.rows("SELECT data FROM events WHERE kind='provider.receipt'")[0]
        self.assertEqual(json.loads(receipt['data'])['payload']['output_bytes'], 500)

    def test_pause_discards_proposal_but_keeps_accounting(self):
        class Paused(FixtureProvider):
            def propose(inner, *args):
                runtime.control('paused')
                proposal = empty_proposal('DO_NOT_RETAIN_DISCARDED_CONTENT')
                return Response(proposal, inner.model, {'output': 9}, .5, 120)
        runtime = self.runtime(Paused()); runtime.goal('Goal'); runtime.tick()
        call = runtime.db.rows('SELECT * FROM calls')[0]
        self.assertEqual(call['status'], 'cancelled')
        self.assertEqual(json.loads(call['usage'])['output'], 9)
        self.assertEqual(call['elapsed'], .5)
        self.assertIsNone(runtime.db.get('pending_proposal'))
        self.assertNotIn('DO_NOT_RETAIN_DISCARDED_CONTENT', '\n'.join(runtime.db.db.iterdump()))
        self.assertEqual(runtime.db.rows('SELECT * FROM operations'), [])

    def test_invalid_proposal_keeps_accounting_without_effect(self):
        class Invalid(FixtureProvider):
            def propose(inner, *args):
                return Response({'invalid': True}, inner.model, {'output': 11}, .6, 100)
        runtime = self.runtime(Invalid()); runtime.goal('Goal'); runtime.tick()
        call = runtime.db.rows('SELECT * FROM calls')[0]
        self.assertEqual(call['status'], 'failed')
        self.assertEqual(json.loads(call['usage'])['output'], 11)
        self.assertEqual(runtime.db.rows('SELECT * FROM operations'), [])


class CompletedResumeTests(Base):
    def campaign(self, completed):
        directory = self.path / 'campaign'; directory.mkdir()
        unit = {'id': 'fixture-1', 'family': 'delayed_dependencies', 'scenario': 'fixture-1',
                'seed': 1, 'repetition': 0, 'condition': 'D', 'budget': 2}
        protocol = {'units': [unit], 'source_manifest': source_manifest(),
                    'limits': {'provider_calls': 5, 'campaign_seconds': 10, 'concurrency': 1}}
        raw = canonical(protocol).encode()
        (directory / 'protocol.json').write_bytes(raw)
        (directory / 'protocol.sha256').write_text(hashlib.sha256(raw).hexdigest())
        budget = Budget(directory, 5)
        with budget.connect() as db:
            result = canonical({**unit, 'goal_completion': 0, 'valid_execution': 0}) if completed else None
            db.execute('INSERT INTO units VALUES (?,?,?,NULL)', (unit['id'], 'succeeded' if completed else 'queued', result))
        return directory

    def test_completed_resume_with_source_drift_makes_no_calls(self):
        directory = self.campaign(True)
        with patch('continuum.research.campaign.source_manifest', return_value={'changed': 'hash'}), \
             patch('continuum.research.campaign.execute') as execute:
            self.assertEqual(_run_campaign(directory, resume=True)['attempted_episodes'], 1)
            execute.assert_not_called()
        with Budget(directory, 5).connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM calls').fetchone()[0], 0)

    def test_unfinished_resume_rejects_source_drift(self):
        directory = self.campaign(False)
        with patch('continuum.research.campaign.source_manifest', return_value={'changed': 'hash'}), \
             patch('continuum.research.campaign.execute') as execute:
            with self.assertRaisesRegex(ValueError, 'source changed'):
                _run_campaign(directory, resume=True)
            execute.assert_not_called()

    def test_completed_resume_still_rejects_protocol_tampering(self):
        directory = self.campaign(True)
        with (directory / 'protocol.json').open('a') as file:
            file.write(' ')
        with self.assertRaisesRegex(ValueError, 'protocol tampered'):
            _run_campaign(directory, resume=True)
