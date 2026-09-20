"""Compare fixed observation cohorts without rewarding dropped wet predictions."""
import math

from services.reference.site_metrics import site_balanced_errors


def compare_assessments(baseline, candidate, tolerance_m=0.01):
    if baseline['event_id'] != candidate['event_id']:
        raise ValueError('Regression comparisons require the same event')
    if not math.isfinite(tolerance_m) or tolerance_m < 0:
        raise ValueError('A finite nonnegative tolerance is required')
    def indexed(run):
        samples = run['samples']
        result = {s['observation_id']: s for s in samples}
        if len(result) != len(samples):
            raise ValueError('Duplicate observation IDs')
        return result
    old, new = indexed(baseline), indexed(candidate)
    if old.keys() != new.keys():
        raise ValueError('Observation cohort changed')
    for key in old:
        for sample in (old[key], new[key]):
            unavailable = sample['status'] in ('vertical_datum_unresolved','measured_elevation_unavailable')
            value = sample['observed_elevation_m']
            if (unavailable and value is not None) or (not unavailable and (value is None or not math.isfinite(value))):
                raise ValueError('Nonfinite observation')
            if sample['status'] == 'compared' and not math.isfinite(sample['error_m']):
                raise ValueError('Nonfinite prediction error')
        if old[key]['observed_elevation_m'] != new[key]['observed_elevation_m']:
            raise ValueError('Observation values changed')
        if old[key].get('site_id') != new[key].get('site_id'):
            raise ValueError('Observation site membership changed')
    common = [key for key in old if old[key]['status'] == new[key]['status'] == 'compared']
    lost = [key for key in old if old[key]['status'] == 'compared' and new[key]['status'] != 'compared']
    gained = [key for key in old if old[key]['status'] != 'compared' and new[key]['status'] == 'compared']
    supported_statuses={'compared','observed_flood_model_dry'}
    lost_supported=[key for key in old if old[key]['status'] in supported_statuses and new[key]['status'] not in supported_statuses]
    rmse = lambda rows: math.sqrt(sum(rows[k]['error_m']**2 for k in common)/len(common)) if common else None
    before, after = rmse(old), rmse(new)
    site_before=site_balanced_errors([old[k] for k in common])['rmse_m']
    site_after=site_balanced_errors([new[k] for k in common])['rmse_m']
    dry_before = sum(s['status'] == 'observed_flood_model_dry' for s in old.values())
    dry_after = sum(s['status'] == 'observed_flood_model_dry' for s in new.values())
    numerical_ok = candidate.get('mass_gate_passed') is True
    passed = (numerical_ok and bool(common) and not lost and not lost_supported and dry_after <= dry_before
              and after <= before+tolerance_m and site_after <= site_before+tolerance_m)
    return {'event_id': baseline['event_id'], 'common_wet_ids': common,
        'lost_wet_ids': lost, 'gained_wet_ids': gained, 'baseline_common_rmse_m': before,
        'lost_supported_ids': lost_supported,
        'candidate_common_rmse_m': after, 'dry_before': dry_before, 'dry_after': dry_after,
        'baseline_common_site_rmse_m': site_before,'candidate_common_site_rmse_m': site_after,
        'mass_gate_passed': numerical_ok, 'tolerance_m': tolerance_m,
        'regression_gate_passed': passed,
        'limitation': 'A passed development regression gate is not independent validation. Newly wet points and individual errors still require review; no flood extent or timing skill is established.'}
