"""Prepare real landscape fixtures before running the browser-only benchmark."""
import json
import sys
from pathlib import Path

from services.geodata.context import city_context

for bundle_id in sys.argv[1:]:
    if len(bundle_id)!=64 or any(c not in '0123456789abcdef' for c in bundle_id):
        raise ValueError('Expected prepared bundle ID')
    manifest=json.loads((Path('data/local/bundles')/bundle_id/'manifest.json').read_text())
    context=city_context(manifest)
    destination=Path('artifacts/verification/landscape-fixtures')
    destination.mkdir(parents=True,exist_ok=True)
    (destination/(bundle_id+'.json')).write_text(json.dumps(context),encoding='utf-8')
    print(bundle_id[:12],len(context['trees']),'trees',len(context.get('water',[])),'water cells',flush=True)
