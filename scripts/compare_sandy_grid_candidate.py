"""Apply unchanged acceptance checks to the legacy Sandy prior-event baseline."""
import hashlib
import json
from pathlib import Path

import numpy as np

from services.reference.validation_regression import compare_assessments

base=Path('artifacts/validation/sandy-2012');root=Path('artifacts/validation/sandy-2012-grid128')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((base/'protocol.json').read_text());q=json.loads((root/'protocol.json').read_text())
for folder in (base,root):
    if sha(folder/'protocol.json')!=(folder/'protocol.sha256').read_text().strip():raise ValueError('Protocol changed')
for path,expected in q['source_sha256'].items():
    if sha(Path(path))!=expected:raise ValueError('Frozen candidate source changed: '+path)
if q['parent_protocol_sha256']!=sha(base/'protocol.json'):raise ValueError('Wrong parent')
for key in ('center','extent_m','roughness','max_step_s','duration_s','start_utc','end_utc','rainfall_m','infiltration_m_s','soil_storage_m'):
    if p[key]!=q[key]:raise ValueError('Non-resolution change: '+key)
if q['boundary_edge']!='west':raise ValueError('Boundary changed')
for name in ('hwms.json','current-buildings.geojson','battery-water-level.json','terrain-catalog.json','ny-terrain-metadata.json'):
    if (base/name).read_bytes()!=(root/name).read_bytes():raise ValueError('Source changed: '+name)
frozen=Path('artifacts/validation/baselines/sandy-initial')
for name in ('protocol.json','accuracy.json','simulation-64.json'):
    if (frozen/base/name).read_bytes()!=(base/name).read_bytes():raise ValueError('Baseline changed: '+name)
levels=[]
for protocol in (p,q):
    r=protocol['bundles'][-1];b=Path('data/local/bundles')/r['bundle_id'];g=json.loads((b/'manifest.json').read_text())['grid']
    levels.append(np.array([[k['timeS'],k['elevationM']+g['elevation_origin_m']] for k in r['levels']]))
if not np.allclose(*levels,atol=1e-12,rtol=0):raise ValueError('Forcing changed')
old=json.loads((base/'accuracy.json').read_text())['runs'][-1]
new=json.loads((root/'accuracy.json').read_text())['runs'][-1]
result=compare_assessments(old,new)
lookup={s['observation_id']:s for s in new['samples']}
result.update(baseline_directory=str(base),candidate_directory=str(root),baseline_grid=64,candidate_grid=128,
    observation_transitions=[{'id': a['observation_id'],'before': a['status'],'after': lookup[a['observation_id']]['status']} for a in old['samples'] if a['status']!=lookup[a['observation_id']]['status']],
    decision='candidate_passes_this_event_only' if result['regression_gate_passed'] else 'reject_candidate_on_this_event',
    adoption='Prior-event development regression, not fresh independent validation. No production default change.',
    comparison_software_sha256={s:sha(Path(s)) for s in ('scripts/compare_sandy_grid_candidate.py','services/reference/validation_regression.py','services/reference/site_metrics.py')})
(root/'regression-comparison.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
