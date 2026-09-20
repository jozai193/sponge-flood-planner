"""Show the fixed-cell-size boundary diagnostic and its exact core invariants."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from pyproj import Transformer

root=Path('artifacts/validation/matthew-2016-domain4km');p=json.loads((root/'protocol.json').read_text())
run=p['bundles'][0];folder=Path('data/local/bundles')/run['bundle_id'];g=json.loads((folder/'manifest.json').read_text())['grid']
z=np.fromfile(folder/'z.bin',dtype='<f4').reshape(128,128)+g['elevation_origin_m'];solid=np.fromfile(folder/'solid.bin',dtype='u1').reshape(128,128)
fig,ax=plt.subplots(figsize=(8,7),constrained_layout=True)
cmap=plt.get_cmap('terrain').copy();cmap.set_bad('#4b5055')
im=ax.imshow(np.ma.masked_where(solid==1,z),origin='lower',extent=(0,4000,0,4000),cmap=cmap,vmin=-10,vmax=5)
ax.add_patch(Rectangle((1000,1000),2000,2000,fill=False,edgecolor='#d3278d',lw=2,label='Original 2 km core: exact same bed and mask'))
ax.axvline(4000,color='#086c93',lw=6,label='East reservoir forced by gauge')
for mark in json.loads((root/'hwms.json').read_text()):
    transform=Transformer.from_crs({2:4269,3:4267,4:4326}[mark['hdatum_id']],g['crs'],always_xy=True)
    x,y=transform.transform(mark['longitude_dd'],mark['latitude_dd']);x-=g['origin_x_m'];y-=g['origin_y_m']
    ax.scatter(x,y,c='#be126c',marker='x',s=45)
transform=Transformer.from_crs(4326,g['crs'],always_xy=True);x,y=transform.transform(-79.9236,32.7808)
ax.scatter(x-g['origin_x_m'],y-g['origin_y_m'],c='white',edgecolors='black',marker='^',s=65,label='NOAA gauge location')
ax.legend(loc='upper left',fontsize=8);ax.set(xlabel='East from enlarged domain origin (m)',ylabel='North from enlarged domain origin (m)',
    title='Matthew domain diagnostic: 4 km, 128 × 128 cells\nSame 31.25 m spacing as original 2 km, 64 × 64 model')
fig.colorbar(im,ax=ax,label='Grid terrain (m NAVD88; clipped −10 to 5)')
fig.savefig(root/'domain-inputs.png',dpi=140)
diagnostic=''
if (root/'connectivity-diagnosis.json').exists():
    c=json.loads((root/'connectivity-diagnosis.json').read_text())
    mark=next(m for m in c['observations'] if m['id']==16664)
    diagnostic=f'<h2>Input diagnosis before the result</h2><p>Initial water within the original core matches exactly: {c["core_initialization"]["added_volume_m3"]:.1f} m³ added and no newly connected or lost wet cells. The minimum static access barrier to mark 16664 changes from {mark["original_access_level_navd88_m"]:.4f} to {mark["expanded_access_level_navd88_m"]:.4f} m NAVD88. Other original marks retain their barriers. This points to an alternative route but does not predict flow capacity or arrival time.</p><p>The north and south edges still cut through initially wet terrain. Moving the walls farther away tests sensitivity to domain extent; it does not remove the closed-boundary approximation.</p><p><a href="connectivity-diagnosis.json">Initial-water and barrier checks</a> · <a href="checkpoint-audit-128.json">Most recent partial replay audit</a></p>'
doc='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Matthew domain-size experiment</title><style>body{font:16px/1.6 system-ui;background:#f5f4ee;color:#183c42}main{max-width:1000px;margin:auto;padding:24px}.notice{background:#fff0d7;padding:18px}img{max-width:100%}progress{width:100%}a{color:#006b85}</style><main>
<h1>Does the original domain restrict flood access?</h1><p class="notice">Exposed development diagnostic, not a fresh holdout. Production solver and defaults remain unchanged. Only the domain expands; grid spacing and the entire original core stay fixed.</p>
<p id="status">Checking local run…</p><progress id="bar" max="24" value="0"></progress><p id="detail"></p>
<img src="domain-inputs.png" alt="Four-kilometre domain showing the exact two-kilometre core, gauge position, building mask and east reservoir edge">
<h2>Controlled inputs</h2><ul><li>4 km at 128 × 128 cells versus 2 km at 64 × 64 cells: both 31.25 m spacing.</li><li>Original bed and building mask preserved bitwise in the central core; same vertical origin and forcing series.</li><li>Original solver, roughness, dry-cell threshold, rain, infiltration and storage settings retained.</li><li>All five original marks retained. Coordinate-only inventory found no additional marks inside the expanded area.</li></ul>
<h2>Why preserve the core explicitly?</h2><p>The underlying native DEM overlap is bitwise identical, but a larger reprojection warp produced up to 0.04835 m differences in shared terrain. The old core raster is retained exactly so those resampling shifts cannot masquerade as a boundary effect. The join with newly resampled outer terrain is documented as a limitation.</p>
<h2>What changes together?</h2><p>The artificial edges move farther away, new exterior terrain and buildings enter the model, and the initial connected water may change. This tests the larger domain as a whole; it cannot isolate each of those effects. One reservoir gauge still does not establish correct harbour-wide water levels.</p>
<h2>Frozen evaluation</h2><p>Require strict replay and mass integrity, no lost wet or supported marks, no additional dry misses, and no more than 0.01 m worsening in common-point or equal-site RMSE. A pass needs another event before adoption. Existing Matthew results informed this test.</p>
<!--INPUT_DIAGNOSIS--><p><a href="core-integrity.json">Exact input checks</a> · <a href="evaluation-plan.json">Frozen criteria</a> · <a href="domain-comparison.json">Comparison when complete</a> · <a href="../matthew-2016/error-diagnosis.html">Earlier diagnosis</a> · <a href="../index.html">All experiments</a></p></main>
<script>let last=null,changed=Date.now();async function read(name){const r=await fetch(name+'?v='+Date.now(),{cache:'no-store'});if(!r.ok||r.headers.get('content-type')?.includes('text/html'))return null;return r.json();}async function refresh(){try{const [job,p,result]=await Promise.all([read('job-status.json'),read('progress.json'),read('domain-comparison.json')]);const status=document.getElementById('status'),detail=document.getElementById('detail'),bar=document.getElementById('bar');status.textContent=job?'Local job: '+job.stage:'Not running';if(p){if(p.simulatedHours!==last){last=p.simulatedHours;changed=Date.now();}bar.value=p.simulatedHours;detail.textContent=p.simulatedHours.toFixed(2)+' / 24 simulated hours'+(Date.now()-changed>60000?' · progress unchanged for over one minute':'');}if(result){bar.value=24;status.textContent=result.regression_gate_passed?'Passes this development check only':'Fails this development check';detail.textContent='Common wet-point RMSE: '+result.baseline_common_rmse_m+' → '+result.candidate_common_rmse_m+' m. Dry misses: '+result.dry_before+' → '+result.dry_after+'.';}if(job?.error)status.textContent+=' · '+job.error;}catch{document.getElementById('status').textContent='Evidence unavailable; no success inferred';}}refresh();setInterval(refresh,10000);</script></html>'''
(root/'experiment-report.html').write_text(doc.replace('<!--INPUT_DIAGNOSIS-->',diagnostic),encoding='utf-8');print(root/'experiment-report.html')
