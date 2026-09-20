> Current decision (2026-09-14): [Architecture v2](architecture-v2.md) governs full rainfall, coastal and compound scope, composable scenarios, engine adapters and optional authenticated/AI services. It supersedes conflicting v1 restrictions and mandatory Claude requirements. Runtime capabilities must still be verified; this notice does not mark them implemented.

Current migration priority is the scenario contract, capability assessment and separate rainfall/coastal validation tracks in architecture v2. The dated work items below are historical checkpoints; consult their linked artifacts before inferring current status.

# Remaining readiness work

User-authorized priorities: reliable loading, responsive interaction, flood-model validation, planning evidence, release readiness. Preserve the original product scope and all pending acceptance requirements.

1. Loading: context deadline/concurrency/worker cleanup now integrated and tested. Audit preparation, imagery and enrichment lifetimes separately; verify failures do not leave orphaned jobs. Immediate client-disconnect cancellation remains optional improvement beyond the context deadline.
2. Responsiveness: prepared data benchmarks and native-time-heavy CPU profile recorded. Terrain mesh reuse removes redundant work but measured speedup is unproven. Installed Chrome now verified on Intel UHD / Direct3D11: eight of nine prepared loads reached controls in 0.80–1.02 seconds, while first load took 5.13 seconds. Bundled Chromium remains software-rendered. Next isolate first-load graphics initialization and measure actual interactive draw/frame timing; NVIDIA and real API cold loading remain unmeasured.
3. Flood validation: independent small-amplitude coastal refinement passed. Audit the full existing numerical/reference matrix and repeat affected suites. Terrain datum, nearshore bathymetry and observed-event accuracy remain unresolved; never describe synthetic coastal demonstrations as validated hazard estimates.
4. Planning evidence: audit eligibility, cost assumptions and objective reports. Implement defensible missing inputs where obtainable; retain unavailable damage estimates without invented valuations.
5. Release: reconcile every acceptance criterion against direct evidence, verify clean installation, prepare reproducible demonstration and submission materials. No public submission or acceptance of terms is authorized by this implementation request.

Evidence and limitations are recorded in build-notes.md, location-performance.md, coastal-progress.md and implementation-status.json. Individual milestone completion is not full release acceptance.
