"""Conservative footprint reconciliation and immutable bundle revisions."""
import json

import numpy as np
from pyproj import Transformer
from shapely.geometry import mapping, shape
from shapely.ops import transform
from shapely.strtree import STRtree

from services.geodata.enrichment import EVIDENCE
from services.geodata.prepare import ROOT, prepare


def reconcile(existing,incoming):
    geometries=[shape(f['geometry']) for f in existing]
    tree=STRtree(geometries)
    accepted=[];duplicates=0;invalid=0
    incoming_geometries=[shape(f['geometry']) for f in incoming]
    incoming_tree=STRtree(incoming_geometries)
    accepted_indices=set()
    for incoming_index,feature in enumerate(incoming):
        geom=incoming_geometries[incoming_index]
        if geom.is_empty or not geom.is_valid or geom.geom_type not in ('Polygon','MultiPolygon'):
            invalid+=1;continue
        overlap=False
        for index in tree.query(geom):
            other=geometries[index]
            if geom.intersection(other).area/max(min(geom.area,other.area),1e-15)>.5:
                overlap=True;break
        if not overlap:
            for index in incoming_tree.query(geom):
                if int(index) not in accepted_indices:continue
                other=incoming_geometries[index]
                if geom.intersection(other).area/max(min(geom.area,other.area),1e-15)>.5:
                    overlap=True;break
        if overlap:duplicates+=1
        else:accepted.append(feature);accepted_indices.add(incoming_index)
    return existing+accepted,{'added': len(accepted),'overlapping_kept_existing': duplicates,'invalid': invalid}


def apply_evidence(bundle_id,evidence_id,buildings=True,landcover=True):
    folder=ROOT/bundle_id
    m=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    g=m['grid'];cx=g['origin_x_m']+m['extent_m']/2;cy=g['origin_y_m']+m['extent_m']/2
    inverse=Transformer.from_crs(g['crs'],4326,always_xy=True)
    existing=[]
    for building in m['buildings']:
        geometry=transform(lambda x,y,z=None:inverse.transform(np.asarray(x)+cx,np.asarray(y)+cy),shape(building['geometry']))
        props={}
        if not building.get('height_source','').startswith('assumed'):props['height']=building['height_m']
        existing.append({'type': 'Feature','id': building['id'],'geometry': mapping(geometry),'properties': props})
    supplement={'terrain':(np.fromfile(folder/'z.bin',dtype='<f4')+g['elevation_origin_m']).tolist(),
        'vertical_datum':g['vertical_datum'],'buildings':existing,'sources':m['sources'],'evidence_id':evidence_id,
        'materials':{k:np.fromfile(folder/f'{k}.bin',dtype='<f4').tolist() for k in ['roughness','infiltration','soil_capacity']}}
    supplement['quality']=m['quality']
    supplement['assumptions']=m['assumptions']
    report={}
    if buildings:
        payload=json.loads((EVIDENCE/evidence_id/'buildings.json').read_text(encoding='utf-8'))
        supplement['buildings'],report=reconcile(existing,payload['features'])
        supplement['sources']=supplement['sources']+payload['sources']
    if landcover:
        payload=json.loads((EVIDENCE/evidence_id/'landcover.json').read_text(encoding='utf-8'))
        if payload['coverage_fraction']<1:raise ValueError('Land-cover coverage incomplete; retain current materials')
        if payload['shape']!=[g['ny'],g['nx']]:raise ValueError('Land-cover grid mismatch')
        supplement['landcover']=payload['values']
        supplement['sources']=supplement['sources']+payload['sources']
    request={'longitude': m['location'][0],'latitude': m['location'][1],'extent_m': m['extent_m'],
        'grid_cells': g['nx'],'source': 'terrarium','label': m['label']}
    return prepare(request,supplements=supplement),report
