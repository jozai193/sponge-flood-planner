"""Preserve the completed laboratory result and exact local implementation."""
import hashlib
import json
import shutil
from pathlib import Path

root=Path('artifacts/validation/okushiri-lab')
destination=Path('artifacts/validation/baselines/okushiri-lab-segments-v1-completed')
audit=json.loads((root/'integrity-audit.json').read_text())
if not audit['source_checks_passed'] or not audit['all_mass_checks_passed']:
    raise ValueError('Cannot archive as completed accepted diagnostic: source/mass checks failed')
if destination.exists():
    raise FileExistsError('Never overwrite a preserved laboratory comparison')
protocol=json.loads((root/'protocol.json').read_text())
paths=list(root.glob('*'))
paths=[p for p in paths if p.is_file()]
paths+=list(map(Path,protocol['source_sha256']))
paths+=list(map(Path,['scripts/audit_okushiri_results.py','scripts/render_okushiri_report.py',
    'tests/numerics/test_coastal_segments.py','scripts/archive_okushiri_benchmark.py']))
manifest={}
for path in paths:
    target=destination/path
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(path,target)
    expected=hashlib.sha256(path.read_bytes()).hexdigest()
    if hashlib.sha256(target.read_bytes()).hexdigest()!=expected:raise ValueError('Archive copy differs')
    manifest[path.as_posix()]=expected
(destination/'checksums.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({'archive': str(destination),'files_verified': len(manifest),'production_enabled': False}))
