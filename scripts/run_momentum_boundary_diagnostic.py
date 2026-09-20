"""Factorial open/closed and full/reduced momentum diagnostic, frozen before runs."""
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np

from scripts.run_refined_compartment_benchmark import scene
from services.api.contracts import SolverConfig
from services.reference.coastal import CoastalBoundary
from services.reference.coastal_segments import CoastalSegments
from services.reference.compartment_flow_candidate import CompartmentFlow, build_graph
from services.reference.momentum_diagnostic import MomentumDiagnosticSolver
from services.reference.solver_segments_candidate import Surface

ROOT=Path('artifacts/validation/momentum-boundary-v1')
TIMES=np.arange(181.)
GAUGES=[(4,8),(4,16),(4,28),(4,52)]
CASES=['open_island','closed_island','closed_straight']


def geometry(case):
    z,wall,initial,levels=scene('wide_short_pulse')
    if case!='open_island':
        if case=='closed_straight':wall[5:7,24:28]=False
        initial[4:8,:12]=.07
        levels=None
    return z,wall,initial,levels


def model(case,kind):
    z,wall,h,levels=geometry(case)
    if kind=='graph_local_inertial':
        graph=build_graph(z,wall,1)
        boundaries={} if levels is None else {'west':lambda t:float(np.interp(t,*np.asarray(levels).T)), 'east':lambda t:0.}
        return CompartmentFlow(graph,h[~wall],boundaries,dt_max=.025),wall
    boundary=None
    if levels is not None:
        ny,nx=z.shape
        boundary=CoastalSegments((('upstream',CoastalBoundary('west',tuple(r*nx for r in range(ny) if not wall[r,0]),levels,'local metres','Fixed pulse')),
            ('downstream',CoastalBoundary('east',tuple(r*nx+nx-1 for r in range(ny) if not wall[r,-1]),((0.,0.),),'local metres','Dry reservoir'))))
    return MomentumDiagnosticSolver(Surface(z,1.,1.,solid=wall,roughness=.025),
        SolverConfig(spatial_order=2,dt_max_s=.025,boundary='closed'),depth=h,coastal=boundary,
        advective_momentum=kind=='hll_full'),wall


def metrics(a,b):
    result=[]
    for k in range(len(GAUGES)):
        thresholds=[]
        for threshold in (1e-5,.001,.01):
            ai=np.flatnonzero(a[:,k]>=threshold);bi=np.flatnonzero(b[:,k]>=threshold)
            ac=int(ai[0]) if len(ai) else None;bc=int(bi[0]) if len(bi) else None
            thresholds.append({'threshold_m': threshold,'candidate_arrival_s': ac,'full_hll_arrival_s': bc,
                'signed_arrival_difference_s': ac-bc if ac is not None and bc is not None else None,
                'both_never': ac is None and bc is None})
        result.append({'gauge': k,'rmse_m': float(np.sqrt(np.mean((a[:,k]-b[:,k])**2))),'thresholds': thresholds})
    return result


