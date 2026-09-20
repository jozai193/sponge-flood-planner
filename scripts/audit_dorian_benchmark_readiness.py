"""Reconcile new bridge evidence with forcing support before any target-score run."""

if not __debug__:
    raise RuntimeError("Integrity verification is disabled under python -O; rerun without optimization.")
import hashlib
import html
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
import matplotlib
import numpy as np

matplotlib.use('Agg')
import matplotlib.pyplot as plt

from services.reference.boundary_support import boundary_support

ROOT = Path('artifacts/validation/dorian-2019')
OUT = ROOT/'bridge-geometry-review'


def main():
    profile=json.loads((OUT/'pre-dorian-profile.json').read_text())
    sources=json.loads((OUT/'sources.json').read_text())
    for source in sources:
        assert hashlib.sha256((OUT/source['file']).read_bytes()).hexdigest()==source['sha256']
    freeze=json.loads(Path('artifacts/verification/stabilization-v1/solver-freeze.json').read_text())
    for name,digest in freeze['source_sha256'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest
    z=np.load(ROOT/'topobathy-64.npy')
    forcing=json.loads((ROOT/'cora-forcing-candidate-v1/results.json').read_text())
    datum=json.loads((ROOT/'vdatum-gauge-screen.json').read_text())['response']
    gauge=json.loads((ROOT/'cora-boundary-mapping.json').read_text())['datum_review']
    centre=float(datum['t_z']); uncertainty=float(datum['uncertainty'])
    offsets=[centre-uncertainty,centre,gauge['gauge_msl_zero_in_navd88_m'],centre+uncertainty]
    support=boundary_support(z,forcing['points'],offsets,len(forcing['time_utc']))
    assert [s['unsupported_faces'] for s in support]==[79,80,82,82]
    audit=json.loads((ROOT/'sensor-input-audit.json').read_text())
    for site in audit['sites']:
        assert site['metadata']['observation_values_read'] is False
    checks={"relative_pre_event_profile_available": True, "project_vertical_datum_documented": True,
        "old_rail_to_navd88_tie": False, "historical_profile_georeferenced": False,
        "continuous_creek_bathymetry": False, "physical_open_boundaries_reviewed": False,
        "all_potentially_wet_boundary_faces_supported": False,"regional_datum_conversion_admitted": False,
        "ferry_location_resolved": False, "sensor_scoring_protocol_frozen": False}
    result={"verified_at": datetime.now(UTC).isoformat(),"status": 'not_ready_for_accuracy_run',
        "changes": 'New source evidence, vector profile extraction and quantified boundary support; no terrain or production model change',
        "checks": checks,"boundary_support": support, "frozen_physics_files": len(freeze['source_sha256']),
        "profile_vertices": len(profile['vertices']), "extraction_check_max_error_ft": max(c['error_ft'] for c in profile['calibration']['table_checks']),
        "project_datum": 'NAVD88 / GEOID G12NC; survey-control page 1. This is not an old-rail height.',
        "benchmark_crosscheck": {"BM1_permit_ft": 5.75,"BM1_control_ft": 5.75,
            "BM2_permit_ft": 2.84,"BM2_control_ft": 2.83,
            "conclusion": 'Matching benchmark descriptions/coordinates support project linkage; a 0.01 ft revision remains explicit. No exact elevation identity assumed.'},
        "observation_processing": {"proposed_variable": 'water_surface_height_above_reference_datum',
            "source_processing": 'Source metadata describes forward/backward fourth-order Butterworth filtering with 1-minute cutoff and surveyed orifice added.',
            "policy_status": 'draft_not_frozen', "wetness": 'Require a reviewed valid-submergence rule at the sensor orifice; never count below-orifice pressure-derived values as a dry-ground observation.',
            "metrics": ['Signed bias, MAE and RMSE of stage in NAVD88 on admissible times',
                     'Peak stage and peak timing with sampling support stated',
                     'Observed-valid/model-dry count retained as failures, not deleted from scores'],
            "prohibited": ['Do not choose smoothing, datum shifts or sensor relocation to minimize target error',
                        'Do not use the target trace as boundary forcing',
                        'Do not infer flood extent, dry-ground specificity or general accuracy from two wet sensors']},
        "exposure": {"usgs_sensor_trace_values_read": False,
            "prior_event_exposure": 'Dorian already partially exposed through a published creek high-water mark; not an untouched event.',
            "current_incidental_exposure": 'Inspection page 79 contains an undated highwater note. It is not admitted as a Dorian observation.',
            "heldout_policy": 'Treat Dorian as a development comparison. Reserve a distinct event and freeze its inputs before evaluating any resulting model change.'},
        "next_actions": ['Tie the old downstream rail profile to surveyed NAVD88 and geographical endpoints; recover the original 2019 sounding sheet if available.',
            'Obtain along-creek geometry; do not extrapolate one cross section through the whole channel.',
            'Prepare a separate geometry-only domain/boundary candidate extending to wet regional triangles on both sound and ocean sides, then recheck all forcing samples.',
            'Resolve the regional datum transformation; freeze model inputs, targets, time window, submergence policy and metrics before opening sensor traces.'],
        "general_flood_accuracy_validated": False,"production_enabled": False,"terrain_modified": False}
    evidence=[ROOT/'topobathy-64.npy',ROOT/'cora-forcing-candidate-v1/results.json',OUT/'pre-dorian-profile.json',
              ROOT/'sensor-input-audit.json',ROOT/'vdatum-gauge-screen.json',ROOT/'cora-boundary-mapping.json',
              Path('services/reference/boundary_support.py'),Path(__file__)]
    result['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in evidence}
    (OUT/'readiness.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    v=profile['vertices'];axes[0].plot([p['distance_ft']*.3048 for p in v],[p['sounding_ft_below_rail']*.3048 for p in v],'o-',color='#833fac')
    axes[0].invert_yaxis();axes[0].set(xlabel='Distance along profile (m)',ylabel='Sounding below rail (m)',
        title='June 10, 2019 downstream streambed\nRelative profile only; NAVD88 tie unresolved');axes[0].grid(alpha=.2)
    axes[1].imshow(z,extent=(-1000,1000,-1000,1000),origin='lower',cmap='terrain',vmin=-5,vmax=5)
    mid=support[1]
    for row in mid['edges']:
        edge=row['edge'];indices=np.array(row['unsupported_faces']);q=-1000+(indices+.5)*2000/64
        px,py={'west':(np.full_like(q,-1000),q),'east':(np.full_like(q,1000),q),'south':(q,np.full_like(q,-1000)),'north':(q,np.full_like(q,1000))}[edge]
        axes[1].scatter(px,py,c='#d32732',s=16)
    axes[1].set(xlabel='East from fixed domain centre (m)',ylabel='North from centre (m)',
        title='80 potentially submerged faces lack forcing\nRed: terrain below -0.067 m; incomplete CORA samples',xlim=(-1100,1100),ylim=(-1100,1100))
    fig.savefig(OUT/'readiness.png',dpi=150);plt.close(fig)
    table=''.join(f'<tr><td>{r["reference_navd88_m"]:.3f}</td><td>{r["below_reference_faces"]}</td><td>{r["unsupported_faces"]}</td><td>{r["unsupported_faces"]/r["below_reference_faces"]:.1%}</td></tr>' for r in support)
    links=''.join(f'<li><a href="{html.escape(s["file"])}">{html.escape(s["file"])}</a> · <a href="{html.escape(s["url"])}">NCDOT source</a></li>' for s in sources)
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Dorian benchmark readiness</title>
<style>body{{background:#eff3ef;color:#183c3b;font:16px/1.65 system-ui;margin:0}}main{{max-width:1120px;margin:auto;padding:32px}}img{{max-width:100%;background:white}}.notice{{padding:18px;background:#fff0d4;border-left:5px solid #ac6425}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{text-align:left;padding:10px;border-bottom:1px solid #cddad4}}a{{color:#066c7c}}h1,h2{{line-height:1.25}}.cards{{display:flex;gap:15px;flex-wrap:wrap}}.cards p{{flex:1;min-width:200px;background:white;padding:16px}}</style><main>
<p>SPONGE · Dorian / Hatteras · input review · 14 September 2026</p><h1>Pre-storm channel evidence recovered</h1>
<p class="notice"><strong>Not ready for an accuracy run.</strong> New bridge evidence narrows the geometry problem. It does not resolve absolute bed elevations or missing regional forcing. Production physics and terrain remain unchanged; USGS target trace arrays remain unread.</p>
<div class="cards"><p><strong>13 profile vertices</strong><br>June 2019 downstream soundings extracted from original PDF vectors.</p><p><strong>79–82 unsupported faces</strong><br>Of 176–179 potentially submerged perimeter faces across the reviewed offsets.</p><p><strong>5 physics hashes unchanged</strong><br>13 targeted metadata and boundary tests passed.</p></div>
<img src="readiness.png" alt="Pre-Dorian relative channel profile and missing perimeter forcing on the fixed domain">
<h2>What the bridge archive establishes</h2><p>The old 86-foot bridge is documented in the environmental review signed in July 2019. The later underwater inspection report preserves a June 10, 2019 downstream streambed curve. Native PDF vector extraction was checked against nine 2023 tabulated soundings: maximum axis-extraction error {result['extraction_check_max_error_ft']:.4f} ft. This is extraction precision, not survey uncertainty.</p>
<p>The 2023 permit profile cites a May 21, 2019 survey. Later project-control sheets explicitly specify NAVD88 / GEOID G12NC. Matching benchmark descriptions and coordinates support linking these project records; BM1 matches at 5.75 ft, while BM2 differs by 0.01 ft (2.84 versus 2.83). The old rail elevation is not established by these benchmark values.</p>
<p>The soundings are below the old rail. They cannot yet replace NAVD88 terrain. Proposed replacement deck, riprap, excavation and drainage are excluded from the historical geometry. Cross sections and the existing bridge outline are retained for further georeferencing. A single bridge section also does not define the full creek.</p>
<details><summary>Inspect the original profile and datum sheets</summary><img src="soundings-80.png" alt="NCDOT historical streambed profiles, including June 2019"><img src="datum-page1.png" alt="Project control with NAVD88 datum declaration"><img src="profile-page16.png" alt="Permit profile distinguishing proposed construction and existing bridge"></details>
<h2>Datum adjustment cannot repair missing boundary data</h2><table><tr><th>Reference level (m NAVD88)</th><th>Terrain below reference</th><th>Incomplete forcing</th><th>Fraction unsupported</th></tr>{table}</table>
<p>Offsets are the existing VDatum central result and its reported ±0.070 m uncertainty, plus the nearby gauge datum difference. These are diagnostic alternatives, not an admitted spatial conversion or confidence interval. A negative-bed test is only a conservative screening proxy for candidate water faces; physical shoreline review is still required. Corners represent two distinct faces, not duplicated cells.</p>
<p>Every face must retain all 73 hourly CORA samples from September 5–8 and all contributing triangle vertices. Missing values are not replaced with zero or a nearest node across the island. The audit finds 44.9–45.8% of below-reference faces unsupported. Masking them away or treating them as walls would conceal a boundary assumption.</p>
<h2>Observation scoring remains gated</h2><p>The NetCDF metadata identifies NAVD88 metres, UTC time and a source-filtered storm-tide variable. Its documented one-minute filtering is preferable to inventing error-minimizing smoothing. Valid submergence at the sensor orifice must be reviewed. A model-dry result at an observed-wet time must remain a failure rather than being dropped from the score. Ferry coordinates remain ambiguous. No extent accuracy can be calculated from two wet sensors alone.</p>
<p>Dorian is already partly exposed through a published high-water mark. The inspection table also incidentally exposed an undated highwater note; it is not used. Any Dorian-driven changes must be checked against a distinct event whose results were not used for tuning.</p>
<h2>Concrete next work</h2><ol>{''.join('<li>'+html.escape(x)+'</li>' for x in result['next_actions'])}</ol>
<h2>Evidence and reproducibility</h2><p><a href="readiness.json">Readiness checks and hashes</a> · <a href="pre-dorian-profile.json">Extracted profile and calibration</a> · <a href="sources.json">Source inventory</a> · <a href="../input-audit.html">Prior input audit</a> · <a href="../../index.html">Validation dashboard</a></p><ul>{links}</ul>
<p>Run scripts/extract_slash_creek_profile.py with the bundled document Python, then scripts/audit_dorian_benchmark_readiness.py with the project Python. Terrain or boundary candidates require separate versioned protocols before they can be used for scoring.</p></main></html>'''
    (OUT/'report.html').write_text(page,encoding='utf-8')
    print(json.dumps({"status": result['status'],"unsupported": [s['unsupported_faces'] for s in support],"profile_vertices": len(v)}))


if __name__=='__main__':main()
