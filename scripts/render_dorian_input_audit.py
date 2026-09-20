"""Render metadata findings and native-versus-model creek geometry."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import TwoSlopeNorm
from pyproj import Transformer

ROOT=Path('artifacts/validation/dorian-2019')
a=json.loads((ROOT/'sensor-input-audit.json').read_text())
d=json.loads((ROOT/'candidate-screen.json').read_text())['domain']
transform=Transformer.from_crs(4326,d['projected_crs'],always_xy=True)
cx,cy=transform.transform(d['center_lon'],d['center_lat'])
site=a['sites'][1]['locations'][0];sx,sy=site['projected_xy']
fig,axes=plt.subplots(1,3,figsize=(13,4.8),layout='constrained')
norm=TwoSlopeNorm(vmin=-2,vcenter=0,vmax=3)
with rasterio.open(ROOT/'noaa-topobathy-subset.tif') as src:
    z=src.read(1)
    rr,cc=src.index(site['lon'],site['lat'])
    rows=np.arange(rr-45,rr+46);cols=np.arange(cc-45,cc+46)
    lon,lat=src.transform * np.meshgrid(cols,rows)
    x,y=Transformer.from_crs(4269,d['projected_crs'],always_xy=True).transform(lon,lat)
    im=axes[0].pcolormesh(x-sx,y-sy,z[rr-45:rr+45,cc-45:cc+45],cmap='terrain',norm=norm,shading='flat')
    axes[0].set_title('Native CUDEM pixels\nabout 2.8 x 3.4 m')
for ax,n in zip(axes[1:],(64,128)):
    z=np.load(ROOT/f'topobathy-{n}.npy')
    extent=(cx-1000-sx,cx+1000-sx,cy-1000-sy,cy+1000-sy)
    ax.imshow(z,origin='lower',extent=extent,cmap='terrain',norm=norm,interpolation='nearest')
    ax.set_title(f'{n} x {n} model grid\n{2000/n:.3f} m spacing')
for ax in axes:
    ax.scatter(0,0,c='magenta',edgecolors='black',s=65,zorder=5,label='USGS creek sensor')
    ax.set(xlim=(-95,95),ylim=(-95,95),aspect='equal',xlabel='East from sensor (m)',ylabel='North from sensor (m)')
axes[0].legend(loc='lower left',fontsize=8)
fig.colorbar(im,ax=axes,label='Terrain elevation (m NAVD88)',shrink=.8)
fig.suptitle('Dorian input diagnosis: narrow creek lost in coarse terrain sampling\nGeometry only; no observed flood trace used',fontsize=14)
fig.savefig(ROOT/'creek-grid-diagnosis.png',dpi=160)
plt.close(fig)

rows=''
for s in a['sites']:
    for location in s['locations']:
        rows += '<tr>'+''.join(f'<td>{v}</td>' for v in [s['site'],location['source'],
            f"{location['native_bed_m_navd88']:.3f}",
            f"{location['grids'][0]['bed_m_navd88']:.3f}",
            f"{location['grids'][1]['bed_m_navd88']:.3f}"] )+'</tr>'
ferry=a['sites'][0]
html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Dorian input audit</title><style>body{{font:16px/1.6 system-ui;background:#f5f4ee;color:#183c42;margin:0}}main{{max-width:1120px;margin:auto;padding:28px}}h1{{font-size:2rem}}img{{width:100%}}.notice{{background:#fff0d7;padding:18px;border-left:5px solid #a95c0c}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #d8ded9}}.scroll{{overflow:auto}}a{{color:#006b85}}code{{overflow-wrap:anywhere}}li{{margin:8px 0}}</style><main>
<h1>Dorian: input audit found material conflicts</h1>
<p class="notice"><strong>Latest exposure update:</strong> A later source-search preview revealed a published creek-site high-water mark. Dorian is now partially exposed and cannot serve as a fully untouched event. The sensor time-series arrays remain unread. Earlier archived no-exposure statements describe the earlier audit time. <a href="exposure-notice.json">Exposure record</a>.</p>
<p class="notice"><strong>Historical comparison has not started.</strong> The files have been cached, but observed water-level arrays and their extrema remain unread. Metadata, timestamps, coordinates and pre-storm survey information were examined. No production model change or new accuracy score.</p>
<h2>What is now verified</h2><p>Both NetCDF files declare metres relative to NAVD88 and GMT/UTC epoch timestamps at 30-second spacing. The CSV headers instead label feet and US/Eastern. Use each format's own metadata; copying the CSV label onto NetCDF times would introduce a four-hour error during this event. The source filename says unfiltered but contains both processed storm tide and an unfiltered series.</p>
<h2>Ferry location cannot yet be treated as resolved</h2><p>The catalogue and NetCDF positions differ by <strong>{ferry['catalogue_to_netcdf_distance_m']:.1f} m</strong>. Deployment and recovery forms name another coordinate about <strong>{ferry['field_form_to_catalogue_distance_m']/1000:.1f} km</strong> away, despite the same Hatteras site name and sensor serial. At the catalogue point the 128-grid terrain is -0.695 m; at the NetCDF point it is +1.033 m. Choosing whichever position scores better would invalidate the comparison.</p>
<h2>The creek exists in native terrain but coarse cells miss it</h2><img src="creek-grid-diagnosis.png" alt="Native creek terrain compared with two coarser model grids around the same fixed sensor location">
<p>The creek sensor's catalogue, NetCDF and field-form coordinates agree within 0.32 m. Its pre-storm form reports local ground near -0.148 m NAVD88 and an orifice near +0.442 m. NetCDF ground metadata gives -0.1494 m. The 128-grid bed is +0.506 m, around 0.655 m higher than the metadata survey value and above the instrument opening. The native pixel is -0.751 m at the catalogue coordinate: neither native pixel nor coarse cell should be mistaken for the exact survey point.</p>
<div class="scroll"><table><tr><th>Site</th><th>Coordinate source</th><th>Native bed, m</th><th>64-grid bed, m</th><th>128-grid bed, m</th></tr>{rows}</table></div>
<p>This supports investigating channel preservation during terrain reduction. It does not justify carving a single cell or lowering every coarse cell to its minimum source elevation: those changes alter storage and flow capacity. A point survey cannot establish a whole channel cross-section.</p>
<h2>Comparison admission</h2><ul>
<li>Datum, units and NetCDF time encoding: verified.</li><li>Ferry position: unresolved.</li><li>Creek conveyance in the computational grid: unsupported at the two existing resolutions.</li><li>Sensor dry periods: need an explicit exclusion and reporting rule; no per-sample quality flag variable is present. The creek instrument was not submerged at deployment.</li>
<li>Forcing: the sound-side NOAA gauge alone does not establish ocean-side levels or a wind-driven sound gradient.</li><li>Incoming-wave boundary: stays separate; total gauge levels are not an incoming-wave signal.</li></ul>
<h2>Free regional forcing route located</h2><p>The older RENCI THREDDS catalogue returned HTTP 404. NOAA's current CORA bucket is accessible anonymously and lists the 2019 water-level file. CORA can be investigated as a regional boundary input; it is modeled data, not independent flood truth. Its MSL datum must be reconciled with NAVD88, and its NOAA gauge assimilation means those assimilated gauges cannot independently validate it. No regional level arrays have been used to configure this model.</p><p><a href="regional-forcing-screen.json">Access check and unresolved forcing requirements</a> · <a href="https://registry.opendata.aws/noaa-nos-cora/">NOAA CORA public data</a> · <a href="https://github.com/NOAA-CO-OPS/CORA-Coastal-Ocean-Reanalysis-CORA">Official extraction examples and known issues</a></p>
<p><a href="cora-boundary-preflight.html">New: 256 perimeter points mapped to CORA triangles, with datum screening</a> · <a href="../subgrid-storage-v1/report.html">New: conservative terrain-storage experiment on Dorian and Matthew</a>.</p>
<h2>Next work required for a fair run</h2><ol>{''.join('<li>'+x+'</li>' for x in a['next_actions'])}</ol>
<p><a href="sensor-input-audit.json">Machine-readable audit and hashes</a> · <a href="sensor-review.html">Earlier sensor screen</a> · <a href="../index.html">Validation dashboard</a></p>
<p>Primary records: <a href="https://stn.wim.usgs.gov/STNServices/Files/118238/Item">USGS ferry NetCDF</a>, <a href="https://stn.wim.usgs.gov/STNServices/Files/118294/Item">USGS creek NetCDF</a>, <a href="deployment-117260.pdf">ferry deployment</a>, <a href="recovery-118149.pdf">ferry recovery</a>, <a href="deployment-118277.pdf">creek deployment</a>.</p>
</main></html>'''
(ROOT/'input-audit.html').write_text(html,encoding='utf-8')
print(ROOT/'input-audit.html')
