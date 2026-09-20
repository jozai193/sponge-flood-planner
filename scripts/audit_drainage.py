"""Read public inventories; do not infer hydraulic capacities from locations."""
import json
from pathlib import Path

from services.geodata.providers import fetch

BASE='https://mapservices.pasda.psu.edu/server/rest/services/pasda/CityPhillyWater/MapServer'
output={'scope':'Spring Garden 600 m neighbourhood bounding envelope','layers':[]}
for layer in [1,2,4]:
    meta,meta_source=fetch(f'{BASE}/{layer}',{'f':'json'})
    raw,source=fetch(f'{BASE}/{layer}/query',{'f':'geojson','where':'1=1','geometry':'-75.16752,39.96229,-75.16048,39.96771','geometryType':'esriGeometryEnvelope','inSR':4326,'spatialRel':'esriSpatialRelIntersects','outFields':'*','outSR':4326,'resultRecordCount':1000})
    data=json.loads(raw);metadata=json.loads(meta)
    if 'features' not in data or len(data['features'])>=1000:raise ValueError('Incomplete inventory response')
    output['layers'].append({'id':layer,'name':metadata.get('name'),'count':len(data['features']),'fields':[f['name'] for f in metadata.get('fields',[])],'source':source,'metadata_source':meta_source,'features':data['features']})
folder=Path('artifacts/verification');folder.mkdir(parents=True,exist_ok=True)
(folder/'drainage-inventory.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
print(json.dumps([{k:v for k,v in item.items() if k in ['name','count','fields']} for item in output['layers']]))
