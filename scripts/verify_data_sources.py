"""Exercise all configured adapters through the authenticated queue/API on a public example."""
import json
import time
from pathlib import Path

import httpx


def verify():
    with httpx.Client(base_url='http://127.0.0.1:8787/api/v1',timeout=30) as client:
        response=client.post('/sessions');response.raise_for_status()
        client.headers['Authorization']='Bearer '+response.json()['token']
        examples=client.get('/examples');examples.raise_for_status();bundle=examples.json()[0]['bundle_id']
        response=client.post('/bundles/'+bundle+'/enrichment',json={'start_date':'2024-08-01','end_date':'2024-08-01'})
        response.raise_for_status();job=response.json();start=time.perf_counter();last=None
        while time.perf_counter()-start<1800:
            response=client.get('/enrichment/'+job['id']);response.raise_for_status();result=response.json()
            if result.get('stage')!=last:
                print(result['status'],result.get('stage'),flush=True);last=result.get('stage')
            if result['status'] not in ['queued','running']:break
            time.sleep(1)
        else:raise TimeoutError('Enrichment verification exceeded 30 minutes')
        evidence={'elapsed_seconds':time.perf_counter()-start,'results':result['results']}
        output=Path('artifacts/verification/full-enrichment.json');output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
        print({k:v['status'] for k,v in result['results'].items()},flush=True)
        print('Elapsed seconds:',round(evidence['elapsed_seconds'],2),flush=True)
        if any(v['status']=='unavailable' for v in result['results'].values()):raise SystemExit(1)


if __name__=='__main__':verify()
