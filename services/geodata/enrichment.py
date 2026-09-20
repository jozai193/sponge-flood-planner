"""Independent, restartable evidence jobs with per-provider failure isolation."""
import hashlib
import json
import subprocess
import sys
import time
from datetime import date
from typing import Literal
from uuid import uuid4

from pydantic import Field, model_validator

from services.api.contracts import WireModel
from services.api.settings import settings
from services.geodata.prepare import ROOT

EVIDENCE=settings.storage_root/'enrichment'
CAPABILITIES=('buildings','terrain','landcover','soils','waterways','rainfall','hydrorivers','catchments','dynamic_world')


class EnrichmentRequest(WireModel):
    capabilities:list[Literal['buildings','terrain','landcover','soils','waterways','rainfall','hydrorivers','catchments','dynamic_world']]=Field(
        default_factory=lambda:list(CAPABILITIES),min_length=1,max_length=9)
    start_date:date|None=None
    end_date:date|None=None

    @model_validator(mode='after')
    def dates(self):
        if len(set(self.capabilities))!=len(self.capabilities):raise ValueError('Duplicate capability')
        if bool(self.start_date)!=bool(self.end_date):raise ValueError('Both event dates are required')
        if self.start_date and not 0<=(self.end_date-self.start_date).days<=2:
            raise ValueError('Choose an event lasting at most three calendar days')
        return self


class ApplyEvidenceRequest(WireModel):
    buildings:bool=True
    landcover:bool=False
    accept_exploratory_materials:bool=False

    @model_validator(mode='after')
    def acknowledge(self):
        if not self.buildings and not self.landcover:raise ValueError('Select a layer to apply')
        if self.landcover and not self.accept_exploratory_materials:
            raise ValueError('Land-cover parameter assumptions must be acknowledged')
        return self


def run_one(manifest,capability,request):
    from services.geodata import global_sources as g
    adapters={'buildings':g.overture,'terrain':lambda m:g.tiled_raster(m,'terrain'),
              'landcover':lambda m:g.tiled_raster(m,'landcover'),'soils':g.soils,'waterways':g.waterways,'hydrorivers':g.hydrorivers,'catchments':g.catchments,
              'rainfall':lambda m:g.rainfall_catalog(m,request.get('start_date'),request.get('end_date')),
              'dynamic_world':lambda m:g.dynamic_world(m,None,request.get('end_date'))}
    return adapters[capability](manifest)


def enrichment_job(resource_id,bundle_id,request):
    from services.api.database import update_resource
    folder=EVIDENCE/resource_id;folder.mkdir(parents=True,exist_ok=True)
    (folder/'request.json').write_text(json.dumps(request),encoding='utf-8')
    results={}
    for capability in request['capabilities']:
        from services.api.settings import settings
        if capability=='dynamic_world' and not settings.ee_project:
            results[capability]={'status':'needs_access','reason':'Configure an Earth Engine project and application-default credentials; WorldCover is the keyless alternative'}
            continue
        if capability=='rainfall' and not request.get('start_date'):
            results[capability]={'status':'needs_input','reason':'Select event dates to discover rainfall records'}
            continue
        update_resource(resource_id,'running',stage=capability,results=results)
        started=time.perf_counter()
        # Network/native GIS libraries can block. A separate process gives each a hard deadline.
        try:
            attempt=uuid4().hex
            completed=folder/f'{capability}.{attempt}.json'
            log_path=folder/f'{capability}.{attempt}.log'
            with log_path.open('wb') as log:
                process=subprocess.Popen([sys.executable,'-m','services.geodata.enrichment',resource_id,bundle_id,capability,attempt],
                               stdout=log,stderr=log)
                budget=(1200 if capability=='rainfall' and settings.earthdata_token else 180)
                deadline=time.monotonic()+budget
                while not completed.exists() and process.poll() is None and time.monotonic()<deadline:
                    time.sleep(.1)
                # The atomically committed result is the completion handshake. Native
                # teardown or inherited pipe handles must not hold a finished job open.
                if process.poll() is None:
                    if sys.platform=='win32':
                        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=10,check=False)
                    else:process.kill()
                    process.wait(timeout=10)
            if not completed.exists():
                if time.monotonic()>=deadline:raise subprocess.TimeoutExpired(process.args,budget)
                raise subprocess.CalledProcessError(process.returncode,process.args,stderr=log_path.read_bytes())
            payload=json.loads(completed.read_text(encoding='utf-8'))
            completed.replace(folder/f'{capability}.json')
            results[capability]={'status':'catalog_only' if capability=='rainfall' and 'survey' not in payload else 'available','seconds':round(time.perf_counter()-started,2),
                'note':payload.get('note',''),'coverage_fraction':payload.get('coverage_fraction'),
                'feature_count':len(payload['features']) if 'features' in payload else None}
        except subprocess.TimeoutExpired as exc:
            results[capability]={'status':'unavailable','reason':f'Provider exceeded the {exc.timeout}-second acquisition budget'}
        except subprocess.CalledProcessError as exc:
            results[capability]={'status':'unavailable','reason':exc.stderr.decode('utf-8',errors='replace').splitlines()[-1][-400:] if exc.stderr else 'Provider failed'}
        except Exception as exc:  # noqa: BLE001 - provider isolation records failure and continues other layers.
            results[capability]={'status':'unavailable','reason':str(exc)[:400]}
        update_resource(resource_id,'running',stage=capability,results=results)
    update_resource(resource_id,'completed',stage='ready',results=results,bundle_id=bundle_id)


if __name__=='__main__':
    resource_id,bundle_id,capability,*attempt=sys.argv[1:]
    folder=EVIDENCE/resource_id
    manifest=json.loads((ROOT/bundle_id/'manifest.json').read_text(encoding='utf-8'))
    request=json.loads((folder/'request.json').read_text(encoding='utf-8'))
    cache=EVIDENCE/'cache';cache.mkdir(exist_ok=True)
    from services.api.settings import settings
    access=bool(settings.earthdata_token) if capability=='rainfall' else settings.ee_project if capability=='dynamic_world' else None
    key=hashlib.sha256(json.dumps([bundle_id,capability,request,'adapters-0.4.0',access],sort_keys=True).encode()).hexdigest()
    cached=cache/f'{key}.json'
    if cached.exists() and time.time()-cached.stat().st_mtime<86400:
        result=json.loads(cached.read_text(encoding='utf-8'))
    else:
        result=run_one(manifest,capability,request)
        stage=cache/f'{key}.{resource_id}.tmp'
        stage.write_text(json.dumps(result,allow_nan=False,default=str),encoding='utf-8');stage.replace(cached)
    result_path=folder/(f'{capability}.{attempt[0]}.json' if attempt else f'{capability}.json')
    stage=result_path.with_suffix('.tmp')
    stage.write_text(json.dumps(result,allow_nan=False,default=str),encoding='utf-8')
    stage.replace(result_path)
    # All dataset handles and output files are closed above. Windows GIS DLL teardown
    # can deadlock at interpreter exit; this disposable process has no remaining work.
    import os
    os._exit(0)
