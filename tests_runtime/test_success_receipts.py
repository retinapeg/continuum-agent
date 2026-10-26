"""Execution reports are derived from operation receipts, not model claims."""
import json
import sqlite3
from unittest.mock import patch

from test_core import Base
from continuum.runtime.contracts import empty_proposal
from continuum.runtime.providers import ProviderError, Response
from continuum.lab.live import public_input, run_pilot


class SuccessReceiptTests(Base):
    def proposal(self, runtime):
        runtime.goal('Write brief', goal_id='brief')
        runtime.observe('status', {'text': 'Public source'}, event_id='source')
        proposal = empty_proposal()
        proposal['actions'] = [{'capability': 'create_artifact', 'args': {
            'path': 'brief.md', 'content': 'A brief.', 'sources': ['source'], 'goal_id': 'brief'}}]
        proposal['message'] = {'text': 'The brief was successfully created.', 'reason': 'new_evidence',
                               'topic': 'brief', 'evidence_ids': ['source']}
        return proposal

    def test_failed_effect_never_publishes_claimed_success(self):
        runtime = self.runtime()
        proposal = self.proposal(runtime)
        with patch('continuum.runtime.capabilities.os.open', side_effect=OSError('controlled disk failure')):
            runtime.apply(proposal, runtime.context(100), 'failure', 100)
        operation = runtime.db.rows('SELECT * FROM operations')[0]
        notification = runtime.db.rows('SELECT * FROM outbox')[0]
        self.assertEqual(operation['status'], 'failed')
        self.assertIn('create_artifact: failed', notification['content'])
        self.assertNotIn('successfully created', notification['content'])
        self.assertEqual(json.loads(notification['evidence']), [operation['id']])
        self.assertEqual(runtime.db.rows('SELECT * FROM artifacts'), [])
        self.assertIn('controlled disk failure', operation['result'])
        self.assertEqual(runtime.status()['operations'][0]['status'], 'failed')

    def test_success_message_contains_actual_receipt(self):
        runtime = self.runtime()
        proposal = self.proposal(runtime)
        runtime.apply(proposal, runtime.context(100), 'success', 100)
        operation = runtime.db.rows('SELECT * FROM operations')[0]
        notification = runtime.db.rows('SELECT * FROM outbox')[0]
        self.assertEqual(operation['status'], 'succeeded')
        self.assertIn('succeeded: brief.md', notification['content'])
        self.assertEqual(json.loads(notification['evidence']), [operation['id']])
        self.assertTrue((runtime.directory / 'artifacts/brief.md').is_file())

    def test_unapproved_effect_remains_waiting(self):
        runtime = self.runtime()
        proposal = self.proposal(runtime)
        runtime.db.set('permissions', [])
        runtime.apply(proposal, runtime.context(100), 'waiting', 100)
        notification = runtime.db.rows('SELECT * FROM outbox')[0]
        self.assertIn('waiting-for-approval', notification['content'])
        self.assertNotIn('successfully created', notification['content'])

    def test_old_receipt_cannot_support_a_different_claim(self):
        runtime = self.runtime()
        proposal = self.proposal(runtime)
        runtime.apply(proposal, runtime.context(100), 'first', 100)
        operation = runtime.db.rows('SELECT * FROM operations')[0]
        proposal['actions'] = []
        proposal['message'].update(text='I deployed a website.', evidence_ids=[operation['id']])
        runtime.apply(proposal, runtime.context(140), 'second', 140)
        self.assertNotIn('deployed', '\n'.join(r['content'] for r in runtime.db.rows('SELECT * FROM outbox')))

    def test_proposal_without_receipt_is_not_verified(self):
        runtime = self.runtime()
        runtime.observe('user.message', {'text': 'Status?'}, event_id='source')
        proposal = empty_proposal()
        proposal['message'] = {'text': 'Done.', 'reason': 'reply', 'topic': 'status', 'evidence_ids': ['source']}
        runtime.apply(proposal, runtime.context(100), 'no-receipt', 100, reply_ids={'source'})
        notification = runtime.db.rows('SELECT * FROM outbox')[0]
        self.assertIn('completed work has not been verified', notification['content'])
        self.assertNotIn('Done.', notification['content'])
        self.assertEqual(runtime.db.rows('SELECT * FROM operations'), [])


