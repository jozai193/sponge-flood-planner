"""Freeze a Sandy retrospective screening case before evaluating observations."""
import hashlib
import itertools
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from pyproj import Transformer

from services.geodata.prepare import prepare
from services.geodata.providers import buildings
from services.geodata.usgs import sample_products

ROOT = Path('artifacts/validation/sandy-2012')
lon, lat, extent = -74.015, 40.717, 1000
forward = Transformer.from_crs(4326, 32618, always_xy=True)
inverse = Transformer.from_crs(32618, 4326, always_xy=True)
cx, cy = forward.transform(lon, lat)
bounds = inverse.transform_bounds(cx-500, cy-500, cx+500, cy+500, densify_pts=21)
catalog = json.loads((ROOT/'terrain-catalog.json').read_text())
product = next(p for p in catalog['items'] if 'NY CMPG 2013' in p['title'])
metadata = json.loads((ROOT/'ny-terrain-metadata.json').read_text())
if 'North American Vertical Datum of 1988 (NAVD88)' not in metadata['body']:
    raise ValueError('Terrain vertical reference not confirmed')
print('Acquiring current footprint evidence', flush=True)
features, building_sources = buildings(bounds)
(ROOT/'current-buildings.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features}))
raw = json.loads((ROOT/'battery-water-level.json').read_text())
start = datetime(2012,10,29,12,tzinfo=UTC)
end = datetime(2012,10,30,6,tzinfo=UTC)
levels = []
for row in raw['data']:
    t = datetime.strptime(row['t'], '%Y-%m-%d %H:%M').replace(tzinfo=UTC)
    if start <= t <= end:
        if row['q'] != 'v' or not np.isfinite(float(row['v'])):
            raise ValueError('Unverified or missing gauge level')
        levels.append({'timeS': (t-start).total_seconds(),'elevationM': float(row['v'])})
if len(levels)!=181 or any(b['timeS']-a['timeS']!=360 for a,b in itertools.pairwise(levels)):
    raise ValueError('Incomplete six-minute measured forcing')
protocol = {
    'event_id':'USGS-STN-24-2012-Sandy', 'city':'New York City',
    'area':'Battery Park City / Hudson waterfront',
    'created_at':datetime.now(UTC).isoformat(),
    'start_utc':start.isoformat(),'end_utc':end.isoformat(),'duration_s':64800,
    'forcing':'NOAA 8518750 The Battery, verified six-minute total water levels, NAVD88 metres',
    'forcing_url':(ROOT/'battery-request.txt').read_text(),
    'independent_observations':'USGS STN event 24 high-water marks; never used to set forcing, roughness or terrain',
    'selection':'All event marks inside the fixed domain retained in the audit. Compare exterior, non-solid, wet cells; identify duplicate sites and excluded marks explicitly. Report poor-quality marks separately.',
    'horizontal_crs':'EPSG:32618','vertical_datum':'NAVD88','extent_m':extent,
    'center':[lon,lat],'grid_sizes':[32,64],'max_step_s':10,
    'roughness':.035,'rainfall_m':0,'infiltration_m_s':0,'soil_storage_m':0,
    'boundary':'Measured reservoir at west edge; north/east/south closed; no artificial bed changes',
    'success_criteria':'Report error in metres, wet/missed counts and mass balance. No overall accuracy percentage or site-validation badge from this small, correlated sample.',
    'limitations':[
        'Terrain is post-event NY CMPG 2013; current building footprints are not a 2012 inventory.',
        'Bare-earth DEM water surfaces are not surveyed bathymetry; western water cells act as a local reservoir approximation.',
        'The Battery gauge is spatially transferred along this waterfront without hydrodynamic harbour propagation.',
        'Only 18 hours around the peak are run; initial water is assumed equilibrated with the first measured level.',
        'Rainfall, wave action, wind stress, sewer/backflow, underground flooding and temporary defences are omitted.',
        'Closed lateral boundaries and coarse building rasterisation can strongly bias local results.',
        'High-water marks are point maxima; grid outputs are cell-average maxima, with uncertain location and survey quality.'
    ],'bundles':[]
}
for n in protocol['grid_sizes']:
    print('Preparing',n,'cells',flush=True)
    z,sources,_ = sample_products([product],'EPSG:32618',cx-500,cy-500,n,extent/n)
    supplements={'terrain':z.ravel().tolist(),'vertical_datum':'NAVD88',
        'sources':sources+building_sources,'buildings':features,
        'evidence_id':'sandy-2012-unfitted-screening',
        'quality':{'terrain_provider':'USGS NY CMPG 2013','native_resolution_m':1,'observation_validation':'not_yet_compared'},
        'assumptions':protocol['limitations']}
    m=prepare({'longitude': lon,'latitude': lat,'extent_m': extent,'grid_cells': n,'source': 'terrarium','label': 'Sandy 2012 retrospective screening - '+str(n)},supplements=supplements)
    local_levels=[{**k,'elevationM':k['elevationM']-m['grid']['elevation_origin_m']} for k in levels]
    item={'grid_cells':n,'bundle_id':m['bundle_id'],'levels':local_levels}
    protocol['bundles'].append(item)
    print('Bundle',m['bundle_id'],flush=True)
(ROOT/'protocol.json').write_text(json.dumps(protocol,indent=2))
(ROOT/'protocol.sha256').write_text(hashlib.sha256((ROOT/'protocol.json').read_bytes()).hexdigest())
print('Frozen protocol saved before simulation',flush=True)
