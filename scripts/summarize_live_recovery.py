"""Reconcile retained live recovery evidence before publishing its summary."""

if not __debug__:
    raise RuntimeError("Integrity verification is disabled under python -O; rerun without optimization.")
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.verify_export import verify

root = Path('artifacts/verification/stabilization-v1')
api = json.loads((root/'live-api.json').read_text())
docker = json.loads((root/'docker-recovery.json').read_text(encoding='utf-8-sig'))
tests = (root/'live-browser-tests.log').read_text(encoding='utf-8-sig')
planner = (root/'live-planner.log').read_text(encoding='utf-8-sig')
rerun_log = (root/'live-export-rerun.log').read_text(encoding='utf-8-sig')
rerun = json.loads(next(line for line in rerun_log.splitlines() if line.startswith('{"results":')))
scenario = json.loads((root/'live-export-set/sponge-reproducible-comparison.json').read_text())
assert api['status'] == 'passed'
assert docker['ready']['database'] == docker['ready']['queue'] == 'ready'
assert '11 passed' in tests
assert '"restored":true' in planner
assert all(side['depthErrorM'] == side['peakErrorM'] == 0 for side in rerun['results'])
assert scenario['evidence']['searchResult']['evaluations'] == 2
assert scenario['selectedDesigns'] == [] and scenario['summary']['costMinor'] == 0
count = verify(root/'live-export-set/sponge-export-manifest.json')
assert count == 4
summary = {"verified_at": datetime.now(UTC).isoformat(), "status": 'passed',
    "browser_tests": 11, "api_evidence": 'live-api.json', "docker_evidence": 'docker-recovery.json',
    "export_manifest_files": count, "exported_reruns": rerun, "comparison_restored": True,
    "replay_final_state": '120/120 reached in Playwright CLI, screenshot output/playwright/live-recovery-planner.png',
    "planner": scenario['evidence']['searchResult'],
    "caveats": ['Provider caches retained; not an uncached acquisition benchmark',
             'Synthetic functional storms do not establish real-event accuracy',
             'Same-device reproducibility does not establish cross-device reproducibility',
             'Docker socket recovery is a workaround; no upstream or reboot fix claimed',
             'Clean installation, demo and submission remain paused']}
(root/'live-verification.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps({"status": summary['status'], "browser_tests": 11, "export_manifest_files": count}))
