"""Map domain perimeter points to actual CORA triangles, without level arrays."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.tri as mtri
import numpy as np
from pyproj import Transformer

ROOT=Path('artifacts/validation/dorian-2019')
r=json.loads((ROOT/'cora-local-topology.json').read_text())
d=json.loads((ROOT/'candidate-screen.json').read_text())['domain']
project=Transformer.from_crs(4326,d['projected_crs'],always_xy=True)
cx,cy=project.transform(d['center_lon'],d['center_lat'])
nodes=r['local_mesh_nodes'];ids=[n['node_index_zero_based'] for n in nodes];lookup={v:i for i,v in enumerate(ids)}
x,y=project.transform([n['lon'] for n in nodes],[n['lat'] for n in nodes]);x=np.asarray(x)-cx;y=np.asarray(y)-cy
triangles=np.asarray([[lookup[i] for i in t] for t in r['local_triangles_zero_based']])
tri=mtri.Triangulation(x,y,triangles);finder=tri.get_trifinder();points=[]
for edge in ('west','east','south','north'):
    for i in range(64):
        q=-1000+(i+.5)*2000/64
        px,py={'west':(-1000,q),'east':(1000,q),'south':(q,-1000),'north':(q,1000)}[edge]
        t=int(finder(px,py));item={'edge': edge,'face_index': i,'x_from_center_m': px,'y_from_center_m': py,'triangle_index': t}
        if t>=0:
            verts=triangles[t]
            matrix=np.vstack((x[verts]-px,y[verts]-py,np.ones(3)))
            w=np.linalg.solve(matrix,np.array([0.,0.,1.]))
            if min(w)<-1e-8 or abs(w.sum()-1)>1e-12:raise ValueError('Invalid interpolation weights')
            item.update(node_indices_zero_based=[ids[v] for v in verts],weights=w.tolist(),
                all_vertices_below_model_zero=all(nodes[v]['depth_m_below_model_reference']>0 for v in verts))
        points.append(item)
datums=json.loads((ROOT/'noaa-hatteras-datums.json').read_text())['metadata']
table={v['name']:v['value'] for v in datums['datums']};gauge_offset=table['MSL']-table['NAVD88']
v=json.loads((ROOT/'vdatum-gauge-screen.json').read_text());vd=v.get('response',{})
report={'status': 'geometric_mapping_complete_forcing_not_admitted','source_url': r['source_url'],'source_etag': r['etag'],
    'local_nodes': len(nodes),'local_triangles': len(triangles),'perimeter_points': len(points),
    'mapped_points': sum(p['triangle_index']>=0 for p in points),'mappings': points,
    'time_axis': r['time_axis'],'sensor_trace_values_read': False,'cora_water_levels_read': False,'production_enabled': False,
    'datum_review': {'cora_reference': 'MSL, 1983-2001 epoch, according to NOAA Technical Report 108 pages 13-14',
        'gauge_msl_zero_in_navd88_m': gauge_offset,'gauge_epoch': datums['epoch'],
        'vdatum_lmsl_zero_in_navd88_m': vd.get('t_z'),'vdatum_reported_uncertainty_m': vd.get('uncertainty'),
        'applied_offset': None,
        'interpretation': 'Gauge datum difference is local. Current VDatum differs from that local value and from the original mesh conversion surface. Carry spatial datum uncertainty; do not fit an offset to target observations.',
        'original_mesh_conversion_file': 'hsofs_nomad_msl2navd88.grd; NOAA report says archived with OCM, not located in public searches'},
    'limitations': ['Perimeter mapping is geometric; it does not determine open-water boundary faces.',
        'CORA is hourly and uses NOAA NWLON observations for assimilation; it is a forcing candidate, not independent observed truth.',
        'Must reject missing or dry CORA nodes; no nearest-node fallback across the barrier island.',
        'MSL-to-NAVD88 conversion and uncertainty are not yet admitted.',
        'Ferry location remains ambiguous; the 2017 USGS Matthew report corroborates the catalogue location for 2016, not necessarily the 2019 deployment.',
        'Dorian is partially exposed through a published creek HWM; an untouched event is still required.']}
source_files=['cora-local-topology.json','noaa-hatteras-datums.json','vdatum-gauge-screen.json','CORA-technical-report-108.pdf','exposure-notice.json']
report['source_sha256']={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in source_files}
(ROOT/'cora-boundary-mapping.json').write_text(json.dumps(report,indent=2))
fig,ax=plt.subplots(figsize=(8,7),layout='constrained')
depth=np.array([n['depth_m_below_model_reference'] for n in nodes])
im=ax.tripcolor(tri,depth,cmap='viridis',vmin=-6,vmax=16,shading='flat')
ax.triplot(tri,color='white',lw=.45,alpha=.7)
ax.plot([-1000,1000,1000,-1000,-1000],[-1000,-1000,1000,1000,-1000],color='#ee7141',lw=2,label='Fixed 2 km SPONGE domain')
for name,lon,lat,marker in [('Ferry catalogue',-75.702839,35.207906,'o'),('Ferry NetCDF',-75.70372009277344,35.20729064941406,'x'),('Creek sensor',-75.688823,35.218333,'s')]:
    px,py=project.transform(lon,lat);ax.scatter(px-cx,py-cy,s=45,c='#ee81d8',marker=marker,label=name)
ax.set(xlim=(-2200,2200),ylim=(-2200,2200),aspect='equal',xlabel='East from domain centre (m)',ylabel='North from domain centre (m)',title='CORA regional mesh at Hatteras\nGeometry and model bed only; no flood levels read')
ax.legend(fontsize=8,loc='lower left');fig.colorbar(im,ax=ax,label='Model depth below its reference (m)')
fig.savefig(ROOT/'cora-mesh-map.png',dpi=150);plt.close(fig)
html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>CORA boundary preflight</title><style>body{{font:16px/1.6 system-ui;background:#f5f4ee;color:#183c42}}main{{max-width:950px;margin:auto;padding:24px}}img{{max-width:100%}}.notice{{background:#fff0d7;padding:18px}}a{{color:#006b85}}</style><main><h1>Regional boundary mapping is available</h1>
<p class="notice">Geometry and timestamps only. CORA water levels and the USGS sensor traces remain unread. No historical flood run or production change.</p>
<p>Found {len(nodes)} local nodes and {len(triangles)} actual model triangles. {report['mapped_points']} of {len(points)} candidate perimeter points map into those triangles. Interpolation weights are stored explicitly; this avoids selecting a nearby node across the island. Physical open-water boundary selection and dynamic node validity remain separate checks.</p>
<img src="cora-mesh-map.png" alt="CORA mesh, model bathymetry, fixed local domain and the candidate sensor positions">
<p>The file contains 8,760 hourly timestamps covering 2019. Metadata and local topology were read through bounded HTTP ranges, rather than downloading the approximately 128 GB file. The archived requests identify the file version and byte ranges.</p>
<h2>Datum screening found a material uncertainty</h2><p>The station datum table places MSL zero at {gauge_offset:.3f} m NAVD88. The current VDatum query gives {vd.get('t_z','unavailable')} m with a reported uncertainty of {vd.get('uncertainty','unavailable')} m. These are independent metadata comparisons, not fits to flood targets. Neither offset has been applied to CORA.</p>
<p>NOAA's technical report specifies MSL relative to the 1983-2001 epoch, explains that assimilation affects its realized reference, and identifies an older node-specific conversion surface. That archived surface was not located publicly. We must carry this uncertainty into any boundary experiment.</p>
<h2>Remaining limits</h2><ul>{''.join('<li>'+s+'</li>' for s in report['limitations'])}</ul>
<p><a href="cora-boundary-mapping.json">Mappings, weights and datum evidence</a> · <a href="https://repository.library.noaa.gov/view/noaa/66833">NOAA Technical Report 108</a> · <a href="https://vdatum.noaa.gov/docs/services.html">VDatum API</a> · <a href="../subgrid-storage-v1/report.html">Terrain storage candidate</a> · <a href="input-audit.html">Input audit</a></p></main></html>'''
(ROOT/'cora-boundary-preflight.html').write_text(html,encoding='utf-8')
print(json.dumps({'mapped': report['mapped_points'],'total': len(points),'gauge_offset': gauge_offset}))
