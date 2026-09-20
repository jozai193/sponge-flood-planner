"""Find the lowest terrain barrier from the prescribed reservoir to each mark."""
import heapq
import itertools
import json
import sys
from collections import deque
from pathlib import Path

import numpy as np

root=Path(sys.argv[1]);p=json.loads((root/'protocol.json').read_text());runs=json.loads((root/'accuracy.json').read_text())['runs']
selected_grid=int(sys.argv[2]) if len(sys.argv)>2 else None
a=next(a for a in runs if a['grid_cells']==selected_grid) if selected_grid else runs[-1]
r=next(r for r in p['bundles'] if r['grid_cells']==a['grid_cells'])
folder=Path('data/local/bundles')/r['bundle_id'];g=json.loads((folder/'manifest.json').read_text())['grid'];nx,ny=g['nx'],g['ny']
z=np.fromfile(folder/'z.bin',dtype='<f4').astype(float)+g['elevation_origin_m'];solid=np.fromfile(folder/'solid.bin',dtype='u1')
edge=p['boundary_edge'];boundary=[i for i in range(nx*ny) if not solid[i] and (i%nx==0 if edge=='west' else i%nx==nx-1 if edge=='east' else i<nx if edge=='south' else i>=(ny-1)*nx)]
cost=np.full(nx*ny,np.inf);parent=np.full(nx*ny,-1,dtype=int);heap=[]
for i in boundary:cost[i]=z[i];heapq.heappush(heap,(cost[i],i))
while heap:
    c,i=heapq.heappop(heap)
    if c!=cost[i]:continue
    x,y=i%nx,i//nx
    neighbors=([i-1] if x else [])+([i+1] if x<nx-1 else [])+([i-nx] if y else [])+([i+nx] if y<ny-1 else [])
    for j in neighbors:
        v=max(c,z[j])
        if not solid[j] and v<cost[j]:cost[j]=v;parent[j]=i;heapq.heappush(heap,(v,j))
levels=[(k['timeS'],k['elevationM']+g['elevation_origin_m']) for k in r['levels']]
rows=[]
for s in a['samples']:
    i=s['row']*nx+s['col'];threshold=cost[i]
    if not np.isfinite(threshold):rows.append({'id': s['observation_id'],'status': s['status'],'access': 'no_non_solid_path'});continue
    # Once the minimum barrier is known, find the shortest path under that
    # barrier. A Dijkstra tie can otherwise produce an unnecessarily long path.
    previous={j:None for j in boundary if z[j]<=threshold};queue=deque(previous)
    while queue and i not in previous:
        j=queue.popleft();x,y=j%nx,j//nx
        neighbors=([j-1] if x else [])+([j+1] if x<nx-1 else [])+([j-nx] if y else [])+([j+nx] if y<ny-1 else [])
        for k in neighbors:
            if not solid[k] and z[k]<=threshold and k not in previous:
                previous[k]=j;queue.append(k)
    path=[i]
    while previous[path[-1]] is not None:path.append(previous[path[-1]])
    duration=0
    for (ta,ha),(tb,hb) in itertools.pairwise(levels):
        if ha>threshold and hb>threshold:duration+=tb-ta
        elif max(ha,hb)>threshold:duration+=(tb-ta)*(max(ha,hb)-threshold)/abs(hb-ha)
    rows.append({'id': s['observation_id'],'status': s['status'],'minimum_access_level_navd88_m': float(threshold),
        'gauge_peak_above_access_level_m': max(h for t,h in levels)-threshold,
        'total_gauge_time_above_access_level_s': duration,
        'path_cell_indices': path,'path_length_m': (len(path)-1)*g['dx_m'],
        'highest_path_cell': int(max(path,key=lambda j:z[j]))})
(root/(f'access-threshold-diagnosis-{selected_grid}.json' if selected_grid else 'access-threshold-diagnosis.json')).write_text(json.dumps({'observations': rows,
    'method': 'Minimize maximum fixed bed elevation along four-neighbor non-solid paths from frozen reservoir cells, then find the shortest path under that minimum barrier. Integrate supplied piecewise-linear gauge time above that threshold.',
    'limitations': 'Not a hydraulic travel-time prediction: ignores friction, momentum, flow capacity and volume. Distance follows grid axes. No observations relocated or terrain fitted.'},indent=2))
print(json.dumps([{k:v for k,v in s.items() if k!='path_cell_indices'} for s in rows],indent=2))
