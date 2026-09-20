"""Display-only OSM context; never changes the hydraulic raster."""
import json

import numpy as np
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon, box, mapping
from shapely.ops import transform

from services.geodata.providers import fetch


def mapped_context(manifest):
    grid=manifest['grid']; extent=manifest['extent_m']
    cx=grid['origin_x_m']+extent/2; cy=grid['origin_y_m']+extent/2
    inverse=Transformer.from_crs(grid['crs'],4326,always_xy=True)
    forward=Transformer.from_crs(4326,grid['crs'],always_xy=True)
    corners=[inverse.transform(cx+x,cy+y) for x in [-extent/2,extent/2] for y in [-extent/2,extent/2]]
    west,south=min(p[0] for p in corners),min(p[1] for p in corners)
    east,north=max(p[0] for p in corners),max(p[1] for p in corners)
    bbox=f'{south},{west},{north},{east}'
    query=f'[out:json][timeout:10];(way["highway"]({bbox});way["leisure"~"park|garden|pitch"]({bbox});way["landuse"~"grass|forest|recreation_ground"]({bbox});node["natural"="tree"]({bbox}););out geom;'
    attribution='© OpenStreetMap contributors'
    vegetation_source=None
    vegetation_status='Mapped vegetation; coverage may be incomplete.'
    if -75.30 < west < -74.94 and 39.86 < south < 40.14:
        raw,source=fetch('https://services.arcgis.com/fLeGjb7u4uXqeF9q/ArcGIS/rest/services/Street_Centerline/FeatureServer/0/query',{'f':'geojson','where':'1=1','geometry':f'{west},{south},{east},{north}','geometryType':'esriGeometryEnvelope','inSR':4326,'spatialRel':'esriSpatialRelIntersects','outFields':'*','outSR':4326,'resultRecordCount':2000},timeout_s=15)
        features=json.loads(raw)
        if 'features' not in features or len(features['features'])>=2000:raise ValueError('Street dataset incomplete')
        data: dict[str, list[dict]] = {'elements':[]}
        for feature in features['features']:
            props={k.lower():v for k,v in feature['properties'].items()};geom=feature['geometry']
            parts=[geom['coordinates']] if geom['type']=='LineString' else geom['coordinates']
            for part in parts:
                data['elements'].append({'type':'way','id':feature.get('id',props.get('objectid','')),'tags':{'highway':'residential','name':props.get('stname') or props.get('st_name') or ''},'geometry':[{'lon':p[0],'lat':p[1]} for p in part]})
        attribution='City of Philadelphia street centerlines'
        # Municipal tree inventory supplies actual mapped positions, not image guesses.
        try:
            vegetation_raw,vegetation_source=fetch('https://services.arcgis.com/fLeGjb7u4uXqeF9q/ArcGIS/rest/services/ppr_tree_inventory_2025/FeatureServer/0/query',{'f':'geojson','where':'1=1','geometry':f'{west},{south},{east},{north}','geometryType':'esriGeometryEnvelope','inSR':4326,'spatialRel':'esriSpatialRelIntersects','outFields':'*','outSR':4326,'resultRecordCount':2000},timeout_s=15)
            vegetation=json.loads(vegetation_raw)
            if 'features' not in vegetation or vegetation.get('exceededTransferLimit') or len(vegetation['features'])>=2000:raise ValueError('Incomplete tree inventory response')
            for feature in vegetation['features']:
                geometry=feature.get('geometry') or {}
                if geometry.get('type')!='Point':continue
                lon,lat=geometry['coordinates'][:2]
                data['elements'].append({'type':'node','id':'philly-tree-'+str(feature.get('id',feature.get('properties',{}).get('OBJECTID',''))),'lon':lon,'lat':lat,'tags':{'natural':'tree'}})
            vegetation_status='City of Philadelphia 2025 tree inventory positions; current coverage and crown dimensions unverified.'
        except Exception:  # noqa: BLE001 - optional city inventory failure is disclosed and isolated.
            vegetation_status='Mapped tree inventory unavailable; classified-cover fallback is reported separately.'

    else:
        for endpoint in ('https://overpass-api.de/api/interpreter','https://overpass.private.coffee/api/interpreter'):
            try:
                raw,source=fetch(endpoint,{'data':query},timeout_s=15)
                data=json.loads(raw)
                if not isinstance(data,dict) or data.get('remark') or not isinstance(data.get('elements'),list):
                    raise ValueError('Incomplete or invalid map response')
                break
            except Exception:
                if 'private.coffee' in endpoint:raise
    if data.get('remark'):raise ValueError('Map context provider returned incomplete results')
    bounds=box(-extent/2,-extent/2,extent/2,extent/2)
    def local(x,y,z=None):
        px,py=forward.transform(x,y);return np.asarray(px)-cx,np.asarray(py)-cy
    roads=[];green=[];trees=[]
    for item in data.get('elements',[]):
        tags=item.get('tags',{})
        if item['type']=='node':
            x,y=local(item['lon'],item['lat'])
            if bounds.covers(Point(x,y)):trees.append({'position':[float(x),float(y)],'id':str(item['id'])})
            continue
        coordinates=[(p['lon'],p['lat']) for p in item.get('geometry',[])]
        if len(coordinates)<2:continue
        if 'highway' in tags:
            geom=transform(local,LineString(coordinates)).intersection(bounds)
            parts=[geom] if geom.geom_type=='LineString' else list(getattr(geom,'geoms',[]))
            for part in parts:
                if part.geom_type=='LineString' and part.length>1:
                    roads.append({'id':str(item['id']),'name':tags.get('name',''),'kind':tags['highway'],'path':list(part.coords)})
        elif len(coordinates)>3 and coordinates[0]==coordinates[-1]:
            geom=transform(local,Polygon(coordinates)).buffer(0).intersection(bounds)
            if not geom.is_empty and geom.geom_type in ('Polygon','MultiPolygon'):
                green.append({'id':str(item['id']),'name':tags.get('name',''),'geometry':mapping(geom)})
    tree_attribution='City of Philadelphia 2025 tree inventory' if attribution.startswith('City') else '© OpenStreetMap contributors'
    return {'roads':roads,'green':green,'trees':trees,'source':source,'vegetation_source':vegetation_source,'vegetation_status':vegetation_status,'attribution':attribution,'license_url':'https://www.phila.gov/open-data/' if attribution.startswith('City') else 'https://www.openstreetmap.org/copyright','assumptions':['Road widths and pavement styling are illustrative; centreline positions are sourced map geometry.',f'Vegetation: {tree_attribution}. Inventory trees use mapped positions; crown shape and height are illustrative.',vegetation_status,'Map context is display-only and does not modify simulation materials.']}


def city_context(manifest):
    # Independent providers: a street service outage must not erase vegetation/water.
    try:
        context=mapped_context(manifest)
    except Exception:  # noqa: BLE001 - optional mapped context has an explicit degraded response.
        context={'roads': [],'green': [],'trees': [],'assumptions': ['Mapped street/tree provider unavailable.'],'vegetation_status': 'Mapped tree source unavailable.'}
    try:
        from services.geodata.landscape import add_landscape
        return add_landscape(manifest,context)
    except Exception:  # noqa: BLE001 - optional classified-cover failure is disclosed in context.
        context['landscape_status']='Global tree-cover and water source unavailable.'
        context['assumptions'].append(context['landscape_status'])
        return context
