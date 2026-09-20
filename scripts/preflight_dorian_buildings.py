"""Check current footprint overlap using only the unexposed metadata screen."""
import json
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Point, box, shape
from shapely.ops import transform, unary_union

from services.geodata.providers import buildings

root=Path('artifacts/validation/dorian-2019');c=json.loads((root/'candidate-screen.json').read_text());d=c['domain']
project=Transformer.from_crs(4326,d['projected_crs'],always_xy=True)
cx,cy=project.transform(d['center_lon'],d['center_lat'])
bounds=Transformer.from_crs(d['projected_crs'],4326,always_xy=True).transform_bounds(cx-1000,cy-1000,cx+1000,cy+1000,densify_pts=21)
path=root/'current-buildings.geojson'
if path.exists():features=json.loads(path.read_text())['features']
else:
    features,sources=buildings(bounds)
    path.write_text(json.dumps({'type': 'FeatureCollection','features': features}))
    (root/'building-sources.json').write_text(json.dumps(sources,indent=2))
geometries=[transform(project.transform,shape(f['geometry'])) for f in features]
union=unary_union(geometries);rows=[]
for mark in c['marks']:
    t=Transformer.from_crs({2:4269,3:4267,4:4326}[mark['hdatum_id']],d['projected_crs'],always_xy=True)
    x,y=t.transform(mark['longitude_dd'],mark['latitude_dd']);point=Point(x,y)
    row={'observation_id': mark['hwm_id'],'description': mark['description'],
        'exact_coordinate_in_current_building': union.covers(point),'distance_to_current_building_m': union.distance(point),
        'setting_review': 'outdoor_sidewalk_description' if mark['hwm_id']==36721 else 'building_corner_setting_needs_independent_review','grids': []}
    for n in (64,128):
        dx=2000/n;col=int((x-(cx-1000))//dx);r=int((y-(cy-1000))//dx)
        west=cx-1000+col*dx;south=cy-1000+r*dx;cell=box(west,south,west+dx,south+dx)
        row['grids'].append({'grid_cells': n,'row': r,'col': col,'cell_center_in_current_building': union.covers(Point(west+dx/2,south+dx/2)),
            'footprint_fraction': union.intersection(cell).area/(dx*dx)})
    rows.append(row)
result={'status': 'metadata_geometry_review_only','feature_count': len(features),'observations': rows,
    'observed_hwm_elevations_exposed': False,
    'limitation': 'Current footprints are not verified 2019 geometry. Geometric overlap cannot establish whether the original mark was inside, outside or transferred. Cell-centre checks are preflight estimates, not a frozen simulation mask. Do not move marks or buildings to obtain eligibility.'}
(root/'building-preflight.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
