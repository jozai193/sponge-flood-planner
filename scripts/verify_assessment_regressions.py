"""Re-score unchanged saved model outputs after observation-handling changes."""
import json
from pathlib import Path

import numpy as np

from services.reference.observations import compare_peak_elevations
from services.reference.validation_regression import compare_assessments

root=Path('artifacts/validation');results=[]
for name in ('sandy-2012','michael-2018'):
    folder=root/name;audit=json.loads((folder/'accuracy.json').read_text())
    for old in audit['runs']:
        n=old['grid_cells'];sim=json.loads((folder/f'simulation-{n}.json').read_text())
        bundle=Path('data/local/bundles')/old['bundle_id'];m=json.loads((bundle/'manifest.json').read_text());g=m['grid'];shape=(g['ny'],g['nx'])
        geo=json.loads((folder/f'observations-{n}.geojson').read_text())
        crs=geo.get('crs',{}).get('properties',{}).get('name','EPSG:4326')
        new=compare_peak_elevations(m,np.array(sim['frames'][-1]['maxDepth']).reshape(shape),np.fromfile(bundle/'z.bin',dtype='<f4').reshape(shape),
            np.fromfile(bundle/'solid.bin',dtype='u1').reshape(shape),geo['features'],crs,audit['event_id'],audit['event_id'],'NAVD88')
        new['mass_gate_passed']=old['mass_gate_passed']
        for before,after in zip(old['samples'],new['samples']):
            for key in ('observation_id','status','row','col','predicted_elevation_m','error_m'):
                if before.get(key)!=after.get(key):raise ValueError(f'{name} {n} changed {key} at {before["observation_id"]}')
        gate=compare_assessments(old,new) if old['compared_count'] else {'statistical_gate': 'not_applicable_no_supported_points'}
        if old['compared_count'] and not gate['regression_gate_passed']:raise ValueError('Regression failed')
        results.append(dict(event=name,grid_cells=n,exact_status_and_prediction_match=True,**gate))
(root/'assessment-regression-audit.json').write_text(json.dumps({'results': results,
    'scope': 'Observation-assessment code change only. Reuses unchanged GPU output; this is not a fresh physics rerun. Production source hashes remain frozen.'},indent=2))
print(json.dumps(results,indent=2))
