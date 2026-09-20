"""Exercise the real API and preparation worker after Docker recovery; retain no tokens."""

if not __debug__:
    raise RuntimeError("Integrity verification is disabled under python -O; rerun without optimization.")
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx


def main():
    out = Path('artifacts/verification/stabilization-v1/live-api.json')
    evidence = {'started_at': datetime.now(UTC).isoformat(),
                'conditions': 'Real localhost API, PostgreSQL, Redis and worker. Existing provider caches retained; no mocked routes. This is infrastructure verification, not flood accuracy.'}
    try:
        with httpx.Client(base_url='http://127.0.0.1:8787/api/v1', timeout=60) as client:
            def get(path):
                r = client.get(path)
                r.raise_for_status()
                return r
            evidence['ready'] = get('/ready').json()
            session = client.post('/sessions')
            session.raise_for_status()
            client.headers['Authorization'] = 'Bearer ' + session.json()['token']
            examples = get('/examples').json()
            evidence['public_samples'] = len(examples)
            request = {"longitude": -75.164, "latitude": 39.965, "extent_m": 600,
                           "grid_cells": 128, "source": 'terrarium',
                           "label": 'Live recovery verification ' + evidence['started_at']}
            started = time.monotonic()
            r = client.post('/neighbourhoods', json=request, headers={'Idempotency-Key': request['label']})
            r.raise_for_status()
            job = r.json()
            evidence['job_id'] = job['id']
            duplicate = client.post('/neighbourhoods', json=request, headers={'Idempotency-Key': request['label']})
            duplicate.raise_for_status()
            assert duplicate.json()['id'] == job['id'], 'Duplicate job created'
            evidence['idempotency'] = 'passed'
            stages = []
            while time.monotonic() - started < 620:
                result = get('/neighbourhoods/' + job['id']).json()
                stage = (result['status'], result.get('stage'))
                if not stages or stages[-1] != stage:
                    stages.append(stage)
                    print(stage, flush=True)
                if result['status'] not in ('queued', 'running'):
                    break
                time.sleep(1)
            assert result['status'] == 'completed', result
            evidence['preparation'] = {'stages': stages, 'seconds': time.monotonic() - started}
            bid = result['bundle_id']
            evidence['bundle_id'] = bid
            manifest = get('/bundles/' + bid).json()
            evidence['buildings'] = len(manifest['buildings'])
            evidence['grid'] = manifest['grid']
            arrays = {}
            for name in ['z', 'solid', 'rain_weights', 'roughness', 'soil_capacity', 'infiltration']:
                data = get('/bundles/' + bid + '/arrays/' + name).content
                local = (Path('data/local/bundles') / bid / (name + '.bin')).read_bytes()
                assert data == local, 'Array transport changed: ' + name
                arrays[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
            evidence['arrays'] = arrays
            context = get('/bundles/' + bid + '/context').json()
            assert 'water' in context, 'Water screening missing'
            evidence['context'] = {k: len(context[k]) for k in ['roads', 'green', 'trees', 'water']}
            evidence['audit'] = get('/bundles/' + bid + '/audit').json()
            descriptor = get('/bundles/' + bid + '/imagery').json()
            assert 0 < len(descriptor['tiles']) <= 64
            # Use a separate unauthenticated request: never send the local session token to providers.
            image = httpx.get(descriptor['tiles'][0]['url'], timeout=30)
            image.raise_for_status()
            assert image.headers['content-type'].startswith('image/')
            evidence['imagery'] = {'tile_count': len(descriptor['tiles']), 'checked_tiles': 1,
                                   'bytes': len(image.content), 'type': image.headers['content-type']}
            other = client.post('/sessions')
            other.raise_for_status()
            rejected = client.get('/neighbourhoods/' + job['id'], headers={'Authorization': 'Bearer ' + other.json()['token']})
            assert rejected.status_code == 404
            evidence['other_session_access'] = rejected.status_code
            evidence['status'] = 'passed'
    except Exception as error:
        evidence['status'] = 'failed'
        evidence['error'] = str(error)
        raise
    finally:
        out.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    print(json.dumps({k: evidence[k] for k in ['status', 'bundle_id', 'buildings', 'context', 'imagery']}), flush=True)


if __name__ == '__main__':
    main()
