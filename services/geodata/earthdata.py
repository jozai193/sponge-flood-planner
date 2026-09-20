"""Authenticated NASA downloads with bounded files and credential-safe redirects."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse
from uuid import uuid4

import httpx

from services.api.settings import settings

CACHE=settings.storage_root/'earthdata'


def trusted_nasa(url):
    parsed=urlparse(url);host=(parsed.hostname or '').lower()
    return parsed.scheme=='https' and parsed.port in (None,443) and not parsed.username and not parsed.password and (
        host in ('urs.earthdata.nasa.gov','data.gesdisc.earthdata.nasa.gov') or host.endswith('.gesdisc.eosdis.nasa.gov'))


def download(url,token,client):
    if not trusted_nasa(url):raise ValueError('Rainfall download is not an approved NASA data host')
    name=Path(urlparse(url).path).name
    if not name.endswith('.HDF5') or 'V07' not in name:raise ValueError('Expected an IMERG V07 HDF5 granule')
    folder=CACHE/hashlib.sha256(url.encode()).hexdigest();folder.mkdir(parents=True,exist_ok=True)
    path=folder/name;meta=folder/'source.json'
    if path.exists() and meta.exists():
        try:source=json.loads(meta.read_text())
        except (OSError,ValueError):source={}
        if isinstance(source,dict) and path.stat().st_size==source.get('bytes') and hashlib.sha256(path.read_bytes()).hexdigest()==source.get('sha256'):
            return path,source
    current=url
    cdn_authorized=False
    for _ in range(6):
        parsed=urlparse(current)
        nasa=trusted_nasa(current)
        cdn=cdn_authorized and parsed.scheme=='https' and parsed.port in (None,443) and not parsed.username and not parsed.password and parsed.hostname=='d2b3c3wh8s6en5.cloudfront.net'
        if not nasa and not cdn:raise ValueError('NASA redirected to an unsupported host; credentials were not forwarded')
        headers={'Authorization':'Bearer '+token} if nasa else {}
        with client.stream('GET',current,headers=headers) as response:
            if response.status_code in (301,302,303,307,308):
                if 'location' not in response.headers:raise ValueError('NASA redirect omitted a location')
                cdn_authorized=nasa or cdn
                current=urljoin(current,response.headers['location']);continue
            if response.status_code in (401,403):raise ValueError('Earthdata access denied; check token expiry and dataset access')
            if response.status_code!=200:raise ValueError(f'NASA data service returned HTTP {response.status_code}')
            size=0;digest=hashlib.sha256();stage=folder/f'.{name}.{uuid4().hex}.partial'
            try:
                with stage.open('wb') as output:
                    for chunk in response.iter_bytes(1024*1024):
                        size+=len(chunk)
                        if size>75_000_000:raise ValueError('Rainfall granule exceeds 75 MB')
                        output.write(chunk);digest.update(chunk)
                with stage.open('rb') as f:
                    if f.read(8)!=b'\x89HDF\r\n\x1a\n':raise ValueError('NASA returned a login page or an invalid HDF5 file')
                stage.replace(path)
            finally:
                stage.unlink(missing_ok=True)
            source={'source_url':url,'sha256':digest.hexdigest(),'bytes':size}
            meta_stage=folder/f'.source.{uuid4().hex}.partial'
            try:
                meta_stage.write_text(json.dumps(source),encoding='utf-8');meta_stage.replace(meta)
            finally:
                meta_stage.unlink(missing_ok=True)
            return path,source
    raise ValueError('NASA redirect limit exceeded')


def acquire(catalog,manifest):
    if not settings.earthdata_token:return catalog
    from scripts.import_imerg import convert
    if not catalog['granules']:raise ValueError('No rainfall granules found for this event')
    paths=[];sources=[];size=0
    with httpx.Client(timeout=60,follow_redirects=False) as client:
        for granule in catalog['granules']:
            candidates=[u for u in granule['links'] if trusted_nasa(u) and urlparse(u).path.endswith('.HDF5')]
            if not candidates:raise ValueError('Catalog granule has no supported direct HDF5 download')
            path,source=download(candidates[0],settings.earthdata_token.get_secret_value(),client)
            size+=source['bytes']
            if size>2_000_000_000:raise ValueError('Rainfall event exceeds the 2 GB acquisition budget; select fewer dates')
            paths.append(path);sources.append(source)
    survey=convert(paths,*manifest['location'],{'title': 'NASA IMERG Final V07','attribution': 'NASA GPM',
        'horizontal_crs': 'EPSG:4326','vertical_datum': 'not applicable','license': 'NASA Earth science data policy',
        'observed_at': catalog['granules'][0]['start'],'provenance': 'provider_estimate'})
    return {**catalog,'survey':survey,'download_sources':sources,
        'note':'Downloaded IMERG V07, nearest 0.1-degree rainfall pixel. Exact intervals available for simulation; not a local rain gauge.'}
