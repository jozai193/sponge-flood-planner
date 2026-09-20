"""Versioned 2/3/4 km domain screen, using source mesh triangles and no target traces."""

if not __debug__:
    raise RuntimeError("Integrity verification is disabled under python -O; rerun without optimization.")
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
import h5py
import httpx
import matplotlib
import numpy as np

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import rasterio
from affine import Affine
from pyproj import Transformer
from rasterio.warp import Resampling, reproject

from scripts.inspect_cora_2019 import URL, BoundedHTTP, plain
from services.reference.boundary_support import boundary_support

PARENT=Path('artifacts/validation/dorian-2019')
ROOT=PARENT/'domain-boundary-screen-v1'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ROOT.mkdir(exist_ok=True)
    mesh=json.loads((PARENT/'cora-local-topology.json').read_text())
    d=json.loads((PARENT/'candidate-screen.json').read_text())['domain']
    source=json.loads((PARENT/'regional-forcing-screen.json').read_text())['current_source']['year_2019_file']
    project=Transformer.from_crs(4326,d['projected_crs'],always_xy=True)
    cx,cy=project.transform(d['center_lon'],d['center_lat'])
    protocol={"kind": 'boundary_input_support_screen_not_accuracy_test',"widths_m": [2000,3000,4000],"grids": [64,128],
        "centre": d,"period_utc": ['2019-09-05T00:00:00+00:00','2019-09-08T00:00:00+00:00'],
        "datum_screen_offsets_m_navd88": [-.137,-.067,-.022,.003],
        "missing_policy": 'All three containing-triangle vertices required at every hour; no nearest node or gap filling.',
        "geometry_policy": 'Fixed centred nested squares; terrain below each reference is a screening proxy only, never an admitted open-water mask.',
        "selection_policy": 'Report every grid and width. No score tuning or target traces. Do not call incomplete forcing ready.',
        "budget_bytes": 64*1024*1024,"source_url": URL,"source_etag": source['etag'],
        "hashes": {str(p):sha(p) for p in [Path(__file__),PARENT/'cora-local-topology.json',PARENT/'candidate-screen.json',Path('services/reference/boundary_support.py')]},
        "production_enabled": False}
    pp=ROOT/'protocol.json';encoded=json.dumps(protocol,indent=2)
    if pp.exists() and pp.read_text()!=encoded:raise ValueError('Frozen protocol changed; create a new screen version')
    pp.write_text(encoded)
    nodes=mesh['local_mesh_nodes'];ids=np.array([n['node_index_zero_based'] for n in nodes]);lookup={int(i):k for k,i in enumerate(ids)}
    x,y=project.transform([n['lon'] for n in nodes],[n['lat'] for n in nodes]);x=np.asarray(x)-cx;y=np.asarray(y)-cy
    triangles=np.array([[lookup[i] for i in t] for t in mesh['local_triangles_zero_based']])
    tri=mtri.Triangulation(x,y,triangles);finder=tri.get_trifinder()
    mappings=[]
    for width in protocol['widths_m']:
        for n in protocol['grids']:
            points=[]
            for edge in ('west','east','south','north'):
                for i in range(n):
                    q=-width/2+(i+.5)*width/n
                    px,py={'west':(-width/2,q),'east':(width/2,q),'south':(q,-width/2),'north':(q,width/2)}[edge]
                    it=int(finder(px,py));p={"edge": edge,"face_index": i,"xy": [px,py],"triangle_index": it}
                    if it<0:raise ValueError('Candidate exceeds retained mesh coverage')
                    verts=triangles[it];weights=np.linalg.solve(np.vstack((x[verts]-px,y[verts]-py,np.ones(3))),[0,0,1])
                    if weights.min() < -1e-8 or abs(weights.sum()-1)>1e-12:raise ValueError('Invalid triangle weights')
                    p.update(node_indices_zero_based=ids[verts].tolist(),weights=weights.tolist())
                    points.append(p)
            mappings.append({"width_m": width,"grid": n,"points": points})
    (ROOT/'mappings.json').write_text(json.dumps(mappings,indent=2))
    requested_ids=np.array(sorted({i for m in mappings for p in m['points'] for i in p['node_indices_zero_based']}))
    lp=ROOT/'regional-levels.json'
    if not lp.exists():
        remote=BoundedHTTP(URL,int(source['content_range'].split('/')[-1]),source['etag'],budget=protocol['budget_bytes'])
        try:
            with h5py.File(remote,'r') as f:
                if plain(f['time'].attrs['units'])!='seconds since 1978-12-01' or plain(f['zeta'].attrs['units'])!='m':raise ValueError('Source encoding changed')
                epoch=dt.datetime(1978,12,1,tzinfo=dt.UTC);t=np.asarray(f['time'][:])
                start,end=[(dt.datetime.fromisoformat(v)-epoch).total_seconds() for v in protocol['period_utc']]
                selected=np.flatnonzero((t>=start)&(t<=end))
                assert len(selected)==73 and np.all(np.diff(t[selected])==3600)
                print(f'Fetching 73 hours for {len(requested_ids)} regional nodes',flush=True)
                values=np.asarray(f['zeta'][selected[0]:selected[-1]+1,requested_ids]);fill=float(plain(f['zeta'].attrs['_FillValue']))
            valid=np.isfinite(values)&(values!=fill)
            levels={"ids": requested_ids.tolist(),"values": [[float(v) if ok else None for v,ok in zip(row,mask)] for row,mask in zip(values,valid)],
                "time_utc": [(epoch+dt.timedelta(seconds=int(t[i]))).isoformat() for i in selected],"source_etag": source['etag']}
            lp.write_text(json.dumps(levels,allow_nan=False))
        finally:
            (ROOT/'network-ranges.json').write_text(json.dumps({"bytes": remote.transferred,"ranges": remote.ranges},indent=2))
    levels=json.loads(lp.read_text());assert levels['ids']==requested_ids.tolist() and levels['source_etag']==source['etag']
    index={i:k for k,i in enumerate(levels['ids'])};values=np.array([[np.nan if v is None else v for v in row] for row in levels['values']])
    # Download one pre-event topobathymetric subset encompassing all fixed candidates.
    tp=ROOT/'terrain-4km-buffer.tif'
    bounds=Transformer.from_crs(d['projected_crs'],4269,always_xy=True).transform_bounds(cx-2100,cy-2100,cx+2100,cy+2100,densify_pts=21)
    dataset=json.loads((PARENT/'terrain-preflight.json').read_text())['source_dataset']
    terrain_url=str(httpx.Request('GET','https://www.ngdc.noaa.gov/thredds/wcs/'+dataset,params={"service": 'WCS',"version": '1.0.0',"request": 'GetCoverage',"coverage": 'Band1',"format": 'GeoTIFF_Float',"crs": 'OGC:CRS84',"bbox": ','.join(map(str,bounds))}).url)
    if not tp.exists():
        print('Fetching pre-event terrain for nested domains',flush=True)
        with httpx.stream('GET',terrain_url,timeout=90,follow_redirects=True) as r:
            r.raise_for_status();chunks=[];total=0
            for chunk in r.iter_bytes():
                total+=len(chunk)
                if total>20_000_000:raise ValueError('Terrain byte budget exceeded')
                chunks.append(chunk)
        tp.write_bytes(b''.join(chunks))
    (ROOT/'terrain-source.json').write_text(json.dumps({"url": terrain_url,"sha256": sha(tp),"horizontal_crs": 'EPSG:4269 per original metadata',"vertical_datum": 'NAVD88',"compilation": '2018-09-11; acquisition dates unresolved'},indent=2))
    results=[];fig,axes=plt.subplots(2,3,figsize=(14,9),layout='constrained')
    with rasterio.open(tp) as src:
        for m in mappings:
            width,n=m['width_m'],m['grid'];z=np.full((n,n),np.nan,dtype='f4')
            reproject(src.read(1),z,src_transform=src.transform,src_crs='EPSG:4269',src_nodata=src.nodata,
                dst_transform=Affine(width/n,0,cx-width/2,0,-width/n,cy+width/2),dst_crs=d['projected_crs'],dst_nodata=np.nan,resampling=Resampling.bilinear)
            z=np.flipud(z)
            if not np.isfinite(z).all() or np.any(z<-1000):raise ValueError('Incomplete terrain')
            np.save(ROOT/f'terrain-{width}-{n}.npy',z)
            for p in m['points']:
                a=values[:,[index[i] for i in p['node_indices_zero_based']]];valid=np.isfinite(a).all(axis=1);v=a@np.array(p['weights'])
                p['levels_m_model_msl']=[float(a) if ok else None for a,ok in zip(v,valid)]
            support=boundary_support(z,m['points'],protocol['datum_screen_offsets_m_navd88'],73)
            complete=sum(all(v is not None for v in p['levels_m_model_msl']) for p in m['points'])
            result={"width_m": width,"grid": n,"cell_m": width/n,"total_faces": 4*n,"complete_faces": complete,"support": support,
                "forcing_ready": False,"reason": 'Physical shoreline/land-crossing review and datum remain unresolved; negative terrain is only a screen.'}
            results.append(result)
            ax=axes[protocol['grids'].index(n),protocol['widths_m'].index(width)]
            ax.imshow(z,origin='lower',extent=(-width/2,width/2,-width/2,width/2),vmin=-6,vmax=6,cmap='terrain')
            ax.triplot(tri,color='black',lw=.2,alpha=.2)
            for p in m['points']:
                i,e=p['face_index'],p['edge'];bed={'west':z[:,0],'east':z[:,-1],'south':z[0,:],'north':z[-1,:]}[e][i]
                if bed < -.067:
                    ax.scatter(*p['xy'],s=9,c='#13874c' if all(v is not None for v in p['levels_m_model_msl']) else '#d72c40')
            half=width*.55;ax.set(xlim=(-half,half),ylim=(-half,half),title=f'{width/1000:g} km / {n} cells ({width/n:.2f} m)\n{support[1]["unsupported_faces"]}/{support[1]["below_reference_faces"]} low faces unsupported',xlabel='East from centre (m)',ylabel='North (m)')
            print(json.dumps({"width_m": width,"grid": n,"complete_faces": complete,"unsupported": [s['unsupported_faces'] for s in support]}),flush=True)
    fig.savefig(ROOT/'domain-screen.png',dpi=140);plt.close(fig)
    report={"status": 'screen_complete_no_boundary_admitted',"cases": results,"usgs_target_traces_read": False,"production_enabled": False,
        "protocol_sha256": sha(pp),"regional_levels_sha256": sha(lp),"terrain_sha256": sha(tp),
        "limitations": ['No observed flood scoring or local solver run.', 'Datum transformation, physical open boundaries, land-crossing flows and creek geometry remain unresolved.',
            'Larger domains change both boundary distance and cell size at fixed grid counts; do not interpret this as a numerical resolution improvement.',
            'All candidate widths, both grids and all four datum screens are retained; no best-error selection.']}
    (ROOT/'results.json').write_text(json.dumps(report,indent=2))


if __name__=='__main__':main()
