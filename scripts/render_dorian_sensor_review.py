"""Review sensor metadata independently of measured water levels and HWM values."""
import hashlib
import json
from pathlib import Path

import numpy as np
from pyproj import Transformer
from shapely.geometry import Point, shape

root=Path('artifacts/validation/dorian-2019')
load=lambda f:json.loads((root/f).read_text())
sites=load('sensor-site-metadata.json');screen=load('candidate-screen.json')
files=load('sensor-file-screen.json');df=load('sensor-datafile-metadata.json')
deployments=load('sensor-metadata-screen.json')
buildings=load('current-buildings.geojson')
domain=screen['domain'];project=Transformer.from_crs(4326,domain['projected_crs'],always_xy=True)
cx,cy=project.transform(domain['center_lon'],domain['center_lat'])
rows=[]
for site in sites:
    to_grid=Transformer.from_crs({2:4269,3:4267,4:4326}[site['hdatum_id']],domain['projected_crs'],always_xy=True)
    x,y=to_grid.transform(site['longitude_dd'],site['latitude_dd'])
    original=next(m for m in screen['marks'] if m['site_id']==site['site_id'])
    hx,hy=to_grid.transform(original['longitude_dd'],original['latitude_dd'])
    water_instruments=[i for entry in deployments if entry['site_id']==site['site_id'] for i in entry['instruments'] if i['deployment_type_id']==1]
    data=[]
    for instrument in water_instruments:
        inst=instrument['instrument_id']
        meta=next(r['files'] for r in df if r['instrument_id']==inst)
        links=next(r['records'] for r in files if r['kind']==str(inst))
        for f in links:
            if not f['name'].endswith(('.csv','.nc')):continue
            record=next(r for r in meta if r['data_file_id']==f['data_file_id'])
            data.append({'file_id': f['file_id'],'name': f['name'],'instrument_id': inst,
                'data_file_id': f['data_file_id'],'approval_id': record['approval_id'],
                'elevation_status': record['elevation_status'],'start': record['good_start'],
                'end': record['good_end'],'time_zone': record['time_zone'],
                'measured_values_downloaded': False,'url': f"https://stn.wim.usgs.gov/STNServices/Files/{f['file_id']}/Item"})
    grids=[]
    for n in (64,128):
        col=int(np.floor((x-cx+1000)/(2000/n)));row=int(np.floor((y-cy+1000)/(2000/n)))
        if not(0<=row<n and 0<=col<n):raise ValueError('Sensor outside fixed domain')
        z=np.load(root/f'topobathy-{n}.npy')
        grids.append({'grid': n,'row': row,'col': col,'terrain_m_navd88': float(z[row,col])})
    to_wgs=Transformer.from_crs(4269,4326,always_xy=True);lon,lat=to_wgs.transform(site['longitude_dd'],site['latitude_dd'])
    p=Point(lon,lat);inside=any(shape(f['geometry']).covers(p) for f in buildings['features'] if f.get('geometry'))
    rows.append(dict(**site,hwm_id=original['hwm_id'],distance_from_hwm_m=float(np.hypot(x-hx,y-hy)),
        exact_coordinate_inside_current_building=inside,grids=grids,data_files=data,
        setting_review='Outdoor water-side infrastructure supported by deployment photograph and site description; precise sensor elevation and hydraulic connection still need file metadata/QC.',
        role='candidate_independent_time_series_target_not_boundary_forcing',
        eligible_for_scoring=False))
sources=['candidate-screen.json','sensor-site-metadata.json','sensor-metadata-screen.json',
         'sensor-datafile-metadata.json','sensor-file-screen.json','sensor-photo-sources.json']
review={'status': 'promising_two_site_time_series_preflight','observation_values_exposed': False,
    'hwm_eligibility_unchanged': True,'sites': rows,
    'source_sha256': {f:hashlib.sha256((root/f).read_bytes()).hexdigest() for f in sources},
    'remaining': ['Verify datum, units, sensor QC and processing from metadata before admission; Final does not itself identify NAVD88.',
               'Keep barometric instrument 10027 separate; its arbitrary elevation is not flood stage.',
               'Use actual sensor coordinates; bridge/creek bathymetry and hydraulic access must be resolved.',
               'Freeze model boundary setup, period and time-series scoring before opening measured values.',
               'Do not force the model with a sensor and also score the same trace as independent validation.',
               'Files labelled unfiltered need a declared, physically justified wave/tide processing rule; no error-minimizing smoothing.']}
(root/'sensor-review.json').write_text(json.dumps(review,indent=2))
trs=''.join(f"<tr><td>{s['site_no']}</td><td>{s['waterbody']}</td><td>{s['distance_from_hwm_m']:.1f} m</td><td>{s['data_files'][0]['start']} to {s['data_files'][0]['end']} UTC</td><td>{s['exact_coordinate_inside_current_building']}</td></tr>" for s in rows)
doc=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Dorian sensor preflight</title><style>body{{font:16px/1.6 system-ui;background:#f5f4ee;color:#183c42}}main{{max-width:1050px;margin:auto;padding:24px}}img{{max-width:100%;max-height:650px}}td,th{{padding:12px;text-align:left}}.notice{{background:#fff0d7;padding:18px}}.scroll{{overflow-x:auto}}a{{color:#006b85}}</style><main>
<h1>Dorian: two outdoor water-level sensor candidates</h1><p class="notice">Metadata and deployment photos only. Measured traces and high-water elevations remain unexposed. No new scoring or physics adoption.</p>
<p>USGS lists approved final-elevation CSV and NetCDF files for two water-level pressure transducers spanning the storm. These are two sites with multiple file formats, not four independent observations. Sensor coordinates differ from the high-water marks associated with the sites.</p>
<div class="scroll"><table><tr><th>Site</th><th>Waterbody</th><th>Offset from HWM</th><th>Good data interval</th><th>Inside current footprint</th></tr>{trs}</table></div>
<h2>Ferry-terminal deployment</h2><img src="sensor-deployment-117261.jpg" alt="USGS deployment photograph showing the outdoor ferry terminal and harbour edge"><p>USGS file 117261 supports outdoor harbour context; it does not establish precise sensor elevation.</p>
<h2>Creek-bridge deployment</h2><img src="sensor-deployment-118278.jpg" alt="USGS pressure-transducer housing mounted outside on waterfront timbers next to a creek bridge"><p>USGS file 118278 shows an outdoor instrument housing at the creek bridge. This does not resolve the separate high-water mark on a nearby building.</p>
<h2>Required before comparison</h2><ul>{''.join('<li>'+x+'</li>' for x in review['remaining'])}</ul>
<p><a href="sensor-review.json">Full metadata, mapped cells and file links</a> · <a href="sensor-photo-sources.json">Photograph provenance</a> · <a href="preflight.html">Unchanged HWM and domain review</a> · <a href="../wave-boundary-v1/report.html">Boundary experiment</a></p></main></html>'''
(root/'sensor-review.html').write_text(doc,encoding='utf-8')
print(json.dumps([{'site': r['site_no'],'offset_m': r['distance_from_hwm_m'],'grids': r['grids'],'inside_building': r['exact_coordinate_inside_current_building']} for r in rows]))
