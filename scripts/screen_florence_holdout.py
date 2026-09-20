"""Acquire a new event while exposing only observation-location metadata."""
import json
import re
from pathlib import Path

import httpx

root=Path('artifacts/validation/florence-2018');root.mkdir(parents=True,exist_ok=True)
if (root/'protocol.json').exists():raise ValueError('Already frozen')
with httpx.Client(timeout=90,follow_redirects=True) as client:
    url='https://stn.wim.usgs.gov/STNServices/Events/283/HWMs.json'
    r=client.get(url);r.raise_for_status();marks=r.json();(root/'hwms.json').write_bytes(r.content)
    rows=[]
    for m in marks:
        if -76.77<m.get('longitude_dd',0)<-76.60 and 34.66<m.get('latitude_dd',0)<34.79:
            rows.append({'id': m['hwm_id'],'site_id': m['site_id'],'lon': m['longitude_dd'],'lat': m['latitude_dd'],
                'horizontal_datum_id': m.get('hdatum_id'),'vertical_datum_id': m.get('vdatum_id'),'quality_id': m.get('hwm_quality_id'),
                'description': re.sub(r'[-+]?\d+(?:\.\d+)?','[number]',m.get('hwm_locationdescription') or '')})
    (root/'metadata-screen.json').write_text(json.dumps({'source_url': url,'event_mark_count': len(marks),
        'selection': 'Beaufort and Morehead City region; coordinates and descriptions only. No measured elevations or ground heights exposed.','marks': rows},indent=2))
    print(json.dumps({'event_mark_count': len(marks),'local_metadata': rows},indent=2))
    url='https://www.ngdc.noaa.gov/thredds/catalog/tiles/tiled_19as/catalog.xml'
    r=client.get(url);r.raise_for_status();(root/'terrain-catalog.xml').write_bytes(r.content)
    print('TERRAIN CANDIDATES', '\n'.join(line for line in r.text.splitlines() if 'n34x75_w076x75' in line))
