"""Check independent-event data availability without reading HWM outcome values."""
import json
from pathlib import Path

import httpx

ROOT = Path('artifacts/validation/michael-2018')
ROOT.mkdir(parents=True, exist_ok=True)
with httpx.Client(timeout=60, follow_redirects=True) as client:
    urls = {
        'station': 'https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/8729108.json',
        'forcing': 'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=water_level&application=SPONGE-historical-validation&begin_date=20181010&end_date=20181011&datum=NAVD&station=8729108&time_zone=gmt&units=metric&format=json',
        'terrain': 'https://tnmaccess.nationalmap.gov/api/v1/products?datasets=Digital%20Elevation%20Model%20(DEM)%201%20meter&bbox=-85.67,30.145,-85.65,30.16&max=30&outputFormat=JSON',
    }
    for name, url in urls.items():
        response = client.get(url)
        response.raise_for_status()
        data = response.json()
        (ROOT/f'{name}-preflight.json').write_text(json.dumps(data, indent=2))
        if name == 'forcing':
            print(name, 'records', len(data.get('data', [])), 'error', data.get('error'))
        elif name == 'terrain':
            print(name, [(p['title'], p.get('publicationDate')) for p in data.get('items', [])])
        else:
            print(name, [(s.get('name'), s.get('lat'), s.get('lng')) for s in data.get('stations', [])])
    (ROOT/'preflight-sources.json').write_text(json.dumps(urls, indent=2))
