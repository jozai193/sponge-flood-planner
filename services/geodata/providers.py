"""Bounded, cached public geodata adapters. Provider bytes retain provenance."""
from __future__ import annotations

import hashlib
import io
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
import numpy as np
from PIL import Image

from services.api.settings import settings

UA = "SPONGE-research-prototype/0.1 (bounded interactive neighbourhood requests)"
CACHE = settings.storage_root/"provider-cache"


def fetch(url: str, params: dict | None = None, *, max_bytes=25_000_000, timeout_s=60, max_age_s: float | None = None) -> tuple[bytes, dict]:
    key = hashlib.sha256((url+json.dumps(params or {}, sort_keys=True)).encode()).hexdigest()
    CACHE.mkdir(parents=True, exist_ok=True)
    path, meta = CACHE / key, CACHE / f"{key}.json"
    if path.exists() and meta.exists():
        try:
            if path.stat().st_size > max_bytes:
                raise ValueError('Cached provider response exceeds bounded download size')
            raw = path.read_bytes()
            source = json.loads(meta.read_text(encoding='utf-8'))
            if max_age_s is not None:
                retrieved = datetime.fromisoformat(source['retrieved_at'])
                if not 0 <= (datetime.now(UTC) - retrieved).total_seconds() <= max_age_s:
                    raise ValueError('Cached provider response expired')
            if (isinstance(source, dict) and source.get('byte_length') == len(raw)
                    and source.get('sha256') == hashlib.sha256(raw).hexdigest()):
                return raw, source
        except (OSError, ValueError, KeyError, TypeError):
            pass  # Incomplete or mismatched cache: reacquire, never trust partial bytes.
    with httpx.Client(timeout=timeout_s, headers={"User-Agent": UA}, follow_redirects=False) as client, \
            client.stream("GET", url, params=params) as response:
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content) > max_bytes:
                    raise ValueError("Provider response exceeds bounded download size")
    raw = bytes(content)
    source = {"source_url": str(httpx.URL(url, params=params)), "sha256": hashlib.sha256(raw).hexdigest(),
              "retrieved_at": datetime.now(UTC).isoformat(), "byte_length": len(raw)}
    # Publish each file atomically. A competing writer may still produce a
    # mismatched pair, which the digest check above rejects on the next read.
    for destination, data in ((path, raw), (meta, json.dumps(source).encode('utf-8'))):
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=CACHE, delete=False) as output:
                temporary = Path(output.name)
                output.write(data)
            os.replace(temporary, destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return raw, source


def terrarium(longitudes: np.ndarray, latitudes: np.ndarray, zoom=15):
    """Bilinear sampling of decoded elevations, never RGB interpolation."""
    n = 2**zoom
    gx = (longitudes+180)/360*n*256
    gy = (1-np.arcsinh(np.tan(np.radians(latitudes)))/np.pi)/2*n*256
    xmin, xmax = int(np.floor(gx.min()/256)), int(np.floor(gx.max()/256))
    ymin, ymax = int(np.floor(gy.min()/256)), int(np.floor(gy.max()/256))
    if (xmax-xmin+1)*(ymax-ymin+1) > 64:
        raise ValueError("Requested terrain exceeds tile budget")
    mosaic = np.empty(((ymax-ymin+1)*256, (xmax-xmin+1)*256))
    sources = []
    for ty in range(ymin, ymax+1):
        for tx in range(xmin, xmax+1):
            url = f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{zoom}/{tx}/{ty}.png"
            raw, source = fetch(url, max_bytes=2_000_000)
            rgb = np.asarray(Image.open(io.BytesIO(raw)).convert("RGB"), dtype=float)
            z = rgb[..., 0]*256 + rgb[..., 1] + rgb[..., 2]/256 - 32768
            mosaic[(ty-ymin)*256:(ty-ymin+1)*256, (tx-xmin)*256:(tx-xmin+1)*256] = z
            sources.append({**source,"provider":"AWS Terrain Tiles", "format":"Terrarium",
                            "native_resolution_m":None,"native_resolution_note":"Mixed source DEM resolution; tile sampling is not native survey resolution",
                            "attribution":"Mapzen / source datasets in AWS Terrain Tiles registry",
                            "license_url":"https://registry.opendata.aws/terrain-tiles/"})
    px=np.clip(gx-xmin*256-.5,0,mosaic.shape[1]-1)
    py=np.clip(gy-ymin*256-.5,0,mosaic.shape[0]-1)
    ix,iy=np.floor(px).astype(int),np.floor(py).astype(int)
    jx,jy=np.minimum(ix+1,mosaic.shape[1]-1),np.minimum(iy+1,mosaic.shape[0]-1)
    wx,wy=px-ix,py-iy
    sampled=(1-wy)*((1-wx)*mosaic[iy,ix]+wx*mosaic[iy,jx])+wy*((1-wx)*mosaic[jy,ix]+wx*mosaic[jy,jx])
    if np.any(sampled < -500) or not np.isfinite(sampled).all():
        raise ValueError("Terrain contains missing or unsupported elevations")
    return sampled, sources


PHILLY_BUILDINGS = "https://services.arcgis.com/fLeGjb7u4uXqeF9q/ArcGIS/rest/services/Building_Footprints/FeatureServer/0/query"


def buildings(bounds):
    from services.geodata.registry import select_provider
    provider = select_provider('buildings', bounds)
    west,south,east,north=bounds
    if provider.id == 'philadelphia_buildings':
        features: list[dict] = []
        sources: list[dict] = []
        for offset in range(0, 10000, 1000):
            raw, source = fetch(PHILLY_BUILDINGS, {"f":"geojson","where":"1=1",
                "geometry":f"{west},{south},{east},{north}","geometryType":"esriGeometryEnvelope",
                "inSR":4326,"spatialRel":"esriSpatialRelIntersects","outFields":"*","outSR":4326,
                "resultOffset":offset,"resultRecordCount":1000})
            data=json.loads(raw)
            if "features" not in data:
                raise ValueError("Building provider returned no valid feature collection")
            from services.geodata.building_height import philadelphia_height_properties
            features.extend({**feature,'properties':philadelphia_height_properties(feature.get('properties') or {})} for feature in data['features'])
            sources.append({**source,"provider":"City of Philadelphia building footprints",
                            "attribution":"City of Philadelphia","license_url":"https://www.phila.gov/open-data/"})
            if len(data["features"]) < 1000:
                return features,sources
        raise ValueError("Too many buildings for requested neighbourhood")
    try:
        from services.geodata.city_buildings import acquire
        return acquire(bounds)
    except Exception as exc:  # noqa: BLE001 - any adapter failure must fall back to bounded OSM acquisition.
        fallback_reason=f'Global footprint acquisition failed ({type(exc).__name__}); OSM coverage may be incomplete.'
    query=f'[out:json][timeout:30];way["building"]({south},{west},{north},{east});out geom;'
    raw, source=fetch("https://overpass-api.de/api/interpreter",{"data":query})
    data=json.loads(raw)
    if data.get('remark') or not isinstance(data.get('elements'), list):
        raise ValueError('Building provider returned an incomplete or invalid response; retry preparation')
    features=[]
    for element in data.get("elements",[]):
        coords=[[p["lon"],p["lat"]] for p in element.get("geometry",[])]
        if len(coords)>=4 and coords[0]==coords[-1]:
            features.append({"type":"Feature","id":str(element["id"]),
                             "properties":element.get("tags",{}),"geometry":{"type":"Polygon","coordinates":[coords]}})
    return features,[{**source,"coverage_note":fallback_reason,"provider":"OpenStreetMap / Overpass","attribution":"© OpenStreetMap contributors",
                      "license_url":"https://www.openstreetmap.org/copyright"}]


def usgs_products(bounds):
    raw, source=fetch("https://tnmaccess.nationalmap.gov/api/v1/products",{
        "bbox":",".join(map(str,bounds)),"datasets":"Digital Elevation Model (DEM) 1 meter","max":20})
    data=json.loads(raw)
    return data.get("items",[]),source
