"""Compare initial water and minimum static access barriers on unchanged inputs."""

if not __debug__:
    raise RuntimeError("Integrity verification is disabled under python -O; rerun without optimization.")
import hashlib
import heapq
import json
from pathlib import Path

import numpy as np

from scripts.compare_domain_experiment import verify_core
from services.reference.coastal import CoastalBoundary
from services.reference.solver import Surface


def access_levels(bed,solid,cells):
    ny,nx=bed.shape;cost=np.full(bed.shape,np.inf);queue=[]
    for i in cells:
        row,col=divmod(i,nx);cost[row,col]=bed[row,col];heapq.heappush(queue,(float(bed[row,col]),row,col))
    while queue:
        value,row,col=heapq.heappop(queue)
        if value!=cost[row,col]:continue
        for rr,cc in ((row-1,col),(row+1,col),(row,col-1),(row,col+1)):
            if 0<=rr<ny and 0<=cc<nx and not solid[rr,cc]:
                candidate=max(value,float(bed[rr,cc]))
                if candidate<cost[rr,cc]:cost[rr,cc]=candidate;heapq.heappush(queue,(candidate,rr,cc))
    return cost


def inspect(folder,n):
    p=json.loads((folder/'protocol.json').read_text());run=next(r for r in p['bundles'] if r['grid_cells']==n)
    bundle=Path('data/local/bundles')/run['bundle_id'];g=json.loads((bundle/'manifest.json').read_text())['grid']
    shape=(g['ny'],g['nx']);z=np.fromfile(bundle/'z.bin',dtype='<f4').reshape(shape).astype(float)
    solid=np.fromfile(bundle/'solid.bin',dtype='u1').reshape(shape).astype(bool)
    assert p['boundary_edge']=='east'
    cells=tuple(i for i in range(z.size) if i%g['nx']==g['nx']-1 and not solid.flat[i])
    boundary=CoastalBoundary('east',cells,tuple((k['timeS'],k['elevationM']) for k in run['levels']),'NAVD88 local offset',p['forcing'])
    initial=boundary.initial_depth(Surface(z=z,solid=solid,dx=g['dx_m'],dy=g['dy_m']))
    costs=access_levels(z,solid,cells)+g['elevation_origin_m'];peak=max(k['elevationM'] for k in run['levels'])
    closed={}
    for edge,values,mask,width in [('west',initial[:,0],solid[:,0],g['dy_m']),('south',initial[0],solid[0],g['dx_m']),('north',initial[-1],solid[-1],g['dx_m'])]:
        closed[edge]={"initially_wet_non_solid_cells": int(np.sum((values>0)&~mask)),
            "initially_wet_wall_length_m": float(np.sum((values>0)&~mask)*width)}
    summary={"directory": str(folder),"grid": n,"initial_volume_m3": float(initial.sum()*g['dx_m']*g['dy_m']),
        "initial_wet_area_m2": float((initial>0).sum()*g['dx_m']*g['dy_m']),"closed_edge_diagnostics": closed,
        "peak_navd88_m": peak+g['elevation_origin_m']}
    return g,z,solid,initial,costs,summary


def main():
    root=Path('artifacts/validation/matthew-2016-domain4km');parent=Path('artifacts/validation/matthew-2016')
    a=inspect(parent,64);b=inspect(root,128)
    row,col=verify_core(a[0],b[0],a[1],b[1],a[2],b[2]);core=np.s_[row:row+64,col:col+64]
    delta=b[3][core]-a[3];area=a[0]['dx_m']*a[0]['dy_m']
    samples=next(r for r in json.loads((parent/'accuracy.json').read_text())['runs'] if r['grid_cells']==64)['samples']
    observations=[]
    for sample in samples:
        rr,cc=sample['row'],sample['col'];old=a[4][rr,cc];new=b[4][rr+row,cc+col]
        observations.append({"id": sample['observation_id'],"original_status": sample['status'],
            "original_access_level_navd88_m": float(old) if np.isfinite(old) else None,
            "expanded_access_level_navd88_m": float(new) if np.isfinite(new) else None,
            "access_barrier_change_m": float(new-old) if np.isfinite(old) and np.isfinite(new) else None,
            "original_initial_depth_m": float(a[3][rr,cc]),"expanded_initial_depth_m": float(b[3][rr+row,cc+col])})
    # Verify reconstruction against the original completed replay and an atomic new checkpoint.
    original=json.loads((parent/'simulation-64.json').read_text())['frames'][0]
    if not np.allclose(a[3],np.asarray(original['depth']).reshape(64,64),atol=2e-6,rtol=2e-6):raise ValueError('Original initialization differs')
    checkpoint_path=root/'checkpoint-128.json';checkpoint_check=None
    if checkpoint_path.exists():
        raw=checkpoint_path.read_bytes();e=json.loads(raw)
        if hashlib.sha256(e['payload'].encode()).hexdigest()!=e['sha256']:raise ValueError('Checkpoint checksum differs')
        checkpoint=json.loads(e['payload'])
        difference=float(np.max(np.abs(b[3]-np.asarray(checkpoint['frames'][0]['depth']).reshape(128,128))))
        if difference>2e-6:raise ValueError('Expanded initialization differs')
        checkpoint_check={"sha256": hashlib.sha256(raw).hexdigest(),"initial_depth_max_difference_m": difference}
    result={"cases": [a[5],b[5]],"core_initialization": {
        "original_volume_m3": float(a[3].sum()*area),"expanded_core_volume_m3": float(b[3][core].sum()*area),
        "added_volume_m3": float(delta.sum()*area),"maximum_depth_change_m": float(np.max(np.abs(delta))),
        "newly_connected_cells": int(np.sum((a[3]==0)&(b[3][core]>0))),"lost_connected_cells": int(np.sum((a[3]>0)&(b[3][core]==0)))},
        "observations": observations,"checkpoint_initialization_check": checkpoint_check,
        "scope": 'Static input diagnosis before the expanded result. No expanded predictions or HWM elevations used. Minimum-barrier paths omit travel time, friction and flow capacity. Wet closed-edge lengths are numerical boundary diagnostics, not verified shoreline lengths.'}
    (root/'connectivity-diagnosis.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))


if __name__=='__main__':main()
