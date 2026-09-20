"""Check a downloaded SPONGE export set against its manifest (not publisher authenticity)."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(path: Path):
    manifest=json.loads(path.read_text(encoding='utf-8'))
    if manifest.get('schema')!='sponge-export-manifest' or manifest.get('version')!=1:
        raise ValueError('Unsupported export manifest')
    artifacts=manifest.get('artifacts')
    if not isinstance(artifacts,list) or not artifacts:raise ValueError('Manifest contains no files')
    root=path.resolve().parent
    seen=set()
    for artifact in artifacts:
        name=artifact.get('name')
        if not isinstance(name,str) or not name or '/' in name or '\\' in name or ':' in name or name in ('.','..') or name in seen:
            raise ValueError('Invalid or duplicate artifact filename')
        seen.add(name)
        target=(root/name).resolve()
        if target.parent!=root:raise ValueError('Artifact escapes export directory')
        data=target.read_bytes()
        if len(data)!=artifact.get('bytes') or hashlib.sha256(data).hexdigest()!=artifact.get('sha256'):
            raise ValueError('Checksum or size mismatch: '+name)
    return len(artifacts)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    args=parser.parse_args()
    try:count=verify(args.manifest)
    except (ValueError,OSError,TypeError,KeyError) as exc:parser.exit(1,'Export verification failed: '+str(exc)+'\n')
    print(f'{count} files match the manifest. This does not establish publisher authenticity or model accuracy.')
