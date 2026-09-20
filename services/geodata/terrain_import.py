"""Import a metre terrain/seabed raster without silently merging vertical datums."""
import hashlib
import json

import numpy as np
import rasterio
from pyproj import CRS, Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform

from services.geodata.prepare import ROOT, prepare
from services.geodata.raster import grid_coordinates, sample_window


def import_terrain(bundle_id,path,source):
    m=json.loads((ROOT/bundle_id/'manifest.json').read_text())
    lon,lat=grid_coordinates(m)
    with rasterio.open(path) as dataset:
        if dataset.driver!='GTiff':raise ValueError('Upload a standalone GeoTIFF')
        if not dataset.crs or CRS(dataset.crs)!=CRS(source['horizontal_crs']):raise ValueError('Raster and metadata CRS differ')
        if dataset.count!=1:raise ValueError('Expected a single-band terrain/seabed elevation raster in metres')
        if dataset.units[0] and dataset.units[0].lower() not in ('m','metre','metres','meter','meters'):
            raise ValueError('Raster elevation units must be metres; convert before importing')
        native=max(dataset.res) if dataset.crs.is_projected and dataset.crs.linear_units=='metre' else None
    elevations,provenance=sample_window(path,lon,lat)
    if not np.isfinite(elevations).all():raise ValueError('Terrain has missing pixels or does not cover the full simulation grid')
    if elevations.min()<-12000 or elevations.max()>10000:raise ValueError('Elevation values outside supported metre range')
    g=m['grid'];half=m['extent_m']/2
    inverse=Transformer.from_crs(g['crs'],4326,always_xy=True)
    features=[]
    for b in m['buildings']:
        geom=transform(lambda x,y,z=None:inverse.transform(np.asarray(x)+g['origin_x_m']+half,
            np.asarray(y)+g['origin_y_m']+half),shape(b['geometry']))
        features.append({'type': 'Feature','id': b['id'],'geometry': mapping(geom),'properties': {
            'height':b['height_m'] if not b.get('height_source','').startswith('assumed') else None}})
    provenance={**provenance,**source,'source_url':'user-upload','sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'units':'m','surface_type':source.get('surface_type','bare_earth')}
    supplements={'terrain':elevations.ravel().tolist(),'vertical_datum':source['vertical_datum'],
        'sources':m['sources']+[provenance],'buildings':features,'evidence_id':path.parent.name,
        'quality':{**m['quality'],'terrain_provider':'user_uploaded_dem','native_resolution_m':native},
        'assumptions':m['assumptions'],
        'materials':{k:np.fromfile(ROOT/bundle_id/f'{k}.bin',dtype='<f4').tolist() for k in ['roughness','infiltration','soil_capacity']}}
    return prepare({'longitude': m['location'][0],'latitude': m['location'][1],'extent_m': m['extent_m'],
        'grid_cells': g['nx'],'source': 'terrarium','label': m['label']},supplements=supplements)
