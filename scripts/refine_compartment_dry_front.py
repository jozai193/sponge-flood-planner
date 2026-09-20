"""Separate coarse grouping effects from local-inertial dynamics on the failed front."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np

from scripts.run_compartment_flow_benchmark import TIMES, forcing, geometry
from services.reference.compartment_flow_candidate import CompartmentFlow, build_graph

ROOT=Path('artifacts/validation/compartment-flow-v1/grouping-diagnosis')


def main():
    ROOT.mkdir(exist_ok=True);parent=ROOT.parent
    sources=['scripts/refine_compartment_dry_front.py','services/reference/compartment_flow_candidate.py',
        'scripts/run_compartment_flow_benchmark.py',str(parent/'reference-refinement/dry_start.json')]
    protocol={'scope': 'Dry-front grouping diagnosis, same candidate equations and physical geometry',
        'groupings': [1,2],'original_grouping': 4,'dt_max_s': .05,'roughness': .025,'thresholds_m': [1e-5,.001,.01],
        'declared_after_front_mismatch': True,'production_enabled': False,
        'source_sha256': {f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in sources}}
    encoded=json.dumps(protocol,indent=2);pp=ROOT/'protocol.json'
    if pp.exists() and pp.read_text()!=encoded:raise ValueError('Frozen diagnosis changed')
    pp.write_text(encoded)
    ref=np.asarray(json.loads((parent/'reference-refinement/dry_start.json').read_text())['refined_traces'])
    runs=[]
    for factor in (1,2,4):
        if factor==4:traces=json.loads((parent/'dry_start-east.json').read_text())['traces']['candidate']
        else:
            z,wall=geometry('dry_start');levels=np.asarray(forcing('dry_start'))
            sim=CompartmentFlow(build_graph(z,wall,factor),0.,
                {'west':lambda t, levels=levels:float(np.interp(t,*levels.T)),'east':lambda t:0.},roughness=.025,dt_max=.05)
            traces=[]
            for t in TIMES:
                sim.advance(float(t));h=sim.fine_depth();traces.append([float(h[4,c]) for c in (8,28,52)])
        values=np.asarray(traces);thresholds=[]
        for threshold in protocol['thresholds_m']:
            wet=values[:,-1]>=threshold;truth=ref[:,-1]>=threshold;idx=np.flatnonzero(wet)
            thresholds.append({'threshold_m': threshold,'downstream_first_crossing_s': float(TIMES[idx[0]]) if len(idx) else None,
                'downstream_false_wet_frames': int(np.sum(wet&~truth))})
        runs.append({'grouping': factor,'rmse_m': np.sqrt(np.mean((values-ref)**2,axis=0)).tolist(),
            'downstream_peak_depth_m': float(values[:,-1].max()),'thresholds': thresholds,'traces': traces})
        print(json.dumps({k:v for k,v in runs[-1].items() if k!='traces'}),flush=True)
    result={'status': 'completed','runs': runs,'production_enabled': False,
        'interpretation': 'Finer grouping changes spatial discretization while retaining local-inertial equations and reservoir treatment. It does not independently isolate momentum approximation from boundary differences.'}
    (ROOT/'results.json').write_text(json.dumps(result,indent=2))


if __name__=='__main__':main()
