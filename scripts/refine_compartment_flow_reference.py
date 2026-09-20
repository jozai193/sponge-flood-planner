"""Check selected fine HLL references at half spacing, with unchanged geometry."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np

from scripts.run_compartment_flow_benchmark import TIMES, arrival, forcing, geometry
from services.api.contracts import SolverConfig
from services.reference.coastal import CoastalBoundary
from services.reference.coastal_segments import CoastalSegments
from services.reference.solver_segments_candidate import Solver, Surface

ROOT=Path('artifacts/validation/compartment-flow-v1/reference-refinement')


def main():
    ROOT.mkdir(exist_ok=True)
    parent=ROOT.parent
    original=json.loads((parent/'protocol.json').read_text())
    for p,h in original['sources_sha256'].items():
        if hashlib.sha256(Path(p).read_bytes()).hexdigest()!=h:raise ValueError('Parent source changed')
    sources=['scripts/refine_compartment_flow_reference.py',str(parent/'protocol.json')]+list(original['sources_sha256'])
    protocol={'scope': 'Reference-resolution audit; no candidate changes','cases': ['straight','narrow_opening','dry_start'],
        'spacing_m': .5,'dt_max_s': .025,'geometry': 'Repeat every 1 m source cell into 2 x 2 cells; physical walls unchanged',
        'sampling': 'Average the 2 x 2 refined cells covering each original gauge cell',
        'source_sha256': {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources},
        'gates': {'wet_reference_rmse_max_m': .0025,'dry_reference_rmse_max_m': .01,
                   'wet_arrival_change_max_s': 2,'dry_arrival_change_max_s': 3,'mass_relative_max': 1e-10},
        'declared_after_initial_comparison': True,'production_enabled': False}
    encoded=json.dumps(protocol,indent=2);pp=ROOT/'protocol.json'
    if pp.exists() and pp.read_text()!=encoded:raise ValueError('Frozen refinement protocol changed')
    pp.write_text(encoded);runs=[]
    for case in protocol['cases']:
        old=json.loads((parent/f'{case}-east.json').read_text())
        z,wall=geometry(case);z=z.repeat(2,0).repeat(2,1);wall=wall.repeat(2,0).repeat(2,1)
        ny,nx=z.shape;h0=0 if case=='dry_start' else .5;initial=np.where(wall,0,h0)
        initial[14:16,24:32]=0
        west=tuple(r*nx for r in range(ny) if not wall[r,0]);east=tuple(r*nx+nx-1 for r in range(ny) if not wall[r,-1])
        boundary=CoastalSegments((('upstream',CoastalBoundary('west',west,forcing(case),'local metres','Frozen synthetic pulse')),
            ('downstream',CoastalBoundary('east',east,((0.,h0),),'local metres','Fixed downstream reservoir'))))
        sim=Solver(Surface(z,.5,.5,solid=wall,roughness=.025),SolverConfig(spatial_order=2,dt_max_s=.025),depth=initial,coastal=boundary)
        traces=[];maxmass=0.
        for t in TIMES:
            sim.advance(float(t));traces.append([float(sim.u[r*2:r*2+2,c*2:c*2+2,0].mean()) for r,c in original['gauges_fine_row_col']])
            maxmass=max(maxmass,sim.ledger()['relative_residual'])
        fine=np.asarray(traces);previous=np.asarray(old['traces']['fine_hll']);candidate=np.asarray(old['traces']['candidate'])
        changes=np.sqrt(np.mean((fine-previous)**2,axis=0));canderror=np.sqrt(np.mean((fine-candidate)**2,axis=0))
        threshold=h0+(.01 if case=='dry_start' else .005);lags=[]
        for i in range(3):
            a=arrival(fine[:,i],threshold);b=arrival(previous[:,i],threshold)
            lags.append(abs(a-b) if a is not None and b is not None else 0 if a is None and b is None else None)
        passed=bool(np.all(changes<=(.01 if case=='dry_start' else .0025)) and
            all(t is not None and t<=(3 if case=='dry_start' else 2) for t in lags) and maxmass<=1e-10)
        row={'case': case,'reference_change_rmse_m': changes.tolist(),'candidate_vs_refined_rmse_m': canderror.tolist(),
            'reference_arrival_change_s': lags,'mass_relative_max': maxmass,'reference_gate_passed': passed,
            'final_ledger': sim.ledger()}
        (ROOT/f'{case}.json').write_text(json.dumps({'times_s': TIMES.tolist(),'refined_traces': traces,'result': row},indent=2))
        runs.append(row);print(json.dumps(row),flush=True)
    report={'status': 'completed','runs': runs,'reference_gates_passed': all(r['reference_gate_passed'] for r in runs),
        'production_enabled': False,'limitation': 'A resolution check against the same HLL equations is not observed flood validation.'}
    (ROOT/'results.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
