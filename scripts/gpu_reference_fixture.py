"""Generate controlled CPU outputs for independent GPU parity checks."""
import json
from pathlib import Path

import numpy as np

from services.api.contracts import SolverConfig
from services.reference.solver import Solver, Surface

n=16
z=np.zeros((n,n));depth=np.zeros_like(z);depth[:,:8]=.25
surface=Surface(z,1,1,roughness=0)
solver=Solver(surface,SolverConfig(spatial_order=1),depth)
solver.advance(1)
path=Path('tests/fixtures/cpu-dam-break.json');path.parent.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps({'case':'controlled closed dam break','engine':'cpu-hll-float64','nx':n,'ny':n,'dx':1,'end_s':1,'initial':depth.ravel().tolist(),'depth':solver.u[...,0].ravel().tolist(),'ledger':solver.ledger()},indent=2))
print(path)
