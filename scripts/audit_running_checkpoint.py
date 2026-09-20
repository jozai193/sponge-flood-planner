"""Read one atomic checkpoint and audit saved frames without exposing observations."""
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from services.reference.coastal import CoastalBoundary
from services.reference.replay_integrity import validate_replay
from services.reference.solver import Surface

root=Path(sys.argv[1]);n=int(sys.argv[2]);path=root/f'checkpoint-{n}.json'
raw=path.read_bytes();envelope=json.loads(raw);payload=envelope['payload']
sha=lambda b:hashlib.sha256(b).hexdigest()
if sha(payload.encode())!=envelope['sha256']:raise ValueError('Checkpoint checksum mismatch')
c=json.loads(payload);p=json.loads((root/'protocol.json').read_text())
if c['protocolHash']!=sha((root/'protocol.json').read_bytes()):raise ValueError('Checkpoint protocol differs')
runner='scripts/run-positivity-historical.mjs' if p.get('candidate')=='gpu-positivity-candidate-v1' else 'scripts/run-historical-validation.mjs'
if c['runnerHash']!=sha(Path(runner).read_bytes()):raise ValueError('Checkpoint runner differs')
run=next(r for r in p['bundles'] if r['grid_cells']==n);folder=Path('data/local/bundles')/run['bundle_id']
g=json.loads((folder/'manifest.json').read_text())['grid'];shape=(g['ny'],g['nx'])
solid=np.fromfile(folder/'solid.bin',dtype='u1').reshape(shape);frames=c['frames']
result=validate_replay(frames,shape,solid,frames[-1]['time_s'],expected_frames=len(frames),cell_area_m2=g['dx_m']*g['dy_m'])
bed=np.fromfile(folder/'z.bin',dtype='<f4').reshape(shape).astype(float)
edge=p.get('boundary_edge','west');ny,nx=shape
cells=tuple(i for i in range(nx*ny) if not solid.flat[i] and
    (i%nx==0 if edge=='west' else i%nx==nx-1 if edge=='east' else i<nx if edge=='south' else i>=(ny-1)*nx))
boundary=CoastalBoundary(edge,cells,tuple((k['timeS'],k['elevationM']) for k in run['levels']),'local NAVD88 offset',p['forcing'])
reference=boundary.initial_depth(Surface(z=bed,dx=g['dx_m'],dy=g['dy_m'],solid=solid.astype(bool)))
saved_initial=np.asarray(frames[0]['depth']).reshape(shape)
if not np.allclose(reference,saved_initial,atol=2e-6,rtol=2e-6):raise ValueError('GPU initial state differs from float64 coastal reference')
out=dict(audited_at=datetime.now(UTC).isoformat(),checkpoint_sha256=sha(raw),grid_cells=n,
    event_complete=abs(frames[-1]['time_s']-p['duration_s'])<1e-5,simulated_hours=frames[-1]['time_s']/3600,
    renderer=c['renderer'],**result,float64_initialization_match=True,
    maximum_initial_depth_difference_m=float(np.max(np.abs(reference-saved_initial))),
    scope='Partial saved-frame integrity only. No HWM elevations read and no accuracy score computed. Running job/checkpoint not altered.')
(root/f'checkpoint-audit-{n}.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
