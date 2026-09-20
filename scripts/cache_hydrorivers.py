"""Cache the official global HydroRIVERS archive once for bounded spatial queries."""
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

URL='https://data.hydrosheds.org/file/HydroRIVERS/HydroRIVERS_v10_shp.zip'
DEST=Path('data/local/global/HydroRIVERS_v10_shp.zip')


def cache():
    DEST.parent.mkdir(parents=True,exist_ok=True)
    if DEST.exists():return DEST
    stage=DEST.with_suffix('.partial');size=0;digest=hashlib.sha256();started=time.monotonic();last=started
    with httpx.stream('GET',URL,timeout=60) as response:
        response.raise_for_status()
        with stage.open('wb') as output:
            for chunk in response.iter_bytes(1024*1024):
                size+=len(chunk)
                if size>650_000_000:raise ValueError('Archive exceeds the 650 MB download budget')
                output.write(chunk);digest.update(chunk)
                if time.monotonic()-last>20:
                    print(f'HydroRIVERS: {size//1_000_000} MB cached',flush=True);last=time.monotonic()
    stage.replace(DEST)
    DEST.with_suffix('.json').write_text(json.dumps({'source_url': URL,'sha256': digest.hexdigest(),'bytes': size,
        'retrieved_at': datetime.now(UTC).isoformat(),'attribution': 'Lehner and Grill (2013), HydroSHEDS',
        'license_url': 'https://www.hydrosheds.org/products/hydrorivers'}),encoding='utf-8')
    return DEST


if __name__=='__main__':print(cache(),flush=True)
