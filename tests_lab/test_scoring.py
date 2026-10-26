"""Independent numerical and failure-contract checks for the laboratory scorer.

These examples specify expected results directly, without the simulator or policy
implementations. A scheduling change cannot redefine its own success criteria.
"""

import math
import unittest

from continuum.lab.scoring import score


class IndependentScoringTests(unittest.TestCase):
    def evaluate(self, *, alerts=(), changes=(), detection_window=20.0):
        return score(
            truth=[{"time": 1.0, "x": 0.0}],
            predictions=[
                {"time": 0.0, "target": 1.0, "prediction": 0.0, "prediction_std": 1.0}
            ],
            alerts=list(alerts),
            changes=list(changes),
            resources={"observations": 0, "inferences": 0, "actions": 0, "failures": 0},
            detection_window=detection_window,
        )

    def test_exact_prediction_metrics_and_realized_cost(self):
        # Errors are 0 and -2. Both forecasts use sigma=1, so only one
        # truth value lies within the nominal 95% interval.
        metrics = score(
            truth=[{"time": 1.0, "x": 0.0}, {"time": 2.0, "x": 2.0}],
            predictions=[
                {"time": 0.0, "target": 1.0, "prediction": 0.0, "prediction_std": 1.0},
                {"time": 1.0, "target": 2.0, "prediction": 0.0, "prediction_std": 1.0},
            ],
            alerts=[],
            changes=[],
            resources={"observations": 3, "inferences": 2, "actions": 5, "failures": 2},
        )
        self.assertAlmostEqual(metrics["rmse"], math.sqrt(2.0))
        self.assertAlmostEqual(metrics["nll"], 0.5 * math.log(2.0 * math.pi) + 1.0)
        self.assertAlmostEqual(metrics["coverage95"], 0.5)
        self.assertAlmostEqual(metrics["zero_rmse"], math.sqrt(2.0))
        self.assertEqual(metrics["prediction_count"], 2)
        self.assertAlmostEqual(metrics["cost"], 7.5)
        self.assertEqual(metrics["failures"], 2)

    def test_resource_metadata_cannot_override_independent_metrics(self):
        metrics = score(
            truth=[{"time": 1.0, "x": 2.0}],
            predictions=[
                {"time": 0.0, "target": 1.0, "prediction": 0.0, "prediction_std": 1.0}
            ],
            alerts=[], changes=[],
            resources={"observations": 1, "inferences": 1, "actions": 1, "failures": 1,
                       "rmse": 0.0, "false_alarms": -1, "detected_changes": 100},
        )
        self.assertEqual(metrics["rmse"], 2.0)
        self.assertEqual(metrics["false_alarms"], 0)
        self.assertEqual(metrics["detected_changes"], 0)
        self.assertEqual(metrics["failures"], 1)

    def test_forecast_is_scored_at_target_not_issue_time(self):
        metrics = score(
            truth=[{"time": 0.0, "x": 90.0}, {"time": 1.0, "x": 4.0}],
            predictions=[
                {"time": 0.0, "target": 1.0, "prediction": 4.0, "prediction_std": 2.0}
            ],
            alerts=[],
            changes=[],
            resources={"observations": 0, "inferences": 0, "actions": 0, "failures": 0},
        )
        self.assertEqual(metrics["rmse"], 0.0)
        self.assertAlmostEqual(metrics["nll"], 0.5 * math.log(8.0 * math.pi))

    def test_no_change_alerts_are_all_false_alarms(self):
        metrics = self.evaluate(alerts=[1.0, 2.0, 2.0])
        self.assertEqual(metrics["false_alarms"], 3)
        self.assertEqual(metrics["detected_changes"], 0)
        self.assertEqual(metrics["missed_changes"], 0)
        self.assertIsNone(metrics["detection_delay"])

    def test_duplicate_early_and_late_alerts_do_not_create_success(self):
        metrics = self.evaluate(alerts=[9.0, 11.0, 11.0, 71.0], changes=[10.0, 50.0])
        self.assertEqual(metrics["detected_changes"], 1)
        self.assertEqual(metrics["missed_changes"], 1)
        self.assertEqual(metrics["false_alarms"], 3)
        self.assertEqual(metrics["detection_delay"], 1.0)
        self.assertEqual(metrics["censored_delay"], 10.5)

    def test_missed_changes_remain_in_censored_denominator(self):
        metrics = self.evaluate(changes=[2.0, 10.0], detection_window=7.0)
        self.assertEqual(metrics["detected_changes"], 0)
        self.assertEqual(metrics["missed_changes"], 2)
        self.assertEqual(metrics["false_alarms"], 0)
        self.assertIsNone(metrics["detection_delay"])
        self.assertEqual(metrics["censored_delay"], 7.0)

    def test_detection_window_is_inclusive(self):
        metrics = self.evaluate(alerts=[10.0, 50.0], changes=[10.0, 30.0])
        self.assertEqual(metrics["detected_changes"], 2)
        self.assertEqual(metrics["missed_changes"], 0)
        self.assertEqual(metrics["false_alarms"], 0)
        self.assertEqual(metrics["detection_delay"], 10.0)

    def test_one_alert_cannot_match_multiple_overlapping_changes(self):
        metrics = self.evaluate(alerts=[12.0], changes=[10.0, 11.0])
        self.assertEqual(metrics["detected_changes"], 1)
        self.assertEqual(metrics["missed_changes"], 1)
        self.assertEqual(metrics["detection_delay"], 2.0)
        self.assertEqual(metrics["censored_delay"], 11.0)

    def test_unsorted_alerts_match_by_simulated_time(self):
        metrics = self.evaluate(alerts=[13.0, 11.0], changes=[10.0])
        self.assertEqual(metrics["detection_delay"], 1.0)
        self.assertEqual(metrics["false_alarms"], 1)

    def test_missing_prediction_target_is_rejected(self):
        with self.assertRaises(ValueError):
            score(
                truth=[{"time": 0.0, "x": 0.0}],
                predictions=[
                    {"time": 0.0, "target": 1.0, "prediction": 0.0, "prediction_std": 1.0}
                ],
                alerts=[], changes=[], resources={},
            )

    def test_malformed_and_nonfinite_predictions_are_rejected(self):
        good = {"time": 0.0, "target": 1.0, "prediction": 0.0, "prediction_std": 1.0}
        invalid = [
            {},
            {key: value for key, value in good.items() if key != "prediction_std"},
            {**good, "prediction_std": 0.0},
            {**good, "prediction_std": -1.0},
            {**good, "prediction_std": math.nan},
            {**good, "prediction": math.inf},
            {**good, "target": math.nan},
            {**good, "time": math.inf},
        ]
        for prediction in invalid:
            with self.subTest(prediction=prediction), self.assertRaises(ValueError):
                score(
                    truth=[{"time": 1.0, "x": 0.0}], predictions=[prediction],
                    alerts=[], changes=[], resources={},
                )

    def test_nonfinite_truth_and_event_times_are_rejected(self):
        good = {"time": 0.0, "target": 1.0, "prediction": 0.0, "prediction_std": 1.0}
        invalid = [
            ([{"time": 1.0, "x": math.nan}], [], []),
            ([{"time": 1.0, "x": 0.0}], [math.inf], []),
            ([{"time": 1.0, "x": 0.0}], [], [math.nan]),
        ]
        for truth, alerts, changes in invalid:
            with self.subTest(truth=truth, alerts=alerts, changes=changes), self.assertRaises(ValueError):
                score(truth, [good], alerts, changes, {})

    def test_malformed_truth_and_resources_have_explicit_errors(self):
        good = {"time": 0.0, "target": 1.0, "prediction": 0.0, "prediction_std": 1.0}
        resources = {"observations": 1, "inferences": 1, "actions": 1, "failures": 0}
        for truth in ([{}], [{"time": 1.0, "x": "zero"}], [None]):
            with self.subTest(truth=truth), self.assertRaises(ValueError):
                score(truth, [good], [], [], resources)
        for bad in ({}, {**resources, "failures": -1}, {**resources, "observations": math.nan},
                    {**resources, "inferences": "one"}):
            with self.subTest(resources=bad), self.assertRaises(ValueError):
                score([{"time": 1.0, "x": 0.0}], [good], [], [], bad)

    def test_duplicate_forecasts_and_truth_are_rejected(self):
        truth = [{"time": 1.0, "x": 0.0}]
        prediction = {"time": 0.0, "target": 1.0, "prediction": 0.0, "prediction_std": 1.0}
        for rows, predictions in ((truth * 2, [prediction]), (truth, [prediction] * 2)):
            with self.subTest(rows=rows, predictions=predictions), self.assertRaises(ValueError):
                score(rows, predictions, [], [], {})


if __name__ == "__main__":
    unittest.main()
