"""Verify bounded context on prepared locations; retain raw measurements."""
import json
import time
from pathlib import Path

from services.geodata.context_service import bounded_context

IDS=[
'0be3fe3ca88bc555cbd972b91dffcc4e7cacbba6ff4fc26be147db9e1ad81b4d',
'de83f948c9e1a979adc1f4cfcfffbf63c2a9b9535527f53cb27d8aa4e7ee88b1',
'2c607f51e1a064fc76ee6f5585cbc343358d0e9a39ead1a2806643e21cae37ba']

def main():
    samples=[]
    for bid in IDS:
        manifest=json.loads((Path('data/local/bundles')/bid/'manifest.json').read_text())
        start=time.monotonic()
        context=bounded_context(manifest)
        sample={'bundle_id': bid,'seconds': time.monotonic()-start,'trees': len(context['trees']),'water_cells': len(context.get('water',[])),'landscape_status': context.get('landscape_status')}
        if 'water' not in context:raise RuntimeError('Landscape coverage unavailable: '+bid)
        samples.append(sample)
        print(json.dumps(sample),flush=True)
    Path('artifacts/verification/context-isolation.json').write_text(json.dumps({'samples': samples,'conditions': 'Real providers with retained caches; one sample per location; successful workers reaped before return'},indent=2),encoding='utf-8')

if __name__=='__main__':main()
