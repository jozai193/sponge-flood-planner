"""Convert bounded local GIS/rainfall files to the shared survey JSON contract.

Examples are in docs/hackathon-build/data-expansion.md. No external writes.
"""
import argparse
import csv
import json
from pathlib import Path

from services.geodata.imports import validate_import


def convert_vector(path,kind,source,bounds=None,layer=None):
    import pyogrio
    from shapely import from_wkb
    from shapely.geometry import mapping
    metadata,table=pyogrio.read_arrow(path,bbox=bounds,layer=layer,max_features=20001)
    if len(table)>20000:raise ValueError('More than 20,000 features; supply a smaller bounding box')
    geom_col=metadata['geometry_name'] or 'wkb_geometry'
    source={**source,'horizontal_crs':metadata['crs']}
    features=[]
    for row in table.to_pylist():
        geometry=mapping(from_wkb(row.pop(geom_col)))
        features.append({'type': 'Feature','geometry': geometry,'properties': row})
    return validate_import({'kind': kind,'source': source,'features': features}).model_dump(mode='json')


def convert_rainfall(path,source,name,recession=3600):
    rows=list(csv.DictReader(Path(path).read_text(encoding='utf-8-sig').splitlines()))
    intervals=[{'start_s': float(r['start_s']),'end_s': float(r['end_s']),'rate_m_s': float(r['rate_mm_hr'])/3_600_000} for r in rows]
    duration=max(i['end_s'] for i in intervals)
    depth=sum((i['end_s']-i['start_s'])*i['rate_m_s'] for i in intervals)
    return validate_import({'kind': 'rainfall','source': source,'storm': {'name': name,'duration_s': duration,
        'recession_s': recession,'depth_m': depth,'intervals': intervals,'source_ids': [source['title']]}}).model_dump(mode='json')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('input');p.add_argument('output');p.add_argument('--source',required=True,help='SurveySource metadata JSON')
    p.add_argument('--kind',required=True,choices=['buildings','landcover','waterways','catchments','observations','rainfall'])
    p.add_argument('--bbox',nargs=4,type=float,help='Bounds in the source dataset CRS')
    p.add_argument('--layer');p.add_argument('--name',default='Imported rainfall event')
    args=p.parse_args();source=json.loads(Path(args.source).read_text(encoding='utf-8'))
    result=convert_rainfall(args.input,source,args.name) if args.kind=='rainfall' else convert_vector(args.input,args.kind,source,args.bbox,args.layer)
    Path(args.output).write_text(json.dumps(result,allow_nan=False,default=str),encoding='utf-8')
