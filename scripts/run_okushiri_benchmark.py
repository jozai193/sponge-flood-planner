"""Run SPONGE against published laboratory gauges, without executing ANUGA code.

Fixed 22.5-second, two-resolution diagnostic. Gauge values never calibrate inputs.
The segment candidate splits one wave boundary into two identical named pieces;
this is a compatibility regression, not evidence for distinct coastal forcing.
"""
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import rasterio
from scipy.interpolate import RegularGridInterpolator

from services.api.contracts import SolverConfig
from services.reference.coastal import CoastalBoundary
from services.reference.coastal_segments import CoastalSegments
from services.reference.solver import Solver as Original
from services.reference.solver import Surface
from services.reference.solver_segments_candidate import Solver as Candidate

ROOT=Path('artifacts/validation/okushiri-lab')
GAUGES=((4.521,1.196),(4.521,1.696),(4.521,2.196))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sources=json.loads((ROOT/'sources.json').read_text())
    for item in sources:
        if sha(ROOT/item['file'])!=item['sha256']:raise ValueError('Changed laboratory source')
    files=['services/reference/solver.py','services/reference/coastal.py',
           'services/reference/coastal_segments.py','services/reference/solver_segments_candidate.py',
           'scripts/run_okushiri_benchmark.py']
    protocol={'kind': 'physical_laboratory_diagnostic_not_hurricane_holdout',
        'duration_s': 22.5,'grids': [[64,40],[128,80]],'bounds_m': [0,0,5.448,3.402],
        'preflight_note': 'The upstream example requests 25 seconds but supplied wave input ends at 22.5. Rejected initial 25-second protocol before any simulation; use full supported input interval without extrapolation.',
        'roughness': .0025,'gravity_m_s2': 9.80665,'spatial_order': 2,'cfl': .4,'dt_max_s': .02,
        'initial_stage_m': 0,'output_interval_s': .05,'gauge_xy_m': GAUGES,
        'gauge_source_units': 'cm; divide by 100 for metres',
        'boundary': 'West measured input-wave stage with interior velocity extrapolation; all other faces reflective. No normal-momentum prescription.',
        'candidate': 'Two non-overlapping west segments with identical wave series; unchanged physics elsewhere.',
        'resampling': 'Bilinear native ASCII raster cell centres to model centres; bilinear model stage at gauges.',
        'metrics': ['unshifted RMSE','bias','peak error','peak-time error','mass residual','candidate saved-gauge and final-state differences'],
        'observational_pass_threshold': None,
        'interpretation': 'No calibrated threshold. Report all gauges at both grids; do not shift, scale, demean or select a favourable time window.',
        'source_sha256': {f:sha(Path(f)) for f in files},'input_sources': sources}
    # JSON canonicalization also normalizes tuples for reproducible equality.
    encoded=json.dumps(protocol,indent=2)
    pp=ROOT/'protocol.json'
    if pp.exists() and pp.read_text()!=encoded:raise ValueError('Existing benchmark protocol differs; create a new experiment directory')
    pp.write_text(encoded)
    with rasterio.open(ROOT/'Benchmark_2_Bathymetry.asc') as dataset:
        native=dataset.read(1,masked=True)
        if np.ma.getmaskarray(native).any():raise ValueError('Missing bathymetry')
        tr=dataset.transform
        xx=tr.c+(np.arange(dataset.width)+.5)*tr.a
        yy=(tr.f+(np.arange(dataset.height)+.5)*tr.e)[::-1]
        bed_interp=RegularGridInterpolator((yy,xx),native[::-1],bounds_error=True)
    wave=np.loadtxt(ROOT/'Benchmark_2_input.txt',skiprows=1)
    if not np.isfinite(wave).all() or wave[0,0]!=0 or np.any(np.diff(wave[:,0])<=0) or wave[-1,0]<22.5:
        raise ValueError('Invalid wave time series')
    levels=tuple(map(tuple,wave))
    outputs=[]
    for nx,ny in protocol['grids']:
        dx,dy=5.448/nx,3.402/ny
        x=(np.arange(nx)+.5)*dx;y=(np.arange(ny)+.5)*dy
        Y,X=np.meshgrid(y,x,indexing='ij')
        z=bed_interp(np.stack([Y,X],axis=-1))
        s=Surface(z,dx,dy,roughness=.0025)
        coast=CoastalBoundary('west',tuple(r*nx for r in range(ny)),levels,'laboratory zero metres','Published wave input')
        halves=CoastalSegments(tuple((name,CoastalBoundary('west',cells,levels,coast.datum,coast.source))
              for name,cells in [('south wavemaker',coast.cells[:ny//2]),('north wavemaker',coast.cells[ny//2:])]))
        states=[]
        for label,cls,b in [('original',Original,coast),('segments_candidate',Candidate,halves)]:
            sim=cls(s,SolverConfig(spatial_order=2,dt_max_s=.02),depth=np.maximum(-z,0),coastal=b)
            start=time.monotonic();samples=[]
            for t in np.arange(451)*.05:
                sim.advance(float(t))
                interp=RegularGridInterpolator((y,x),sim.u[...,0]+z,bounds_error=True)
                samples.append(interp([(gy,gx) for gx,gy in GAUGES]).tolist())
                if round(t*20)%100==0:
                    print(json.dumps({'grid': [nx,ny],'engine': label,'time_s': round(t,2),'wall_s': round(time.monotonic()-start,2)}),flush=True)
            ledger=sim.ledger()
            result={'grid': [nx,ny],'engine': label,'time_s': (np.arange(451)*.05).tolist(),
                        'stage_m': samples,'steps': sim.steps,'ledger': ledger,
                        'min_final_depth_m': float(sim.u[...,0].min()),
                        'wall_s': time.monotonic()-start,'accepted_for_diagnostic': bool(ledger['relative_residual']<1e-8)}
            if label=='segments_candidate':result['segment_volumes_m3']=sim.boundary_volumes
            outputs.append(result);states.append(sim.u.copy())
            (ROOT/f'run-{nx}-{label}.json').write_text(json.dumps(result))
        outputs[-1]['max_final_state_difference']=float(np.max(np.abs(states[0]-states[1])))
        outputs[-1]['max_saved_gauge_difference_m']=float(np.max(np.abs(np.asarray(outputs[-2]['stage_m'])-np.asarray(outputs[-1]['stage_m']))))
    # Measurements are used only after both fixed-grid runs have completed.
    observed=np.loadtxt(ROOT/'output_ch5-7-9.txt',skiprows=1)
    if not np.isfinite(observed).all() or np.any(np.diff(observed[:,0])<=0) or observed[0,0]>0 or observed[-1,0]<22.5:
        raise ValueError('Invalid measurement time coverage')
    for out in outputs:
        predicted=np.asarray(out['stage_m']);times=np.asarray(out['time_s']);scores=[]
        for i,name in enumerate(['ch5','ch7','ch9']):
            obs=np.interp(times,observed[:,0],observed[:,i+1]/100)
            residual=predicted[:,i]-obs
            scores.append({'gauge': name,'rmse_m': float(np.sqrt(np.mean(residual**2))),'bias_m': float(residual.mean()),
                'peak_error_m': float(predicted[:,i].max()-obs.max()),
                'peak_time_error_s': float(times[predicted[:,i].argmax()]-times[obs.argmax()]),
                'observed_peak_m': float(obs.max()),'predicted_peak_m': float(predicted[:,i].max())})
        out['scores']=scores
    report={'status': 'completed','production_enabled': False,'general_flood_accuracy_validated': False,
        'interpretation': 'Independent laboratory comparison; coarse regular-grid resampling and our existing wave boundary approximation remain limitations. Identical split forcing checks compatibility, not distinct multi-edge real-world skill.',
        'protocol_sha256': sha(pp),'runs': outputs}
    (ROOT/'results.json').write_text(json.dumps(report,indent=2))
    print(json.dumps([{'grid': o['grid'],'engine': o['engine'],'scores': o['scores'],'mass': o['ledger']['relative_residual']} for o in outputs]),flush=True)


if __name__=='__main__':main()
