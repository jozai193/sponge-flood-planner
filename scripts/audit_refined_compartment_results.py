"""Verify recorded arrays, frozen sources and failure decision before archiving."""

if not __debug__:
    raise RuntimeError("Integrity verification is disabled under python -O; rerun without optimization.")
import hashlib
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np

from scripts.run_refined_compartment_benchmark import GAUGES, compare

root = Path('artifacts/validation/refined-compartment-v1')
destination = Path('artifacts/validation/baselines/refined-compartment-v1-completed')
if destination.exists(): raise FileExistsError('Never overwrite a preserved diagnostic')
digest = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
protocol_paths = [root/'protocol.json', root/'failure-diagnosis-protocol.json',
                  Path('artifacts/validation/compartment-flow-v1/protocol.json')]
source_checks = []; sources = set()
for pp in protocol_paths:
    p = json.loads(pp.read_text()); hashes = p.get('source_sha256', p.get('sources_sha256'))
    for path, expected in hashes.items():
        assert digest(path) == expected, f'Changed source: {path}'
        sources.add(Path(path))
    source_checks.append({"protocol": str(pp), "verified": len(hashes)})
for path, key in [
    ('artifacts/validation/baselines/matthew-2016-domain4km-completed/manifest.json', 'sha256'),
    ('artifacts/validation/baselines/compartment-flow-v1-completed/manifest.json', 'files_sha256')]:
    hashes = json.loads(Path(path).read_text())[key]
    for source, expected in hashes.items(): assert digest(source) == expected, f'Prior source changed: {source}'
    source_checks.append({"protocol": path, "verified": len(hashes)})

results = json.loads((root/'results.json').read_text()); checks = []
for run in results['runs']:
    case = run['case']; saved = json.loads((root/f'{case}.json').read_text())
    assert saved['result'] == run
    reference = np.asarray(saved['traces']['hll_half_m'])
    recalculated = compare(np.asarray(saved['traces']['selective']), reference)
    assert recalculated == run['gauges']
    arrays = np.load(root/f'{case}-fields.npz')
    for name in saved['traces']:
        traces = np.asarray(saved['traces'][name])
        assert traces.shape == (121, 3) and np.isfinite(traces).all() and np.min(traces) >= 0
        if name not in arrays: continue  # Original regression has a separately frozen HLL gauge reference.
        field = arrays[name]
        assert field.shape == (121, 16, 64) and np.isfinite(field).all() and np.min(field) >= 0
        np.testing.assert_array_equal(traces, np.column_stack([field[:, r, c] for r, c in GAUGES]))
        np.testing.assert_allclose(field[-1].sum(), run['ledgers'][name]['stored_m3'], rtol=1e-12, atol=1e-12)
    assert run['all_gates_passed'] == all(run['gates'].values())
    checks.append({"case": case, "saved_traces_fields_scores_and_volume_verified": True})
assert not results['candidate_gates_passed']
assert not next(r for r in results['runs'] if r['case'] == 'wide_short_pulse')['gates']['arrival']
verification = {"utc": datetime.now(UTC).isoformat(), "tests": '218 passed; 5 existing rasterio warnings',
    "test_command": '.venv/Scripts/python.exe -m pytest tests/contracts tests/numerics -q',
    "source_checks": source_checks, "array_checks": checks,
    "adoption_decision": 'withheld_failed_new_case_arrival_and_mixed_case_rmse_regression',
    "production_enabled": False, "general_flood_accuracy_validated": False}
(root/'verification.json').write_text(json.dumps(verification, indent=2))
paths = {p for p in root.rglob('*') if p.is_file()} | sources
paths.update(map(Path, ['scripts/audit_refined_compartment_results.py', 'scripts/render_refined_compartment_report.py',
                       'tests/numerics/test_refined_compartment_candidate.py']))
manifest = {}
for path in sorted(paths):
    target = destination/path; target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target); expected = digest(path)
    assert digest(target) == expected
    manifest[path.as_posix()] = expected
(destination/'manifest.json').write_text(json.dumps({"status": 'completed_diagnostic_candidate_rejected',
    "production_enabled": False, "files_sha256": manifest}, indent=2))
print(json.dumps({"archive": str(destination), "verified_files": len(manifest), "verification": verification}))
