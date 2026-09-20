> Current decision (2026-09-14): [Architecture v2](architecture-v2.md) governs full rainfall, coastal and compound scope, composable scenarios, engine adapters and optional authenticated/AI services. It supersedes conflicting v1 restrictions and mandatory Claude requirements. Runtime capabilities must still be verified; this notice does not mark them implemented.

# SPONGE full build checklist

## Build preferences and execution contract

- Planning: delegated by the user; full original scope retained.
- Current phase: implementation in progress. Partial work and verification evidence are recorded in build-notes.md; packages remain unchecked until every package acceptance requirement passes.
- Requested implementation model: Astra, reasoning low. No model switch, new task or sub-agent was dispatched during architecture.
- Build mode after start: autonomous within the accepted scope, with frequent concise progress updates and evidence-based milestones. No repeated permission request for ordinary implementation/testing.
- Verification: mandatory automated/manual quality checks; no requirement to ask for user approval at every milestone. User review is needed for genuinely unresolved preferences or external commitments, not routine engineering choices.
- Git: inspect/init only during implementation as appropriate; use small milestone commits if authorised by the execution environment, preserve existing research files, never reset unrelated work.
- Scope: all twelve work packages are required. Packages contain bounded subtasks; they are not claims that a scientific/GIS system can be completed in twelve 30-minute steps.
- Handoff tracking: record active subtask, changed files, tests, blockers and exact next action in build-notes.md. Never mark a package done on screenshots alone.

## Checklist

- [ ] **1. Establish the workspace, contracts and dependency evidence**
  Spec ref: `spec.md > 2. Stack and dependency policy`; `contracts.md > 1. Common conventions`.
  What to build: (1a) inspect tools, hardware and existing files; scaffold pnpm/uv workspace and containers; (1b) implement canonical schemas, typed clients, session revisions and units; (1c) add config validation, doctor and CI command skeletons that fail honestly when checks are absent.
  Acceptance: A35, A37, A38 foundations; exact versions and capabilities recorded; representative wire fixtures validate in TS and Python; no public secrets.
  Verify: typecheck, contract fixtures, container health/migration smoke check and doctor report.

- [ ] **2. Audit real data and deliver complete neighbourhood bundles**
  Spec ref: `spec.md > 4. Address-to-bundle preparation`; `contracts.md > 3. CoverageReport and NeighbourhoodBundle`.
  What to build: (2a) audit Philadelphia and a second candidate for DEM/buildings/parcels/materials/storm/inventory/cost access, select hero by evidence; (2b) implement geocode/coverage, direct USGS and Terrarium providers plus uploads; (2c) reproject/condition terrain, derive building/roof/parcel/material maps and boundary templates; (2d) publish immutable bundle and caching/job progress.
  Acceptance: A01–A04, A06; real hero bundle plus a new non-hero address and a missing-data case; roof routing, native resolution and datum checks pass. Cost/valuation catalogs may still be under construction but missing fields are explicit.
  Verify: coordinate/raster/geometry/source tests from validation.md; inspect source manifest and 3D alignment fixture; re-run preparation from raw source hashes.

- [ ] **3. Build and verify the CPU numerical specification**
  Spec ref: `numerics.md > 1. State and governing equations` through `5. Rainfall, infiltration and wetness`.
  What to build: (3a) float64 conservative first-order reference with faces, boundaries and CFL; (3b) positivity, wet/dry, roughness, rain/roof/infiltration and complete ledger; (3c) limited higher-order reconstruction and time integration; (3d) analytic/published reference fixtures and checkpoint/reset.
  Acceptance: A08–A12 foundations; all applicable controlled numerical cases pass before GPU translation. No fake drainage or unexplained clipping.
  Verify: pytest numerical matrix, convergence tables, water ledger and independent analytic/reference comparison artifacts.

- [ ] **4. Implement the live GPU engine and benchmark its resource model**
  Spec ref: `spec.md > 5. Browser runtime and GPU ownership`; `numerics.md > 3. GPU pass graph`.
  What to build: (4a) worker capability handshake, texture registry and pass runner; (4b) GPU solver parity with CPU including high-order path; (4c) reductions, readback, cancellation, checkpoints and context-loss recovery; (4d) resource estimator and baseline benchmark.
  Acceptance: A11–A13, A39; true GPU state evolution on real WebGL2, controlled cases pass, measured memory and performance recorded. Unsupported devices have explicit server/CPU execution.
  Verify: real-browser GPU tests, CPU/GPU map comparison, mass residual, no-rain/reset/context-loss tests and benchmark profile output.

- [ ] **5. Complete infrastructure physics, eligible candidates and economics inputs**
  Spec ref: `numerics.md > 6. Four intervention models` through `10. Candidate generation and feasibility`.
  What to build: (5a) all four GI types and finite soil/storage/outlet flows; (5b) parameterised drainage and transfer links with surcharge; (5c) design compiler, eligibility/conflict graph and costs; (5d) building inventory, versioned damage curves and exposure/economic calculations. Add imported-network coupling as the specified extension after core gates if enabled; do not let it replace core GPU work.
  Acceptance: A14–A17, A25–A28; distinct measured GI behaviours, sourced/assumed fields visible, no duplicated storage or fabricated dollars.
  Verify: hand-calculated storage/overflow/cost/damage fixtures, saturated storm, narrow-site feasibility, roof/inlet accounting, unknown inventory case and zero-design identity.

