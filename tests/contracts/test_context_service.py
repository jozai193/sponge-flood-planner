import subprocess
import sys
from pathlib import Path

import pytest

from services.geodata import context_service as service


def launch_stub(monkeypatch, code):
    original=subprocess.Popen
    processes=[]
    def launch(command,**options):
        child=original([sys._base_executable,'-c',code,*command[-2:]],**options)
        processes.append(child)
        return child
    monkeypatch.setattr(service.subprocess,'Popen',launch)
    return processes


def test_completed_result_reaps_worker_and_cleans_files(monkeypatch):
    processes=launch_stub(monkeypatch,"import json,sys,time; from pathlib import Path; assert json.loads(Path(sys.argv[1]).read_text())=={'test':True}; Path(sys.argv[2]).write_text('{\"trees\": []}'); time.sleep(60)")
    assert service.bounded_context({'test':True})=={'trees':[]}
    assert processes[0].poll() is not None
    assert not Path(processes[0].args[-1]).exists()


def test_timeout_kills_child_and_releases_slot(monkeypatch):
    processes=launch_stub(monkeypatch,'import time; time.sleep(60)')
    with pytest.raises(subprocess.TimeoutExpired):service.bounded_context({},timeout_s=.3)
    assert processes[0].poll() is not None
    assert service._SLOTS.acquire(blocking=False)
    assert service._SLOTS.acquire(blocking=False)
    service._SLOTS.release();service._SLOTS.release()


def test_partial_file_is_not_accepted(monkeypatch):
    processes=launch_stub(monkeypatch,"import sys,time; from pathlib import Path; Path(sys.argv[2]).with_suffix('.partial').write_text('{'); time.sleep(60)")
    with pytest.raises(subprocess.TimeoutExpired):service.bounded_context({},timeout_s=.3)
    assert processes[0].poll() is not None


def test_worker_failure_does_not_wait_for_deadline(monkeypatch):
    processes=launch_stub(monkeypatch,'raise SystemExit(7)')
    with pytest.raises(subprocess.CalledProcessError) as error:service.bounded_context({})
    assert error.value.returncode==7
    assert processes[0].poll()==7


def test_busy_context_rejects_without_starting_process(monkeypatch):
    assert service._SLOTS.acquire(False)
    assert service._SLOTS.acquire(False)
    try:
        monkeypatch.setattr(service.subprocess,'Popen',lambda *a,**k:pytest.fail('Unexpected process'))
        with pytest.raises(RuntimeError,match='busy'):service.bounded_context({})
    finally:
        service._SLOTS.release();service._SLOTS.release()
