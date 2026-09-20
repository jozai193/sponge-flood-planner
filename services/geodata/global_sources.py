"""Global adapters output evidence; hydraulic parameters remain a separate decision."""
import json
from datetime import UTC, datetime

import numpy as np
from shapely import from_wkb
from shapely.geometry import box, mapping

from services.api.settings import settings
from services.geodata.providers import fetch
from services.geodata.raster import bounds_for, grid_coordinates, raster_payload, sample_window


def overture(manifest):
    return overture_bounds(bounds_for(manifest))

def overture_bounds(bounds):
    from overturemaps.core import record_batch_reader
    raw,source=fetch('https://stac.overturemaps.org/catalog.json')
    release=json.loads(raw)['latest']
    reader=record_batch_reader('building',bbox=bounds,release=release,connect_timeout=20,request_timeout=40,stac=True)
    if reader is None:raise ValueError('Overture query failed')
    features=[]
    for batch in reader:
        for row in batch.to_pylist():
            geom=from_wkb(row.pop('geometry'))
            if not geom.intersects(box(*bounds)):continue
            features.append({'type': 'Feature','id': row['id'],'geometry': mapping(geom),'properties': {
                k:row.get(k) for k in ['height','num_floors','names','sources','confidence','subtype']}})
            if len(features)>20000:raise ValueError('Overture feature budget exceeded')
    return {'type': 'FeatureCollection','features': features,'sources': [{**source,'provider':'Overture Maps',
        'release':release,'attribution':'Overture Maps Foundation and upstream contributors',
        'license_url':'https://docs.overturemaps.org/attribution/'}],
        'note': 'Footprint completeness and supplied heights are not independently verified.'}


def tile_name(lat,lon):
    return f'{"N" if lat>=0 else "S"}{abs(lat):02d}{"E" if lon>=0 else "W"}{abs(lon):03d}'


def tiled_raster(manifest,kind):
    lon,lat=grid_coordinates(manifest)
    size=3 if kind=='landcover' else 1
    keys=set(zip((np.floor(lat/size)*size).astype(int).ravel(),(np.floor(lon/size)*size).astype(int).ravel()))
    if len(keys)>9:raise ValueError('Tile budget exceeded')
    result=np.full(lon.shape,np.nan);sources=[]
    for south,west in sorted(keys):
        if kind=='landcover':
            uri=f'https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile_name(south,west)}_Map.tif'
        else:
            name=f'Copernicus_DSM_COG_10_{"N" if south>=0 else "S"}{abs(south):02d}_00_{"E" if west>=0 else "W"}{abs(west):03d}_00_DEM'
            uri=f'https://copernicus-dem-30m.s3.amazonaws.com/{name}/{name}.tif'
        mask=(lat>=south)&(lat<south+size)&(lon>=west)&(lon<west+size)
        values,source=sample_window(uri,lon[mask],lat[mask])
        result[mask]=values;sources.append(source)
    if kind=='landcover':
        result[result==0]=np.nan
        return raster_payload(result,sources,provider='ESA WorldCover',year=2021,native_resolution_m=10,
            units='class_id',license='CC-BY-4.0',classes={10:'trees',20:'shrub',30:'grass',40:'cropland',
            50:'built',60:'bare',70:'snow/ice',80:'water',90:'wetland',95:'mangrove',100:'moss/lichen'},
            note='Satellite classification, not surveyed imperviousness; no per-pixel confidence supplied here.')
    return raster_payload(result,sources,provider='Copernicus GLO-30',native_resolution_m=30,units='m',
        vertical_datum='EGM2008',surface_type='DSM',
        note='Surface elevation includes structures and vegetation. Not approved automatically as bare-earth solver terrain.')


