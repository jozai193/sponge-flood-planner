"""Small explicit live search smoke check, not a worldwide coverage benchmark."""

if not __debug__:
    raise RuntimeError("Integrity verification is disabled under python -O; rerun without optimization.")
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx


def main():
    output=Path('artifacts/verification/location-search-v1')
    output.mkdir(parents=True,exist_ok=True)
    cases=[
        ('ozone evergreen','Bangalore',(12.90,12.92,77.65,77.67),'Evengreen Apartments'),
        ('Shinjuku','Tokyo',(35.67,35.75,139.65,139.75),None),
        ('Kirstenbosch','Cape Town',(-34.0,-33.9,18.35,18.5),None),
        ('12.9086945, 77.6625469','',(12.90869,12.90870,77.66254,77.66255),None),
        ('89, 0','',(89,89,0,0),None),
    ]
    results=[]
    with httpx.Client(base_url='http://127.0.0.1:8787/api/v1',timeout=25) as client:
        session=client.post('/sessions',json={});session.raise_for_status()
        client.headers['Authorization']='Bearer '+session.json()['token']
        for query,region,(lat_min,lat_max,lon_min,lon_max),name in cases:
            response=client.post('/geocode',json={'query':query,'region':region})
            data=response.json()
            matches=[p for p in data.get('locations',[]) if lat_min<=p['latitude']<=lat_max and lon_min<=p['longitude']<=lon_max and (not name or name in p['label'])]
            passed=response.status_code==200 and bool(matches)
            if query=='89, 0':passed=passed and matches[0]['terrain_supported'] is False
            results.append({'query':query,'region':region,'http_status':response.status_code,'passed':passed,**data})
            print(query,passed,flush=True)
            time.sleep(2.1)
    (output/'live-search.json').write_text(json.dumps({'checked_at':datetime.now(UTC).isoformat(),'scope':'Three named places and two coordinates; no claim of exhaustive coverage.','cases':results},indent=2,ensure_ascii=False),encoding='utf8')
    assert all(r['passed'] for r in results)


if __name__=='__main__':main()
