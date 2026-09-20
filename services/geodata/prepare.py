"""Build one canonical local-metre bundle from real elevation and geometry."""
from __future__ import annotations

import hashlib
import json
import shutil
from uuid import uuid4

import numpy as np
from affine import Affine
from pyproj import CRS, Transformer
from rasterio.features import rasterize
from shapely.geometry import box, mapping, shape
from shapely.ops import transform

from services.api.contracts import PrepareRequest, content_hash
from services.api.settings import settings
from services.geodata.building_height import building_height
from services.geodata.currency import currency_for_country
from services.geodata.providers import buildings, terrarium, usgs_products

ROOT=settings.storage_root/"bundles"


def verify_bundle(folder, manifest):
    expected_id=content_hash({"processor":"0.5.0","manifest":{
        key:value for key,value in manifest.items() if key not in {"bundle_id","content_hash"}
    }})
    if manifest.get("bundle_id")!=expected_id:
        raise RuntimeError("Published bundle identity does not match its content")
    if manifest.get("content_hash")!=content_hash({
        key:value for key,value in manifest.items() if key!="content_hash"
    }):
        raise RuntimeError("Published bundle manifest hash is invalid")
    for artifact in manifest.get("artifacts",[]):
        path=folder/f"{artifact['name']}.bin"
        if not path.is_file() or path.stat().st_size!=artifact["bytes"]:
            raise RuntimeError(f"Published {artifact['name']} artifact is missing or truncated")
        if hashlib.sha256(path.read_bytes()).hexdigest()!=artifact["sha256"]:
            raise RuntimeError(f"Published {artifact['name']} artifact hash is invalid")

def binary_dilation(mask):
    p=np.pad(mask,1)
    return p[1:-1,1:-1]|p[:-2,1:-1]|p[2:,1:-1]|p[1:-1,:-2]|p[1:-1,2:]


