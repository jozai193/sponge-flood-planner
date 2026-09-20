"""Expose only coordinates and numeric-redacted descriptions in a fixed region."""
import json
import re
import sys
from pathlib import Path

import httpx

root=Path(sys.argv[1]);event=int(sys.argv[2]);west,south,east,north=map(float,sys.argv[3:7])
root.mkdir(parents=True,exist_ok=True)
if (root/'protocol.json').exists():raise ValueError('Already frozen')
url=f'https://stn.wim.usgs.gov/STNServices/Events/{event}/HWMs.json'
r=httpx.get(url,timeout=90,follow_redirects=True);r.raise_for_status();marks=r.json()
(root/'hwms.json').write_bytes(r.content)
rows=[]
for m in marks:
    if west<m.get('longitude_dd',0)<east and south<m.get('latitude_dd',0)<north:
        rows.append({'id': m['hwm_id'],'site_id': m['site_id'],'lon': m['longitude_dd'],'lat': m['latitude_dd'],
            'horizontal_datum_id': m.get('hdatum_id'),'vertical_datum_id': m.get('vdatum_id'),'quality_id': m.get('hwm_quality_id'),
            'description': re.sub(r'[-+]?\d+(?:\.\d+)?','[number]',m.get('hwm_locationdescription') or '')})
out={'source_url': url,'event_mark_count': len(marks),'bounds': [west,south,east,north],
    'selection': 'Coordinates and numeric-redacted descriptions only. Measured HWM elevations and ground heights not exposed.','marks': rows}
(root/'metadata-screen.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
