"""Frozen outgoing-pulse comparison against a longer computational domain.

The same discretization runs on a twice-longer channel where the wave has not
reached the far wall. This is a numerical boundary test, not observed flood data.
"""
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np

from services.api.contracts import SolverConfig
from services.reference.characteristic_boundary import CharacteristicBoundary
from services.reference.coastal import CoastalBoundary
from services.reference.coastal_segments import CoastalSegments
from services.reference.solver import G, Surface
from services.reference.solver_segments_candidate import Solver as StageSolver
from services.reference.solver_wave_candidate import Solver as WaveSolver

ROOT=Path('artifacts/validation/wave-boundary-v1')


def main():
    ROOT.mkdir(exist_ok=True)
    files=['scripts/run_wave_boundary_experiment.py','services/reference/solver.py','services/reference/coastal.py',
        'services/reference/coastal_segments.py','services/reference/solver_segments_candidate.py',
        'services/reference/solver_wave_candidate.py','services/reference/characteristic_boundary.py']
    protocol={'kind': 'synthetic_outgoing_wave_not_historical_holdout',
        'short_length_m': 80,'long_length_m': 160,'width_m': 4,'spacing_m': 1,'background_depth_m': 1,
        'amplitude_m': .02,'pulse_center_m': 30,'pulse_sigma_m': 4,'duration_s': 30,'output_s': 1,
        'initial_velocity': 'Right-going simple wave: u=2*(sqrt(g*h)-sqrt(g*background_depth))',
        'orientations': ['east','north'],'roughness': 0,'spatial_order': 2,'dt_max_s': .03,
        'candidate_input': 'Zero incoming wave perturbation about background stage 1 m; NOT total observed gauge stage',
        'gates': {'relative_mass_residual_max': 1e-10,'nonnegative_depth': True,
                   'final_stage_rmse_ratio_max': .25,'orientation_max_abs_difference_m': 1e-12},
        'source_sha256': {f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files},
        'methodological_source': 'https://anuga.readthedocs.io/en/develop/reference/generated/anuga.Characteristic_wave_boundary.html',
        'production_enabled': False}
    pp=ROOT/'protocol.json';encoded=json.dumps(protocol,indent=2)
    if pp.exists() and pp.read_text()!=encoded:raise ValueError('Frozen protocol changed')
    pp.write_text(encoded)
    results=[]
    for edge in protocol['orientations']:
        states={};profiles={}
        for name,length in [('long_reference',160),('prescribed_stage',80),('characteristic',80)]:
            nx,ny=(length,4) if edge=='east' else (4,length)
            s=Surface(np.zeros((ny,nx)),1,1,roughness=0)
            x=np.arange(length)+.5;h=1+.02*np.exp(-((x-30)/4)**2)
            initial=np.tile(h,(4,1)) if edge=='east' else np.tile(h[:,None],(1,4))
            cell_end=tuple(r*nx+nx-1 for r in range(ny)) if edge=='east' else tuple(range((ny-1)*nx,ny*nx))
            cell_start=tuple(r*nx for r in range(ny)) if edge=='east' else tuple(range(nx))
            far=CharacteristicBoundary(edge,cell_end,((0.,1.),),'local m','No incoming wave',1.) if name=='characteristic' else CoastalBoundary(edge,cell_end,((0.,1.),),'local m','Fixed reservoir')
            near=CoastalBoundary('west' if edge=='east' else 'south',cell_start,((0.,1.),),'local m','Fixed reservoir')
            boundary=CoastalSegments((('near',near),('far',far)))
            cls=WaveSolver if name=='characteristic' else StageSolver
            sim=cls(s,SolverConfig(spatial_order=2,dt_max_s=.03),depth=initial,coastal=boundary)
            sim.u[...,1 if edge=='east' else 2]=initial*2*(np.sqrt(G*initial)-np.sqrt(G))
            saved=[];start=time.monotonic()
            for t in range(31):
                sim.advance(t)
                profile=sim.u[1,:,0] if edge=='east' else sim.u[:,1,0]
                saved.append(profile[:80].tolist())
            states[name]=np.asarray(saved);profiles[name]=saved
            results.append({'orientation': edge,'method': name,'ledger': sim.ledger(),'steps': sim.steps,
                'min_depth_m': float(sim.u[...,0].min()),'wall_s': time.monotonic()-start,'segment_volumes_m3': sim.boundary_volumes})
            print(json.dumps({'orientation': edge,'method': name,'done': True}),flush=True)
        base=np.sqrt(np.mean((states['prescribed_stage'][-1]-states['long_reference'][-1])**2))
        candidate=np.sqrt(np.mean((states['characteristic'][-1]-states['long_reference'][-1])**2))
        results.append({'orientation': edge,'final_stage_rmse_baseline_m': float(base),
            'final_stage_rmse_candidate_m': float(candidate),'ratio': float(candidate/base),
            'rmse_gate_passed': bool(candidate<=.25*base)})
        (ROOT/f'profiles-{edge}.json').write_text(json.dumps(profiles))
    a=json.loads((ROOT/'profiles-east.json').read_text());b=json.loads((ROOT/'profiles-north.json').read_text())
    rotation=max(float(np.max(np.abs(np.asarray(a[k])-np.asarray(b[k])))) for k in a)
    mass_ok=all(r['ledger']['relative_residual']<=1e-10 and r['min_depth_m']>=0 for r in results if 'ledger' in r)
    report={'status': 'completed','results': results,'rotation_max_difference_m': rotation,'mass_gate_passed': mass_ok,
        'numerical_gate_passed': bool(mass_ok and rotation<=1e-12 and all(r['rmse_gate_passed'] for r in results if 'rmse_gate_passed' in r)),
        'production_enabled': False,'general_flood_accuracy_validated': False,
        'conclusion_scope': 'Numerical reflection suppression for a wet subcritical outgoing pulse only; total gauge forcing and wet/dry/supercritical boundaries are not covered.'}
    (ROOT/'results.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))


if __name__=='__main__':main()
