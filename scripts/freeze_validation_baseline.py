"""Preserve existing Sandy results and current code without overwriting a freeze."""
import hashlib
import json
import shutil
from pathlib import Path

root = Path('artifacts/validation')
destination = root/'baselines/sandy-initial'
if destination.exists():
    frozen = json.loads((destination/'manifest.json').read_text())
    for name, expected in frozen['sha256'].items():
        if hashlib.sha256((destination/name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Frozen evidence changed: {name}')
    print('Existing frozen baseline verified')
else:
    source = root/'sandy-2012'
    paths = [source/name for name in ('protocol.json', 'protocol.sha256', 'accuracy.json',
        'simulation-32.json', 'simulation-64.json', 'source-checksums.json')]
    paths += list(Path('packages/simulation/src').glob('*.ts'))
    paths += [Path(p) for p in ('apps/web/src/testing/gpu-harness.ts',
        'services/geodata/prepare.py', 'services/geodata/usgs.py',
        'services/reference/observations.py', 'scripts/run-sandy-validation.mjs')]
    protocol = json.loads((source/'protocol.json').read_text())
    for run in protocol['bundles']:
        folder = Path('data/local/bundles')/run['bundle_id']
        paths += [folder/name for name in ('manifest.json', 'z.bin', 'solid.bin')]
    hashes = {}
    for path in paths:
        out = destination/path
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, out)
        hashes[path.as_posix()] = hashlib.sha256(out.read_bytes()).hexdigest()
    (destination/'manifest.json').write_text(json.dumps({'sha256': hashes,
        'provenance': 'Results and bundles preserved after initial assessment. Source snapshot taken before subsequent model changes; not a contemporaneous original-run source attestation.'}, indent=2))
    print('Frozen', len(hashes), 'evidence files')
