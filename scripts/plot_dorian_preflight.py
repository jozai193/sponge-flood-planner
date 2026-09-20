"""Visualize only safe metadata, never observed flood elevations."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm
from pyproj import Transformer

root=Path('artifacts/validation/dorian-2019');c=json.loads((root/'candidate-screen.json').read_text());p=json.loads((root/'terrain-preflight.json').read_text())
d=c['domain'];project=Transformer.from_crs(4326,d['projected_crs'],always_xy=True);cx,cy=project.transform(d['center_lon'],d['center_lat'])
fig,ax=plt.subplots(figsize=(8,7),constrained_layout=True);z=np.load(root/'topobathy-128.npy')
im=ax.imshow(z,origin='lower',extent=(0,2000,0,2000),cmap='terrain',norm=TwoSlopeNorm(vmin=-12,vcenter=0,vmax=6))
ax.contour(np.linspace(7.8125,1992.1875,128),np.linspace(7.8125,1992.1875,128),z,levels=[0],colors='black',linewidths=.6)
for mark in c['marks']:
    transform=Transformer.from_crs({2:4269,3:4267,4:4326}[mark['hdatum_id']],d['projected_crs'],always_xy=True)
    x,y=transform.transform(mark['longitude_dd'],mark['latitude_dd']);x=x-cx+1000;y=y-cy+1000
    ax.scatter(x,y,c='#c52992',marker='x',s=75);ax.annotate(str(mark['hwm_id']),(x,y),xytext=(8,8),textcoords='offset points',color='#661246',weight='bold')
x,y=project.transform(c['station']['lon'],c['station']['lat']);x=x-cx+1000;y=y-cy+1000
ax.scatter(x,y,c='#fff',edgecolors='#000',s=80,marker='^');ax.annotate('NOAA 8654467',(x,y),xytext=(8,-18),textcoords='offset points')
ax.set(xlabel='East from domain origin (m)',ylabel='North from domain origin (m)',title='Dorian metadata preflight: Hatteras\n2018 terrain compilation; no observed flood heights exposed')
fig.colorbar(im,ax=ax,label='Terrain elevation (m NAVD88)')
fig.savefig(root/'terrain-preflight.png',dpi=140)
rows=''.join(f'<tr><td>{edge}</td><td>{info["cells_below_navd88_zero"]} / {info["cells"]}</td><td>{info["min_m"]:.2f} to {info["max_m"]:.2f}</td></tr>' for edge,info in p['grids'][-1]['edges'].items())
building_review=''
if (root/'building-preflight.json').exists():
    building_review='<h2>Observation eligibility review</h2><p>Current footprints put the exact coordinate of building-corner mark 36722 inside a building, while both proposed cell centres lie outside it. The model cell being open does not resolve whether the source mark is exterior, interior or transferred. Retain it as setting-unresolved pending independent evidence. Mark 36721 is outside the current footprints and has an outdoor sidewalk description. There is currently only one clearly outdoor mark, so this setup is not ready for the intended multi-site comparison.</p><p><a href="building-preflight.json">Footprint overlap and both grid-cell checks</a></p>'
doc=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Dorian preflight</title><style>body{{font:16px/1.6 system-ui;background:#f5f4ee;color:#183c42}}main{{max-width:950px;margin:auto;padding:20px}}img{{max-width:100%}}td,th{{padding:10px;text-align:left}}.notice{{background:#fff0d7;padding:18px}}a{{color:#006b85}}</style><main>
<h1>Dorian 2019: next-event preflight</h1><p class="notice">Provisional only. No observed HWM elevations inspected; no protocol frozen or simulation started. Boundary geometry and observation eligibility are unresolved.</p>
<img src="terrain-preflight.png" alt="Pre-event compiled terrain with two survey locations, local gauge and terrain at zero NAVD88">
<p>The fixed 2 km domain comes from the midpoint of two metadata-selected marks. Both records use NAVD88 and fair quality, and both are flagged non-stillwater. Mark 36721 is beside the ferry-terminal sidewalk; 36722 is at a building corner, requiring explicit setting and building-overlap review. The records do not provide independent dry areas or arrival times.</p>
<p>The source declares NAD83 and NAVD88 and a 2018-09-11 compilation date. That is before Dorian, but does not establish the dates of its individual surveys. The black contour is zero NAVD88 terrain, not a verified shoreline.</p>
<table><thead><tr><th>128-grid edge</th><th>Cells below zero NAVD88</th><th>Terrain range (m)</th></tr></thead><tbody>{rows}</tbody></table>
<p>Low terrain intersects every edge. Verify which edges connect to the sound and ocean and whether different boundary forcing is necessary before declaring a one-edge coastal model suitable. Do not move the domain or raise a gauge based on hidden outcomes.</p>
{building_review}<p><a href="candidate-screen.json">Metadata screen</a> · <a href="terrain-preflight.json">Terrain provenance</a> · <a href="forcing-availability.json">Gauge availability</a> · <a href="../positivity-report.html">Numerical candidate</a></p></main></html>'''
(root/'preflight.html').write_text(doc,encoding='utf-8');print(root/'preflight.html')
