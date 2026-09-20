"""Cache global level-6 catchment context, partitioned by HydroSHEDS regions."""
import json
from pathlib import Path

from services.geodata.providers import fetch


def cache():
    root=Path('data/local/global/basins');root.mkdir(parents=True,exist_ok=True)
    for region in ['af','ar','as','au','eu','gr','na','sa','si']:
        name=f'hybas_{region}_lev06_v1c'
        if (root/f'{name}.zip').exists():continue
        raw,source=fetch(f'https://data.hydrosheds.org/file/hydrobasins/standard/{name}.zip',max_bytes=40_000_000)
        (root/f'{name}.zip').write_bytes(raw)
        (root/f'{name}.json').write_text(json.dumps({**source,'provider':'HydroBASINS level 6',
            'attribution':'Lehner and Grill (2013), HydroSHEDS','license_url':'https://www.hydrosheds.org/products/hydrobasins'}))
        print(region,len(raw),flush=True)


if __name__=='__main__':cache()
