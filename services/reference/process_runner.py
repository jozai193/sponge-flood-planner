"""Hard-deadline process isolation for public CPU reference runs."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from services.api.contracts import CPUReferenceRequest
from services.api.settings import settings

_capacity = threading.BoundedSemaphore(settings.cpu_reference_concurrency)


class ReferenceBusy(RuntimeError):
    pass


class ReferenceTimedOut(RuntimeError):
    pass


def _terminate(process: subprocess.Popen):
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            timeout=10,
            check=False,
        )
    else:
        process.kill()
    process.wait(timeout=10)


def run_reference_bounded(folder: Path, request: CPUReferenceRequest) -> dict:
    if not _capacity.acquire(blocking=False):
        raise ReferenceBusy("CPU reference capacity is currently in use; retry shortly")
    try:
        settings.storage_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="reference-", dir=settings.storage_root) as temporary:
            work = Path(temporary)
            request_path = work / "request.json"
            result_path = work / "result.json"
            request_path.write_text(request.model_dump_json(), encoding="utf-8")
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "services.reference.process_runner",
                    str(folder.resolve()),
                    str(request_path.resolve()),
                    str(result_path.resolve()),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            try:
                _, stderr = process.communicate(timeout=settings.cpu_reference_timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                _terminate(process)
                raise ReferenceTimedOut("CPU reference exceeded its execution deadline") from exc
            if process.returncode != 0 or not result_path.is_file():
                detail = stderr.decode("utf-8", errors="replace").splitlines()
                raise RuntimeError(detail[-1][-600:] if detail else "CPU reference process failed")
            envelope = json.loads(result_path.read_text(encoding="utf-8"))
            if not envelope["ok"]:
                if envelope["error_type"] == "ValueError":
                    raise ValueError(envelope["error"])
                raise RuntimeError(envelope["error"])
            return envelope["result"]
    finally:
        _capacity.release()


def _child(folder: Path, request_path: Path, result_path: Path):
    from services.reference.bundle_runner import run_bundle_reference

    request = CPUReferenceRequest.model_validate_json(request_path.read_text(encoding="utf-8"))
    try:
        envelope = {"ok": True, "result": run_bundle_reference(folder, request)}
    except Exception as exc:  # noqa: BLE001 - child errors must cross the process boundary as data.
        envelope = {"ok": False, "error_type": type(exc).__name__, "error": str(exc)[:600]}
    stage = result_path.with_suffix(".tmp")
    stage.write_text(json.dumps(envelope, allow_nan=False, separators=(",", ":")), encoding="utf-8")
    stage.replace(result_path)


if __name__ == "__main__":
    _, bundle_folder, request_file, result_file = sys.argv
    _child(Path(bundle_folder), Path(request_file), Path(result_file))
