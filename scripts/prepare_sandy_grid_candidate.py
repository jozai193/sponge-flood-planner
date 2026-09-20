"""Freeze the prior-event resolution regression without altering Sandy's baseline."""
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from services.geodata.prepare import prepare
from services.geodata.usgs import sample_products

base=Path('artifacts/validation/sandy-2012')
root=Path('artifacts/validation/sandy-2012-grid128')
if root.exists():raise ValueError('Candidate already exists; do not overwrite')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((base/'protocol.json').read_text())
if sha(base/'protocol.json')!=(base/'protocol.sha256').read_text().strip():raise ValueError('Baseline protocol changed')
frozen=Path('artifacts/validation/baselines/sandy-initial')
checks=json.loads((frozen/'manifest.json').read_text())['sha256']
for path,expected in checks.items():
    if sha(frozen/path)!=expected:raise ValueError('Frozen baseline altered: '+path)
    if path.startswith(('packages/simulation/src/','apps/web/src/testing/','services/geodata/')) and sha(Path(path))!=expected:
        raise ValueError('Resolution experiment would also change model/preparation code: '+path)
old=p['bundles'][-1];bundle=Path('data/local/bundles')/old['bundle_id']
m=json.loads((bundle/'manifest.json').read_text());g=m['grid']
product=next(s for s in json.loads((base/'terrain-catalog.json').read_text())['items'] if 'NY CMPG 2013' in s['title'])
# Reproduce the previously frozen 64-grid terrain before accepting a remote source.
z64,sources,_=sample_products([product],g['crs'],g['origin_x_m'],g['origin_y_m'],64,g['dx_m'])
old_z=np.fromfile(bundle/'z.bin',dtype='<f4').reshape(64,64)
recreated=(z64-g['elevation_origin_m']).astype('f4')
if not np.array_equal(recreated,old_z):raise ValueError('Native source no longer reproduces exact frozen terrain')
z128,sources,_=sample_products([product],g['crs'],g['origin_x_m'],g['origin_y_m'],128,p['extent_m']/128)
features=json.loads((base/'current-buildings.geojson').read_text())['features']
root.mkdir(parents=True)
for name in ('hwms.json','current-buildings.geojson','battery-water-level.json','terrain-catalog.json','ny-terrain-metadata.json'):
    shutil.copy2(base/name,root/name)
np.save(root/'terrain-128.npy',z128)
candidate=prepare({'longitude': p['center'][0],'latitude': p['center'][1],'extent_m': p['extent_m'],'grid_cells': 128,'source': 'terrarium','label': 'Sandy 2012 resolution regression - 128'},supplements={
    'terrain': z128.ravel().tolist(),'vertical_datum': 'NAVD88','sources': sources,'buildings': features,
    'evidence_id': 'sandy-2012-resolution-regression','quality': {'terrain_provider': 'USGS NY CMPG 2013','native_resolution_m': 1,'observation_validation': 'development_regression'},'assumptions': p['limitations']})
folder=Path('data/local/bundles')/candidate['bundle_id']
levels=[{'timeS': k['timeS'],'elevationM': k['elevationM']+g['elevation_origin_m']-candidate['grid']['elevation_origin_m']} for k in old['levels']]
p.update(created_at=datetime.now(UTC).isoformat(),stn_event_id=24,boundary_edge='west',grid_sizes=[128],
    bundles=[{'grid_cells': 128,'bundle_id': candidate['bundle_id'],'levels': levels}],
    selection=p['selection']+' Prior-event regression after Ian and Irma resolution checks. Observations already exposed; not a blind test. No coordinate, parameter or gauge fitting.',
    parent_protocol_sha256=sha(base/'protocol.json'))
paths=list(root.iterdir())+[folder/n for n in ('manifest.json','z.bin','solid.bin')]
paths+=list(Path('packages/simulation/src').glob('*.ts'))+[Path(s) for s in ('apps/web/src/testing/gpu-harness.ts','services/geodata/prepare.py','services/geodata/usgs.py')]
p['source_sha256']={f.as_posix():sha(f) for f in paths}
(root/'protocol.json').write_text(json.dumps(p,indent=2))
(root/'protocol.sha256').write_text(sha(root/'protocol.json'))
(root/'candidate-hypothesis.json').write_text(json.dumps({'change': 'Grid resolution only',
    'native_source_64_grid_bitwise_reproduction': True,'parent_protocol_sha256': p['parent_protocol_sha256'],
    'acceptance': 'Same frozen regression gates: no lost supported/wet points, no additional dry misses, common-point and equal-site RMSE worsening at most 0.01 m, passing mass and saved-depth checks.',
    'limitation': 'Development regression on an already exposed event; not independent new validation.'},indent=2))
print('Frozen Sandy 128 candidate',candidate['bundle_id'],flush=True)
