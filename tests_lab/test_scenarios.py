"""Scenario timing remains valid when the simulated grid is configured."""

import unittest

from continuum.lab.world import Change, World, scenario


class ConfiguredScenarioTests(unittest.TestCase):
    def test_changes_and_sensor_faults_scale_to_horizon_and_grid(self):
        for name in ('no_change', 'change', 'stale', 'adversarial'):
            for horizon, dt in ((12.0, .3), (24.0, .25), (3.0, 1.0), (240.0, .5)):
                with self.subTest(name=name, horizon=horizon, dt=dt):
                    config = scenario(name, 91, horizon=horizon, dt=dt)
                    self.assertEqual(config.horizon, horizon)
                    self.assertEqual(config.dt, dt)
                    for change in config.changes:
                        self.assertGreater(change.time, 0)
                        self.assertLess(change.time, horizon)
                        self.assertAlmostEqual(change.time / dt, round(change.time / dt))
                    for start, end, _ in config.stale + config.contradictions:
                        self.assertGreaterEqual(start, 0)
                        self.assertGreater(end, start)
                        self.assertLessEqual(end, horizon)
                        self.assertAlmostEqual(start / dt, round(start / dt))
                        self.assertAlmostEqual(end / dt, round(end / dt))
                    self.assertEqual(len(World(config).truth()), round(horizon / dt) + 1)

    def test_stale_measurements_have_scaled_original_timestamps(self):
        config = scenario('stale', 12, horizon=12.0, dt=.25)
        start, end, lag = config.stale[0]
        measurement = World(config).measure(round(start / config.dt))
        self.assertAlmostEqual(lag / config.dt, round(lag / config.dt))
        self.assertEqual(measurement['time'], start)
        self.assertEqual(measurement['measured_at'], start - lag)
        self.assertLess(measurement['measured_at'], measurement['time'])

    def test_explicit_changes_are_preserved(self):
        changes = (Change(2.0, 1.2, .03),)
        config = scenario('change', 3, horizon=4.0, changes=changes)
        self.assertEqual(config.changes, changes)

    def test_too_short_change_grid_has_explicit_error(self):
        with self.assertRaisesRegex(ValueError, 'three simulation steps'):
            scenario('change', horizon=1.0, dt=1.0)
        self.assertEqual(scenario('no_change', horizon=1.0, dt=1.0).changes, ())

    def test_seed_replays_parameter_schedule(self):
        self.assertEqual(scenario('change', 19, horizon=24, dt=.3),
                         scenario('change', 19, horizon=24, dt=.3))


if __name__ == '__main__':
    unittest.main()
