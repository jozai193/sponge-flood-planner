"""Evaluate a frozen two-resolution event without post-result parameter fitting."""
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from services.reference.validation_regression import compare_assessments

root=Path(sys.argv[1]);p=json.loads((root/'protocol.json').read_text())
audit=json.loads((root/'accuracy.json').read_text());old,new=audit['runs']
if [old['grid_cells'],new['grid_cells']]!=[64,128]:raise ValueError('Expected frozen control and candidate')
if audit['protocol_sha256']!=(root/'protocol.sha256').read_text().strip():raise ValueError('Wrong assessment')
plan=json.loads((root/'evaluation-plan.json').read_text())
if plan['observed_high_water_elevations_inspected'] is not False:raise ValueError('Not an unexposed design')
rules=plan['comparison_rules'];gate=compare_assessments(old,new,tolerance_m=rules['common_point_and_equal_site_rmse_worsening_tolerance_m'])

def metrics(samples,gauge):
    wet=[s for s in samples if s['status']=='compared'];errors=np.array([s['error_m'] for s in wet])
    reference=np.array([gauge-s['observed_elevation_m'] for s in wet])
    return {'retained_ids': [s['observation_id'] for s in samples],'wet_ids': [s['observation_id'] for s in wet],
        'dry_ids': [s['observation_id'] for s in samples if s['status']=='observed_flood_model_dry'],
        'unresolved_ids': [s['observation_id'] for s in samples if s['status'] not in ('compared','observed_flood_model_dry')],
        'rmse_m': float(np.sqrt(np.mean(errors**2))) if len(errors) else None,
        'mae_m': float(np.abs(errors).mean()) if len(errors) else None,'bias_m': float(errors.mean()) if len(errors) else None,
        'worst_absolute_error_m': float(np.abs(errors).max()) if len(errors) else None,
        'same_wet_gauge_rmse_m': float(np.sqrt(np.mean(reference**2))) if len(reference) else None}

strata=[]
for r in (old,new):
    gauge=r['gauge_only_baseline']['peak_navd88_m'];samples=r['samples']
    strata.append({'grid_cells': r['grid_cells'],'all': metrics(samples,gauge),
        'good_or_excellent': metrics([s for s in samples if s['quality'] in (1,2)],gauge),
        'fair': metrics([s for s in samples if s['quality']==3],gauge),
        'poor_or_very_poor': metrics([s for s in samples if s['quality'] in (4,5)],gauge),
        'spatial_groups': {name:metrics([s for s in samples if s['observation_id'] in ids],gauge) for name,ids in
            {'visitor_centre_lawn_and_shrubs':[16663,16667,16664],'exterior_stairs':[16723],'aquarium_unresolved':[16666]}.items()}})

result={'event_id': p['event_id'],'assessed_at': datetime.now(UTC).isoformat(),'regression': gate,'quality_and_spatial_strata': strata,
    'individual_observations': [{'grid_cells': r['grid_cells'],'samples': r['samples']} for r in (old,new)],
    'decision': 'refinement_passes_this_new_event_screening' if gate['regression_gate_passed'] else 'refinement_does_not_generalize_without_regression_to_this_event',
    'general_flood_accuracy_validated': False,'production_default_changed': False,
    'protocol_sha256': audit['protocol_sha256'],'software_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'interpretation': 'A failed coverage or regression gate is retained even if candidate wet-only RMSE is low. Gauge-only comparison uses identical wet points. Nearby poor-quality lawn marks are spatially correlated; no overall accuracy percentage or city-wide extent/timing claim.',
    'event_status_after_inspection': 'development_evidence; a future fitted change requires another unexposed event','limitations': p['limitations']}
(root/'holdout-comparison.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'decision': result['decision'],'regression': gate,'quality_and_spatial_strata': strata},indent=2))
