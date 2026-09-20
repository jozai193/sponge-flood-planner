"""Inspect unchanged Matthew runs; no parameter fitting or observation relocation."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

root=Path('artifacts/validation/matthew-2016')
protocol=json.loads((root/'protocol.json').read_text())
assessment=json.loads((root/'accuracy.json').read_text())
fig,axes=plt.subplots(2,2,figsize=(13,9),constrained_layout=True)
colors={64:'#067c91',128:'#b94b27'}; records=[]; sources=[]
for column,run in enumerate(assessment['runs']):
    n=run['grid_cells']; path=root/f'simulation-{n}.json';sources.append(path)
    sim=json.loads(path.read_text());g=sim['grid'];nx,ny=g['nx'],g['ny']
    folder=Path('data/local/bundles')/run['bundle_id']
    bed=np.fromfile(folder/'z.bin',dtype='<f4').reshape(ny,nx)+g['elevation_origin_m']
    solid=np.fromfile(folder/'solid.bin',dtype='u1').reshape(ny,nx)
    access_path=root/f'access-threshold-diagnosis-{n}.json'; sources.append(access_path)
    access={s['id']:s for s in json.loads(access_path.read_text())['observations']}
    samples={s['observation_id']:s for s in run['samples']}
    shrub=samples[16664];route=access[16664];indices=np.array(route['path_cell_indices'])
    ax=axes[0,column];masked=np.ma.masked_where(solid==1,bed)
    cmap=plt.get_cmap('terrain').copy();cmap.set_bad('#4b5055')
    image=ax.imshow(masked,origin='lower',extent=(0,2000,0,2000),cmap=cmap,vmin=0,vmax=2.5,interpolation='nearest')
    px=(indices%nx+.5)*g['dx_m'];py=(indices//nx+.5)*g['dy_m']
    ax.plot(px,py,color='#a81088',lw=1.6,label='Minimum-barrier grid path')
    ax.scatter(px[0],py[0],c='#a81088',marker='x',s=75,label='Cell containing mark 16664')
    ax.set(xlim=(1000,2000),ylim=(0,650),xlabel='East from domain origin (m)',ylabel='North from domain origin (m)',
        title=f'{n}-grid: barrier {route["minimum_access_level_navd88_m"]:.3f} m; above barrier {route["total_gauge_time_above_access_level_s"]/3600:.2f} h')
    handles,labels=ax.get_legend_handles_labels()
    ax.legend(handles+[Patch(color='#4b5055')],labels+['Current building cells'],fontsize=8,loc='upper right')
    for k,identifier in enumerate((16664,16663)):
        sample=samples[identifier];cell=sample['row']*nx+sample['col']
        times=np.array([f['time_s']/3600 for f in sim['frames']])
        depths=np.array([f['depth'][cell] for f in sim['frames']])
        water=np.where(depths>.01,sample['ground_elevation_m']+depths,np.nan)
        axes[1,k].plot(times,water,c=colors[n],lw=2,label=f'{n}-grid wet-cell water level')
    records.append({'grid_cells': n,'mark_16664': {'error_m': shrub['error_m'],
        'ground_navd88_m': shrub['ground_elevation_m'],'peak_water_navd88_m': shrub['predicted_elevation_m'],
        'minimum_access_level_navd88_m': route['minimum_access_level_navd88_m'],
        'gauge_above_barrier_hours': route['total_gauge_time_above_access_level_s']/3600,
        'path_length_m': route['path_length_m']}})
fig.colorbar(image,ax=list(axes[0]),shrink=.75,label='Source-derived grid terrain (m NAVD88; scale clipped 0–2.5)')
g=sim['grid'];forcing=protocol['bundles'][-1]['levels']
for k,identifier in enumerate((16664,16663)):
    ax=axes[1,k];sample=samples[identifier]
    ax.plot([v['timeS']/3600 for v in forcing],[v['elevationM']+g['elevation_origin_m'] for v in forcing],c='#48525c',ls='--',label='Supplied NOAA gauge')
    ax.axhline(sample['observed_elevation_m'],c='#722d89',ls=':',label='Observed HWM (maximum only)')
    ax.set(xlim=(0,24),ylim=(1.35,2.4),xlabel='Hours from 2016-10-08 00:00 UTC',ylabel='Water elevation (m NAVD88)',title=f'Mark {identifier}: poor-quality source record')
    ax.legend(fontsize=8,loc='upper right');ax.grid(alpha=.2)
fig.suptitle('Matthew: isolate the error before choosing the next model change\nPaths show terrain access, not measured travel times. Blank traces are dry cells; source terrain is not independent ground truth.',fontsize=12)
fig.savefig(root/'error-diagnosis.png',dpi=145)
sources += [root/'protocol.json',root/'accuracy.json',Path(__file__)]
result={'records': records,'source_sha256': {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
    'interpretation': 'The finer grid raises the minimum access barrier and reduces time above it at mark 16664; simulated peak water is lower. This is a mechanism to test, not proof that terrain or hydraulic connectivity is the sole cause.',
    'acceptance': 'The frozen held-out gate remains failed. No gauge adjustment, observation relocation or solver change applied.'}
(root/'error-diagnosis.json').write_text(json.dumps(result,indent=2))
rows=''.join(f'<tr><td>{r["grid_cells"]}</td><td>{r["mark_16664"]["error_m"]:+.4f}</td><td>{r["mark_16664"]["minimum_access_level_navd88_m"]:.4f}</td><td>{r["mark_16664"]["gauge_above_barrier_hours"]:.2f}</td></tr>' for r in records)
doc=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Matthew error diagnosis</title>
<style>body{{font:16px/1.6 system-ui;background:#f5f4ee;color:#183c42;margin:0}}main{{max-width:1150px;margin:auto;padding:28px}}.notice{{background:#fff0d7;padding:18px;border-left:4px solid #b97828}}img{{width:100%}}table{{border-collapse:collapse}}td,th{{padding:10px;border-bottom:1px solid #ccd5d0;text-align:left}}a{{color:#006b85}}</style>
<main><h1>Matthew: what caused the comparison to worsen?</h1>
<p class="notice">The frozen 128-grid candidate failed. These are diagnostics of completed results, not fitted changes or a new accuracy pass. Matthew is now exposed development evidence; another untouched event is needed to test the next candidate.</p>
<p>Common wet-point RMSE rose from 0.2906 to 0.3121 m. One observed flooded point stayed dry, and the good-quality stairs point became a building-cell exclusion. The current default remains unchanged.</p>
<img src="error-diagnosis.png" alt="Two terrain grids with minimum-barrier routes and two water-level histories compared against the gauge and observed maxima">
<h2>16664: access and terrain representation</h2><p>The shrub-wall point changes from +0.0035 m error to −0.1967 m. The minimum terrain barrier rises by 0.1162 m, and time above that barrier falls from 4.36 to 3.53 hours. The path lengths are similar, about 1.05 km. This supports testing terrain and passage representation, rather than assuming path length alone explains the difference. Both paths approach the southern domain boundary, so domain truncation also deserves a controlled check.</p>
<table><thead><tr><th>Grid</th><th>Water-level error (m)</th><th>Minimum barrier (m NAVD88)</th><th>Gauge above barrier (hours)</th></tr></thead><tbody>{rows}</tbody></table>
<p>The path is a static four-neighbour terrain diagnostic. It is not a measured flow route, travel time or causal hydraulic experiment. The terrain source is shared with the model and is not independent ground truth.</p>
<h2>16663 and 16667: forcing or observation mismatch remains</h2><p>At 16663, the gauge peak is 1.874 m NAVD88, while the poor-quality observed maximum is 2.286 m. The fine-grid model reaches 1.891 m. At dry point 16667, fine-grid ground is 2.156 m, above the supplied gauge peak, and the observed maximum is 2.195 m. Possible explanations include local water-level variation, wave effects, survey uncertainty and changed terrain. These records alone do not identify one cause. Raising the gauge to match them would be calibration and could worsen other marks.</p>
<h2>16723: geometry coverage</h2><p>The surveyed stairs coordinate lies within a current footprint. Coarse and fine cell centres fall on different sides of it, so the fine result is unscorable. Retain the observation and the failed coverage gate. Do not shift the mark or remove the building simply to obtain a score.</p>
<h2>Next tests</h2><ol><li>Verify the isolated numerical positivity candidate against reference cases, replay integrity and retained historical events.</li><li>Test a larger domain at the same cell spacing, with a matched control, to separate boundary effects from resolution changes.</li><li>Obtain independent terrain, structure and water-level evidence before changing forcing or local barriers.</li><li>Freeze the resulting candidate and compare against an untouched event. Report all dry and unsupported marks.</li></ol>
<p><a href="holdout-report.html">Frozen comparison and every observation</a> · <a href="error-diagnosis.json">Diagnostic values and checksums</a> · <a href="../index.html">All events</a></p></main></html>'''
(root/'error-diagnosis.html').write_text(doc,encoding='utf-8')
print(json.dumps(records,indent=2))
