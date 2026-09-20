"""Bounded extraction of modeled regional levels, never USGS target traces.

The result is a forcing preflight in model MSL, not an admitted NAVD88 boundary.
All triangle vertices must be valid at a time; missing vertices are not replaced.
"""
import datetime
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import h5py
import numpy as np

from scripts.inspect_cora_2019 import URL, BoundedHTTP, plain

ROOT=Path('artifacts/validation/dorian-2019/cora-forcing-candidate-v1')
PARENT=ROOT.parent


def main():
    ROOT.mkdir(exist_ok=True)
    mappings=json.loads((PARENT/'cora-boundary-mapping.json').read_text())
    source=json.loads((PARENT/'regional-forcing-screen.json').read_text())['current_source']['year_2019_file']
    ids=np.array(sorted({i for p in mappings['mappings'] for i in p['node_indices_zero_based']}))
    start=datetime.datetime(2019,9,5,tzinfo=datetime.UTC)
    end=datetime.datetime(2019,9,8,tzinfo=datetime.UTC)
    files=['scripts/extract_cora_dorian_candidate.py','scripts/inspect_cora_2019.py',str(PARENT/'cora-boundary-mapping.json')]
    protocol={'kind': 'regional_model_forcing_preflight_not_observed_truth','source_url': URL,'etag': source['etag'],
        'start_utc': start.isoformat(),'end_utc': end.isoformat(),'node_indices_zero_based': ids.tolist(),
        'quantity': 'zeta, model MSL metres; no NAVD88 offset applied',
        'vertex_policy': 'Every contributing triangle vertex finite and unequal to source fill value; no nearest-node fallback.',
        'missing_interpolation': 'null, never zero or filled from another side of the island',
        'boundary_geometry': 'All geometric perimeter points extracted; no physical open-water face selection admitted.',
        'source_sha256': {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in files},
        'byte_budget': 64*1024*1024,'production_enabled': False}
    encoded=json.dumps(protocol,indent=2);pp=ROOT/'protocol.json'
    if pp.exists() and pp.read_text()!=encoded:raise ValueError('Frozen extraction protocol changed')
    pp.write_text(encoded)
    remote=BoundedHTTP(URL,int(source['content_range'].split('/')[-1]),source['etag'],budget=protocol['byte_budget'])
    with h5py.File(remote,'r') as f:
        if plain(f['time'].attrs['units'])!='seconds since 1978-12-01':raise ValueError('Time units changed')
        if plain(f['zeta'].attrs['units'])!='m':raise ValueError('Water-level units changed')
        epoch=datetime.datetime(1978,12,1,tzinfo=datetime.UTC)
        t=np.asarray(f['time'][:],dtype=float)
        selected=np.flatnonzero((t>=(start-epoch).total_seconds())&(t<=(end-epoch).total_seconds()))
        if len(selected)!=73 or not np.all(np.diff(selected)==1):raise ValueError('Expected complete hourly period including endpoints')
        values=np.asarray(f['zeta'][selected[0]:selected[-1]+1,ids])
        fill=float(plain(f['zeta'].attrs['_FillValue']))
    valid=np.isfinite(values)&(values!=fill)
    times=[(epoch+datetime.timedelta(seconds=float(t[i]))).isoformat() for i in selected]
    lookup={int(i):k for k,i in enumerate(ids)}
    point_values=[];point_valid=[]
    for p in mappings['mappings']:
        columns=[lookup[i] for i in p['node_indices_zero_based']]
        ok=valid[:,columns].all(axis=1)
        interpolated=values[:,columns]@np.asarray(p['weights'])
        point_values.append([float(x) if k else None for x,k in zip(interpolated,ok)])
        point_valid.append(ok)
    point_valid=np.asarray(point_valid)
    nodes=[{'node_index_zero_based': int(i),'valid_hours': int(valid[:,k].sum()),
                'levels_m_model_msl': [float(x) if ok else None for x,ok in zip(values[:,k],valid[:,k])]} for k,i in enumerate(ids)]
    report={'status': 'extracted_not_admitted_as_boundary','time_utc': times,'node_count': len(ids),'nodes': nodes,
        'points': [{'edge': p['edge'],'face_index': p['face_index'],'node_indices_zero_based': p['node_indices_zero_based'],
                    'weights': p['weights'],'all_vertices_below_model_zero': p['all_vertices_below_model_zero'],
                    'levels_m_model_msl': levels,'valid_hours': int(ok.sum())} for p,levels,ok in zip(mappings['mappings'],point_values,point_valid)],
        'perimeter_points_valid_entire_period': int(point_valid.all(axis=1).sum()),
        'node_samples_valid': int(valid.sum()),'node_samples_total': int(valid.size),
        'transferred_bytes': remote.transferred,'byte_ranges': remote.ranges,
        'datum_offset_applied': None,'usgs_sensor_traces_read': False,'production_enabled': False,
        'remaining': ['Select open boundary faces using physical coastline/hydraulic geometry.',
            'Resolve datum and spatial uncertainty before using modeled MSL as NAVD88.',
            'Retain assimilation provenance and hourly forcing resolution.',
            'Reject invalid/dry contributing nodes; do not interpolate across gaps.']}
    (ROOT/'results.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps({k:report[k] for k in ('status','node_count','perimeter_points_valid_entire_period','node_samples_valid','node_samples_total','transferred_bytes')}))


if __name__=='__main__':main()
