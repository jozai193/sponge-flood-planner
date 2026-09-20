"""Controlled reference for simultaneous rainfall, inflow and coastal exchange."""

if not __debug__:
    raise RuntimeError("Integrity verification is disabled under python -O; rerun without optimization.")
import json
from pathlib import Path

import numpy as np

from services.api.contracts import SolverConfig
from services.reference.coastal import CoastalBoundary
from services.reference.solver import Solver, Surface


def main():
    results=[]
    for rain_on,inflow_on in [(True,True),(False,True),(True,False)]:
        inflow=np.zeros((4,4));inflow[3,3]=.01 if inflow_on else 0
        s=Surface(np.zeros((4,4)),2,3,roughness=.03,rain_weights=np.ones((4,4)),
                  inflow_m3_s=inflow,inflow_start_s=0,inflow_end_s=10)
        b=CoastalBoundary('west',(0,4,8,12),((0.,.2),(5.,.4),(10.,.2),(20.,.2)),'local metres','controlled composition test')
        solver=Solver(s,SolverConfig(spatial_order=2,dt_max_s=.05),depth=b.initial_depth(s),coastal=b)
        solver.advance(5,.0005 if rain_on else 0);solver.advance(20,0)
        ledger=solver.ledger()
        assert ledger['relative_residual']<1e-8
        assert abs(ledger['rain_m3']-(.24 if rain_on else 0))<1e-10
        results.append({'rain':rain_on,'inflow':inflow_on,'depth':solver.u[...,0].ravel().tolist(),'ledger':ledger})
    out=Path('artifacts/verification/scenario-composition-v1');out.mkdir(parents=True,exist_ok=True)
    (out/'cpu-reference.json').write_text(json.dumps(results,indent=2))
    print('3 controlled combined-forcing CPU runs passed conservation and rainfall totals.')


if __name__=='__main__':main()
