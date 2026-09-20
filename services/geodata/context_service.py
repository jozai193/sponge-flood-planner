"""Bounded one-shot process for native geodata acquisition."""
import json
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

_SLOTS = threading.BoundedSemaphore(2)
_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

def bounded_context(manifest, *, timeout_s=35):
    if not _SLOTS.acquire(blocking=False):
        raise RuntimeError('Landscape service is busy; retry shortly')
    try:
        with tempfile.TemporaryDirectory(prefix='sponge-context-') as directory:
            request = Path(directory)/'request.json'
            response = Path(directory)/'response.json'
            request.write_text(json.dumps(manifest), encoding='utf-8')
            # Run the actual interpreter, not Windows' venv redirector, so the
            # owned process handle is the process doing native acquisition.
            bootstrap = 'import sys,runpy; sys.path[:]=' + repr(sys.path) + '; runpy.run_module("services.geodata.context_worker",run_name="__main__")'
            process = subprocess.Popen(
                [getattr(sys, '_base_executable', sys.executable), '-c', bootstrap, str(request), str(response)],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=_CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            )
            try:
                deadline=time.monotonic()+timeout_s
                while True:
                    # Worker atomically publishes only a fully closed result.
                    if response.exists():
                        return json.loads(response.read_text(encoding='utf-8'))
                    code=process.poll()
                    if code is not None:
                        raise subprocess.CalledProcessError(code or 1,process.args)
                    if time.monotonic()>=deadline:
                        raise subprocess.TimeoutExpired(process.args,timeout_s)
                    time.sleep(.05)
            finally:
                # No queued/shared work exists in this disposable process.
                # Reap it even if a native library stalls interpreter shutdown.
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=5)
    finally:
        _SLOTS.release()