def soils(manifest):
    from pyproj import Transformer
    from rasterio.io import MemoryFile
    lon,lat=grid_coordinates(manifest)
    # WCS uses Interrupted Goode Homolosine native coordinates.
    projection='+proj=igh +lat_0=0 +lon_0=0 +datum=WGS84 +units=m +no_defs'
    x,y=Transformer.from_crs(4326,projection,always_xy=True).transform(lon,lat)
    layers={};sources=[]
    for prop in ('sand','clay'):
        for quantile in ('Q0.05','Q0.5','Q0.95'):
            params={'map':f'/map/{prop}.map','SERVICE':'WCS','VERSION':'2.0.1','REQUEST':'GetCoverage',
                'COVERAGEID':f'{prop}_0-5cm_{quantile}','FORMAT':'GEOTIFF_INT16',
                'SUBSET':[f'X({x.min()-250},{x.max()+250})',f'Y({y.min()-250},{y.max()+250})']}
            raw,source=fetch('https://maps.isric.org/mapserv',params,max_bytes=5_000_000)
            with MemoryFile(raw) as memory, memory.open() as src:
                    source['horizontal_crs']=str(src.crs) if src.crs else projection
                    source['crs_basis']='embedded raster CRS' if src.crs else 'documented SoilGrids WCS native Interrupted Goode Homolosine'
                    sx,sy=Transformer.from_crs(4326,src.crs or projection,always_xy=True).transform(lon.ravel(),lat.ravel())
                    values=np.array([v[0] for v in src.sample(zip(sx,sy),masked=True)],dtype=float).reshape(lon.shape)
                    if src.nodata is not None:values[values==src.nodata]=np.nan
            layers[prop+'_'+quantile]=raster_payload(values/10,[],units='percent')
            sources.append(source)
    return {'provider': 'SoilGrids','native_resolution_m': 250,'depth': '0-5 cm','layers': layers,'sources': sources,
                'note': 'Estimated texture and marginal 90% prediction intervals; not measured infiltration or urban fill.'}


def waterways(manifest):
    w,s,e,n=bounds_for(manifest)
    query=f'[out:json][timeout:30];way["waterway"~"river|stream|canal|drain"]({s},{w},{n},{e});out geom;'
    try:
        raw,source=fetch('https://overpass-api.de/api/interpreter',{'data':query})
    except Exception:  # noqa: BLE001 - a second independent provider is the deliberate fallback boundary.
        raw,source=fetch('https://overpass.private.coffee/api/interpreter',{'data':query})
    data=json.loads(raw)
    if data.get('remark') or 'elements' not in data:raise ValueError('Incomplete waterway response')
    features=[{'type': 'Feature','id': str(el['id']),'properties': el.get('tags',{}),
        'geometry': {'type': 'LineString','coordinates': [[p['lon'],p['lat']] for p in el.get('geometry',[])]}}
        for el in data['elements'] if len(el.get('geometry',[]))>=2]
    return {'type': 'FeatureCollection','features': features,'sources': [{**source,'provider':'OSM waterways',
        'license_url':'https://www.openstreetmap.org/copyright'}],
        'note': 'Mapped channels only; absent records do not mean absent drainage. No bathymetry or flow boundary inferred.'}


def rainfall_catalog(manifest,start,end):
    if not start or not end:raise ValueError('Select an event start and end date to discover IMERG rainfall')
    west,south,east,north=bounds_for(manifest)
    raw,source=fetch('https://cmr.earthdata.nasa.gov/search/granules.json',{
        'short_name':'GPM_3IMERGHH','version':'07','temporal':f'{start}T00:00:00Z,{end}T23:59:59Z',
        'bounding_box':f'{west},{south},{east},{north}','page_size':1000})
    data=json.loads(raw)
    entries=data.get('feed',{}).get('entry')
    if entries is None:raise ValueError('Invalid NASA catalog response')
    catalog={'provider': 'NASA IMERG Final V07','sources': [source],'granules': [{
        'id':x['id'],'start':x.get('time_start'),'end':x.get('time_end'),
        'links':[l['href'] for l in x.get('links',[]) if l.get('rel','').endswith('/data#')]} for x in entries],
        'native_resolution_degrees': .1,'interval_minutes': 30,
        'note': 'Catalog discovery only. Data access may require Earthdata authentication; import a rainfall series to run the event.'}
    from services.geodata.earthdata import acquire
    return acquire(catalog,manifest)


def hydrorivers(manifest):
    import zipfile

    import pyogrio
    archive=settings.storage_root/'global/HydroRIVERS_v10_shp.zip'
    if not archive.exists():raise ValueError('Global HydroRIVERS cache is not ready; run python -m scripts.cache_hydrorivers once on the server')
    with zipfile.ZipFile(archive) as z:
        member=next(n for n in z.namelist() if n.endswith('.shp'))
    metadata,table=pyogrio.read_arrow(f'/vsizip/{archive.resolve().as_posix()}/{member}',bbox=bounds_for(manifest),max_features=20001)
    if len(table)>20000:raise ValueError('River feature budget exceeded')
    features=[]
    for row in table.to_pylist():
        geometry=mapping(from_wkb(row.pop(metadata['geometry_name'] or 'wkb_geometry')))
        features.append({'type': 'Feature','geometry': geometry,'properties': row})
    return {'type': 'FeatureCollection','features': features,'sources': [json.loads(archive.with_suffix('.json').read_text())],
        'note': 'Regional river network with long-term discharge estimates. Not storm discharge, channel bathymetry or underground drainage.'}


