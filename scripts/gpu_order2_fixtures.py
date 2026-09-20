"""Reproducible CPU reference fixtures for the order-2 GPU reconstruction."""
import json
from pathlib import Path

import numpy as np

from services.api.contracts import SolverConfig
from services.reference.solver import Solver, Surface

n=24
y,x=np.mgrid[:n,:n]
hill=.12*np.exp(-((x-12)**2+(y-12)**2)/30)
cases=[]
for name,z,depth in [
    ('lake',hill,.5-hill),
    ('smooth-wave',hill,.5-hill+.03*np.exp(-((x-7)**2+(y-12)**2)/8)),
    ('dry-front',np.zeros_like(hill),np.where(x<12,.2,0.)),
]:
    solver=Solver(Surface(z,1,1,roughness=0),SolverConfig(spatial_order=2),depth)
    solver.advance(1)
    cases.append({'name': name,'nx': n,'ny': n,'end_s': 1,'z': z.ravel().tolist(),'initial': depth.ravel().tolist(),'depth': solver.u[...,0].ravel().tolist(),'ledger': solver.ledger()})
Path('tests/fixtures/cpu-order2.json').write_text(json.dumps(cases),encoding='utf-8')