def prepare(request: dict, progress=lambda stage: None, supplements: dict | None = None) -> dict:
    req=PrepareRequest.model_validate(request)
    currency=currency_for_country(req.country_code) or req.currency
    progress("projecting")
    zone=int((req.longitude+180)//6)+1
    crs=CRS.from_epsg((32600 if req.latitude>=0 else 32700)+min(zone,60))
    forward=Transformer.from_crs(4326,crs,always_xy=True)
    inverse=Transformer.from_crs(crs,4326,always_xy=True)
    cx,cy=forward.transform(req.longitude,req.latitude)
    n=req.grid_cells; dx=req.extent_m/n
    xmin,ymin=cx-req.extent_m/2,cy-req.extent_m/2
    yy,xx=np.mgrid[:n,:n]
    lon,lat=inverse.transform(xmin+(xx+.5)*dx,ymin+(yy+.5)*dx)
    bounds=inverse.transform_bounds(xmin,ymin,xmin+req.extent_m,ymin+req.extent_m,densify_pts=21)
    progress("fetching_elevation")
    selected_source=req.source
    selection_note=None
    if supplements and 'terrain' in supplements:
        z=np.array(supplements['terrain'],dtype=float).reshape(n,n)
        sources=supplements.get('sources',[])
        datum=supplements['vertical_datum']
    elif req.source=="auto":
        # Provider discovery is spatial, not a city-name switch. Require complete
        # high-resolution coverage before replacing the global terrain fallback.
        try:
            products,catalog=usgs_products(bounds)
            if not products:raise ValueError('No catalog coverage')
            from services.geodata.usgs import sample_products
            z,sources,datum=sample_products(products,crs,xmin,ymin,n,dx)
            sources.insert(0,{**catalog,"provider":"USGS TNMAccess","attribution":"USGS 3DEP"})
            selected_source='usgs_1m'
        except Exception as exc:  # noqa: BLE001 - auto mode deliberately falls back for any 3DEP adapter failure.
            z,sources=terrarium(lon,lat)
            selected_source='terrarium'
            datum="Mixed source datum: unresolved for quantitative building losses"
            selection_note=f'High-resolution coverage unavailable or failed ({type(exc).__name__}); using global terrain. Native accuracy remains unverified.'
    elif req.source=="terrarium":
        z,sources=terrarium(lon,lat)
        datum="Mixed source datum: unresolved for quantitative building losses"
    else:
        products,catalog=usgs_products(bounds)
        if not products:
            raise ValueError("No USGS 1 m DEM coverage found. Choose another source or upload terrain.")
        from services.geodata.usgs import sample_products
        z,sources,datum=sample_products(products,crs,xmin,ymin,n,dx)
        sources.insert(0,{**catalog,"provider":"USGS TNMAccess","attribution":"USGS 3DEP"})
    progress("fetching_buildings")
    if supplements and 'buildings' in supplements:
        features,building_sources=supplements['buildings'],[]
    else:
        features,building_sources=buildings(bounds)
    sources.extend(building_sources)
    extent=box(xmin,ymin,xmin+req.extent_m,ymin+req.extent_m)
    output_buildings: list[dict] = []; polygons=[]
    for i,feature in enumerate(features):
        geo=feature.get("geometry")
        if not geo: continue
        geom=transform(forward.transform,shape(geo))
        if not geom.is_valid: geom=geom.buffer(0)
        geom=geom.intersection(extent)
        if geom.is_empty or geom.area<4: continue
        if geom.geom_type not in ("Polygon","MultiPolygon"): continue
        polygons.append((geom,len(output_buildings)+1))
        local=transform(lambda x,y,z=None:(np.asarray(x)-cx,np.asarray(y)-cy),geom)
        props=feature.get("properties",{})
        height,height_source=building_height(props)
        output_buildings.append({"id":str(feature.get("id",props.get("OBJECTID",i))),
            "geometry":mapping(local),"area_m2":geom.area,"height_m":height,
            "height_source":height_source,
            "structure_value_minor":None,"valuation_currency":currency,
            "first_floor_elevation_m":None,"damage_curve_id":None})
    progress("rasterising")
    affine=Affine(dx,0,xmin,0,dx,ymin)
    labels=rasterize(polygons,out_shape=(n,n),transform=affine,fill=0,dtype="int32") if polygons else np.zeros((n,n),dtype=np.int32)
    solid=labels>0
    if solid.all(): raise ValueError("No exposed surface cells in this neighbourhood")
    rain_weights=(~solid).astype(float)
    for i,building in enumerate(output_buildings):
        mask=labels==i+1
        ring=binary_dilation(mask)&~solid
        exterior=np.flatnonzero(ring)
        roof_receivers=exterior
        if not exterior.size and mask.any():
            expanded=mask.copy()
            for _ in range(n):
                expanded=binary_dilation(expanded)
                roof_receivers=np.flatnonzero(expanded&~solid)
                if roof_receivers.size:break
            if not roof_receivers.size:raise ValueError("Roof block has no runoff receiver")
            building["roof_routing_assumption"]="Internal/attached roof routed to nearest exposed block boundary; facade exposure unavailable"
        if roof_receivers.size:
            rain_weights.flat[roof_receivers]+=mask.sum()/roof_receivers.size
        building["exterior_cells"]=exterior.tolist()
        building["base_elevation_m"]=float(np.median(z[ring])) if ring.any() else float(z.mean())
    if abs(rain_weights.sum()-n*n)>1e-6:
        raise ValueError("Roof allocation does not conserve rainfall")
    elevation_origin=float(np.floor(z.min()))
    z=z-elevation_origin
    for b in output_buildings:b["base_elevation_m"]-=elevation_origin
    progress("deriving_candidates")
    # Candidate areas are screened geometry, NOT inferred cadastral ownership.
    near_solid=solid.copy()
    for _ in range(3):near_solid=binary_dilation(near_solid)
    gy,gx=np.gradient(z,dx)
    candidates=[]
    stride=max(4,n//12)
    for y in range(stride,n-stride,stride):
        for x in range(stride,n-stride,stride):
            radius=2
            if near_solid[y,x] or np.hypot(gx[y,x],gy[y,x])>.15:continue
            cells=[j*n+k for j in range(y-radius,y+radius+1) for k in range(x-radius,x+radius+1) if not solid[j,k]]
            candidates.append({"id":f"site-{x}-{y}","x_m":(x+.5)*dx-req.extent_m/2,
                "y_m":(y+.5)*dx-req.extent_m/2,"elevation_m":float(z[y,x]),"cells":cells,
                "area_m2":len(cells)*dx*dx,"slope":float(np.hypot(gx[y,x],gy[y,x])),
                "eligibility":"unverified","parcel_ids":[],"source_note":"Open ground screening; parcel/utility eligibility not verified"})
    # An explicit uncalibrated material assumption, never dressed up as a soil survey.
    roughness=np.where(solid,0,.035)
    capacity=np.where(solid,0,.025)
    infiltration=np.where(solid,0,2e-6)
    if supplements and 'materials' in supplements:
        roughness=np.where(solid,0,np.array(supplements['materials']['roughness']).reshape(n,n))
        infiltration=np.where(solid,0,np.array(supplements['materials']['infiltration']).reshape(n,n))
        capacity=np.where(solid,0,np.array(supplements['materials']['soil_capacity']).reshape(n,n))
    if supplements and 'landcover' in supplements:
        classes=np.array(supplements['landcover']).reshape(n,n)
        # Explicit exploratory presets, not measured hydraulic properties.
        for codes,rough,rate,store in [([10,20,95],.08,2e-6,.025),([30,40,100],.05,2e-6,.025),
                                       ([50],.02,0.,0.),([60],.035,1e-6,.015),([70,80,90],.035,0.,0.)]:
            mask=np.isin(classes,codes)&~solid
            roughness[mask]=rough;infiltration[mask]=rate;capacity[mask]=store
    arrays={"z":z.astype("<f4"),"solid":solid.astype("u1"),"rain_weights":rain_weights.astype("<f4"),
            "roughness":roughness.astype("<f4"),"soil_capacity":capacity.astype("<f4"),
            "infiltration":infiltration.astype("<f4")}
    artifacts=[]
    for name,array in arrays.items():
        raw=array.tobytes()
        artifacts.append({"name":name,"dtype":str(array.dtype),"shape":[n,n],"bytes":len(raw),
                          "sha256":hashlib.sha256(raw).hexdigest()})
    manifest={"schema_version":"sponge.v1","label":req.label,
        "country_code":req.country_code,"currency":currency,
        "currency_source":"geocoded_country" if currency_for_country(req.country_code) else "fallback",
        "location":[req.longitude,req.latitude],"extent_m":req.extent_m,
        "grid":{"nx":n,"ny":n,"dx_m":dx,"dy_m":dx,"crs":crs.to_string(),
                "origin_x_m":xmin,"origin_y_m":ymin,"elevation_origin_m":elevation_origin,
                "row_direction":"north","vertical_datum":datum},
        "buildings":output_buildings,"candidates":candidates,"sources":sources,"artifacts":artifacts,
        "quality":{"building_coverage":"Source footprints; completeness unverified", "supplied_height_count":sum(b["height_source"].startswith("provider") for b in output_buildings), "floor_estimated_height_count":sum(b["height_source"].startswith("estimated") for b in output_buildings), "assumed_height_count":sum(b["height_source"]=="assumed display height" for b in output_buildings), "terrain_provider":selected_source,"terrain_selection_note":selection_note,"native_resolution_m":1 if selected_source=="usgs_1m" else None,
                   "parcels":"not_loaded","materials":"uncalibrated_assumptions","boundary":"must_select",
                   "drainage":"surface_only","valuation_coverage":0,"observation_validation":"not_performed"},
        "assumptions":["Materials uniform: n=0.035, infiltration=7.2 mm/h, finite storage=25 mm; uncalibrated",
            "Buildings use sourced heights, mapped floor counts at assumed 3 m per floor, or assumed 9 m display heights; valuations and first-floor elevations unavailable",
            "Computational extent is not yet verified as a contributing catchment",
            "Candidate areas require explicit user eligibility assumption or authoritative parcel import"]}
    if supplements:
        if 'assumptions' in supplements:manifest['assumptions']=list(supplements['assumptions'])
        manifest['quality'].update(supplements.get('quality',{}))
        manifest['quality']['enrichment']=supplements.get('evidence_id')
        if 'landcover' in supplements:
            manifest['quality']['materials']='source_classified_exploratory_presets'
            manifest['assumptions'][0]='WorldCover 2021 classes mapped to exploratory hydraulic presets; 10 m classification is not surveyed imperviousness. SoilGrids is not used to invent infiltration rates.'
    bundle_id=content_hash({"processor":"0.5.0","manifest":manifest})
    manifest["bundle_id"]=bundle_id
    manifest["content_hash"]=content_hash(manifest)

    ROOT.mkdir(parents=True,exist_ok=True)
    staging_root=ROOT/".staging";staging_root.mkdir(exist_ok=True)
    stage=staging_root/uuid4().hex
    folder=ROOT/bundle_id
    stage.mkdir()
    try:
        for name,array in arrays.items():
            raw=array.tobytes()
            path=stage/f"{name}.bin"
            path.write_bytes(raw)
            if hashlib.sha256(path.read_bytes()).hexdigest()!=next(
                artifact["sha256"] for artifact in artifacts if artifact["name"]==name
            ):
                raise OSError(f"Failed to verify staged {name} artifact")
        (stage/"manifest.json").write_text(json.dumps(manifest,separators=(",",":")),encoding="utf-8")
        if folder.exists():
            existing=json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
            if existing.get("content_hash")!=manifest["content_hash"]:
                raise RuntimeError("Content-address collision or corrupt published bundle")
            verify_bundle(folder,existing)
            manifest=existing
        else:
            try:
                stage.replace(folder)
            except FileExistsError:
                existing=json.loads((folder/"manifest.json").read_text(encoding="utf-8"))
                if existing.get("content_hash")!=manifest["content_hash"]:
                    raise RuntimeError("Concurrent bundle publication failed integrity verification")
                verify_bundle(folder,existing)
                manifest=existing
    finally:
        if stage.exists():shutil.rmtree(stage)
    progress("ready")
    return manifest
