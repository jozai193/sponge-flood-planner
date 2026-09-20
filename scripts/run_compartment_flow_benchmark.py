"""Frozen synthetic flow comparison against the existing fine-grid HLL solver."""
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np

from services.api.contracts import SolverConfig
from services.reference.coastal import CoastalBoundary
from services.reference.coastal_segments import CoastalSegments
from services.reference.compartment_flow_candidate import CompartmentFlow, build_graph
from services.reference.solver_segments_candidate import Solver, Surface

ROOT=Path('artifacts/validation/compartment-flow-v1')
CASES=('straight','blocked','narrow_opening','expansion','dry_start')
TIMES=np.arange(0.,121.,1.)


def geometry(case):
    z=np.zeros((16,64));solid=np.ones(z.shape,bool);solid[4:6,:]=False
    solid[7,12:16]=False # isolated pool, sharing coarse row 4:8 with the channel
    if case=='blocked':solid[:,31]=True
    if case=='narrow_opening':solid[4,31]=True
    if case=='expansion':solid[6:8,32:]=False
    return z,solid


def forcing(case):
    if case=='dry_start':return ((0.,0.),(10.,.1),(40.,.1),(60.,0.),(120.,0.))
    return ((0.,.5),(10.,.5),(30.,.52),(50.,.5),(120.,.5))


def arrival(values,threshold):
    i=np.flatnonzero(np.asarray(values)>=threshold)
    return float(TIMES[i[0]]) if len(i) else None


