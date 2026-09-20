"""Freeze same-input, same-grid candidate reruns of already exposed events."""
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

base=Path('artifacts/validation')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for parent_name,n,target_name in [('sandy-2012-grid128',128,'sandy-2012-positivity-v1'),('matthew-2016',64,'matthew-2016-positivity-v1')]:
    parent=base/parent_name;target=base/target_name
    if target.exists():raise ValueError('Refusing to replace candidate experiment '+str(target))
    p=json.loads((parent/'protocol.json').read_text())
    for name,digest in p['source_sha256'].items():
        if sha(Path(name))!=digest:raise ValueError('Parent source changed: '+name)
    target.mkdir()
    required=['hwms.json']+([p['observation_review']] if p.get('observation_review') else [])
    for name in required:shutil.copy2(parent/name,target/name)
    p['bundles']=[r for r in p['bundles'] if r['grid_cells']==n]
    p.update(grid_sizes=[n],candidate='gpu-positivity-candidate-v1',production_enabled=False,
        candidate_frozen_at=datetime.now(UTC).isoformat(),
        candidate_parent_directory=parent.as_posix(),candidate_parent_protocol_sha256=sha(parent/'protocol.json'),
        candidate_scope='Already exposed same-grid numerical regression. No terrain, building, forcing or physical-parameter fitting. No untouched-event validation inferred.')
    for name in ['packages/simulation/src/gpu-positivity-candidate.ts','packages/simulation/src/positivity-roundoff.ts',
                 'scripts/run-positivity-historical.mjs','scripts/assess_historical_validation.py','services/reference/replay_integrity.py']:
        p['source_sha256'][name]=sha(Path(name))
    for name in required:p['source_sha256'][(target/name).as_posix()]=sha(target/name)
    (target/'evaluation-plan.json').write_text(json.dumps({
        'frozen_before_candidate_run': True,'observations_already_exposed': True,
        'require_complete_121_frame_replay': True,'require_nonnegative_depths': True,
        'relative_mass_tolerance': .001,'cumulative_roundoff_relative_budget': 1e-8,
        'maximum_common_peak_change_m': 1e-4,
        'comparison': 'Compare every saved candidate depth and peak against the same-grid original. Original Sandy remains rejected; no original observation score may be manufactured.',
        'adoption': 'Experimental only; full historical regressions and another untouched event required.'},indent=2))
    for path in (target/'evaluation-plan.json',Path('scripts/compare_positivity_replay.py'),Path('services/reference/validation_regression.py')):
        p['source_sha256'][path.as_posix()]=sha(path)
    (target/'protocol.json').write_text(json.dumps(p,indent=2))
    (target/'protocol.sha256').write_text(sha(target/'protocol.json'))
    print('Frozen',target)
