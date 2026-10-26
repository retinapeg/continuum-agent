"""Freeze, evidence accounting and reproduction checks on a tiny test campaign."""
from contextlib import ExitStack
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from continuum.lab import campaign


class CampaignTests(unittest.TestCase):
    def setUp(self):
        (campaign.ROOT / '.cache').mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix='campaign-test-', dir=campaign.ROOT / '.cache')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.patches = ExitStack()
        self.addCleanup(self.patches.close)
        for name, value in (('DEV_SEEDS', (70,)), ('HELDOUT_SEEDS', (71,)),
                            ('SCENARIOS', ('no_change',)), ('BUDGETS', (2,)), ('BOOTSTRAP_REPLICATES', 30)):
            self.patches.enter_context(patch.object(campaign, name, value))
        # Other agents may edit unrelated code during tests. Real campaigns hash
        # all source; this fixture freezes its own stable file only.
        relative = 'tests_lab/test_campaign.py'
        hashes = {relative: hashlib.sha256((campaign.ROOT / relative).read_bytes()).hexdigest()}
        self.patches.enter_context(patch.object(campaign, 'source_hashes', return_value=hashes))

    def frozen(self):
        dev = self.base / 'development'
        manifest = campaign.develop(dev)
        target = self.base / 'heldout'
        protocol = campaign.freeze(target, dev)
        return target, manifest, protocol

    def test_equal_development_allowance_and_lowest_rmse_selection(self):
        manifest = campaign.develop(self.base / 'development')
        self.assertTrue(manifest['valid'])
        self.assertEqual(manifest['units'], 12)
        for policy in campaign.LABELS:
            rows = [row for row in manifest['candidates'] if row['policy'] == policy]
            self.assertEqual(len(rows), 3)
            self.assertEqual({row['units'] for row in rows}, {1})
            best = min(rows, key=lambda row: (row['mean_rmse'], row['candidate_index']))
            self.assertEqual(manifest['selected_parameters'][policy], best['parameters'])

    def test_freeze_run_and_exact_reproduction_preserve_original_files(self):
        directory, _, protocol = self.frozen()
        self.assertEqual(protocol['expected_units'], 4)
        self.assertEqual(campaign.verify(directory)['stage'], 'frozen')
        result = campaign.run_campaign(directory)
        self.assertTrue(result['valid_comparison'])
        before = {path.name: path.read_bytes() for path in directory.iterdir()}
        verification = campaign.verify(directory, reproduce=True)
        self.assertEqual(verification['reproduced_units'], 4)
        self.assertEqual(before, {path.name: path.read_bytes() for path in directory.iterdir()})
        with self.assertRaises(FileExistsError):
            campaign.run_campaign(directory)
        with self.assertRaises(FileExistsError):
            campaign.freeze(directory, self.base / 'development')

    def test_protocol_source_and_evidence_drift_are_rejected(self):
        directory, _, _ = self.frozen()
        with patch.object(campaign, 'source_hashes', return_value={}):
            with self.assertRaisesRegex(ValueError, 'source drift'):
                campaign.run_campaign(directory)
        campaign.run_campaign(directory)
        with (directory / 'results.jsonl').open('a') as output:
            output.write('{}\n')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            campaign.verify(directory)
        with (directory / 'protocol.json').open('a') as output:
            output.write(' ')
        with self.assertRaisesRegex(ValueError, 'protocol hash mismatch'):
            campaign.verify(directory)

    def test_unit_exception_is_preserved_and_invalidates_comparison(self):
        directory, _, _ = self.frozen()
        original = campaign.PolicyRun.step

        def failing_step(run, world, tick, events, deadlines):
            if run.name == 'periodic' and tick == 1:
                raise RuntimeError('controlled campaign failure')
            return original(run, world, tick, events, deadlines)

        with patch.object(campaign.PolicyRun, 'step', failing_step):
            result = campaign.run_campaign(directory)
        self.assertFalse(result['valid_comparison'])
        self.assertEqual(len(result['runtime_failures']), 1)
        self.assertEqual(result['overall'], {})
        rows = [json.loads(line) for line in (directory / 'results.jsonl').read_text().splitlines()]
        failed = [row for row in rows if row['status'] == 'failed']
        self.assertEqual(failed[0]['error']['message'], 'controlled campaign failure')
        with gzip.open(directory / 'traces.jsonl.gz', 'rt') as traces:
            trace_rows = [json.loads(line) for line in traces]
        self.assertEqual(len(trace_rows), 4)
        self.assertTrue(trace_rows[0]['receipts'])
        self.assertEqual(trace_rows[0]['status'], 'failed')

    def test_development_failures_block_freeze(self):
        with patch.object(campaign.PolicyRun, 'finish', side_effect=RuntimeError('controlled failure')):
            development = campaign.develop(self.base / 'development')
        self.assertFalse(development['valid'])
        self.assertEqual(development['runtime_failures'], 12)
        with self.assertRaisesRegex(ValueError, 'development invalid'):
            campaign.freeze(self.base / 'heldout', self.base / 'development')

    def test_external_destination_is_rejected_before_writing(self):
        with self.assertRaisesRegex(ValueError, 'child of this repository'):
            campaign.develop(campaign.ROOT.parent / 'forbidden-test-campaign')

    def test_seed_cluster_bootstrap_uses_paired_difference(self):
        protocol = {'expected_units': 8, 'primary_metric': 'rmse', 'policies': list(campaign.LABELS),
                    'scenarios': ['no_change'], 'budgets': [12], 'heldout_seeds': [1, 2],
                    'bootstrap': {'seed': 9, 'replicates': 100}}
        rows = []
        for seed in (1, 2):
            for policy in campaign.LABELS:
                metrics = {key: 0. for key in ('zero_rmse', 'nll', 'coverage95', 'detected_changes', 'missed_changes',
                           'false_alarms', 'observations', 'inferences', 'actions', 'cost', 'failures')}
                metrics.update(rmse=float(seed) if policy == 'uncertainty' else float(seed) + .5,
                               detection_delay=None, censored_delay=None)
                rows.append({'unit_id': f'{seed}:{policy}', 'status': 'succeeded', 'seed': seed,
                             'policy': policy, 'scenario': 'no_change', 'observation_budget': 12, 'metrics': metrics})
        report = campaign.summarize(rows, protocol)
        for comparison in report['paired_rmse'].values():
            self.assertEqual(comparison['difference'], -.5)
            self.assertEqual(comparison['ci95'], [-.5, -.5])
            self.assertEqual(comparison['seed_clusters'], 2)


if __name__ == '__main__':
    unittest.main()
