"""Offline accounting invariants; CLI processes below are local Python fixtures."""
import json
import sqlite3
import sys
import threading
from unittest.mock import patch

from test_core import Base
from continuum.runtime.contracts import empty_proposal
from continuum.runtime.database import Database
from continuum.runtime.engine import Runtime
from continuum.runtime.providers import CLIProvider, FixtureProvider, ProviderError, Response, claude_result_usage
from continuum.runtime.routing import RoutedProvider
from continuum.runtime.telemetry import initialize, safe_usage, summarize


class PaidReceipt(FixtureProvider):
    def propose(self, context, cancel, progress):
        progress({'type': 'provider.delta', 'received_chars': 10})
        return Response(empty_proposal(), self.model, {'output': 7, 'api_equivalent_usd': .02}, .25, 100)


class TelemetryTests(Base):
    def attempts(self, runtime):
        return runtime.db.rows('SELECT * FROM provider_attempts ORDER BY attempt_index')

    def router(self, first, second):
        config = {'allow_known_unsent_fallback': True, 'models': [
            {'provider': 'claude', 'model': name, 'task_classes': ['conversation'],
             'measured_attempts': 10, 'measured_valid_responses': successes, 'live_verified': True}
            for name, successes in [('first-model', 10), ('second-model', 8)]]}
        router = RoutedProvider(config, self.path / 'router')
        first.name = second.name = 'claude'
        first.model, second.model = 'first-model', 'second-model'
        router.providers = {('claude', 'first-model'): first, ('claude', 'second-model'): second}
        return router

    def test_success_identity_usage_and_duplicate_receipt(self):
        r = self.runtime(PaidReceipt(), schedule=[100]); r.goal('Goal'); r.tick()
        attempt = self.attempts(r)[0]
        self.assertEqual(attempt['status'], 'succeeded')
        self.assertEqual(json.loads(attempt['usage'])['output'], 7)
        self.assertIsNone(attempt['retry_of'])
        self.assertEqual(attempt['elapsed'], .25)
        self.assertEqual(attempt['output_bytes'], 100)
        self.assertEqual(attempt['call_id'], r.db.rows('SELECT id FROM calls')[0]['id'])
        events = [json.loads(row['data']) for row in r.db.rows(
            "SELECT data FROM events WHERE kind IN ('attempt.started','attempt.finished','provider.progress')")]
        self.assertTrue(all(e['attempt_id'] == attempt['id'] and e['trace_id'] == attempt['trace_id'] for e in events))
        before = summarize(r.db)
        r.attempts.finish(attempt['id'], Response(empty_proposal(), 'bad', {'api_equivalent_usd': 99}, 1, 1))
        r.tick()  # Replayed activation must not add a call or an attempt.
        self.assertEqual(summarize(r.db), before)
        self.assertEqual(before['categories']['api_equivalent_usd']['complete_total'], .02)
        self.assertEqual(len(r.db.rows("SELECT * FROM events WHERE kind='attempt.finished'")), 1)

    def test_failure_retains_cost_without_error_text(self):
        class Failed(FixtureProvider):
            def propose(self, *args):
                raise ProviderError('PRIVATE_ERROR_CANARY', usage={'output': 3, 'api_equivalent_usd': .01},
                                    terminal_subtype='error_max_structured_output_retries',
                                    failure_code='malformed_response')
        r = self.runtime(Failed()); r.goal('Goal'); r.tick()
        attempt = self.attempts(r)[0]
        self.assertEqual((attempt['status'], attempt['failure_code']), ('failed', 'malformed_response'))
        self.assertEqual(attempt['terminal_subtype'], 'error_max_structured_output_retries')
        self.assertEqual(summarize(r.db)['categories']['api_equivalent_usd']['complete_total'], .01)
        self.assertNotIn('PRIVATE_ERROR_CANARY', '\n'.join(r.db.db.iterdump()))

    def test_known_unsent_fallback_has_two_linked_attempts(self):
        class Unsent(FixtureProvider):
            def propose(self, *args):
                raise ProviderError('authentication denied', known_unsent=True, failure_code='authentication')
        r = self.runtime(self.router(Unsent(), PaidReceipt())); r.goal('Goal'); r.tick()
        first, second = self.attempts(r)
        self.assertEqual(first['failure_code'], 'authentication')
        self.assertEqual(first['known_unsent'], 1)
        self.assertEqual(second['retry_of'], first['id'])
        self.assertEqual(second['attempt_index'], 1)
        self.assertEqual(first['trace_id'], second['trace_id'])
        self.assertEqual(first['call_id'], second['call_id'])
        self.assertEqual([a['requested_model'] for a in (first, second)], ['first-model', 'second-model'])
        summary = summarize(r.db)
        self.assertEqual((summary['attempts'], summary['retries']), (2, 1))
        cost = summary['categories']['api_equivalent_usd']
        self.assertEqual(cost['known_subtotal'], .02)
        self.assertIsNone(cost['complete_total'])  # Unsent does not invent a zero-cost receipt.
        self.assertEqual(len(r.db.rows('SELECT * FROM calls')), 1)

    def test_ambiguous_failure_never_falls_back(self):
        class Timeout(FixtureProvider):
            def propose(self, *args):
                raise ProviderError('timeout', 'outcome-unknown', failure_code='timeout')
        second = PaidReceipt()
        r = self.runtime(self.router(Timeout(), second)); r.goal('Goal')
        with patch.object(second, 'propose') as fallback:
            r.tick(); self.clock.advance(500); r.tick(); fallback.assert_not_called()
        self.assertEqual(len(self.attempts(r)), 1)
        self.assertEqual(self.attempts(r)[0]['failure_code'], 'timeout')
        self.assertEqual(r.db.get('control'), 'paused')

    def test_exhausted_fallback_preserves_both_errors(self):
        class Unsent(FixtureProvider):
            def propose(self, *args):
                raise ProviderError('unavailable', known_unsent=True, failure_code='unavailable')
        r = self.runtime(self.router(Unsent(), Unsent())); r.goal('Goal'); r.tick()
        summary = summarize(r.db)
        self.assertEqual(summary['statuses'], {'failed': 2})
        self.assertEqual(summary['failure_codes'], {'unavailable': 2})
        self.assertIsNone(summary['categories']['api_equivalent_usd']['known_subtotal'])

    def test_invalid_schema_retains_usage_and_excludes_response_body(self):
        class Invalid(FixtureProvider):
            def propose(self, *args):
                return Response({'invalid': 'PRIVATE_RESPONSE_CANARY'}, self.model, {'output': 11}, .2, 100)
        r = self.runtime(Invalid()); r.goal('Goal'); r.tick()
        self.assertEqual(self.attempts(r)[0]['failure_code'], 'malformed_response')
        self.assertEqual(json.loads(self.attempts(r)[0]['usage'])['output'], 11)
        self.assertNotIn('PRIVATE_RESPONSE_CANARY', '\n'.join(r.db.db.iterdump()))
        self.assertEqual(r.db.rows('SELECT * FROM operations'), [])

    def test_control_discard_is_not_a_provider_failure(self):
        class Paused(PaidReceipt):
            def propose(self, *args):
                r.control('paused')
                return super().propose(*args)
        r = self.runtime(Paused()); r.goal('Goal'); r.tick()
        self.assertEqual(r.db.rows('SELECT status FROM calls')[0]['status'], 'cancelled')
        self.assertEqual(self.attempts(r)[0]['status'], 'succeeded')
        self.assertEqual(summarize(r.db)['categories']['api_equivalent_usd']['complete_total'], .02)
        self.assertEqual(r.db.rows('SELECT * FROM operations'), [])

    def test_application_rejection_is_separate_from_provider_failure(self):
        class Unsupported(PaidReceipt):
            def propose(self, *args):
                response = super().propose(*args)
                response.proposal['goal_updates'] = [{'id': 'goal', 'status': 'succeeded', 'evidence_ids': ['invented']}]
                return response
        r = self.runtime(Unsupported()); r.goal('Goal'); r.tick()
        self.assertEqual(self.attempts(r)[0]['status'], 'succeeded')
        self.assertEqual(r.db.rows('SELECT error FROM calls')[0]['error'], 'proposal_rejected')
        event = json.loads(r.db.rows("SELECT data FROM events WHERE kind='deliberation.failed'")[0]['data'])
        self.assertEqual(event['payload']['stage'], 'application')

    def test_restart_marks_unfinished_attempt_once_and_never_resends(self):
        class Crash(FixtureProvider):
            def propose(self, *args):
                raise SystemExit('injected crash')
        r = self.runtime(Crash()); r.goal('Goal')
        with self.assertRaises(SystemExit):
            r.tick()
        attempt_id = self.attempts(r)[0]['id']; r.close()
        second = Runtime(self.path / 'run', PaidReceipt(), clock=self.clock, fixtures=self.docs)
        self.addCleanup(second.close)
        self.assertFalse(second.tick())
        recovered = self.attempts(second)[0]
        self.assertEqual((recovered['id'], recovered['status'], recovered['failure_code']),
                         (attempt_id, 'outcome-unknown', 'process_restart'))
        self.assertIsNone(recovered['known_unsent'])
        before = summarize(second.db); second.close()
        third = Runtime(self.path / 'run', PaidReceipt(), clock=self.clock, fixtures=self.docs)
        self.addCleanup(third.close)
        self.assertEqual(summarize(third.db), before)
        self.assertEqual(len(third.db.rows("SELECT * FROM events WHERE kind='attempt.finished'")), 1)

    def test_schema_two_migration_preserves_legacy_calls_and_unknown_coverage(self):
        path = self.path / 'old.sqlite'
        with sqlite3.connect(path) as db:
            db.execute('CREATE TABLE meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
            db.execute("INSERT INTO meta VALUES ('schema','2')")
            db.execute('CREATE TABLE calls(id TEXT PRIMARY KEY,provider TEXT NOT NULL,requested_model TEXT,reported_model TEXT,status TEXT NOT NULL,input_hash TEXT NOT NULL,output_hash TEXT,usage TEXT,error TEXT,elapsed REAL,created REAL NOT NULL)')
            db.execute("INSERT INTO calls VALUES ('old','claude','m','m','failed','hash',NULL,NULL,'historical',1,100)")
            before = db.execute('SELECT * FROM calls').fetchall()
        for _ in range(2):
            db = Database(path)
            try:
                self.assertEqual([tuple(r) for r in db.db.execute('SELECT * FROM calls')], before)
                self.assertEqual(db.get('schema'), 2)
                self.assertEqual(db.get('attempt_schema'), 1)
                self.assertEqual(summarize(db)['legacy_calls_without_attempts'], 1)
                self.assertEqual(summarize(db)['attempts'], 0)
                self.assertIsNone(summarize(db)['categories']['api_equivalent_usd']['complete_total'])
            finally:
                db.close()

    def test_restart_after_attempt_receipt_keeps_cost_without_resend(self):
        r = self.runtime(PaidReceipt()); r.goal('Goal')
        with patch.object(r, '_record_provider_receipt', side_effect=SystemExit('crash after receipt')):
            with self.assertRaises(SystemExit):
                r.tick()
        before = summarize(r.db); r.close()
        second = Runtime(self.path / 'run', PaidReceipt(), clock=self.clock, fixtures=self.docs)
        self.addCleanup(second.close)
        self.assertFalse(second.tick())
        self.assertEqual(summarize(second.db), before)
        self.assertEqual(self.attempts(second)[0]['status'], 'succeeded')
        self.assertEqual(second.db.rows('SELECT status FROM calls')[0]['status'], 'outcome-unknown')
        self.assertEqual(before['categories']['api_equivalent_usd']['complete_total'], .02)

    def test_additive_migration_rolls_back_on_failure(self):
        r = self.runtime()
        with r.db.transaction() as tx:
            tx.execute('DROP TABLE provider_attempts')
            tx.execute("DELETE FROM meta WHERE key='attempt_schema'")
        with patch.object(r.db, 'set', side_effect=sqlite3.OperationalError('injected disk failure')):
            with self.assertRaises(sqlite3.OperationalError):
                initialize(r.db)
        self.assertFalse(r.db.rows("SELECT name FROM sqlite_master WHERE name='provider_attempts'"))
        self.assertIsNone(r.db.get('attempt_schema'))
        initialize(r.db)
        self.assertEqual(r.db.get('attempt_schema'), 1)

    def test_usage_and_progress_allowlist(self):
        class Private(PaidReceipt):
            def propose(self, context, cancel, progress):
                progress({'type': 'provider.delta', 'received_chars': 1, 'payload': 'PRIVATE_PROGRESS_CANARY'})
                response = super().propose(context, cancel, progress)
                response.usage['debug'] = 'PRIVATE_USAGE_CANARY'
                response.terminal_subtype = 'PRIVATE_SUBTYPE_CANARY'
                return response
        r = self.runtime(Private()); r.goal('Goal'); r.tick()
        dump = '\n'.join(r.db.db.iterdump())
        for canary in ('PRIVATE_PROGRESS_CANARY', 'PRIVATE_USAGE_CANARY', 'PRIVATE_SUBTYPE_CANARY'):
            self.assertNotIn(canary, dump)
        self.assertEqual(summarize(r.db)['categories']['api_equivalent_usd']['complete_total'], .02)

    def test_missing_nonfinite_and_negative_usage_remain_unknown(self):
        self.assertIsNone(safe_usage(None))
        for value in (None, True, -1, float('nan'), float('inf'), '0'):
            self.assertIsNone(safe_usage({'api_equivalent_usd': value})['api_equivalent_usd'])
        self.assertEqual(safe_usage({'api_equivalent_usd': 0})['api_equivalent_usd'], 0)
        r = self.runtime(); r.goal('Goal'); r.tick()
        cost = summarize(r.db)['categories']['api_equivalent_usd']
        self.assertEqual(cost['attempts_with_value'], 0)
        self.assertIsNone(cost['known_subtotal']); self.assertIsNone(cost['complete_total'])

    def test_malformed_usage_retains_available_terminal_cost(self):
        usage = claude_result_usage({'usage': 'bad', 'modelUsage': {'test': None}, 'total_cost_usd': .05})
        self.assertEqual(usage['api_equivalent_usd'], .05)
        self.assertIsNone(usage['output'])


class AdapterClassificationTests(Base):
    def test_real_local_timeout_classification(self):
        provider = CLIProvider('claude', 'test-model', self.path / 'provider', timeout=.05)
        with patch.object(provider, 'command', return_value=[sys.executable, '-c', 'import time; time.sleep(5)']):
            with self.assertRaises(ProviderError) as caught:
                provider._propose({}, threading.Event(), lambda event: None)
        self.assertEqual(caught.exception.failure_code, 'timeout')
        self.assertEqual(caught.exception.status, 'outcome-unknown')

    def test_malformed_stream_classification(self):
        provider = CLIProvider('claude', 'test-model', self.path / 'provider')
        with patch.object(provider, 'command', return_value=[sys.executable, '-c', 'print("invalid-json")']):
            with self.assertRaises(ProviderError) as caught:
                provider._propose({}, threading.Event(), lambda event: None)
        self.assertEqual(caught.exception.failure_code, 'malformed_response')

    def test_codex_remains_gated_without_auth_or_subprocess(self):
        provider = CLIProvider('codex', 'test-model', self.path / 'provider')
        with patch.object(provider, 'auth') as auth, patch('continuum.runtime.providers.subprocess.Popen') as popen:
            with self.assertRaises(ProviderError) as caught:
                provider.propose({}, threading.Event(), lambda event: None)
            auth.assert_not_called(); popen.assert_not_called()
        self.assertEqual(caught.exception.failure_code, 'tool_isolation')
        self.assertTrue(caught.exception.known_unsent)
