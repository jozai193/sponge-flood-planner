"""Diagnose raw replay failures without altering outputs or scoring observations."""
import argparse
import copy
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from services.reference.replay_integrity import validate_replay


def diagnose(sim, solid, duration_s):
    g = sim['grid']; shape = (g['ny'], g['nx'])
    kwargs = {'cell_area_m2': g['dx_m'] * g['dy_m']}
    try:
        raw = validate_replay(sim['frames'], shape, solid, duration_s, **kwargs)
    except ValueError as exc:
        raw = {'replay_structure_passed': False, 'error': str(exc)}
    invalid = []
    for index, frame in enumerate(sim['frames']):
        for field in ('depth', 'maxDepth'):
            values = np.asarray(frame[field], dtype=float)
            ids = np.flatnonzero(~np.isfinite(values) | (values < 0))
            for cell in ids:
                invalid.append({'frame_index': index, 'time_s': frame['time_s'], 'field': field,
                    'cell_index': int(cell), 'row': int(cell)//g['nx'], 'column': int(cell)%g['nx'],
                    'value_m': frame[field][int(cell)]})
    # A diagnostic sensitivity check only: frozen acceptance still uses the raw data.
    normalized = copy.deepcopy(sim['frames']); adjusted = 0
    for frame in normalized:
        for field in ('depth', 'maxDepth'):
            for i, value in enumerate(frame[field]):
                if value is not None and np.isfinite(value) and -1e-6 <= value < 0:
                    frame[field][i] = 0.; adjusted += 1
    try:
        sensitivity = validate_replay(normalized, shape, solid, duration_s, **kwargs)
    except ValueError as exc:
        sensitivity = {'replay_structure_passed': False, 'error': str(exc)}
    return {'raw_audit': raw, 'invalid_values': invalid,
        'diagnostic_only_zeroing_submicrometre_negatives': dict(adjusted_values=adjusted, **sensitivity),
        'accepted_for_accuracy': bool(raw.get('replay_structure_passed') and raw.get('mass_gate_passed')),
        'scope': 'Raw output unchanged. Zeroing is an in-memory sensitivity diagnosis, not a changed acceptance criterion, repaired result or observed flood comparison.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('event_directory', type=Path)
    parser.add_argument('grid', type=int)
    args = parser.parse_args(); root = args.event_directory
    path = root/f'simulation-{args.grid}.json'; raw = path.read_bytes(); sim = json.loads(raw)
    protocol = json.loads((root/'protocol.json').read_text())
    folder = Path('data/local/bundles')/sim['bundle_id']
    solid = np.fromfile(folder/'solid.bin', dtype='u1').reshape(sim['grid']['ny'], sim['grid']['nx'])
    result = diagnose(sim, solid, protocol['duration_s'])
    sha = lambda b: hashlib.sha256(b).hexdigest()
    result.update(diagnosed_at=datetime.now(UTC).isoformat(), simulation_sha256=sha(raw),
        protocol_sha256=sha((root/'protocol.json').read_bytes()),
        diagnostic_software_sha256=sha(Path(__file__).read_bytes()))
    checkpoint = root/f'checkpoint-{args.grid}.json'
    if checkpoint.exists():
        envelope = json.loads(checkpoint.read_bytes())
        if sha(envelope['payload'].encode()) != envelope['sha256']: raise ValueError('Checkpoint checksum mismatch')
        saved = json.loads(envelope['payload'])
        result['checkpoint_prefix_matches_output'] = saved['frames'] == sim['frames'][:len(saved['frames'])]
    (root/'replay-failure-diagnosis.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
