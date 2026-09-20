"""Convert downloaded IMERG V07 half-hourly HDF5 files to a SPONGE rainfall survey."""
import argparse
import hashlib
import itertools
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import h5py
import numpy as np

from services.geodata.imports import validate_import


def sample_granule(path,longitude,latitude):
    match=re.search(r'(\d{8})-S(\d{6})-E(\d{6})',Path(path).name)
    if not match or 'V07' not in Path(path).name:raise ValueError('Expected an IMERG V07 filename with start/end timestamps')
    day,start,end=match.groups()
    begin=datetime.strptime(day+start,'%Y%m%d%H%M%S').replace(tzinfo=UTC)
    finish=datetime.strptime(day+end,'%Y%m%d%H%M%S').replace(tzinfo=UTC)+timedelta(seconds=1)
    if finish<=begin:finish+=timedelta(days=1)
    if (finish-begin).total_seconds()!=1800:raise ValueError('Expected a half-hourly IMERG granule')
    with h5py.File(path) as f:
        g=f['Grid'];lat=np.asarray(g['lat']);lon=np.asarray(g['lon']);rain=g['precipitation']
        units=rain.attrs.get('units','');units=units.decode() if isinstance(units,bytes) else str(units)
        if units.strip() not in ('mm/hr','mm/h','mm hr-1'):raise ValueError(f'Unsupported precipitation units: {units}')
        i=int(np.abs(lon-longitude).argmin());j=int(np.abs(lat-latitude).argmin())
        if abs(float(lon[i])-longitude)>.051 or abs(float(lat[j])-latitude)>.051:
            raise ValueError('Requested location is outside the granule grid')
        if rain.shape==(1,len(lon),len(lat)):value=float(rain[0,i,j])
        elif rain.shape==(1,len(lat),len(lon)):value=float(rain[0,j,i])
        else:raise ValueError('Unsupported IMERG dimension order')
        if not np.isfinite(value) or value<0:raise ValueError('IMERG precipitation sample is missing')
    return begin,finish,value


def convert(files,longitude,latitude,source):
    records=sorted(sample_granule(f,longitude,latitude) for f in files)
    if not records:raise ValueError('No IMERG files selected')
    for previous,current in itertools.pairwise(records):
        if previous[1]!=current[0]:raise ValueError('IMERG granules have gaps or overlaps; missing rainfall cannot become zero')
    origin=records[0][0]
    intervals=[{'start_s': (a-origin).total_seconds(),'end_s': (b-origin).total_seconds(),'rate_m_s': rate/3_600_000} for a,b,rate in records]
    depth=sum((i['end_s']-i['start_s'])*i['rate_m_s'] for i in intervals)
    source={**source,'observed_at':origin.isoformat(),'provenance':'provider_estimate'}
    hashes=[hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files]
    return validate_import({'kind': 'rainfall','source': source,'storm': {'name': 'IMERG V07 nearest 0.1-degree pixel',
        'duration_s': intervals[-1]['end_s'],'recession_s': 3600,'depth_m': depth,'intervals': intervals,
        'source_ids': hashes,'distribution': f'IMERG satellite estimate at {latitude}, {longitude}; not a local gauge'}}).model_dump(mode='json')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('files',nargs='+');p.add_argument('--longitude',type=float,required=True)
    p.add_argument('--latitude',type=float,required=True);p.add_argument('--source',required=True);p.add_argument('--output',required=True)
    a=p.parse_args();result=convert(a.files,a.longitude,a.latitude,json.loads(Path(a.source).read_text()))
    Path(a.output).write_text(json.dumps(result,allow_nan=False),encoding='utf-8')
