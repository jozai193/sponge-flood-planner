import importlib
import json
import os
import platform
import shutil
from pathlib import Path

checks={"python":platform.python_version(),"platform":platform.platform(),"node":shutil.which("node"),
        "docker":shutil.which("docker"),"claude_key_present":bool(os.getenv("ANTHROPIC_API_KEY")),"libraries":{}}
for name in ("numpy","rasterio","pyproj","shapely","fastapi","sqlalchemy","redis"):
    try:
        module=importlib.import_module(name)
        checks["libraries"][name]=getattr(module,"__version__","available")
    except (ImportError, OSError) as exc:
        checks["libraries"][name]={"status":"unavailable","error":str(exc)[:600]}
checks['ready']=all(isinstance(value,str) for value in checks['libraries'].values()) and bool(checks['node'])
path=Path("artifacts/verification/doctor.json")
path.parent.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps(checks,indent=2))
print(json.dumps(checks,indent=2))
raise SystemExit(0 if checks['ready'] else 1)
