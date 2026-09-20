"""Prepare an event after metadata-only review; enforce suitability before freezing."""
import hashlib
import itertools
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from pyproj import Transformer

from services.geodata.prepare import prepare
from services.geodata.providers import buildings

root=Path(sys.argv[1]);c=json.loads((root/'design.json').read_text())
if (root/'protocol.json').exists():raise ValueError('Protocol already frozen')
review=json.loads((root/'observation-review.json').read_text())['marks']
lon,lat=c['center'];extent=c['extent_m']
cx,cy=Transformer.from_crs(4326,c['crs'],always_xy=True).transform(lon,lat)
bounds=Transformer.from_crs(c['crs'],4326,always_xy=True).transform_bounds(cx-extent/2,cy-extent/2,cx+extent/2,cy+extent/2,densify_pts=21)
cache=root/'current-buildings.geojson'
if cache.exists():features=json.loads(cache.read_text())['features'];building_sources=json.loads((root/'building-sources.json').read_text())
else:
    features,building_sources=buildings(bounds)
    cache.write_text(json.dumps({'type': 'FeatureCollection','features': features}))
    (root/'building-sources.json').write_text(json.dumps(building_sources))
start=datetime.fromisoformat(c['start_utc']);end=datetime.fromisoformat(c['end_utc']);duration=(end-start).total_seconds()
levels=[]
for row in json.loads((root/'forcing-preflight.json').read_text())['data']:
    t=datetime.strptime(row['t'],'%Y-%m-%d %H:%M').replace(tzinfo=UTC)
    if start<=t<=end:
        if row['q']!='v' or not np.isfinite(float(row['v'])):raise ValueError('Invalid forcing')
        levels.append({'timeS': (t-start).total_seconds(),'elevationM': float(row['v'])})
if not levels or levels[0]['timeS']!=0 or levels[-1]['timeS']!=duration or any(b['timeS']-a['timeS']!=360 for a,b in itertools.pairwise(levels)):raise ValueError('Forcing gap')
source=json.loads((root/'topobathy-source.json').read_text())
limitations=['Terrain date: '+c['terrain_date']+'. Source survey ages and shoreline change are unresolved.',
    'Current Overture buildings are not an event-era inventory.',
    'Single reservoir edge and closed lateral edges approximate complex shoreline flow.',
    'Gauge levels transferred spatially; wind, waves, rainfall, sewers and indoor flooding omitted.',
    'Sparse outdoor point maxima cannot validate extent or timing. Indoor and ambiguous marks retained as unsupported.',
    'Observation descriptions and coordinates reviewed with numbers redacted before measured elevations were inspected. No elevation-based fitting.']
runs=[];suitability=[];paths=[]
marks=json.loads((root/'hwms.json').read_text())
for n in c['grid_sizes']:
    z=np.load(root/f'topobathy-{n}.npy')
    m=prepare({'longitude': lon,'latitude': lat,'extent_m': extent,'grid_cells': n,'source': 'terrarium','label': c['event_id']},supplements={
        'terrain': z.ravel().tolist(),'vertical_datum': 'NAVD88','sources': [{'provider': 'NOAA NCEI','source_url': source['request_url'],'title': c['terrain_dataset'],'native_resolution_m': 3.4,'vertical_datum': 'NAVD88','attribution': 'NOAA NCEI'}]+building_sources,
        'buildings': features,'evidence_id': c['event_id']+'-unfitted','quality': {'terrain_provider': 'NOAA CUDEM','native_resolution_m': 3.4,'observation_validation': 'not_yet_compared'},'assumptions': limitations})
    folder=Path('data/local/bundles')/m['bundle_id'];g=m['grid'];solid=np.fromfile(folder/'solid.bin',dtype='u1').reshape(n,n)
    eligible=[];inside=[]
    for mark in marks:
        datum={2:4269,3:4267,4:4326}.get(mark.get('hdatum_id'))
        if datum is None:continue
        x,y=Transformer.from_crs(datum,c['crs'],always_xy=True).transform(mark['longitude_dd'],mark['latitude_dd'])
        row=int(np.floor((y-g['origin_y_m'])/g['dy_m']));col=int(np.floor((x-g['origin_x_m'])/g['dx_m']))
        if not(0<=row<n and 0<=col<n):continue
        mid=str(mark['hwm_id'])
        if mid not in review:raise ValueError('Unreviewed in-domain observation '+mid)
        supported=review[mid]['eligibility']=='outdoor' and not solid[row,col] and mark.get('vdatum_id')==2
        inside.append({'id': mark['hwm_id'],'row': row,'col': col,'solid': bool(solid[row,col]),'eligibility': review[mid]['eligibility'],'datum_supported': mark.get('vdatum_id')==2})
        if supported:eligible.append(mark['hwm_id'])
    suitability.append({'grid_cells': n,'in_domain': inside,'supported_metadata_ids': eligible})
    (root/'suitability.json').write_text(json.dumps(suitability,indent=2))
    print('Suitability',json.dumps(suitability[-1]),flush=True)
    if len(eligible)<2:raise ValueError('Fewer than two outdoor non-solid observations; do not run')
    runs.append({'grid_cells': n,'bundle_id': m['bundle_id'],'levels': [{'timeS': k['timeS'],'elevationM': k['elevationM']-g['elevation_origin_m']} for k in levels]})
    paths += [folder/p for p in ('manifest.json','z.bin','solid.bin')]+[root/f'topobathy-{n}.npy']
protocol={'event_id': c['event_id'],'stn_event_id': c['stn_event_id'],'city': c['city'],'created_at': datetime.now(UTC).isoformat(),
    'start_utc': c['start_utc'],'end_utc': c['end_utc'],'duration_s': duration,'center': c['center'],'extent_m': extent,'grid_sizes': c['grid_sizes'],'horizontal_crs': c['crs'],'vertical_datum': 'NAVD88',
    'roughness': .035,'max_step_s': 10,'boundary_edge': c['boundary_edge'],'rainfall_m': 0,'infiltration_m_s': 0,'soil_storage_m': 0,
    'forcing': 'NOAA '+c['gauge']+' verified six-minute total levels, NAVD88 metres','terrain_acquisition': c['terrain_date'],'selection': c['selection'],'limitations': limitations,'bundles': runs,
    'observation_review': 'observation-review.json'}
paths+=list(Path('packages/simulation/src').glob('*.ts'))+[Path('apps/web/src/testing/gpu-harness.ts'),Path('services/geodata/prepare.py'),Path('services/geodata/usgs.py')]
paths += [root/p for p in ('design.json','hwms.json','observation-review.json','forcing-preflight.json','current-buildings.geojson','terrain-metadata.das','topobathy-source.json','noaa-topobathy-subset.tif')]
paths += [root/p for p in c.get('additional_frozen_files',[])]
protocol['source_sha256']={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
(root/'protocol.json').write_text(json.dumps(protocol,indent=2))
(root/'protocol.sha256').write_text(hashlib.sha256((root/'protocol.json').read_bytes()).hexdigest())
print('Frozen reviewed event:',c['event_id'],flush=True)