def main():
    ROOT.mkdir(exist_ok=True)
    sources=['scripts/run_compartment_flow_benchmark.py','services/reference/compartment_flow_candidate.py',
        'services/reference/solver_segments_candidate.py','services/reference/solver.py','services/reference/coastal.py',
        'services/reference/coastal_segments.py','services/api/contracts.py']
    protocol={'scope': 'Controlled flat-bed permanent-wall local-inertial candidate, compared with full HLL fine-grid reference',
        'cases': list(CASES),'orientations': ['east','north'],'fine_spacing_m': 1,'coarse_grouping': 4,
        'domain_m': [64,16],'duration_s': 120,'output_s': 1,'roughness': .025,
        'initial_level_wet_m': .5,'pocket_initially_dry': True,'initial_discharge': 0,
        'reference': {'spatial_order': 2,'dt_max_s': .05},'candidate': {'dt_max_s': .05},
        'forcing': {c:forcing(c) for c in CASES},'gauges_fine_row_col': [[4,8],[4,28],[4,52]],
        'gates': {'mass_relative_max': 1e-10,'isolated_pool_depth_max_m': 1e-12,'barrier_downstream_change_max_m': 1e-12,
            'wet_case_stage_rmse_max_m': .005,'wet_case_peak_error_max_m': .01,'wet_case_arrival_error_max_s': 3.,
            'arrival_threshold_above_initial_m': .005,'dry_case_stage_rmse_max_m': .02,
            'dry_case_arrival_error_max_s': 5.,'dry_case_arrival_depth_m': .01,
            'downstream_recession_rmse_max_m': .005,'rotation_depth_max_m': 1e-12},
        'acceptance': 'Every declared gate must pass before advancing this candidate; failures retained, no post-result threshold edits.',
        'limitations': ['Local inertial equations omit advective acceleration; dry fronts and constrictions are intentional challenges.',
            'Flat bed per compartment only; no internal sill/overtopping support. Not a Dorian-ready solver.',
            'Reference is numerical, not independent observed flood data.'],
        'sources_sha256': {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in sources},'production_enabled': False}
    pp=ROOT/'protocol.json';encoded=json.dumps(protocol,indent=2)
    if pp.exists() and pp.read_text()!=encoded:raise ValueError('Frozen protocol changed')
    pp.write_text(encoded)
    results=[];rotation={}
    for case in CASES:
        z0,wall0=geometry(case)
        for orientation in ('east','north'):
            # Transpose maps increasing columns to increasing rows without a reflection.
            z,wall=(z0,wall0) if orientation=='east' else (z0.T,wall0.T)
            ny,nx=z.shape;edge='west' if orientation=='east' else 'south';far='east' if orientation=='east' else 'north'
            h0=0. if case=='dry_start' else .5
            initial=np.where(wall,0.,h0);pocket=(7,slice(12,16)) if orientation=='east' else (slice(12,16),7)
            initial[pocket]=0.
            levels=forcing(case)
            nearcells=tuple(r*nx for r in range(ny) if not wall[r,0]) if edge=='west' else tuple(c for c in range(nx) if not wall[0,c])
            farcells=tuple(r*nx+nx-1 for r in range(ny) if not wall[r,-1]) if far=='east' else tuple((ny-1)*nx+c for c in range(nx) if not wall[-1,c])
            boundary=CoastalSegments((('upstream',CoastalBoundary(edge,nearcells,levels,'local metres','Frozen synthetic pulse')),
                ('downstream',CoastalBoundary(far,farcells,((0.,h0),),'local metres','Fixed downstream reservoir'))))
            fine=Solver(Surface(z,1.,1.,solid=wall,roughness=.025),SolverConfig(spatial_order=2,dt_max_s=.05),depth=initial,coastal=boundary)
            graph=build_graph(z,wall,4)
            stage=np.zeros(len(graph.area))
            for node in range(len(stage)):stage[node]=float(initial[graph.labels==node].mean())
            fn=lambda t, levels=levels:float(np.interp(t,*np.asarray(levels).T))
            candidate=CompartmentFlow(graph,stage,{edge:fn,far:lambda t, h0=h0:h0},roughness=.025,dt_max=.05)
            gauges=[(r,c) if orientation=='east' else (c,r) for r,c in protocol['gauges_fine_row_col']]
            traces={'fine_hll':[],'candidate':[]};volume={'fine_hll':[],'candidate':[]}
            worstmass={'fine_hll':0.,'candidate':0.};drymax=0.;negative=0.;start=time.monotonic()
            for t in TIMES:
                fine.advance(float(t));candidate.advance(float(t));h=candidate.fine_depth()
                traces['fine_hll'].append([float(fine.u[r,c,0]) for r,c in gauges]);traces['candidate'].append([float(h[r,c]) for r,c in gauges])
                volume['fine_hll'].append(float(fine.u[...,0].sum()));volume['candidate'].append(float(candidate.volume.sum()))
                for name,sim in [('fine_hll',fine),('candidate',candidate)]:worstmass[name]=max(worstmass[name],sim.ledger()['relative_residual'])
                drymax=max(drymax,float(h[pocket].max()),float(fine.u[...,0][pocket].max()))
                negative=min(negative,float(h.min()),float(fine.u[...,0].min()))
            ref=np.asarray(traces['fine_hll']);cand=np.asarray(traces['candidate']);threshold=h0+(.01 if case=='dry_start' else .005)
            scores=[]
            for k in range(3):
                ar=arrival(ref[:,k],threshold);ac=arrival(cand[:,k],threshold)
                lag=abs(ar-ac) if ar is not None and ac is not None else 0. if ar is None and ac is None else None
                scores.append({'gauge': k,'rmse_m': float(np.sqrt(np.mean((cand[:,k]-ref[:,k])**2))),
                    'peak_error_m': float(cand[:,k].max()-ref[:,k].max()),'reference_arrival_s': ar,'candidate_arrival_s': ac,'arrival_error_s': lag})
            recession=float(np.sqrt(np.mean((cand[TIMES>=60,-1]-ref[TIMES>=60,-1])**2)))
            barrier=max(float(np.max(np.abs(cand[:,-1]-h0))),float(np.max(np.abs(ref[:,-1]-h0)))) if case=='blocked' else None
            gates={'mass': all(v<=1e-10 for v in worstmass.values()),'nonnegative': negative>=0,'isolated_pool': drymax<=1e-12,
                'stage': all(s['rmse_m']<=(.02 if case=='dry_start' else .005) for s in scores),
                'arrival': all(s['arrival_error_s'] is not None and s['arrival_error_s']<=(5 if case=='dry_start' else 3) for s in scores),
                'recession': recession<=.005,'barrier': barrier is None or barrier<=1e-12,
                'peak': all(abs(s['peak_error_m'])<=.01 for s in scores) if case!='dry_start' else True}
            item={'case': case,'orientation': orientation,'compartments': len(graph.area),'fine_open_cells': int((~wall).sum()),
                'seconds': time.monotonic()-start,'scores': scores,'downstream_recession_rmse_m': recession,
                'max_mass_residual': worstmass,'isolated_pool_max_depth_m': drymax,'barrier_downstream_change_m': barrier,
                'gates': gates,'all_gates_passed': all(gates.values()),'candidate_max_froude': candidate.max_froude,
                'candidate_limited_steps': candidate.limited_steps,'ledgers': {'fine_hll': fine.ledger(),'candidate': candidate.ledger()},
                'final_storage_difference_m3': volume['candidate'][-1]-volume['fine_hll'][-1]}
            name=f'{case}-{orientation}'
            (ROOT/f'{name}.json').write_text(json.dumps({'times_s': TIMES.tolist(),'traces': traces,'volumes_m3': volume,'result': item},indent=2))
            if orientation=='east':rotation[case]=h.T.copy()
            else:item['rotation_max_depth_difference_m']=float(np.max(np.abs(rotation[case]-h)))
            results.append(item)
            (ROOT/'progress.json').write_text(json.dumps({'completed': len(results),'total': 10,'latest': name}))
            print(json.dumps({'case': case,'orientation': orientation,'gates': gates,'rmse': [s['rmse_m'] for s in scores]}),flush=True)
    rotation_pass=all(r.get('rotation_max_depth_difference_m',0)<=1e-12 for r in results)
    result={'status': 'completed','runs': results,'rotation_passed': rotation_pass,
        'candidate_gate_passed': all(r['all_gates_passed'] for r in results) and rotation_pass,
        'production_enabled': False,'general_flood_accuracy_validated': False}
    (ROOT/'results.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'candidate_gate_passed': result['candidate_gate_passed']}))


if __name__=='__main__':main()