def main():
    ROOT.mkdir(exist_ok=True)
    paths=['scripts/run_momentum_boundary_diagnostic.py','services/reference/momentum_diagnostic.py',
        'services/reference/solver_segments_candidate.py','services/reference/compartment_flow_candidate.py',
        'services/reference/coastal.py','services/reference/coastal_segments.py','services/api/contracts.py',
        'scripts/run_refined_compartment_benchmark.py','scripts/run_compartment_flow_benchmark.py']
    protocol={'scope': 'Mechanism diagnosis, not a deployable candidate or observed accuracy test',
        'cases': CASES,'models': ['hll_full','hll_no_advection','graph_local_inertial'],
        'grid_spacing_m': 1.,'duration_s': 180,'dt_max_s': .025,'roughness': .025,'gauges': GAUGES,
        'closed_initial_depth_m': .07,'closed_initial_wet_columns': [0,12],'thresholds_m': [1e-5,.001,.01],
        'numerical_gates': {'mass_relative_max': 1e-10,'nonnegative': True,'closed_exchange_max_m3': 1e-10},
        'discrimination': 'Closed cases eliminate external exchange. Full versus no-advection HLL shares reconstruction, integration, friction and wall treatment; momentum fluxes and corresponding wave speeds differ.',
        'limits': ['Open runs share ghost construction for both HLL equations, not necessarily identical fluxes.',
                'Graph versus HLL also differs in staggering, numerical diffusion and friction discretization.',
                'Closed pulse differs from original forcing; it tests whether boundary mismatch is necessary, not a percentage attribution for the original case.',
                'One-metre diagnosis is not a convergence proof.'],
        'source_sha256': {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths},
        'literature': 'https://agupubs.onlinelibrary.wiley.com/doi/abs/10.1002/wrcr.20366','production_enabled': False}
    pp=ROOT/'protocol.json';encoded=json.dumps(protocol,indent=2)
    if pp.exists() and pp.read_text()!=encoded:raise ValueError('Frozen protocol changed')
    pp.write_text(encoded);runs=[]
    for case in CASES:
        for kind in protocol['models']:
            path=ROOT/f'{case}-{kind}.json'
            if path.exists():runs.append(json.loads(path.read_text())['result']);continue
            sim,wall=model(case,kind);traces=[];fields=[];volumes=[];mass=0.;minh=0.;error=None
            start=time.perf_counter()
            try:
                for t in TIMES:
                    sim.advance(float(t));h=sim.fine_depth() if kind=='graph_local_inertial' else sim.u[...,0].copy()
                    if not np.isfinite(h).all():raise ValueError('Nonfinite depth')
                    minh=min(minh,float(h.min()));mass=max(mass,sim.ledger()['relative_residual'])
                    fields.append(h);traces.append([float(h[r,c]) for r,c in GAUGES]);volumes.append(sim.ledger())
                    if t%60==0:print(json.dumps({'case': case,'model': kind,'seconds_simulated': t}),flush=True)
            except Exception as exc:  # noqa: BLE001 - each diagnostic failure is retained in the result set.
                error=f'{type(exc).__name__}: {exc}'
            ledger=sim.ledger();closed_exchange=abs(ledger['inflow_m3'])+abs(ledger['outflow_m3']) if case!='open_island' else None
            gates={'completed': error is None and len(traces)==len(TIMES),'mass': mass<=1e-10,
                       'nonnegative': minh>=0,'closed_exchange': closed_exchange is None or closed_exchange<=1e-10}
            row={'case': case,'model': kind,'status': 'completed' if error is None else 'failed','error': error,
                'frames': len(traces),'simulated_time_s': sim.time,'elapsed_s': time.perf_counter()-start,
                'mass_relative_max': mass,'min_depth_m': minh,'ledger': ledger,'closed_exchange_m3': closed_exchange,
                'numerical_gates': gates,'numerical_gates_passed': all(gates.values())}
            path.write_text(json.dumps({'times_s': TIMES[:len(traces)].tolist(),'traces': traces,'volume_ledgers': volumes,'result': row},indent=2))
            np.savez_compressed(ROOT/f'{case}-{kind}-fields.npz',depth=np.asarray(fields),solid=wall)
            runs.append(row);print(json.dumps(row),flush=True)
    comparisons=[]
    for case in CASES:
        full=json.loads((ROOT/f'{case}-hll_full.json').read_text())
        for kind in ('hll_no_advection','graph_local_inertial'):
            other=json.loads((ROOT/f'{case}-{kind}.json').read_text())
            ready=full['result']['numerical_gates_passed'] and other['result']['numerical_gates_passed']
            comparisons.append({'case': case,'model': kind,'eligible': ready,
                'gauges': metrics(np.asarray(other['traces']),np.asarray(full['traces'])) if ready else None})
    (ROOT/'results.json').write_text(json.dumps({'status': 'completed','runs': runs,'comparisons': comparisons,
        'production_enabled': False,'general_flood_accuracy_validated': False},indent=2))


if __name__=='__main__':main()
