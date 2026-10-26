"""Independent scorer: private truth joins only completed, fixed-grid forecasts."""

from collections.abc import Mapping
import math


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{label} must be a finite number')
    try:
        valid = math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f'{label} must be a finite number')
    return value


def _field(row, key):
    if not isinstance(row, Mapping) or key not in row:
        raise ValueError(f'missing numeric field: {key}')
    return _finite(row[key], key)


def score(truth, predictions, alerts, changes, resources, detection_window=20.):
    """Score forecasts and one-to-one detections, retaining failed operations.

    Forecasts must target existing truth timestamps. Invalid or missing forecasts
    are rejected, never silently omitted. The runner supplies the common grid.
    Misses contribute a full detection window to censored delay; conditional delay
    is undefined when no change was detected. Resource metadata cannot replace
    independently computed metrics.
    """
    if _finite(detection_window, 'detection window') <= 0:
        raise ValueError('positive finite detection window required')
    actual = {}
    for row in truth:
        at, value = _field(row, 'time'), _field(row, 'x')
        if at in actual:
            raise ValueError('duplicate truth timestamp')
        actual[at] = value

    errors, nll, covered, targets = [], [], [], set()
    for row in predictions:
        issued, target = _field(row, 'time'), _field(row, 'target')
        sd, mean = _field(row, 'prediction_std'), _field(row, 'prediction')
        if sd <= 0 or target <= issued or target not in actual or target in targets:
            raise ValueError('invalid or duplicate forecast')
        targets.add(target)
        error = mean - actual[target]
        try:
            square = error * error
            likelihood = .5 * math.log(2 * math.pi) + math.log(sd) + .5 * (error / sd) ** 2
        except (OverflowError, ZeroDivisionError) as exc:
            raise ValueError('forecast exceeds numerical scoring range') from exc
        if not math.isfinite(square) or not math.isfinite(likelihood):
            raise ValueError('forecast exceeds numerical scoring range')
        errors.append(square)
        nll.append(likelihood)
        covered.append(abs(error) <= 1.96 * sd)
    if not errors:
        raise ValueError('predictions required')

    unmatched = sorted(_finite(at, 'alert time') for at in alerts)
    change_times = sorted(_finite(at, 'change time') for at in changes)
    if len(set(change_times)) != len(change_times):
        raise ValueError('duplicate change timestamp')
    delays = []
    for change in change_times:
        candidates = [at for at in unmatched if change <= at <= change + detection_window]
        if candidates:
            at = candidates[0]
            unmatched.remove(at)
            delays.append(at - change)
    misses = len(change_times) - len(delays)

    counts = {}
    for key in ('observations', 'inferences', 'actions', 'failures'):
        value = _field(resources, key)
        if value < 0:
            raise ValueError('nonnegative resource counts required')
        counts[key] = value
    return {
        'rmse': math.sqrt(math.fsum(errors) / len(errors)),
        'nll': math.fsum(nll) / len(nll),
        'coverage95': sum(covered) / len(covered),
        'prediction_count': len(errors),
        'zero_rmse': math.sqrt(math.fsum(actual[t] ** 2 for t in sorted(targets)) / len(targets)),
        'detection_delay': math.fsum(delays) / len(delays) if delays else None,
        'censored_delay': (math.fsum(delays) + misses * detection_window) / len(change_times) if change_times else None,
        'detected_changes': len(delays),
        'missed_changes': misses,
        'false_alarms': len(unmatched),
        **counts,
        'cost': counts['observations'] + 2 * counts['inferences'] + .1 * counts['actions'],
    }
