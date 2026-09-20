"""Freeze Michael case inputs; never use high-water elevations to set parameters."""
import hashlib
import itertools
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import numpy as np
from pyproj import Transformer

from services.geodata.prepare import prepare
from services.geodata.providers import buildings

ROOT = Path('artifacts/validation/michael-2018')
if (ROOT/'protocol.json').exists():
    raise SystemExit('Protocol exists; use a new experiment directory instead of overwriting')
lon, lat, extent, n = -85.654, 30.15, 2000, 64
crs = 'EPSG:32616'
cx, cy = Transformer.from_crs(4326, crs, always_xy=True).transform(lon, lat)
bounds = Transformer.from_crs(crs, 4326, always_xy=True).transform_bounds(
    cx-extent/2, cy-extent/2, cx+extent/2, cy+extent/2, densify_pts=21)
products = [p for p in json.loads((ROOT/'terrain-preflight.json').read_text())['items']
            if 'Lower Choctawhatchee 2017' in p['title']]
if not products or any('North American Vertical Datum of 1988 (NAVD88)' not in p['body'] for p in products):
    raise ValueError('Missing confirmed NAVD88 source')
lookup_url = 'https://stn.wim.usgs.gov/STNServices/HorizontalDatums.json'
response = httpx.get(lookup_url, timeout=60)
response.raise_for_status()
(ROOT/'horizontal-datums.json').write_text(response.text)
print('Horizontal datum lookup:', response.json(), flush=True)
print('Loading sourced topobathymetry and acquiring current footprints', flush=True)
topobathy = json.loads((ROOT/'topobathy-source.json').read_text())
z = np.load(ROOT/'topobathy-64.npy')
if z.shape != (n,n) or not np.isfinite(z).all():
    raise ValueError('Incomplete sourced topobathymetry')
sources = [{'provider': 'NOAA NCEI', 'source_url': topobathy['request_url'],
    'title': 'Panama City 2010 NAVD88 integrated coastal DEM', 'native_resolution_m': 10,
    'vertical_datum': 'NAVD88', 'attribution': 'NOAA NCEI', 'acquisition_range': '1935-2010'}]
features, building_sources = buildings(bounds)
(ROOT/'current-buildings.geojson').write_text(json.dumps({'type': 'FeatureCollection', 'features': features}))
start = datetime(2018, 10, 10, 6, tzinfo=UTC)
end = datetime(2018, 10, 11, 0, tzinfo=UTC)
levels = []
for row in json.loads((ROOT/'forcing-preflight.json').read_text())['data']:
    t = datetime.strptime(row['t'], '%Y-%m-%d %H:%M').replace(tzinfo=UTC)
    if start <= t <= end:
        if row['q'] != 'v' or not np.isfinite(float(row['v'])):
            raise ValueError('Invalid forcing')
        levels.append({'timeS': (t-start).total_seconds(), 'elevationM': float(row['v'])})
if len(levels) != 181 or any(b['timeS']-a['timeS'] != 360 for a, b in itertools.pairwise(levels)):
    raise ValueError('Forcing gap')
limitations = [
    'NOAA 2010 integrated topobathymetry includes surveys from 1935-2010; shoreline changes and old interpolated depths remain uncertain.',
    'Current Overture buildings are not a 2018 inventory. Available 2017 lidar leaves bay gaps and was not silently substituted or filled.',
    'Single south reservoir edge; other edges closed. Complex shoreline and lateral flow remain approximations.',
    'NOAA Panama City total water levels are transferred spatially without bay hydrodynamic propagation.',
    'Rainfall, waves, wind stress, sewers, erosion and underground flooding omitted.',
    'Two HWM locations within the 2 km application domain; limited correlated point evidence cannot validate city flood extent. The western third mark requires a separate domain.',
    'A published report preview exposed one nearby HWM elevation during source discovery. No HWM elevations were used for forcing, parameters or terrain; this is not a strictly blinded test.'
]
m = prepare({'longitude': lon, 'latitude': lat, 'extent_m': extent, 'grid_cells': n,
    'source': 'terrarium', 'label': 'Michael 2018 unfitted historical comparison'}, supplements={
        'terrain': z.ravel().tolist(), 'vertical_datum': 'NAVD88', 'sources': sources+building_sources,
        'buildings': features, 'evidence_id': 'michael-2018-unfitted-screening',
        'quality': {'terrain_provider': 'NOAA Panama City 2010 topobathymetry', 'native_resolution_m': 10,
                     'observation_validation': 'not_yet_compared'}, 'assumptions': limitations})
protocol = {'event_id': 'USGS-STN-287-2018-Michael', 'stn_event_id': 287, 'city': 'Panama City',
    'created_at': datetime.now(UTC).isoformat(), 'start_utc': start.isoformat(), 'end_utc': end.isoformat(),
    'duration_s': 64800, 'center': [lon, lat], 'extent_m': extent, 'grid_sizes': [n], 'horizontal_crs': crs,
    'vertical_datum': 'NAVD88', 'roughness': .035, 'max_step_s': 10, 'boundary_edge': 'south',
    'rainfall_m': 0, 'infiltration_m_s': 0, 'soil_storage_m': 0,
    'forcing': 'NOAA 8729108 Panama City verified six-minute total levels, NAVD88 metres',
    'forcing_url': json.loads((ROOT/'preflight-sources.json').read_text())['forcing'],
    'terrain_acquisition': '1935-2010 source compilation published 2010',
    'terrain_acquisition_source': topobathy['metadata_url'],
    'selection': 'All STN event marks within fixed domain, without elevation-based selection. The 2 km application limit prevents enclosing all three nearby marks; this domain covers the two eastern locations with a boundary buffer. Exact coordinates, matching datums and all exclusions retained.',
    'limitations': limitations, 'bundles': [{'grid_cells': n, 'bundle_id': m['bundle_id'],
        'levels': [{'timeS': k['timeS'], 'elevationM': k['elevationM']-m['grid']['elevation_origin_m']} for k in levels]}]}
paths = list(Path('packages/simulation/src').glob('*.ts')) + [
    Path('apps/web/src/testing/gpu-harness.ts'), Path('services/geodata/prepare.py'),
    Path('services/geodata/usgs.py'), ROOT/'forcing-preflight.json', ROOT/'hwms.json',
    ROOT/'current-buildings.geojson', ROOT/'terrain-preflight.json',
    ROOT/'noaa-topobathy-subset.tif', ROOT/'topobathy-source.json', ROOT/'topobathy-64.npy']
folder = Path('data/local/bundles')/m['bundle_id']
paths += [folder/p for p in ('manifest.json', 'z.bin', 'solid.bin')]
protocol['source_sha256'] = {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
(ROOT/'protocol.json').write_text(json.dumps(protocol, indent=2))
(ROOT/'protocol.sha256').write_text(hashlib.sha256((ROOT/'protocol.json').read_bytes()).hexdigest())
print('Frozen', m['bundle_id'], 'buildings', len(features), 'gauge peak', max(k['elevationM'] for k in levels), flush=True)
