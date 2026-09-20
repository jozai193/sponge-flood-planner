"""Geometry-only comparison on two event domains; no flood observations loaded."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy as np
import rasterio
from affine import Affine
from pyproj import Transformer
from rasterio.warp import Resampling, reproject

from services.reference.subgrid_storage import SubgridStorage

ROOT=Path('artifacts/validation/subgrid-storage-v1')
STAGES=(-1.,-.5,0.,.25,.5,1.,2.,3.)


def main():
    ROOT.mkdir(exist_ok=True)
    sources=['services/reference/subgrid_storage.py','scripts/check_subgrid_storage_terrain.py']
    for event in ('dorian-2019','matthew-2016'):
        sources.append(f'artifacts/validation/{event}/noaa-topobathy-subset.tif')
    protocol={'scope': 'Potential terrain storage, not flood inundation or hydraulic conveyance',
        'stages_m_navd88': STAGES,'coarse_grids': [64,128],'fine_grids': [512,1024],
        'fine_resampling': 'nearest native source pixel; fine grid is an integration quadrature, not new terrain information',
        'mask': 'Terrain only; no building mask or connected-water assumption',
        'cell_model': 'Equal stage among subpixels in a coarse cell; exact sum of positive fine-pixel depths',
        'gates': {'relative_volume_difference_max': 1e-12,'inverse_stage_tolerance_m': 1e-10},
        'source_sha256': {f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in sources},
        'scientific_context': 'https://gmd.copernicus.org/articles/18/843/2025/',
        'production_enabled': False,'observed_flood_data_used': False}
    pp=ROOT/'protocol.json';encoded=json.dumps(protocol,indent=2)
    if pp.exists() and pp.read_text()!=encoded:raise ValueError('Do not replace frozen experiment')
    pp.write_text(encoded)
    results=[]
    for event in ('dorian-2019','matthew-2016'):
        folder=Path('artifacts/validation')/event
        if event=='dorian-2019':
            d=json.loads((folder/'candidate-screen.json').read_text())['domain']
            center=(d['center_lon'],d['center_lat']);crs=d['projected_crs']
            originals={n:np.load(folder/f'topobathy-{n}.npy').astype(float) for n in (64,128)}
        else:
            p=json.loads((folder/'protocol.json').read_text());center=p['center'];crs=p['horizontal_crs']
            originals={}
            for run in p['bundles']:
                n=run['grid_cells'];b=Path('data/local/bundles')/run['bundle_id']
                g=json.loads((b/'manifest.json').read_text())['grid']
                originals[n]=np.fromfile(b/'z.bin',dtype='<f4').reshape(n,n).astype(float)+g['elevation_origin_m']
        cx,cy=Transformer.from_crs(4326,crs,always_xy=True).transform(*center)
        for nfine in (512,1024):
            dx=2000/nfine;fine=np.full((nfine,nfine),np.nan,dtype=float)
            with rasterio.open(folder/'noaa-topobathy-subset.tif') as src:
                reproject(src.read(1),fine,src_transform=src.transform,src_crs='EPSG:4269',
                    src_nodata=src.nodata,dst_transform=Affine(dx,0,cx-1000,0,-dx,cy+1000),
                    dst_crs=crs,dst_nodata=np.nan,resampling=Resampling.nearest)
            fine=np.flipud(fine)
            if not np.isfinite(fine).all():raise ValueError('Incomplete native source coverage')
            if nfine==1024:np.save(ROOT/f'{event}-integration-bed.npy',fine)
            for n in (64,128):
                storage=SubgridStorage(fine,nfine//n,dx,dx)
                rows=[]
                for stage in STAGES:
                    volumes=storage.volume(stage);wet=storage.wet_area(stage)
                    direct=float(np.maximum(stage-fine,0).sum()*dx*dx)
                    total=float(volumes.sum());coarse=float(np.maximum(stage-originals[n],0).sum()*(2000/n)**2)
                    residual=abs(total-direct)/max(1,direct)
                    recovered=storage.stage(volumes);expected=np.maximum(stage,storage.beds[...,0])
                    inverse=float(np.max(np.abs(recovered-expected)))
                    rows.append({'stage_m_navd88': stage,'reference_storage_m3': direct,
                        'subgrid_storage_m3': total,'original_coarse_storage_m3': coarse,
                        'original_coarse_bias_m3': coarse-direct,'relative_conservation_error': residual,
                        'max_inverse_stage_error_m': inverse,'subgrid_potential_wet_area_m2': float(wet.sum()),
                        'original_coarse_potential_wet_area_m2': float((stage>originals[n]).sum()*(2000/n)**2)})
                item={'event': event,'coarse_grid': n,'integration_grid': nfine,'stages': rows}
                if event=='dorian-2019':
                    x,y=Transformer.from_crs(4269,crs,always_xy=True).transform(-75.688823,35.218333)
                    rr=int((y-cy+1000)//(2000/n));cc=int((x-cx+1000)//(2000/n))
                    item['creek_sensor_cell']={'row': rr,'col': cc,'coarse_bed_m_navd88': float(originals[n][rr,cc]),
                        'at_zero_navd88': {'potential_storage_m3': float(storage.volume(0)[rr,cc]),
                            'potential_wet_area_m2': float(storage.wet_area(0)[rr,cc]),
                            'cell_area_m2': (2000/n)**2}}
                results.append(item)
        print(json.dumps({'event': event,'completed': True}),flush=True)
    passed=all(s['relative_conservation_error']<=1e-12 and s['max_inverse_stage_error_m']<=1e-10 for r in results for s in r['stages'])
    summary={'status': 'completed','geometry_gates_passed': passed,'runs': results,
        'production_enabled': False,'general_flood_accuracy_validated': False,
        'limitation': 'Conservation against the same fine terrain is an implementation property, not independent accuracy. This does not implement face conveyance, wet/dry flow, momentum, connectivity or GPU support.'}
    (ROOT/'results.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps({'geometry_gates_passed': passed,'comparisons': len(results)*len(STAGES)}))


if __name__=='__main__':main()