- [ ] **6. Deliver the full interactive terrain and live storm experience**
  Spec ref: `spec.md > 5.3 Rendering`; `prd.md > E02`, `E03`, `E05`, `E08`.
  What to build: (6a) deck terrain/buildings/water with MapLibre context and correct transforms; (6b) storm/antecedent editors and live solver progress; (6c) four manual GI tools with locks/exclusions/budget; (6d) building exposure colours, physical metrics and computed running damage counter; keyboard/numeric alternatives.
  Acceptance: A05–A16, A25–A28; user can change real inputs and see new physical outcomes; unsupported/missing-data states are usable.
  Verify: browser journey with manual placement of each GI type, grid picking against control points, live metrics/ledger comparison and accessible controls.

- [ ] **7. Build simulation-based constrained search**
  Spec ref: `numerics.md > 11. Optimisation and Claude loop`; `contracts.md > 10. Worker protocol`.
  What to build: (7a) deterministic feasible seed/baseline search; (7b) recomputed greedy insertions, removals, pairs and swaps; (7c) explicit coarse screening/full-grid evaluation with cache identity; (7d) hard constraints, best-found progress, deadline/cancel handling and robustness evaluation.
  Acceptance: A18–A20, A31; no infeasible or incomplete run accepted as best, synergy cases exercised, zero budget preserves baseline and no-benefit case returns honestly.
  Verify: tiny exhaustive comparison, interaction fixtures, budget/exclusion cases, coarse rank reversal test and held-out storm results.

- [ ] **8. Integrate simulation-backed planning, feedback and alternatives**
  Spec ref: `spec.md > 6. Planning and optimisation orchestration`; `contracts.md > 6. Claude proposals`.
  What to build: (8a) no runtime LLM dependency; (8b) terrain/site features and constraints; (8c) structured candidate plans and semantic validators; (8d) browser solver feedback, bounded search and alternatives; saved-plan states.
  Acceptance: A21–A24, A35; actual live proposal → evaluation → revision demonstrated; numerical facts and constraints cannot be overridden by generated prose. If credentials are missing, complete independent implementation, record the live-check dependency, and do not call this package fully complete.
  Verify: live configured test plus malformed/stale/overbudget/refusal/timeout fixtures; compare AI proposal, deterministic baseline and search-assisted results.

- [ ] **9. Complete synchronised replay, uncertainty and evidence inspection**
  Spec ref: `contracts.md > 8. Replay format`; `numerics.md > 12. Uncertainty and model checks`.
  What to build: (9a) lossless chunked snapshots and full restart checkpoints; (9b) paired views, camera/timeline/scrub controls and same-scale rendering; (9c) uncertainty batches, local adverse changes and source inspection; (9d) IndexedDB budgets, reload and stale-result protection.
  Acceptance: A10, A26–A31, A35–A36, A40; display and metrics match stored physical time; replay never fabricates a rerun; residual risk visible.
  Verify: paired-hash rejection, scrub/counter tests, forced storage quota, reload recovery, wet/dry sensitivity and frame-time measurements.

- [ ] **10. Deliver reports, export and full reproducibility**
  Spec ref: `spec.md > 8. Reports and economics presentation`; `contracts.md > 7. Result artifacts`.
  What to build: (10a) deterministic report tables/maps and narrative evidence schema; (10b) Evidence-bound template narrative with factual checks; (10c) PDF, HTML, GeoJSON, costs and evidence bundle export; (10d) reference comparisons and provenance/verification display.
  Acceptance: A32–A34, A42; exported numbers reconcile with UI, missing valuation/validation remains visible and all input/model identities resolve.
  Verify: table arithmetic, broken/missing evidence tests, full PDF visual inspection and recreate a selected run from exported inputs.

- [ ] **11. Deploy, profile and complete release verification**
  Spec ref: `spec.md > 9. Deployment and operations`; `validation.md > 7. Device and performance protocol` and `8. Reliability and public-demo checks`.
  What to build: (11a) local Windows launchers and production container profile; (11b) durable storage, backup/restore, public quotas and session privacy; (11c) hosted preview using available approved account/resources; (11d) measure cold/warm journeys, optimise observed bottlenecks and resolve integration failures.
  Acceptance: A35–A41; actual no-login public judge flow plus reproducible local flow; no missing functionality hidden as “demo mode”; eight-second/60fps targets have honest measured status. A missing hosting account remains a named dependency with deployment package ready.
  Verify: verify:release, cross-session access checks, job restart/restore, real-browser hosted run, all benchmark profiles and unmet-target report.

- [ ] **12. Prepare the complete Devpost handoff**
  Spec ref: `prd.md > Submission proof points`; `spec.md > 10. Performance and full demo`.
  What to build: record live address/storm/search/plan/constraint-edit/replay/report demo; prepare story, screenshots, attribution, repository/deployment links, install/test instructions and evidence index. Recheck current event requirements using official Devpost tools during submission preparation.
  Acceptance: A42 and all preceding required acceptance IDs; no unmeasured speed, fixed savings or unsupported novelty claims. Distinguish achieved functionality, unmet targets and unvalidated real-world assumptions.
  Verify: reviewer follows instructions in a fresh session; inventory every original pitch feature against evidence. Finish with submission-ready drafts; public submission remains a separate explicitly authorised action.

## Suggested execution windows

Treat these as scheduling guidance, not estimates of proven effort: foundations/data/reference first; GPU immediately after numerical baseline; GI/economics and scene next; search; replay/report; integration/performance/deployment; submission evidence. Do not spend the early build polishing visuals while the solver and real data path remain untested. Preserve time for full integration and reference checks. Update actual durations as work proceeds.
