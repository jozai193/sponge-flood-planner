"""Freeze the completed diagnostic, including its failed admission decision."""

if not __debug__:
    raise RuntimeError("Integrity verification is disabled under python -O; rerun without optimization.")
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


root = Path('artifacts/validation/compartment-flow-v1')
cora = Path('artifacts/validation/dorian-2019/cora-forcing-candidate-v1')
destination = Path('artifacts/validation/baselines/compartment-flow-v1-completed')
if destination.exists():
    raise FileExistsError('Never overwrite a preserved diagnostic')

paths = {p for folder in (root, cora) for p in folder.rglob('*') if p.is_file()}
checks = []
for protocol in (root/'protocol.json', root/'reference-refinement/protocol.json',
                 root/'grouping-diagnosis/protocol.json', cora/'protocol.json'):
    data = json.loads(protocol.read_text())
    sources = data.get('source_sha256', data.get('sources_sha256', {}))
    assert sources, f'No frozen sources: {protocol}'
    for source, expected in sources.items():
        path = Path(source)
        assert digest(path) == expected, f'Source changed: {path}'
        paths.add(path)
    checks.append({'protocol': protocol.as_posix(), 'verified_sources': len(sources)})

audit = json.loads((root/'integrity-audit.json').read_text())
assert audit['status'] == 'passed'
for check in audit['checks']:
    assert digest(root/check['run']) == check['sha256']
decision = json.loads((root/'dry-front-diagnosis.json').read_text())
assert decision['status'] == 'not_admitted_for_historical_or_production_flow'
assert not decision['production_enabled']
verification = {
    'utc': datetime.now(UTC).isoformat(),
    'tests': '211 passed; 5 existing rasterio deprecation warnings',
    'test_command': '.venv/Scripts/python.exe -m pytest tests/contracts tests/numerics -q',
    'test_evidence': 'Completed earlier in this implementation turn before report-only edits',
    'source_checks': checks,
    'original_declared_gates_passed': decision['original_declared_gates_passed'],
    'reference_resolution_gates_passed': decision['reference_resolution_gates_passed'],
    'adoption_decision': decision['status'],
    'production_enabled': False,
    'general_flood_accuracy_validated': False,
}
(root/'verification.json').write_text(json.dumps(verification, indent=2))
paths.add(root/'verification.json')
paths.update(map(Path, [
    'scripts/archive_compartment_flow_diagnostic.py',
    'scripts/diagnose_compartment_dry_front.py',
    'scripts/render_compartment_flow_report.py',
    'tests/numerics/test_compartment_flow_candidate.py',
    'artifacts/validation/dorian-2019/cora-local-topology.json',
    'artifacts/validation/dorian-2019/exposure-notice.json',
]))
assert all(path.is_file() for path in paths)
manifest = {}
for path in sorted(paths):
    target = destination/path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    expected = digest(path)
    assert digest(target) == expected, f'Copy differs: {target}'
    manifest[path.as_posix()] = expected
(destination/'manifest.json').write_text(json.dumps({
    'status': 'completed_diagnostic_candidate_withheld',
    'production_enabled': False, 'files_sha256': manifest,
}, indent=2))
print(json.dumps({'archive': destination.as_posix(), 'verified_files': len(manifest),
                  'adoption_decision': decision['status']}))
