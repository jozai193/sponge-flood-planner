"""Present geometric storage tests without suggesting flood validation."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
sys.path.insert(0,str(Path.cwd()))
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from services.reference.subgrid_storage import SubgridStorage

ROOT=Path('artifacts/validation/subgrid-storage-v1')
r=json.loads((ROOT/'results.json').read_text());runs=r['runs']
fig,axes=plt.subplots(1,3,figsize=(13,4.6),layout='constrained')
for ax,event,title in zip(axes[:2],('dorian-2019','matthew-2016'),('Hatteras terrain','Charleston terrain')):
    for grid,color in ((64,'#ba5941'),(128,'#57799a')):
        run=next(x for x in runs if x['event']==event and x['coarse_grid']==grid and x['integration_grid']==1024)
        stage=[x['stage_m_navd88'] for x in run['stages']]
        bias=[x['original_coarse_bias_m3']/1000 for x in run['stages']]
        ax.plot(stage,bias,'o-',label=f'Current {grid} grid',color=color)
    ax.axhline(0,color='#147363',linestyle='--',label='Subgrid storage')
    ax.set(title=title,xlabel='Assumed level (m NAVD88)',ylabel='Storage minus fine-terrain sum (1,000 m³)')
    ax.legend(fontsize=8);ax.grid(alpha=.2)
z=np.load(ROOT/'dorian-2019-integration-bed.npy');s=SubgridStorage(z,8,2000/1024,2000/1024)
run=next(x for x in runs if x['event']=='dorian-2019' and x['coarse_grid']==128 and x['integration_grid']==1024)
cell=run['creek_sensor_cell'];row,col=cell['row'],cell['col']
levels=np.array([x['stage_m_navd88'] for x in run['stages']])
axes[2].plot(levels,[s.volume(x)[row,col] for x in levels],'-o',color='#147363',label='Fine-pixel storage')
axes[2].plot(levels,np.maximum(levels-cell['coarse_bed_m_navd88'],0)*cell['at_zero_navd88']['cell_area_m2'],'-o',color='#ba5941',label='Current cell')
axes[2].set(title='Dorian creek sensor cell',xlabel='Assumed level (m NAVD88)',ylabel='Potential storage (m³)')
axes[2].legend(fontsize=8);axes[2].grid(alpha=.2)
fig.suptitle('Preserving terrain storage within coarse cells\nGeometry checks only; no flow, connectivity or observed-flood score',fontsize=14)
fig.savefig(ROOT/'storage-comparison.png',dpi=160);plt.close(fig)
table=''
for event in ('dorian-2019','matthew-2016'):
    for grid in (64,128):
        b=next(x for x in runs if x['event']==event and x['coarse_grid']==grid and x['integration_grid']==1024)
        fine=next(x for x in b['stages'] if x['stage_m_navd88']==0)
        low=next(x for x in runs if x['event']==event and x['coarse_grid']==grid and x['integration_grid']==512)
        low=next(x for x in low['stages'] if x['stage_m_navd88']==0)
        change=100*(fine['reference_storage_m3']/low['reference_storage_m3']-1)
        table+=f"<tr><td>{event}</td><td>{grid}</td><td>{fine['original_coarse_bias_m3']:,.0f}</td><td>{change:+.4f}%</td></tr>"
html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Terrain storage experiment</title><style>body{{font:16px/1.6 system-ui;background:#f5f4ee;color:#183c42}}main{{max-width:1180px;margin:auto;padding:24px}}img{{width:100%}}.notice{{padding:18px;background:#fff0d7}}td,th{{padding:12px;text-align:left}}.scroll{{overflow:auto}}a{{color:#006b85}}</style><main>
<h1>Terrain storage retained without flattening the creek</h1><p class="notice"><strong>Experimental preprocessing only.</strong> No production solver change, historical flood run or accuracy gain is claimed. A storage curve is only one component of a hydraulic model.</p>
<p>Replacing a coarse cell with one terrain height can erase its low creek pixels. This candidate keeps the distribution of fine elevations and computes potential water volume and wet area at a given level. It also recovers level from volume. The surrounding higher ground stays higher; we do not lower an entire cell to its minimum pixel.</p>
<img src="storage-comparison.png" alt="Potential storage differences on two terrain domains, and the creek cell's storage curve">
<h2>What passed</h2><p>64 geometry checks across two domains, two coarse grids, two integration grids and eight declared levels. Subgrid totals reproduce the sums over the same fine terrain within the declared tolerance, and volume-to-level inversion passes. This is an implementation property, not independent validation. Nine unit tests cover narrow channels, repeated elevations, wetting, volume inversion, partition independence, rotation, datum shifts and invalid inputs.</p>
<p>At zero NAVD88, the 128-grid creek sensor cell retains <strong>{cell['at_zero_navd88']['potential_storage_m3']:.1f} m³</strong> of potential storage and <strong>{cell['at_zero_navd88']['potential_wet_area_m2']:.1f} m²</strong> of subpixel wet area. Its current single terrain height gives zero. Neither quantity proves that floodwater reaches that cell.</p>
<h2>Terrain integration sensitivity</h2><p>The 512 and 1024 fine grids sample existing native pixels with nearest-neighbour resampling. They do not add survey detail. The table gives a sensitivity check at zero NAVD88; no integration resolution is declared a validated optimum.</p><div class="scroll"><table><tr><th>Domain</th><th>Coarse grid</th><th>Current storage bias (m³)</th><th>Fine storage change, 512 to 1024</th></tr>{table}</table></div>
<h2>Required before hydraulic adoption</h2><p>Flow across cell faces must preserve channel width and account for disconnected depressions, internal barriers, pressure forces, friction and wet/dry transitions. These storage curves alone must not be plugged into the existing shallow-water equations without deriving and testing those changes. The methodology is informed by <a href="https://gmd.copernicus.org/articles/18/843/2025/">published SFINCS subgrid research</a>; no SFINCS solver code was copied.</p>
<p>Dorian is now partially exposed after a public search preview revealed a creek-site high-water mark. Sensor traces remain unread. Matthew is existing development evidence. Any improvement informed by these domains still requires another untouched flood comparison.</p>
<p><a href="results.json">All geometry results</a> · <a href="protocol.json">Frozen scope and source hashes</a> · <a href="../dorian-2019/input-audit.html">Dorian input audit</a> · <a href="../index.html">Validation dashboard</a></p></main></html>'''
(ROOT/'report.html').write_text(html,encoding='utf-8')
print(ROOT/'report.html')
