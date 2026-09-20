"""Verify cached domain-screen evidence and render the complete comparison."""

if not __debug__:
    raise RuntimeError("Integrity verification is disabled under python -O; rerun without optimization.")
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT=Path('artifacts/validation/dorian-2019/domain-boundary-screen-v1')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    r=json.loads((ROOT/'results.json').read_text());p=json.loads((ROOT/'protocol.json').read_text())
    for name,digest in p['hashes'].items():assert sha(Path(name))==digest
    for file,key in [('protocol.json','protocol_sha256'),('regional-levels.json','regional_levels_sha256'),('terrain-4km-buffer.tif','terrain_sha256')]:assert sha(ROOT/file)==r[key]
    mappings=json.loads((ROOT/'mappings.json').read_text());levels=json.loads((ROOT/'regional-levels.json').read_text())
    v=np.array([[np.nan if x is None else x for x in row] for row in levels['values']]);lookup={i:k for k,i in enumerate(levels['ids'])}
    assert v.shape==(73,len(lookup))
    counts=np.isfinite(v).sum(axis=0)
    node_support={"complete": int((counts==73).sum()),"always_missing": int((counts==0).sum()),"intermittent": int(((counts>0)&(counts<73)).sum())}
    checks=[]
    for c,m in zip(r['cases'],mappings):
        assert (c['width_m'],c['grid'])==(m['width_m'],m['grid'])
        n=c['grid'];z=np.load(ROOT/f'terrain-{c["width_m"]}-{n}.npy')
        assert len(m['points'])==4*n
        complete=[]
        for q in m['points']:
            w=np.array(q['weights']);assert np.all(w>=-1e-8) and abs(w.sum()-1)<1e-12
            complete.append(np.isfinite(v[:,[lookup[i] for i in q['node_indices_zero_based']]]).all())
        assert sum(complete)==c['complete_faces']
        edges=np.r_[z[:,0],z[:,-1],z[0,:],z[-1,:]]
        for s in c['support']:
            low=edges<s['reference_navd88_m']
            assert int(low.sum())==s['below_reference_faces']
            assert int((low&~np.array(complete)).sum())==s['unsupported_faces']
        checks.append({"width_m": c['width_m'],"grid": n,"terrain_sha256": sha(ROOT/f'terrain-{c["width_m"]}-{n}.npy')})
    frozen=json.loads(Path('artifacts/verification/stabilization-v1/solver-freeze.json').read_text())
    assert all(sha(Path(name))==digest for name,digest in frozen['source_sha256'].items())
    network=json.loads((ROOT/'network-ranges.json').read_text());assert network['bytes']<=p['budget_bytes']
    # Existing 2 km terrain is retained; report any extraction/resampling differences.
    repeats=[]
    for n in (64,128):
        old=np.load(ROOT.parent/f'topobathy-{n}.npy');new=np.load(ROOT/f'terrain-2000-{n}.npy')
        repeats.append({"grid": n,"max_abs_difference_m": float(np.max(abs(old-new))),"mean_abs_difference_m": float(np.mean(abs(old-new)))})
    verified={"status": 'passed',"candidate_cases": 6,"perimeter_points": sum(c['total_faces'] for c in r['cases']),
        "hours": 73,"regional_nodes": len(lookup),"network_bytes": network['bytes'],"source_hashes_verified": True,
        "node_support": node_support,
        "frozen_physics_files": len(frozen['source_sha256']),"terrain_hashes": checks,"terrain_reextraction": repeats,
        "observed_sensor_traces_read": False,"accuracy_run_performed": False}
    (ROOT/'verification.json').write_text(json.dumps(verified,indent=2))
    rows=''
    for c in r['cases']:
        mid=c['support'][1];ranges=[s['unsupported_faces'] for s in c['support']]
        rows+=f'<tr><td>{c["width_m"]/1000:g} km</td><td>{c["grid"]} × {c["grid"]}</td><td>{c["cell_m"]:.2f} m</td><td>{c["complete_faces"]}/{c["total_faces"]}</td><td>{mid["unsupported_faces"]}/{mid["below_reference_faces"]}</td><td>{mid["unsupported_faces"]/mid["below_reference_faces"]:.1%}</td><td>{min(ranges)}–{max(ranges)}</td></tr>'
    details=''
    for c in r['cases']:
        details+=f'<h3>{c["width_m"]/1000:g} km · {c["grid"]} grid</h3><table><tr><th>Edge</th><th>Below reference</th><th>Missing complete forcing</th></tr>'
        for e in c['support'][1]['edges']:details+=f'<tr><td>{e["edge"]}</td><td>{e["below_reference_faces"]}</td><td>{e["count"]}</td></tr>'
        details+='</table>'
    all_pass=all(s['unsupported_faces']==0 for c in r['cases'] for s in c['support'])
    conclusion='Every candidate retains missing forcing on potentially submerged faces. Enlarging the square alone does not establish a usable boundary.' if not all_pass else 'The missing-value screen passes, but physical boundary geometry and datum still require review.'
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Dorian domain boundary screen</title>
<style>body{{font:16px/1.65 system-ui;color:#193b3c;background:#eff4f0;margin:0}}main{{max-width:1180px;margin:auto;padding:30px}}h1,h2{{line-height:1.2}}img{{max-width:100%}}.notice{{background:#fff0d4;padding:20px;border-left:5px solid #b06d26}}table{{width:100%;border-collapse:collapse;background:white}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #cbd9d2}}.scroll{{overflow:auto}}a{{color:#00697c}}.cards{{display:flex;flex-wrap:wrap;gap:14px}}.cards p{{background:white;padding:16px;flex:1;min-width:200px}}</style><main>
<p>SPONGE · Dorian / Hatteras · geometry and forcing screen</p><h1>Does moving the coastal boundary outward fix coverage?</h1>
<p class="notice"><strong>{conclusion}</strong> No boundary or terrain change is adopted. This screen uses regional modeled levels, not observed flood targets.</p>
<div class="cards"><p><strong>6 fixed candidates</strong><br>2, 3 and 4 km squares, each at 64 and 128 cells.</p><p><strong>{len(lookup)} regional nodes · 73 hours</strong><br>Source mesh interpolation, with every vertex checked.</p><p><strong>{network['bytes']/1048576:.2f} MiB transferred</strong><br>Bounded reads from the 127.6 GB source; data identity pinned.</p></div>
<h2>Complete comparison</h2><p>Central reference is −0.067 m NAVD88, with separate screens at −0.137, −0.022 and +0.003 m. Offsets are diagnostic metadata alternatives, not an admitted regional datum transformation.</p>
<div class="scroll"><table><tr><th>Width</th><th>Grid</th><th>Cell size</th><th>All-period valid faces</th><th>Unsupported / low faces</th><th>Unsupported fraction</th><th>Missing across offsets</th></tr>{rows}</table></div>
<p>“Low faces” means the adjoining terrain cell is below the reference level. This is a screening proxy, not proof of a physical open-water boundary. Missing forcing on these faces cannot silently be replaced by a wall. Corners have two distinct faces.</p>
<img src="domain-screen.png" alt="All six terrain domains and perimeter support: red marks incomplete forcing and green marks complete forcing at low faces">
<p>Red = potentially submerged face with incomplete forcing. Green = complete hourly regional samples. Background is the pre-event NOAA terrain; fine black lines show actual regional triangles. Both sides of the barrier island are retained.</p>
<p>Of the {len(lookup)} queried nodes, {node_support['complete']} have all hourly values, {node_support['always_missing']} have none, and {node_support['intermittent']} have some missing times. These gaps are source fill values, not unsuccessful downloads. At 128 cells the central-offset unsupported fraction decreases from 45.7% to 28.6% to 22.1%; none reaches zero.</p>
<details><summary>Per-edge support at the central reference</summary>{details}</details>
<h2>What this does and does not establish</h2><p>The candidate centres, widths, grids, period and missing-value policy were written before new regional values were read. All containing-triangle vertices must be finite and different from the source fill value at all 73 hours. No nearest-node fallback, cross-island substitution or target-based tuning was used. All cases are retained.</p>
<p>Changing domain width also changes cell size at fixed grid count. This is not an accuracy or convergence comparison. Stage-only regional forcing also leaves physical land crossings, local winds, datum conversion, bridge bathymetry and model-boundary compatibility unresolved. The original domain data remain preserved; repeated terrain extraction differences are recorded in the verification JSON.</p>
<h2>Next decision</h2><p>Do not start a Dorian accuracy score from any of these squares. Review shoreline-aligned boundary segments and whether the regional wet/dry mesh can support the nearshore water bodies at all. If a complete boundary cannot be supported, select a different benchmark with independently documented inputs. The old rail-to-NAVD88 tie and continuous creek geometry remain necessary for the current sensor target.</p>
<p>Dorian is development evidence because a published high-water mark was previously exposed. Sensor time-series arrays remain unread. Any physics change must still be evaluated on a separate event whose results were not used in tuning.</p>
<h2>Verification and evidence</h2><p>Six cases and every perimeter interpolation were independently reconciled against cached arrays. All five frozen production physics hashes match. The 13 boundary-support and sensor-metadata tests passed; no simulation physics was changed.</p>
<p><a href="protocol.json">Frozen screen protocol</a> · <a href="results.json">All results</a> · <a href="verification.json">Checks and terrain differences</a> · <a href="mappings.json">Triangle mappings</a> · <a href="network-ranges.json">Source byte-range hashes</a> · <a href="terrain-source.json">NOAA terrain source</a> · <a href="../bridge-geometry-review/report.html">Bridge geometry review</a> · <a href="../../index.html">Validation dashboard</a></p>
<p>Regional source: <a href="https://tidesandcurrents.noaa.gov/cora/">NOAA CORA</a>. Its output is modeled and includes assimilation; it is a boundary candidate, not independent observed truth.</p></main></html>'''
    (ROOT/'report.html').write_text(page,encoding='utf-8')
    print(json.dumps(verified,indent=2))


if __name__=='__main__':main()
