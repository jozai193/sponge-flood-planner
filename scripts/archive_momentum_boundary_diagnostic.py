"""Preserve valid controls alongside the explicitly failed boundary replay."""

if not __debug__:
    raise RuntimeError("Integrity verification is disabled under python -O; rerun without optimization.")
import hashlib
import json
import shutil
from pathlib import Path

root=Path('artifacts/validation/momentum-boundary-v1')
dest=Path('artifacts/validation/baselines/momentum-boundary-v1-completed')
if dest.exists():raise FileExistsError('Never overwrite a preserved diagnostic')
verify=json.loads((root/'verification.json').read_text())
assert verify['field_runs_verified']==9
assert verify['exchange_verified']['matched_exchange_verified'] is False
paths={p for p in root.rglob('*') if p.is_file()}
for pp in (root/'protocol.json',root/'exchange-protocol.json'):
    data=json.loads(pp.read_text())
    for path,expected in data['source_sha256'].items():
        p=Path(path);assert hashlib.sha256(p.read_bytes()).hexdigest()==expected;paths.add(p)
paths.update(map(Path,['scripts/archive_momentum_boundary_diagnostic.py','scripts/audit_momentum_boundary_diagnostic.py',
    'scripts/render_momentum_boundary_report.py','tests/numerics/test_momentum_diagnostic.py',
    'tests/numerics/test_exchange_replay_diagnostic.py']))
manifest={}
for path in sorted(paths):
    target=dest/path;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    expected=hashlib.sha256(path.read_bytes()).hexdigest()
    assert hashlib.sha256(target.read_bytes()).hexdigest()==expected
    manifest[path.as_posix()]=expected
(dest/'manifest.json').write_text(json.dumps({"status": 'completed_diagnosis_including_failed_exchange_control',
    "files_sha256": manifest,"production_enabled": False},indent=2))
print(json.dumps({"archive": str(dest),"files_verified": len(manifest)}))
