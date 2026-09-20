"""Bounded, cached global footprint acquisition in an isolated GIS process."""
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

from services.api.settings import settings

CACHE=settings.storage_root/'city-buildings'
def cache_path(bounds):
    return CACHE/(hashlib.sha256(json.dumps(list(bounds)).encode()).hexdigest()+'.json')
def acquire(bounds):
    target=cache_path(bounds)
    if target.exists() and time.time()-target.stat().st_mtime<7*86400:
        result=json.loads(target.read_text(encoding='utf-8'))
    else:
        CACHE.mkdir(parents=True,exist_ok=True)
        temporary=target.with_suffix('.'+uuid.uuid4().hex+'.tmp')
        try:
            subprocess.run([sys.executable,'-m','services.geodata.city_buildings',json.dumps(list(bounds)),str(temporary)],check=True,timeout=180,capture_output=True)
            result=json.loads(temporary.read_text(encoding='utf-8'))
            if not result.get('features'):raise ValueError('Global footprint source has no buildings in this area')
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    return result['features'],result['sources']
if __name__=='__main__':
    from services.geodata.global_sources import overture_bounds
    result=overture_bounds(json.loads(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(result,allow_nan=False,default=str),encoding='utf-8')
    os._exit(0)
