"""Fetch forcing and source metadata without reading held-out HWM elevations."""
import asyncio
from pathlib import Path

import httpx

root=Path('artifacts/validation/matthew-2016')
async def main():
    async with httpx.AsyncClient(timeout=90,follow_redirects=True) as client:
        queries={
            'terrain-metadata.das':'https://www.ngdc.noaa.gov/thredds/dodsC/tiles/tiled_19as/ncei19_n33x00_w080x00_2019v1.nc.das',
            'regional-catalog.xml':'https://www.ngdc.noaa.gov/thredds/catalog/regional/catalog.xml',
            'forcing-preflight.json':'https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?product=water_level&application=SPONGE-historical-validation&begin_date=20161007&end_date=20161009&datum=NAVD&station=8665530&time_zone=gmt&units=metric&format=json'}
        async def fetch(name,url):
            r=await client.get(url);r.raise_for_status();(root/name).write_bytes(r.content)
            if name.endswith('.das'):print(r.text)
            elif name.endswith('.xml'):print('REGIONAL', '\n'.join(line for line in r.text.splitlines() if 'charleston' in line.lower()))
            else:
                data=r.json();print('GAUGE',data.get('metadata'), 'count',len(data.get('data',[])))
                if 'error' in data:raise ValueError(data['error'])
                print('GAUGE PEAK',max(data['data'],key=lambda k:float(k['v'])))
        await asyncio.gather(*(fetch(n,u) for n,u in queries.items()))
asyncio.run(main())
