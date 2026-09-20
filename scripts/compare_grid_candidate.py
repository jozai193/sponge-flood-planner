"""Evaluate a completed resolution candidate against its unchanged cohort."""
import hashlib
import json
import sys
from pathlib import Path

from services.reference.validation_regression import compare_assessments

baseline=Path(sys.argv[1]);candidate=Path(sys.argv[2])
before=json.loads((baseline/'accuracy.json').read_text());after=json.loads((candidate/'accuracy.json').read_text())
old=before['runs'][-1];new=after['runs'][-1]
for folder in (baseline,candidate):
    protocol=json.loads((folder/'protocol.json').read_text())
    if hashlib.sha256((folder/'protocol.json').read_bytes()).hexdigest()!=(folder/'protocol.sha256').read_text().strip():raise ValueError('Changed protocol')
    for path,sha in protocol['source_sha256'].items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=sha:raise ValueError('Changed source '+path)
p=json.loads((baseline/'protocol.json').read_text());q=json.loads((candidate/'protocol.json').read_text())
for key in ('center','extent_m','roughness','max_step_s','boundary_edge','duration_s','start_utc','end_utc','rainfall_m','infiltration_m_s','soil_storage_m'):
    if p[key]!=q[key]:raise ValueError('Not a resolution-only comparison: '+key)
for name in ('hwms.json','observation-review.json','current-buildings.geojson','forcing-preflight.json','noaa-topobathy-subset.tif'):
    if (baseline/name).read_bytes()!=(candidate/name).read_bytes():raise ValueError('Changed input '+name)
result=compare_assessments(old,new)
result.update(baseline_directory=str(baseline),candidate_directory=str(candidate),
    comparison_software_sha256={path:hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in ('scripts/compare_grid_candidate.py','services/reference/validation_regression.py','services/reference/site_metrics.py')},
    baseline_grid=old['grid_cells'],candidate_grid=new['grid_cells'],
    observation_transitions=[{'id': a['observation_id'],'before': a['status'],'after': b['status']} for a,b in zip(old['samples'],new['samples']) if a['status']!=b['status']],
    decision='candidate_passes_this_event_only' if result['regression_gate_passed'] else 'reject_candidate_on_this_event',
    adoption='No production default change. A pass still requires cross-event and prior-event review.')
(candidate/'regression-comparison.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
