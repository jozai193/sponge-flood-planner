"""Preserve completed event evidence before any candidate changes are evaluated."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('event_directory', type=Path)
parser.add_argument('baseline_name')
args = parser.parse_args()
if Path(args.baseline_name).name != args.baseline_name or args.baseline_name in ('.','..'):
    raise ValueError('Baseline name must be one directory component')
destination = Path('artifacts/validation/baselines')/args.baseline_name
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
if destination.exists():
    manifest = json.loads((destination/'manifest.json').read_text())
    for name, expected in manifest['sha256'].items():
        if digest(destination/name) != expected:
            raise ValueError('Frozen evidence changed: '+name)
    print('Existing baseline verified:', destination)
else:
    root = args.event_directory
    protocol = json.loads((root/'protocol.json').read_text())
    if digest(root/'protocol.json') != (root/'protocol.sha256').read_text().strip():
        raise ValueError('Protocol changed')
    audit = json.loads((root/'accuracy.json').read_text())
    if audit['protocol_sha256'] != digest(root/'protocol.json'):
        raise ValueError('Assessment does not match protocol')
    paths = {root/'protocol.json', root/'protocol.sha256', root/'accuracy.json', root/'source-checksums.json'}
    for path, expected in protocol['source_sha256'].items():
        p = Path(path)
        if digest(p) != expected:
            raise ValueError('Frozen input changed: '+path)
        paths.add(p)
    for run in protocol['bundles']:
        paths.add(root/f'simulation-{run["grid_cells"]}.json')
    paths.update(Path(p) for p in ('scripts/run-historical-validation.mjs',
        'scripts/assess_historical_validation.py','services/reference/observations.py',
        'services/reference/site_metrics.py','services/reference/replay_integrity.py'))
    assessment_freeze=root/'assessment-plan-freeze.json'
    if assessment_freeze.exists():
        paths.add(assessment_freeze)
        for name,expected in json.loads(assessment_freeze.read_text())['sha256'].items():
            p=Path(name)
            if digest(p)!=expected:raise ValueError('Frozen assessment software changed: '+name)
            paths.add(p)
    for name in ('holdout-comparison.json','candidate-comparison.json','domain-comparison.json','connectivity-diagnosis.json','building-overlap-diagnosis.json','point-diagnosis.json','access-threshold-diagnosis.json','timing-diagnosis.json'):
        if (root/name).exists():paths.add(root/name)
    # Validate every path before creating a baseline; a partial copy is never accepted.
    for path in paths:
        if path.is_absolute() or '..' in path.parts or not path.is_file():
            raise ValueError('Expected a workspace-relative evidence file: '+str(path))
    hashes = {}
    for path in sorted(paths):
        out = destination/path
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, out)
        hashes[path.as_posix()] = digest(out)
    (destination/'manifest.json').write_text(json.dumps({'event_id': audit['event_id'],'sha256': hashes,
        'provenance': 'Completed initial result and frozen protocol inputs. Assessment tooling snapshot captured after scoring; no model calibration applied.'},indent=2))
    print('Preserved',len(hashes),'files:',destination)
