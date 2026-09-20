"""Compare candidate raw outputs to preserved same-grid exposed baselines."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

from services.reference.replay_integrity import validate_replay
from services.reference.validation_regression import compare_assessments

root=Path(sys.argv[1]);p=json.loads((root/'protocol.json').read_text())
parent=Path(p['candidate_parent_directory']);n=p['bundles'][0]['grid_cells']
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
if sha(parent/'protocol.json')!=p['candidate_parent_protocol_sha256']:raise ValueError('Parent changed')
old_path=parent/f'simulation-{n}.json';new_path=root/f'simulation-{n}.json'
old=json.loads(old_path.read_text());new=json.loads(new_path.read_text());g=new['grid']
if old['grid']!=g or old['inputHash']!=new['inputHash']:raise ValueError('Grid or solver input changed')
solid=np.fromfile(Path('data/local/bundles')/new['bundle_id']/'solid.bin',dtype='u1').reshape(g['ny'],g['nx'])
integrity=validate_replay(new['frames'],solid.shape,solid,p['duration_s'],cell_area_m2=g['dx_m']*g['dy_m'])
try:
    original_integrity=validate_replay(old['frames'],solid.shape,solid,p['duration_s'],cell_area_m2=g['dx_m']*g['dy_m'])
except ValueError as exc:original_integrity={'replay_structure_passed': False,'error': str(exc)}
if [f['time_s'] for f in old['frames']]!=[f['time_s'] for f in new['frames']]:raise ValueError('Output schedules differ')
differences={key:max(float(np.max(np.abs(np.asarray(a[key])-np.asarray(b[key])))) for a,b in zip(old['frames'],new['frames'])) for key in ('depth','maxDepth')}
corrections=np.array([f['ledger']['roundoff_correction_m3'] for f in new['frames']])
if not np.isfinite(corrections).all() or np.any(corrections<0) or np.any(np.diff(corrections)<0):raise ValueError('Invalid roundoff history')
for f in new['frames']:
    ledger=f['ledger'];supply=ledger['initial_m3']+ledger['rain_m3']+ledger['inflow_m3']
    if ledger['roundoff_correction_m3']>max(supply,1)*1e-8:raise ValueError('Roundoff budget exceeded')
    if not np.isclose(ledger['roundoff_adjusted_residual_m3'],ledger['residual_m3']+ledger['roundoff_correction_m3'],rtol=1e-12,atol=1e-12):raise ValueError('Correction accounting mismatch')
point_regression=None
if original_integrity['replay_structure_passed'] and (parent/'accuracy.json').exists():
    a=next(r for r in json.loads((parent/'accuracy.json').read_text())['runs'] if r['grid_cells']==n)
    b=json.loads((root/'accuracy.json').read_text())['runs'][0]
    point_regression=compare_assessments(a,b)
passed=integrity['mass_gate_passed'] and max(differences.values())<=1e-4 and (point_regression is None or point_regression['regression_gate_passed'])
result={'candidate_integrity': integrity,'original_integrity': original_integrity,
    'max_saved_depth_difference_m': differences['depth'],'max_saved_peak_difference_m': differences['maxDepth'],
    'final_roundoff_correction_m3': float(corrections[-1]),'point_regression': point_regression,
    'candidate_numerical_regression_passed': bool(passed),'production_enabled': False,
    'evidence_sha256': {str(path):sha(path) for path in (old_path,new_path,root/'protocol.json',root/'evaluation-plan.json',Path(__file__))},
    'limitation': 'Same-grid already exposed regression only. Rejected original Sandy remains rejected. Candidate assessment is separate. No untouched-event or general flood accuracy validation.'}
(root/'candidate-comparison.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
