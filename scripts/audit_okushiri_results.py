"""Check source integrity, time support, gauge wetness and segment accounting."""

if not __debug__:
    raise RuntimeError("Integrity verification is disabled under python -O; rerun without optimization.")
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.interpolate import RegularGridInterpolator

root=Path('artifacts/validation/okushiri-lab')
protocol=json.loads((root/'protocol.json').read_text())
result=json.loads((root/'results.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert result['protocol_sha256']==sha(root/'protocol.json')
for path,digest in protocol['source_sha256'].items():assert sha(Path(path))==digest,path
for source in protocol['input_sources']:assert sha(root/source['file'])==source['sha256'],source['file']
with rasterio.open(root/'Benchmark_2_Bathymetry.asc') as ds:
    t=ds.transform;x=t.c+(np.arange(ds.width)+.5)*t.a;y=(t.f+(np.arange(ds.height)+.5)*t.e)[::-1]
    native=RegularGridInterpolator((y,x),ds.read(1)[::-1],bounds_error=True)
checks=[]
for run in result['runs']:
    nx,ny=run['grid'];xs=(np.arange(nx)+.5)*5.448/nx;ys=(np.arange(ny)+.5)*3.402/ny
    yy,xx=np.meshgrid(ys,xs,indexing='ij');z=native(np.stack([yy,xx],axis=-1))
    gauge_bed=RegularGridInterpolator((ys,xs),z)([(gy,gx) for gx,gy in protocol['gauge_xy_m']])
    stages=np.asarray(run['stage_m']);times=np.asarray(run['time_s'])
    assert stages.shape==(451,3) and np.isfinite(stages).all()
    np.testing.assert_allclose(times,np.arange(451)*.05,rtol=0,atol=1e-12)
    assert run['min_final_depth_m']>=0
    dry=(stages-gauge_bed)<=1e-5
    if run['engine']=='segments_candidate':
        incoming=sum(v[0] for v in run['segment_volumes_m3'].values())
        outgoing=sum(v[1] for v in run['segment_volumes_m3'].values())
        np.testing.assert_allclose([incoming,outgoing],[run['ledger']['inflow_m3'],run['ledger']['outflow_m3']],rtol=1e-10,atol=1e-12)
        assert run['max_final_state_difference']==0 and run['max_saved_gauge_difference_m']==0
    checks.append({"grid": run['grid'],"engine": run['engine'],"gauge_bed_m": gauge_bed.tolist(),
        "dry_or_unresolved_interpolated_gauge_samples": dry.sum(axis=0).tolist(),
        "min_interpolated_gauge_depth_m": (stages-gauge_bed).min(axis=0).tolist(),
        "mass_passed": bool(run['ledger']['relative_residual']<1e-8)})
audit={"status": 'completed',"source_checks_passed": True,"run_checks": checks,
    "all_mass_checks_passed": all(r['mass_passed'] for r in checks),
    "all_gauge_samples_wet": all(sum(r['dry_or_unresolved_interpolated_gauge_samples'])==0 for r in checks),
    "production_enabled": False,"general_flood_accuracy_validated": False}
(root/'integrity-audit.json').write_text(json.dumps(audit,indent=2))
print(json.dumps(audit))
