"""Create float64 coastal fixtures independently of the GPU results."""
import json
from pathlib import Path

import numpy as np

from services.api.contracts import SolverConfig
from services.reference.coastal import CoastalBoundary
from services.reference.solver import Solver, Surface

cases=[]
for edge,cells in {'west':[0,4,8,12],'east':[3,7,11,15],'south':[0,1,2,3],'north':[12,13,14,15]}.items():
    levels=((0.,.2),(10.,.6),(20.,.2),(30.,.2))
    boundary=CoastalBoundary(edge,tuple(cells),levels,'local metres','analytic verification fixture')
    solver=Solver(Surface(np.zeros((4,4)),2,2,roughness=.035),
        SolverConfig(spatial_order=2,dt_max_s=.05),depth=.2,coastal=boundary)
    solver.advance(30)
    cases.append({'edge': edge,'cells': cells,'levels': [{'timeS': t,'elevationM': h} for t,h in levels],
        'depth': solver.u[...,0].ravel().tolist(),'maxDepth': solver.max_depth.ravel().tolist(),
        'ledger': solver.ledger(),'duration_s': 30,'max_step_s': .05})
# A rectangular grid with unequal face widths and a partial boundary catches
# orientation/flux-area errors that a square, all-open-edge fixture can hide.
z=np.array([[0,.03,.08,.1,.02],[.01,.07,.15,.05,0],[.03,0,.1,.02,.04],[0,.05,.08,0,.02]])
solid=np.zeros((4,5),bool);solid[1,2]=True
surface=Surface(z,2,7,solid=solid,roughness=.035)
levels=((0.,.2),(10.,.6),(20.,.2),(30.,.2))
boundary=CoastalBoundary('east',(4,14,19),levels,'local metres','rectangular partial-edge fixture')
initial=boundary.initial_depth(surface)
solver=Solver(surface,SolverConfig(spatial_order=2,dt_max_s=.05),depth=initial,coastal=boundary)
solver.advance(30)
cases.append({'edge': 'east','case_name': 'rectangular-partial-edge','cells': [4,14,19],
    'nx': 5,'ny': 4,'dx': 2,'dy': 7,'z': z.ravel().tolist(),'solid': solid.astype(int).ravel().tolist(),'initial': initial.ravel().tolist(),
    'levels': [{'timeS': t,'elevationM': h} for t,h in levels],'depth': solver.u[...,0].ravel().tolist(),
    'maxDepth': solver.max_depth.ravel().tolist(),'ledger': solver.ledger(),'duration_s': 30,'max_step_s': .05})
folder=Path('artifacts/validation/coastal-reference');folder.mkdir(parents=True,exist_ok=True)
(folder/'float64.json').write_text(json.dumps({'cases': cases,
    'limitation': 'Independent float64 implementation of the same HLL boundary assumptions. Agreement verifies implementation, not real coastal flood accuracy.'},indent=2))
print('Saved',len(cases),'float64 coastal fixtures')