def catchments(manifest):
    import zipfile

    import pyogrio
    root=settings.storage_root/'global/basins'
    archives=list(root.glob('*.zip'))
    if len(archives)!=9:raise ValueError('Global basin cache incomplete; run python -m scripts.cache_hydrobasins once on the server')
    features=[];sources=[];bounds=bounds_for(manifest)
    for archive in archives:
        with zipfile.ZipFile(archive) as z:member=next(n for n in z.namelist() if n.endswith('.shp'))
        uri=f'/vsizip/{archive.resolve().as_posix()}/{member}'
        info=pyogrio.read_info(uri)
        if not box(*info['total_bounds']).intersects(box(*bounds)):continue
        metadata,table=pyogrio.read_arrow(uri,bbox=bounds,max_features=1001)
        if len(table)>1000:raise ValueError('Basin feature budget exceeded')
        for row in table.to_pylist():
            geometry=mapping(from_wkb(row.pop(metadata['geometry_name'] or 'wkb_geometry')))
            features.append({'type': 'Feature','geometry': geometry,'properties': row})
        if len(table):sources.append(json.loads(archive.with_suffix('.json').read_text()))
    return {'type': 'FeatureCollection','features': features,'sources': sources,
        'note': 'HydroBASINS level-6 regional catchments; this does not delineate urban drainage or establish upstream storm inflow.'}


def dynamic_world(manifest,start=None,end=None):
    from datetime import date, timedelta

    from services.api.settings import settings
    project=settings.ee_project
    if not project:raise ValueError('Earth Engine project and application-default credentials are required; WorldCover remains available without them')
    import ee
    import google.auth
    scopes=['https://www.googleapis.com/auth/earthengine']
    if settings.ee_credentials_file:
        from google.oauth2.service_account import Credentials
        credentials=Credentials.from_service_account_file(str(settings.ee_credentials_file),scopes=scopes)
    else:credentials,_=google.auth.default(scopes=scopes)
    ee.Initialize(credentials=credentials,project=project)
    last=date.fromisoformat(end) if end else datetime.now(UTC).date()
    first=date.fromisoformat(start) if start else last-timedelta(days=90)
    g=manifest['grid'];extent=manifest['extent_m']
    region=ee.Geometry.Rectangle([g['origin_x_m'],g['origin_y_m'],g['origin_x_m']+extent,g['origin_y_m']+extent],proj=g['crs'],geodesic=False)
    bands=['water','trees','grass','flooded_vegetation','crops','shrub_and_scrub','built','bare','snow_and_ice']
    collection=ee.ImageCollection('GOOGLE/DYNAMICWORLD/V1').filterBounds(region).filterDate(first.isoformat(),(last+timedelta(days=1)).isoformat())
    count=collection.size().getInfo()
    if not count:raise ValueError('No Dynamic World observations in the selected date range')
    affine=[10,0,g['origin_x_m'],0,-10,g['origin_y_m']+extent]
    values=collection.select(bands).mean().reproject(crs=g['crs'],crsTransform=affine).sampleRectangle(region=region,defaultValue=-1).getInfo()['properties']
    arrays={b:np.array(values[b],dtype=float) for b in bands}
    if any(a.size>50000 for a in arrays.values()):raise ValueError('Dynamic World sample exceeds pixel budget')
    for a in arrays.values():a[a<0]=np.nan
    coverage=float(np.logical_and.reduce([np.isfinite(a) for a in arrays.values()]).mean())
    if coverage==0:raise ValueError('Dynamic World observations contain no valid cloud-free pixels in this area and window')
    return {'provider': 'Dynamic World','coverage_fraction': coverage,'bands': {k:raster_payload(v,[],units='probability') for k,v in arrays.items()},
        'horizontal_crs': g['crs'],'transform': affine,'row_direction': 'south','image_count': count,
        'sources': [{'source_url': 'https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1',
            'dataset': 'GOOGLE/DYNAMICWORLD/V1','start_date': first.isoformat(),'end_date': last.isoformat(),
            'attribution': 'Google and World Resources Institute','license': 'CC-BY-4.0'}],
        'note': 'Mean class probabilities across available cloud-masked observations; not a measured impervious-surface map.'}
