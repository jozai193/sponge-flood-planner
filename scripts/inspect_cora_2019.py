"""Bounded anonymous range reads of regional model metadata and mesh only."""
import datetime
import hashlib
import io
import json
import sys
from collections import OrderedDict
from pathlib import Path

import h5py
import numpy as np
import requests

ROOT = Path('artifacts/validation/dorian-2019')
URL = 'https://noaa-nos-cora-pds.s3.amazonaws.com/cora_gec/native_grid/water_levels/fort.63_2019.nc'


class BoundedHTTP(io.RawIOBase):
    def __init__(self, url, size, etag, budget=64*1024*1024):
        self.url, self.size, self.etag = url, size, etag
        self.position = 0
        self.budget = budget
        self.transferred = 0
        self.blocks = OrderedDict()
        self.block_size = 256*1024
        self.session = requests.Session()
        self.ranges = []

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.position
    def seek(self, offset, whence=0):
        pos = offset + (0 if whence == 0 else self.position if whence == 1 else self.size)
        if not 0 <= pos <= self.size: raise ValueError('Invalid remote seek')
        self.position = pos
        return pos

    def read(self, size=-1):
        if size < 0 or size > self.budget: raise ValueError('Unbounded remote read rejected')
        end = min(self.position+size, self.size)
        chunks=[]
        while self.position < end:
            block=self.position//self.block_size
            if block not in self.blocks:
                start=block*self.block_size; stop=min(start+self.block_size,self.size)-1
                if self.transferred+stop-start+1>self.budget: raise ValueError('Remote byte budget exhausted')
                with self.session.get(self.url,headers={'Range':f'bytes={start}-{stop}','If-Match':self.etag},stream=True,timeout=45) as r:
                    r.raise_for_status()
                    if r.status_code!=206 or r.headers.get('Content-Range')!=f'bytes {start}-{stop}/{self.size}':
                        raise ValueError('Server ignored exact range')
                    payload=r.raw.read(stop-start+2)
                    if len(payload)!=stop-start+1: raise ValueError('Remote range length mismatch')
                self.transferred+=len(payload)
                self.ranges.append({'start': start,'end': stop,'sha256': hashlib.sha256(payload).hexdigest()})
                self.blocks[block]=payload
                if len(self.blocks)>128:self.blocks.popitem(last=False)
            payload=self.blocks[block]; offset=self.position%self.block_size
            n=min(end-self.position,len(payload)-offset)
            chunks.append(payload[offset:offset+n]);self.position+=n
        return b''.join(chunks)

    def readinto(self, buffer):
        value=self.read(len(buffer));buffer[:len(value)]=value;return len(value)


def plain(x):
    if isinstance(x,bytes):return x.decode('utf-8')
    if isinstance(x,np.ndarray):return plain(x.item()) if x.size==1 else [plain(v) for v in x]
    if isinstance(x,np.generic):return plain(x.item())
    if isinstance(x,float) and not np.isfinite(x):return None
    return x


def main():
    screen=json.loads((ROOT/'regional-forcing-screen.json').read_text())
    source=screen['current_source']['year_2019_file']
    size=int(source['content_range'].split('/')[-1])
    remote=BoundedHTTP(URL,size,source['etag'])
    report={'source_url': URL,'etag': source['etag'],'remote_size_bytes': size,'water_level_values_read': False,
                'sensor_observation_arrays_read': False,'production_enabled': False}
    try:
        with h5py.File(remote,'r') as f:
            report['global_attributes']={k:plain(v) for k,v in f.attrs.items() if k not in ('_NCProperties',)}
            report['variables']={k:{'shape': list(v.shape),'dtype': str(v.dtype),'attributes': {a:plain(v.attrs[a]) for a in ('units','long_name','standard_name','_FillValue') if a in v.attrs}} for k,v in f.items()}
            print(json.dumps({'metadata_read': True,'variables': list(report['variables'])}),flush=True)
            if '--mesh' in sys.argv:
                x=np.asarray(f['x'][:]);y=np.asarray(f['y'][:])
                ids=np.flatnonzero((x>=-75.73)&(x<=-75.66)&(y>=35.18)&(y<=35.25))
                nodes=[{'node_index_zero_based': int(i),'lon': float(x[i]),'lat': float(y[i])} for i in ids]
                report['local_mesh_nodes']=nodes
                print(json.dumps({'local_nodes': len(nodes)}),flush=True)
            if '--local-topology' in sys.argv:
                previous=json.loads((ROOT/'cora-mesh-screen.json').read_text())
                nodes=previous['local_mesh_nodes']
                ids=np.asarray([n['node_index_zero_based'] for n in nodes])
                depth=np.asarray(f['depth'][ids])
                for node,value in zip(nodes,depth):node['depth_m_below_model_reference']=float(value)
                report['local_mesh_nodes']=nodes
                t=np.asarray(f['time'][:])
                if plain(f['time'].attrs['units'])!='seconds since 1978-12-01':
                    raise ValueError('Unreviewed CORA time encoding')
                epoch=datetime.datetime(1978,12,1,tzinfo=datetime.UTC)
                report['time_axis']={'count': len(t),'first_utc': (epoch+datetime.timedelta(seconds=int(t[0]))).isoformat(),
                    'last_utc': (epoch+datetime.timedelta(seconds=int(t[-1]))).isoformat(),
                    'spacing_seconds': np.unique(np.diff(t)).tolist()}
                element=f['element'];attrs={k:plain(v) for k,v in element.attrs.items() if k!='DIMENSION_LIST'}
                report['element_attributes']=attrs
                if attrs.get('start_index')!=1:raise ValueError('Unreviewed triangle index convention')
                selected=[]
                for start in range(0,len(element),100000):
                    block=np.asarray(element[start:start+100000])
                    keep=np.isin(block,ids+1).all(axis=1)
                    selected.extend((block[keep]-1).tolist())
                report['local_triangles_zero_based']=selected
                print(json.dumps({'local_triangles': len(selected)}),flush=True)
    except Exception as error:  # noqa: BLE001 - the audit persists all remote-format failures as evidence.
        report['error']=f'{type(error).__name__}: {error}'
    report.update(transferred_bytes=remote.transferred,read_ranges=remote.ranges)
    output='cora-local-topology.json' if '--local-topology' in sys.argv else 'cora-mesh-screen.json'
    (ROOT/output).write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps({k:report[k] for k in ('transferred_bytes','error') if k in report}),flush=True)
    if 'error' in report:raise SystemExit(1)


if __name__=='__main__': main()
