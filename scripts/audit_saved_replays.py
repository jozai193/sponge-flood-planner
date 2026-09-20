"""Audit existing completed outputs without mutating their frozen assessments."""
import json
import sys
from pathlib import Path

import numpy as np

from services.reference.replay_integrity import validate_replay

paths=list(Path('artifacts/validation/sandy-2012').glob('simulation-*.json'))
for event in ('michael-2018','ian-2022','irma-2017','ian-2022-grid128','irma-2017-grid128','sandy-2012-grid128','matthew-2016','sandy-2012-positivity-v1','matthew-2016-positivity-v1','matthew-2016-domain4km'):
    paths+=list((Path('artifacts/validation')/event).glob('simulation-*.json'))
paths+=list(Path('artifacts/validation/checkpoint-recovery').glob('*/simulation-*.json'))
results=[]
for path in paths:
    sim=json.loads(path.read_text())
    p=json.loads((path.parent/'protocol.json').read_text())
    folder=Path('data/local/bundles')/sim['bundle_id']
    g=sim['grid'];shape=(g['ny'],g['nx'])
    solid=np.fromfile(folder/'solid.bin',dtype='u1').reshape(shape)
    try:
        result=validate_replay(sim['frames'],shape,solid,p['duration_s'],cell_area_m2=g['dx_m']*g['dy_m'])
    except ValueError as exc:
        result={'replay_structure_passed': False,'mass_gate_passed': None,
            'depth_volume_crosscheck_passed': None,'error': str(exc),
            'limitation': 'Rejected raw replay; no accepted accuracy score inferred.'}
    results.append(dict(path=str(path),**result))
    print(path,result['mass_gate_passed'])
Path('artifacts/validation/replay-integrity-audit.json').write_text(json.dumps(results,indent=2))
# Inventory mode records every event, including rejected evidence, so one old
# failure cannot prevent a separate event report. Strict callers may gate all runs.
if '--require-all-valid' in sys.argv and any(not r['replay_structure_passed'] or not r['mass_gate_passed'] for r in results):
    raise SystemExit(1)