class LivePilotTests(Base):
    def context(self):
        return {'at': 10., 'belief': {'x': .3, 'v': -.2, 'std': .2, 'variance': .04,
                    'at': 10., 'last_observation': 5., 'innovation': .8},
                'latest_observation': {'time': 5., 'measured_at': 5., 'value': .2,
                    'noise_std': .08, 'id': 'obs-1', 'status': 'succeeded'},
                'budget': {'observations_remaining': 4, 'inferences_remaining': 4, 'actions_remaining': 8},
                'public_events': []}

    def test_no_opt_in_has_no_provider_or_files(self):
        target = self.path / 'pilot'
        with patch('continuum.lab.live.CLIProvider') as provider:
            with self.assertRaises(PermissionError):
                run_pilot(target, [self.context()])
            provider.assert_not_called()
        self.assertFalse(target.exists())

    def test_hidden_world_fields_rejected(self):
        context = self.context()
        context['ground_truth'] = {'x': 99}
        with self.assertRaises(ValueError):
            public_input(context)
        context = self.context()
        context['belief']['change_points'] = [20]
        with self.assertRaises(ValueError):
            public_input(context)

    def test_failed_provider_receipt_and_success_both_survive(self):
        failure = ProviderError('controlled provider failure', usage={'output': 17},
                                reported_model='test-model', elapsed=.25, output_bytes=100)
        response = Response(empty_proposal('Public-state trigger proposal.'), 'test-model', {'output': 9}, .5, 200)
        target = self.path / 'pilot'
        with patch('continuum.lab.live.CLIProvider') as provider:
            provider.return_value.propose.side_effect = [failure, response]
            report = run_pilot(target, [self.context(), self.context()], opt_in=True, model='test-model', max_calls=2)
            self.assertEqual(provider.return_value.propose.call_count, 2)
        self.assertEqual((report['successful_calls'], report['failed_calls']), (1, 1))
        self.assertEqual(report['confirmed_cli_invocations'], 2)
        self.assertEqual(report['successful_cli_invocations'], 1)
        self.assertEqual(report['known_unsent_attempts'], 0)
        self.assertEqual(report['attempts'][0]['usage']['output'], 17)
        self.assertEqual(report['attempts'][0]['requested_model'], 'test-model')
        self.assertEqual(report['attempts'][0]['reported_model'], 'test-model')
        self.assertEqual(report['attempts'][0]['status'], 'failed')
        self.assertEqual(len((target / 'attempts.jsonl').read_text().splitlines()), 2)
        with sqlite3.connect(target / 'pilot.sqlite') as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM calls').fetchone()[0], 2)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM operations').fetchone()[0], 0)
        with patch('continuum.lab.live.CLIProvider') as provider:
            with self.assertRaises(FileExistsError):
                run_pilot(target, [self.context()], opt_in=True)
            provider.assert_not_called()

    def test_unrequested_actions_fail_without_effect_and_keep_proposal(self):
        proposal = empty_proposal()
        proposal['actions'] = [{'capability': 'inspect_events', 'args': {'limit': 1}}]
        with patch('continuum.lab.live.CLIProvider') as provider:
            provider.return_value.propose.return_value = Response(proposal, 'test-model', {'output': 9}, .5, 200)
            report = run_pilot(self.path / 'pilot', [self.context()], opt_in=True, model='test-model')
        self.assertEqual(report['failed_calls'], 1)
        self.assertEqual(report['attempts'][0]['proposal']['actions'], proposal['actions'])
        self.assertIsNone(report['attempts'][0]['next_delay'])
        self.assertEqual(report['successful_cli_invocations'], 1)

    def test_known_unsent_failure_is_not_a_cli_invocation(self):
        with patch('continuum.lab.live.CLIProvider') as provider:
            provider.return_value.propose.side_effect = ProviderError('no subscription', known_unsent=True)
            report = run_pilot(self.path / 'pilot', [self.context()], opt_in=True, model='test-model')
        self.assertEqual(report['attempted_calls'], 1)
        self.assertEqual(report['known_unsent_attempts'], 1)
        self.assertEqual(report['confirmed_cli_invocations'], 0)
        self.assertEqual(report['successful_cli_invocations'], 0)
        self.assertEqual(report['invocation_count_unknown'], 0)
        self.assertEqual(report['failed_calls'], 1)
