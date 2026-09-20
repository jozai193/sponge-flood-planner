# SPONGE build notes

## 2026-09-15 — Scenario data suitability

Added a shared findings registry and matching Python/browser metadata screens,
authenticated stored-bundle assessment, pre-dispatch checks and sidebar findings.
Reports recompute the findings and reject mismatched terrain provenance. Missing
survey, datum transformation, spatial forcing and seabed evidence remain explicit
needs-data states, with exploratory simulation retained. No self-reported quality
label confers validated status. See data-admission-v1.md for verification and
limits. Production physics and historical accuracy claims are unchanged.

## 2026-09-15 — Shared scenario contract and capability assessment

Added canonical Pydantic ScenarioSpecV2, exported schema/generated types, browser
schema and semantic validation, shared engine capability registry, authenticated
read-only assessment endpoint, and scenario evidence in new comparisons/exports.
Capability checks do not assert physical data admission or observed accuracy.
Shared fixtures and live browser/API/report checks pass; legacy opaque IDs remain
supported independently from executable hashes. See scenario-contract-v2.md for
verification and remaining data/engine work. Production physics is unchanged.

## 2026-09-14 — Scenario composition runtime

Added shared forcing composition and execution validation, combined-source UI,
independent inflow/coastal edge controls, and central storm timing for runs,
recovery and planning. Preserved all four legacy input hashes/clocks and the
frozen production physics files. Verified 59 TS checks, three CPU/GPU composition
cases, exact checkpoint restart, actual planner replay/export and four existing
browser regressions. See scenario-composition.md for evidence and remaining work.
This implements the first forcing layer, not the full v2 wire/engine architecture;
no historical accuracy claim is upgraded. Next: shared wire contract and per-engine
capability/data admission.

## 2026-09-10 — Architecture

User direction: “build the full original idea with u improving it where you see fit but no cutting corners” and “first structure the entire architecture ... then we can use astra low to start building”.

Outcome: full scope, PRD, component architecture, numerical specification, contracts, validation plan, twelve build work packages and Astra Low handoff written. This turn created documentation only. No source code, deployment, API key access, live simulations or performance benchmarks were attempted. No sub-agents or separate tasks were created.

Build-spec/build-checklist skills supplied document structure and verification practice. The user already supplied scope/stack/demo and delegated planning, so no repeated interview or guided registration detour was needed. No Devpost workflow/terms state was fabricated; the local state file was absent. Deepening interview rounds: zero; explicit user instruction supplied the decision to proceed with the full architecture.

## Decisions

1. Retain address ingestion, real 3D geometry, live GPU, all four GI types, optimisation, Claude, damage economics, comparison and report.
2. Replace loosely specified virtual-pipes/semi-Lagrangian core with a documented conservative finite-volume shallow-water method and higher-order validated path.
3. Add backend GIS preparation and durable jobs; a thin Claude proxy alone cannot reliably prepare arbitrary neighbourhoods.
4. Use direct USGS data as primary high-resolution US path. OpenTopography is optional due to verified entitlement/key-sharing restrictions.
5. Keep broad geography with explicit data capability reporting and uploads. Global geocoding is not assumed to imply global high-resolution terrain, parcel or design-storm coverage.
6. Put finite storage, roof runoff, drainage/boundary assumptions, exposure inventory and uncertainty into core contracts.
7. Replace unproven submodular/lazy-greedy assumptions with actual combined-plan evaluations plus insertion/pair/swap search.
8. Worker GPU and renderer own separate contexts with explicit bounded snapshot transfer; no impossible cross-context texture sharing.
9. Keep economic counter but derive it from building exposure/inventory/curves. Single-event avoided loss and lifecycle return remain distinct.
10. Keep eight-second planning and 60fps replay as targets with benchmark definitions; do not mark them achieved in the architecture.

## Known dependencies to resolve during implementation

| Dependency | Current evidence | Next action |
| --- | --- | --- |
| Hero location | Philadelphia is a data-audit candidate only | Inspect exact DEM/parcel/building/material coverage and choose an area |
| Secondary real location | Not selected | Verify non-hero ingestion without source edits |
| High-resolution provider | Direct USGS source family verified; no assets downloaded | Implement and test catalogue/asset retrieval |
| Materials/soils | NRCS SSURGO/SDA chosen for initial US soil adapter | Audit exact coverage/units/access, aggregation and urban-soil uncertainty |
| Costs and building valuations | No specific municipal catalog/inventory validated | Acquire source tables with date/currency/coverage or expose explicit assumptions |
| Damage curves | FEMA source identified; direct PDF returned 403 | Retrieve official accessible manual/table during implementation and record exact curve IDs/licensing |
| NOAA ingestion | PFDS tables/grids/distribution source verified | Implement versioned fixture-tested parser and source fallback |
| Claude account/model | Not inspected; no key use authorised by this planning work was needed | Detect configured key presence and supported model at integration |
| GPU/browser | No device benchmark performed | Doctor and real-context capability/pass tests |
| Reference data | Method/source families identified | Commit licensed small analytic/published cases and compare |
| Hosting | Portable deployment selected; account/provider not chosen | Select available deployment target after resource measurements |

## Next action

Begin checklist package 1 in the subsequent implementation phase using Astra Low. Do not rerun ideation or reduce the product to a single hard-coded neighbourhood. Preserve these architecture decisions unless evidence requires a documented correction that maintains the requested feature scope.

## Implementation checkpoint — 2026-09-10

Implementation was explicitly started by the user and continued on request. The current local preview is http://127.0.0.1:5173. No model-switch or separate-task dispatch was performed; do not claim one occurred.

### Implemented and checked

- Workspace: pinned pnpm/uv dependencies, Python 3.12.14 project runtime, schema generation and TS types, PostgreSQL/PostGIS and Redis containers, initial Alembic migration, API health/readiness, scoped sessions and preparation jobs.
- CPU reference: hydrostatic HLL flux, first-/second-order reconstruction, SSP RK2, bounded rainfall/infiltration/finite soil storage, roughness, roof allocation and total ledger. Thirteen Python tests pass (contracts, lake at rest, rainfall, finite infiltration, dry-bed dam break, walls/roofs, checkpoint and CN calculation).
- GPU: first-order HLL WebGL2 solver, worker, basic stability reduction, live depth output, start/cancel UI. Rain and still-water browser test passes. Rain relative residual measured 1.3262e-6; lake level drift 2.98e-8 m in that controlled fixture. Browser used SwiftShader, not the NVIDIA GPU: no hardware performance claim.
- Two real Terrarium/Philadelphia-building bundles prepared: Spring Garden, 685 buildings (bundle 42005ef908cf047c50e6ef57a95d6bc689ea0f230455d92acae28226632e470b), and Rittenhouse, 603 buildings (685d9accc3935ce57df2dd13529e635115adc765e6036c9f133a29a4b7bacc2d). Both use uncalibrated material assumptions, lack parcels/valuation/floor data and lack verified catchment boundaries. They are development datasets, not the final hero validation.
- React/deck.gl real terrain and building view, address search/preparation UI, custom storm controls, physical-time progress, exposure area, ledger and assumptions drawer. Browser test loads the sample, starts worker simulation, observes time advancement and cancels without page errors. Screenshot: artifacts/verification/terrain-view.png (local ignored artifact).
- Optimiser and economics modules: nonlinear feasible search, small-set exhaustive enumeration, complementary pairs, conflicts/budget/exclusions, incomplete-score rejection, first-floor-relative loss calculations and missing-value handling. Four TS tests pass. Modules are not yet connected to complete infrastructure/economic inputs.
- Typecheck, production build, shared TS contract test and launcher syntax checks pass. Release verifier intentionally fails while A01–A42 still lack complete end-to-end evidence. No full checklist package has been falsely marked complete.

### Corrections and limitations discovered

- Windows application control blocked a SciPy native DLL in one process. The preparation path now uses NumPy bilinear sampling and simple morphological operations rather than requiring that DLL; no policy bypass was attempted.
- Attached/internal roofs without exposed neighbours now route to the nearest exposed block boundary with an explicit assumption. Facade exposure remains unavailable for those buildings; do not manufacture exterior samples.
- GPU open-boundary execution is explicitly rejected until its external-flux ledger is implemented. CPU open boundaries exist but need stronger reference coverage.
- GPU still needs full higher-order parity, per-stage positivity/retry, input validation, full checkpoints, accurate overflow/drainage transfers and hardware benchmarks. Current first-order tests are not a complete numerical validation.
- Direct USGS 1 m adapter is written but not exercised; exact datum metadata, asset checksum/source handling, bounds and nodata coverage need validation.
- Claude key and model are absent. `/planning/propose` currently references a not-yet-written adapter and must be implemented before integration; this is not a functioning live planner.
- Session rate limits, transactional/idempotent job dispatch, global cache privacy, authenticated uploads, proper full run manifests and report persistence remain incomplete. Do not publish this development API as production-ready.
- Launchers parse successfully but were not used to take ownership of the existing retained terminal services; Stop-SPONGE only stops launcher-recorded processes. Current retained sessions: API 23800, worker 85594, Vite 69309.

### Exact next work

Finish package 1 contract/persistence coverage and package 2 USGS/provider/parcel/material audit; extend package 3 numerical references. For the visible slice, prioritise GPU CPU-parity/positivity and complete GI compiler/storage/outlets before connecting nonlinear search. Add live Claude adapter, NOAA design storms, quantitative inventory, paired replay and reporting in checklist order. Preserve full scope and record evidence rather than converting a partial demo into completion.

## Architecture review

## Continued implementation — GPU safeguards and editable physical designs

- Added finite/bounds/shape/mask/rain-routing validation before GPU allocation. Added transactional GPU state/history backups, post-source CFL and per-stage finite/negative-depth checks, and bounded timestep retry with rollback. Open GPU boundaries remain explicitly unsupported pending a verified external-flux ledger. Higher-order GPU reconstruction is still pending.
- Added a controlled CPU dam-break output fixture and a GPU comparison test with a 1 mm RMSE acceptance threshold. The comparison passes; this is same-physics implementation parity, not independent observed-city validation.
- Added immutable design compilation for depression geometry, finite subsurface capacity, infiltration, percolation and roughness. It checks eligibility assumptions, budgets, cell validity, overlaps and double-counted storage. Full outlet/spillway/subsurface return-flow models remain pending; the four type selections are not claimed as complete facility implementations.
- Connected exploratory candidate-site editing to the GPU run in the existing preview. User can choose a site/type, edit physical parameters and assumed cost, explicitly assume eligibility, apply/remove the design and rerun. Source inputs stay unchanged. Editing storm inputs clears prior results; changing neighbourhood cancels old worker results.
- Passing checks: three GPU browser tests (rain/lake balance, CPU dam-break parity, finite-capacity saturation); six optimiser/domain/metrics unit tests; browser editor apply/remove and simulation start/stop journey; TypeScript check and production build. In the finite-capacity fixture 20 mm initial water and 5 mm reservoir capacity leave 15 mm on the surface with residual below 0.1%.
- GPU tests still report SwiftShader software WebGL. No hardware speed claim. No full checklist package or release is marked complete.
- Next: complete controlled outlets/overflow and drainage transfers, stronger wet/dry/terrain GPU verification and full checkpoint identity, then integrate evaluation/search and paired replay. Claude credentials, authoritative storm/site/economic inputs and production hardening remain outstanding as recorded above.

Review completed: all 42 acceptance IDs are present; twelve required work packages cover the complete original scope; local document links resolve; zero implementation checkboxes are prematurely complete. Numerical and contract review covered cross-context GPU ownership, roof-water conservation, full-state reset, finite storage, physical-clock replay, paired hashes, loss accounting, no false submodular guarantee and distinction between numerical/reference/observational checks. The soil adapter was made concrete as NRCS SSURGO/SDA; local design/cost source families were added. Performance remains unmeasured. No claims of implemented capability were added.

### Runtime planner change — 2026-09-10
User removed Claude from the current build. No runtime model key is required; Codex is the development agent. Connected bounded subset search to full GPU storm evaluations with a 0.1% mass-balance rejection threshold. Added 121-frame paired replay, shared clock and linked cameras. Objective: peak depth above 10 cm times area outside a fixed candidate/solid mask. User-assumed costs and eligibility remain explicit. Outlets, calibrated hydrology, sourced economics and production validation remain pending.

Verification for runtime planner change: production build/typecheck passed; optimizer/score tests 7 passed; GPU browser tests 4 passed including completed budgeted search and 121 aligned replay timestamps; real neighbourhood UI test passed including planner cancellation; CPU/contracts tests 13 passed. GPU tests use SwiftShader and do not prove hardware performance. Evidence JSON includes exact input hashes, storm settings, candidate assumptions, search history and conservation ledgers. Full-city completed optimisation and visual replay QA remain to be measured.

### Detailed city rendering — 2026-09-10
Shared city renderer now supplies main scene and paired replay: sourced building polygons, illustrative facade windows and roof edges, five material tones, directional lighting, mapped street paths and names, sidewalk styling, hover details and a detail toggle. Static geometry is memoized independently of water frames. Philadelphia context uses official Street_Centerline data (115 clipped segments in Spring Garden); OSM context is available for other locations but public endpoints timed out during this run. Philadelphia green/tree layers remain absent. Display materials, road widths, windows and canopy dimensions are illustrative, and 9 m building heights remain assumed. Context never changes the solver arrays. Corrected context-load revision tracking and provider attribution. Verification: production build/typecheck passed; real neighbourhood browser flow passed with confirmed street attribution; screenshot visually inspected at artifacts/verification/terrain-view.png. Bundled renderer remains large; no hardware performance claim.

### Drainage audit and outlet primitive — 2026-09-10
See drainage-audit.md and location-performance.md. Actual PASDA queries returned 145 inlet records, no outfalls and 23 GSI polygons in the Spring Garden envelope. Parameterised external outlet sources added to CPU/GPU, with explicit water export ledger and source metadata; defaults stay disabled. This is not sewer-network integration or full open-edge support. CPU numerical suite: 11 passed. GPU/browser suite: 5 passed. Production build/typecheck passed. Two prepared locations benchmarked three times each using software WebGL; first-scene median about 0.68 s, street-context median 2.24–2.49 s. Cold preparation and hardware simulation throughput remain unmeasured.

### Flood sources and global selection — 2026-09-10
Added rainfall / external inflow / compound scenario controls. User-entered discharge is divided across non-solid cells on a selected domain edge for a finite interval. CPU/GPU track external inflow separately, split timesteps at forcing knots and account for drainage export. This is zero-momentum prescribed surface input, not a river or coastal boundary solver. Imported drainage JSON is bound to exact input SHA-256 and validates cells, parameters and source. Constant tailwater suppresses drain export. Planner and replay use scenario inputs; evidence includes forcing configuration. Address search now accepts latitude, longitude directly; polar adapter limits remain explicit at +/-80 degrees and coverage no longer asserts unverified terrain availability. CPU numerical tests 12 passed; GPU tests 6 passed; contract tests 6 passed; UI scenario start/cancel passed; build passed. Missing: verified global data coverage, sewer topology, surcharge/backflow, river-channel boundaries, coastal water-level hydrographs/waves, calibration.

### Area size and compute controls — 2026-09-10
Added 600/1200/2000 m area selector and independent 128/256/512 grid choice for new location preparation, with displayed cell size. Camera zoom scales to extent. Added terrain-following boundary outline and Eco/Balanced/High detail render modes; Balanced limits canvas pixel ratio to 1, Eco to 0.75 and hides facade/roof/label detail. Layer creation memoized across unrelated UI changes. Fixed building flood-color update trigger when peak-depth arrays change. Precomputed rainfall collection area in GPU solver and removed redundant worker CFL readback (step retains its own CFL check). GPU tests 6 passed; build/typecheck passed. No measured FPS gain claimed. Larger preparation queries remain subject to provider limits. Investigated bilawalsidhu/gods-eye-view README: recommend optional imagery/3D reference view rather than embedding its whole dashboard. Photorealistic provider credentials/terms and Bengaluru coverage need assessment; no code copied or integration installed.

### Satellite terrain — 2026-09-10
Added Esri World Imagery tiled texture draped over a bounded terrain mesh in main scene and replay. Exact projected-square corners transformed to Web Mercator server-side; UV interpolation within patch, north-to-image-top orientation visually checked against Philadelphia streets/footprints. 4 concurrent tile fetches, maximum 64 tiles and extent-dependent zoom; default mesh capped at 128 cells per axis independently of physics. Model/Satellite toggle and explicit failure state/attribution. Single-image export returned empty metadata, so standard tiled map service used. No imagery is fed to hydraulic material inference. Attribution read from current service metadata: Esri, Vantor, Earthstar Geographics and GIS User Community. Capture dates vary; imagery is reference context rather than live data. Browser visually inspected and production build passed.


### Global evidence pipeline — 2026-09-11
Added isolated, timed and cached enrichment adapters for Overture, Copernicus, WorldCover, SoilGrids WCS, OSM channels, global HydroRIVERS, global level-6 HydroBASINS, NASA IMERG catalog and optional Dynamic World. Added per-session UI/job recovery, explicit source statuses, evidence downloads, footprint reconciliation and opt-in material revisions. Added survey schemas/imports, terrain GeoTIFF revisions, vector/CSV/IMERG conversion scripts and exact nonuniform rainfall in GPU runs/comparisons. See data-expansion.md for tested access and remaining account/model limitations. No claim of worldwide completeness, calibrated drainage or observed flood accuracy.


2026-09-11: Added server-side Earthdata acquisition and direct use of acquired rainfall evidence. Added an experimental native SWMM bridge; startup exchange fails exact conservation, so it remains disconnected from production. See data-expansion.md for the measured discrepancy and account setup.


### Facility controls and conservative surface returns - 2026-09-11

Implemented distinct compilation for graded bioswales, clogging-adjusted pavement, finite garden storage and resolved detention storage. Added explicit distributed surface controls and subsurface underdrains with receiver validation and whole-facility capacity allocation. GPU exchange gathers from an immutable snapshot, accounts for internal returns/external exports and participates in rollback. Added float64 reference exchange, configuration hashing, resolved links in comparison evidence, editor controls and paired replay storage/discharge metrics.

Verification: 11 optimizer/domain/reference unit tests and 3 TS contract tests passed; 10 GPU browser tests passed, including analytic underdrain recession, shared receivers, high downstream head and all four controlled baseline/planned runs. The existing real-neighbourhood browser journey passed. Production build/typecheck passed. Manually applied surface and underdrain controls to a real candidate with another candidate as receiver; screenshot inspected at artifacts/verification/facility-controls.png. Browser console had only the existing missing favicon request. Software WebGL (SwiftShader), not hardware performance evidence.

See facility-controls.md for exact model, units, test boundaries and remaining work. These are explicit linear storage controls; natural overtopping is resolved by surface geometry. Physical spillway ratings, pressure-driven exfiltration/backflow, full engineered channel geometry and site calibration remain incomplete. Package 5 and the full release remain unchecked.

Next concrete work: add independently verified nonlinear outlet/spillway rating curves and coupled-facility timestep convergence cases, then complete the higher-order GPU parity/checkpoint milestone. Preserve the disconnected SWMM bridge until its conservation failure is fixed.


### Nonlinear ratings, convergence and water graphics - 2026-09-11

Added SI orifice and rectangular sharp-crested weir ratings with receiver-head handling, Villemonte submergence correction for the weir, capacity bounds and conservative GPU transfers. Shared equations and independent analytic recession checks are documented in nonlinear-ratings-and-water.md with USACE/EPA sources. Whole-facility opening dimensions are distributed once across cells. Nonlinear designs cap execution steps at 0.2 seconds; planner baseline and alternatives share the same cap. Evidence describes the expanded rating options.

Water now uses shared wet-corner surface interpolation, depth color, shoreline edges and sparse solver-velocity arrows. Removed the 20 cm display lift (now 6 mm), lowered illustrative road offsets to avoid masking shallow water, added water-depth hover text, and fixed the main renderer to use compiled design terrain. Both replay views use the same renderer and scale. No rendering changes modify simulation arrays.

Verified: 15 optimizer/domain/render unit tests, 12 GPU browser tests, the existing real-neighbourhood browser journey, and production build/typecheck. GPU convergence errors approximately halve with timestep halving for isolated and downstream-coupled ratings. At maxStepS=0.2, isolated orifice/weir errors were 0.0173/0.0738 mm versus analytic recession. Tests used SwiftShader. Live Philadelphia rainfall rendering was visually inspected at 8 simulated minutes and captured at artifacts/verification/water-upgrade.png; the run was stopped after inspection. A sharp-crested rating was applied through the actual editor and the controls/units inspected.

Limits: assumed coefficients and distributed outlets, one surface rating per cell, no partial-opening transition/pipe losses/reverse flow, no site calibration or hardware performance claim. Smaller timesteps increase cost. Full higher-order GPU parity and restart checkpoints remain the next numerical milestone; no full package or release completion claimed.


### Water side faces and inspection controls - 2026-09-11

Added a triangle mesh connecting exposed wet edges to terrain, with shaded blue vertical faces. Shared interior wet edges do not create duplicate walls. Added actual/5x/10x display-only water height and a Side view/Overview camera preset. Actual height remains the default; exaggeration is labelled and applied identically to paired replay without changing wet masks, numeric depths or solver arrays. Camera presets reset view state without destroying GPU layers (remounting reused layers caused a rendering failure during QA and was corrected).

Verified production build/typecheck, 15 unit tests including boundary wall count and display-scale isolation, and the existing real-neighbourhood browser journey. Visually checked water side geometry and the low camera preset. Local preview restored at port 5173 after its earlier process stopped.


### Submission-readiness goal and checkpoint foundation - 2026-09-11

User explicitly established an autonomous goal to improve the app until ready to submit. Goal remains active; no public submission authorization inferred. Official event overview/rules now show a one-week extension to September 20, 17:00 EDT (September 21, 02:30 IST). See submission-readiness.md for refreshed requirements and work gates.

Added GPU checkpoint/restore including h, both momentum components, subsurface storage, wetness/peak/export/deep-percolation history, clock, step/retry counters and input volume totals. Exact input hash includes timestep and control configuration. Restore checks version, input identity, array shape/finiteness, solid cells, storage/peak bounds and whole-system water balance before overwriting state. Worker stop emits a checkpoint bound to storm identity; UI offers Resume stopped storm and clears old recovery state on input/comparison changes.

Verified controlled resume produces exactly equal depths, soil storage and ledger to uninterrupted GPU execution; malformed/stale inputs rejected without overwriting current state. Real-neighbourhood browser test now exercises stop/resume/stop and passes. Production build passes. This is in-memory explicit-stop recovery only; IndexedDB reload recovery and unplanned context-loss recovery remain required. Next: persist and validate full run context with checkpoint, then higher-order parity, report/export and full readiness audit. Do not declare the submission ready from this checkpoint.


### Durable stopped-run recovery and order-2 GPU - 2026-09-11

Previous goal turn classified as progress (checkpoint implementation and passing restart evidence). This continuation added IndexedDB storage for explicit-stop checkpoints with full input/storm/design/bundle/render context, a restore/discard UI and persisted identity validation. Writes are serialized. Quota failures retain in-tab resume and display an error. Recovery waits until default startup finishes; browser tests caught and fixed a race where startup overwrote restored controls. Restoring local bundle metadata does not grant backend access to private bundles; optional imagery may be unavailable in a new session. Unplanned context-loss/automatic periodic recovery is still pending.

Implemented optional order-2 GPU reconstruction in free surface, bed and velocity using minmod, nonnegative reconstructed depths and the matching bed source. First-order execution remains supported for old inputs and explicit fixtures. Newly loaded neighbourhoods use order 2 and display the order; checkpoint/cache hashes and planner evidence include it. Generated reproducible CPU fixtures with python -m scripts.gpu_order2_fixtures. Parity cases: still lake over a hill (depth RMSE 8.39e-9 m, maximum spurious speed 3.57e-7 m/s), smooth wave over hill (RMSE 2.45e-8 m), dry front (RMSE 4.64e-9 m). This verifies agreement with the same numerical reference, not observational accuracy or a full grid-convergence study.

Passing checks: 14 GPU browser tests including full restart on order 2; 15 optimizer/domain/render unit tests; real-neighbourhood browser journey including stop/save/reload/restore/resume; production build/typecheck. GPU tests remain SwiftShader. All required work packages remain open pending broader acceptance evidence.

Next: independent analytic/grid-refinement checks and automatic recovery, then deterministic report/export and a measured complete city optimisation. Submission readiness remains unproven; goal active.


## 2026-09-11: location queue recovery and comparison exports

The user-selected Prayagraj request was queued while no RQ worker was running. Started the existing local Windows worker; the pending job completed in 13.4 seconds. Visually confirmed the user preview changed to Prayagraj, 458 building footprints and satellite imagery on a 600 m / 128-cell grid. This confirms rendering, not site-specific hydraulic accuracy.

Location preparation now disables duplicate selections, describes the retained previous map, reports an offline terrain worker, and clears misleading waiting text on failure. The API reuses an active identical request and reports worker availability for queued requests. Four Python regression cases pass. API was restarted and database/queue readiness verified. Automatic service restart and lost-job reconciliation remain outstanding.

Comparison exports now include escaped standalone HTML, cost CSV and reproducible JSON with exact typed-array inputs, storm, evidence hashes, selected designs, provenance and final outputs. Report validation rejects mismatched grids/hashes, incomplete paired frames, inconsistent scores and failed conservation. A controlled browser simulation exported and reloaded the JSON, reran the GPU solver and matched final depths; the HTML was visually inspected. This is a controlled export verification, not a completed real-city optimization benchmark. PDF, GeoJSON and UI scenario import remain unfinished.


## 2026-09-11: missing 3D city coverage

The Prayagraj flat-image gaps were missing OSM footprints, not disabled extrusion. Verified Overture acquisition returned 2,432 source features; clipping and minimum-area validation retained 2,373 buildings versus the prior 458. Both user previews were rebuilt using this new bundle. Screenshot inspection confirms substantially denser 3D geometry across the formerly flat neighbourhood.

Global preparation now tries a bounded Overture query in an isolated process (180 s limit), caches the result for seven days, and retains an explicit OSM fallback note on failure. Philadelphia retains its municipal source. Queries cover the full domain bounds rather than cell-centre extents. Processor identity changed to 0.4.0 to avoid reuse of older sparse bundles on new preparation. Existing saved bundles are not silently replaced.

Height handling now parses numeric strings, metre/feet units and mapped floor counts with explicit assumptions. All 2,373 Prayagraj heights remain assumed 9 m because this source supplied neither heights nor floors. This is a footprint-based city model, not surveyed or photogrammetric 3D. Coverage remains unverified; windows and roof styling remain illustrative. Attribution follows the actual bundle source, with building counts and coverage limitations visible. Production build and 18 focused Python tests pass.


## 2026-09-11: automatic live-storm recovery

Live simulation now emits a full-state checkpoint after its first completed computation batch and approximately every 15 wall-clock seconds at batch boundaries. State/history arrays are transferred to the UI and serialized into IndexedDB with the run inputs and neighbourhood context. Explicit stop still emits a final checkpoint. Worker errors and message-deserialization failures stop the running UI and expose available checkpoint recovery. This does not yet resume optimization searches or preparation jobs.

A real browser run verified periodic save updates, reloaded while the storm was still running, restored the saved context and resumed computation without pressing Stop first. A separate forced WEBGL_lose_context test verifies the old solver rejects computation/checkpointing and a fresh solver restored from the prior snapshot reproduces the uninterrupted depths and ledger exactly. All 15 GPU tests passed. Browser tests run with SwiftShader; hardware performance remains unmeasured. The initial long-storm test found an inaccessible Duration selector; an explicit accessible name fixed it.

There is still a loss window before the first snapshot and between periodic saves. Context-loss recovery requires the user to resume from the saved checkpoint; it is not seamless continuation. The single browser-wide recovery slot, quota handling under load and full completed-run persistence remain outstanding. Report obstacle-array imports additionally reject fractional/out-of-range values before typed-array conversion can silently change them; 18 optimizer/report unit tests pass.


## Recovery isolation between independent tabs

Replaced the shared IndexedDB recovery key with a sessionStorage-backed key for each independently opened tab. Reload retains the key; saving, completing or discarding a run only changes that tab's checkpoint. Existing legacy `latest` checkpoints are moved atomically into the first claiming tab's slot, preserving the record without allowing two tabs to claim it. Build and the active-storm reload browser test pass; the two-tab test confirms independent saves, deletion isolation and reload retention.

Limitations: browser Duplicate Tab may copy sessionStorage and therefore the key; copied-session collision handling remains unverified. Closed-tab checkpoint discovery/management is not implemented, so this is not full multi-session recovery. Do not mark A35/A36 complete on this evidence.


## Selected-design GeoJSON export

Replay now offers Export GeoJSON after the comparison report passes its input/score/ledger checks. A lazy-loaded Proj4js 2.22.0 adapter transforms the supported WGS84 UTM grid to longitude/latitude. It exports one polygon per simulated intervention cell, with design identifiers, eligibility and parameter source; the design catalogue records installation cost once per design. These are simulation-cell boundaries, not surveyed construction limits. Unsupported grids and antimeridian-crossing cells are rejected explicitly.

Production build and 20 optimizer/report tests pass. Northern/southern coordinate fixtures match independent Python PROJ coordinates to eight decimal places. Browser export produced artifacts/verification/selected-designs.geojson; Shapely/PROJ readback found three valid polygons with union area 75 m2 within 0.00001 m2. Full real-city replay-button download testing remains outstanding. PDF and complete evidence manifests are still unfinished; A32 remains pending.


## Exported design/physics reconciliation

Report export now validates rainfall and budget, recompiles the listed selected designs against baseline input, and checks the reconstructed physical-input identity against the evaluated planned input. Absent versus materialized all-zero percolation arrays are normalized for this comparison. It rejects swapped excavation/storage/material/outlet edits even when existing score and input-hash fields have not been changed. Negative water-balance residuals are checked by magnitude. This is internal consistency verification, not authenticity certification or independent rerun validation.

21 optimizer/report tests and production build pass. Existing browser report generation and JSON/GPU rerun remain passing. New browser coverage evaluates an actual rain-garden intervention, accepts its report and checks rejection of altered excavation. Full original acceptance criteria remain pending.


## Export checksum manifest and independent verification

Replay now exposes Export manifest. The manifest records SHA-256 and UTF-8 byte lengths for the HTML, cost CSV, scenario JSON and selected-cell GeoJSON, plus run input identities, engine label, storm and retained source metadata. scripts/verify_export.py checks downloaded files without launching the app. It rejects changed bytes, missing files, duplicate filenames and paths outside the export directory. See export-verification.md for usage and evidence limitations.

22 optimizer/report unit tests, six verifier tests and both browser report tests pass. The browser generated a complete four-file fixture export set; Python independently verified all four files against its manifest. Production build passes. The manifest does not include original provider bytes or a model source-code archive, so complete evidence packaging and A32 remain unfinished.


## Readiness repairs: durable comparisons and closed-wall conservation

Added exclusive Web Locks ownership of per-tab recovery records. A duplicated tab with copied sessionStorage now forks the existing checkpoint and completed comparison; reload retains the owned slot. Independent save/discard operations cannot overwrite the other live tab. Browser storage/Web Locks failures are reported, with the in-memory result retained. Closed-tab discovery and large-grid quota tests remain unfinished.

Completed comparisons now automatically persist full evaluated inputs, candidate/selected designs, paired replay frames, result evidence and neighbourhood context. The UI restores or discards a saved comparison after reload. Report consistency checks, context/input hashes and budget reconciliation run before accepting stored comparisons; invalid saves do not overwrite the previous valid record. This does not persist unfinished edits or resume an interrupted optimizer.

The actual UI compute/save/reload test exposed a second-order wall-flux defect: ghost cells mirrored centre velocities before reconstruction, allowing the reconstructed fluid face and ghost face to disagree at closed edges. Corrected both GPU and CPU reference to mirror reconstructed faces. Added direct CPU zero-wall-flux tests and CPU/GPU rainfall retention at all four excavated corners. Regenerated CPU order-2 fixtures. The fixed smooth-wave GPU/CPU depth RMSE is 2.486e-8 m. The existing conservation threshold was preserved.

Also fixed a TypeScript error in the report export test that blocked production builds. Updated the README and partial acceptance evidence; no full release criterion was marked passed.

Final verification: production build/typecheck passes; 25 TypeScript unit tests, 96 Python tests and all 26 browser tests pass. Browser coverage includes a newly computed comparison automatically saved through the UI, reload/restore with selected cost and replay, persistent discard, invalid-save rejection, live-storm reload recovery, duplicate-tab isolation, and 16 GPU tests. Tests use SwiftShader, not hardware performance evidence. An earlier broad browser run was invalidated by a development reload during editing; the final unchanged-code run passed in 2.5 minutes.

Readiness: still incomplete. Outstanding scope includes independent observed-event and broader convergence validation, sourced high-resolution/site inputs, full economic inventory integration, unfinished-edit/job/search recovery, hardware performance measurements, complete source/model export packaging, hosted judge access and submission materials. Next concrete build task: persist draft scenario edits separately from completed evidence, then implement saved-record discovery for closed tabs and storage-quota fault injection. Keep scientific validation and submission gates explicit.


## September 12: visual fidelity pass

Replaced billboard tree circles with instanced solid trunks and multi-lobed canopy meshes; corrected instance rotation to yaw so trunks stay upright. Found the municipal-street path omitted all tree data, and added the bounded Philadelphia 2025 tree inventory adapter with explicit failure/coverage status. The checked Philadelphia square contains 742 tree positions; dimensions remain illustrative.

Found that municipal building `approx_hgt` values were ignored. Verified provider documentation specifies feet, added source-specific conversion and explicit approximate-source labels, and generated processor-0.4.1 bundle `2c607f51e1a064fc76ee6f5585cbc343358d0e9a39ead1a2806643e21cae37ba`: 688 buildings, 686 source-reported approximate heights and 2 fallback heights. Previous bundles and saved results remain intact. Explicit `?bundle=` links load a chosen bundle through existing access controls. API and idle queue worker were restarted with process identity checks.

Rendering now uses a shared continuous display terrain mesh and one-millimetre satellite offset, overhead-image projection onto flat roof polygons (including holes), and model-view directional shadows. Satellite mode avoids duplicate dynamic shadows over baked imagery illumination. Eco disables dynamic shadows. Main and paired replay renderers use the same geometry helpers. Raw terrain arrays and simulation code were not modified in this pass. Roofs are simplified surfaces with overhead projection; facades and tree shape remain illustrative, and satellite/footprint alignment can differ. This is not photogrammetric reconstruction.

Verified the upgraded view and an actively computing 100 mm / 10-minute storm visually in Playwright CLI. Final checks: 27 TypeScript unit tests, 106 Python tests, production build/typecheck and 3 existing browser journey/report tests pass. Roof courtyard area and display-array preservation checks pass. Browser uses software WebGL, so no hardware FPS claim. Experimental shadow switching may produce luma cached-binding warnings; no final browser journey page errors were observed. Artifacts and source URLs are linked from city-fidelity.md; final visual capture is output/playwright/upgraded-city.png.

Remaining visual scope: true textured facade/roof geometry and verified heights/vegetation for the user's other locations, including Prayagraj; explicit visual level-of-detail and hardware frame-time measurements. A commercial 3D tiles source is not integrated and Google-like city reconstruction is not claimed.


## 2026-09-12: water-aware planning and coastal reservoir milestone

Implemented shared water screening and enforced compiler exclusion, packed/hash-covered masks, mapped-water exclusion from flood metrics, time-varying coastal ghost states, conservative two-stage boundary ledger and checkpoint accounting, connected initial water, dry-start boundary CFL bound, coastal duration and control UI, common saved/live scenario construction, report provenance and topobathymetry import metadata. See coastal-progress.md for evidence and scientific limits. Build + 31 TS + 81 Python contract + 22 selected browser tests passed. A prior GPU-suite run was interrupted by Vite hot reload during editing; the complete rerun passed. Live synthetic Chennai forcing visibly propagated inland; stopped checkpoint preserved. Current open goal proceeds to startup/source reliability and measured coastal validation/performance; full original checklist is not marked complete.


## Continued validation after account/session change

Recreated active goal. Re-ran independent coastal linear-wave refinement: RMSE 0.375/0.189/0.086 mm at 100/200/400 cells, mass error below 1.1e-7. Recorded software-WebGL timings separately from hardware throughput. Direct landscape context checks passed for Greenwood, Chennai and Philadelphia. Build + 31 TS + 82 contract tests passed. Launcher now validates parsed timestamps and executable paths, cleans verified descendant processes, refuses occupied unrecorded ports, uses strict Vite port and checks API/web readiness. PostgreSQL connections have a 10-second connection timeout. Docker was initially unavailable due inaccessible runtime socket reparse points; preserved and recreated only runtime directories, never persistent volumes. Containers/images were visible during successful engine restarts. Docker version changed from 4.76 to 4.90 during recovery and another stale ingest socket required runtime isolation. App restoration and repeated-start verification remain pending until stable infrastructure.


Runtime follow-up: Docker and both SPONGE containers are healthy, but Windows Application Control now rejects pyproj/_context.cp312-win_amd64.pyd. The diagnostic records the exact failure and returns nonzero; launcher preflight verified it fails before attempting services. No policy bypass or security change performed. Full acceptance registry now includes exact requirement text, bounded milestone evidence and the active runtime blocker, while preserving all incomplete gates. Next: restore an administrator-approved geodata runtime, verify repeated launcher startup and complete live performance/QA.


Release verifier follow-up: derives expected acceptance IDs from PRD, rejects missing/duplicate/unknown entries and passing claims without evidence, reports unresolved runtime blockers. It no longer passes an empty acceptance list. Complete automated evidence-content validation remains explicitly unimplemented; verifier does not certify release on status strings alone. Windows pyproj policy block reverified on the third consecutive goal turn. Live startup/idempotence and end-to-end rendering/performance checks require an administrator-approved runtime before continuation.


### Runtime recovery — 2026-09-12

After the user changed Windows Smart App Control settings, pyproj 3.8.0 imports successfully. The launcher passed twice, with database and queue ready. Revalidated 82 Python contract tests and 4 browser app/report tests, including coastal saved-comparison export. Evidence: `artifacts/verification/runtime-recovery.json`. Removed the resolved native-runtime blocker from implementation-status.json; full acceptance requirements remain pending.


### Map-context provider reliability — 2026-09-12

Municipal street and tree requests now use the same 15-second per-operation timeout as global map-context requests. Overpass responses with a missing/null elements collection or non-object root now trigger the alternate provider instead of silently appearing as an empty successful map. Regression coverage includes valid municipal data, inventory outage, and four malformed/incomplete global responses. These limits remain per-operation, not a hard total context deadline.


### Wait for water screening before planning — 2026-09-12

The map can render before landscape context arrives. Simulation, flood configuration and design editing now wait until that request settles, so a late water mask cannot silently change an in-flight comparison. An explicit source outage releases controls with the existing unavailable-coverage warning. TypeScript validation and three app browser tests passed, including delayed success and delayed failure. This does not establish a whole-request deadline.


### Browser context deadline and profiling — 12 September

Context fetch now receives a 45-second AbortSignal timeout. A browser regression held the context response indefinitely and verified disabled controls recover with explicit unavailable water screening (passed in 45.8 seconds). This bounds the foreground browser wait in an active page; it does not cancel backend geodata work or establish a server-side deadline. Timeout coverage and profile artifacts do not prove complete source reliability.

A prepared Philadelphia CPU profile found two long tasks (1.69 and 2.48 seconds). In-page controls-enabled observation was 2.36 seconds, while automation observed controls at 4.89 seconds. Most sampled time was unattributed native/program time, so geometry generation is not established as the bottleneck. Benchmark instrumentation now records both in-page transitions and automation observation; earlier measurements retain their original meaning.


### Server context isolation prototype — 12 September

Added an experimental two-slot subprocess wrapper with a 35-second timeout, temporary-file cleanup and three tests. All 88 contract tests pass. The real Greenwood integration timed out at 35 seconds, so this prototype is deliberately NOT connected to the API. The existing provider implementation remains active. Server-side bounded acquisition is still unfinished; passing mock and synthetic process tests do not establish real-provider compatibility. Next investigation: distinguish provider latency from Windows subprocess lifecycle using stage timestamps and child process identity.


### Context process diagnosis — 12 September

Fresh stage markers confirm Greenwood context generates 1,194 trees before child termination stalls. Empty Python subprocesses exit correctly; switching from the venv launcher to the base interpreter did not resolve the behavior. A forced-exit experiment was inconclusive and removed. Evidence: artifacts/verification/context-diagnostic/findings.json. The experimental wrapper remains disconnected from the API. Do not claim a production server deadline or reliable native-child cleanup yet.


### Shared tree provenance and UI encoding — 12 September

Fixed hover labels in shared city geometry: classified-cover instances now explicitly identify illustrative, non-surveyed positions/crowns/heights; inventory trees identify mapped positions with illustrative dimensions. Applies to main and replay renderers. Repaired 45 garbled punctuation sequences in App.tsx and three in browser expectations after the previous encoding conversion; files are UTF-8. TypeScript check and both delayed-water success/failure browser checks passed. This is a source-label correction, not improved surveyed tree accuracy.


### Landscape retry without terrain reload — 12 September

Added Retry landscape coverage after missing or failed water/context acquisition. Retry is disabled during active simulation/preparation, clears current comparison/frame/checkpoint, keeps terrain and designs, and reapplies the existing loading gate and 45-second browser timeout. Revision checking prevents stale responses from changing a subsequently loaded/restored location. A browser test verified an initial 503 followed by success uses two context requests and only one terrain-array download. TypeScript check passed. Candidate compilation still validates retained designs against the updated water mask. Server cancellation remains separate unfinished work.


### Cancel stale browser context acquisition — 12 September

Context acquisition now tracks an AbortController. Location replacement, restoring saved comparison/storm and unmount abort the prior browser fetch; retries replace the controller. Revision checks remain, and a superseded request cannot overwrite the current coverage status. This cancels client work only; server native work remains an open issue. TypeScript and four relevant browser regressions passed before adding a dedicated stalled-request cancellation assertion; the dedicated stalled-request cancellation assertion also passed in a separate 38.1-second run.


### Preserve terrain mesh across landscape updates — 12 September

Main-view terrain mesh now has a separate memo keyed to terrain input, rather than being recreated when roads, trees or permanent-water context arrives. Shared cityGeometry accepts an optional prepared ground mesh; other callers retain existing behavior. Mesh detail and solver arrays are unchanged. TypeScript, all 31 unit tests, and the real-neighbourhood browser journey passed (35.2 seconds). This avoids a known redundant build/upload but no wall-time or FPS improvement is claimed without a controlled rerun.


### Reproducible process ownership checks — 12 September

Added scripts/test-process-ownership.ps1 and executed it successfully against a disposable Node parent and child. Verified JSON DateTime round-trip, rejection of stale timestamps, rejection of wrong executable identity, and termination of valid owned parent and child. Evidence: artifacts/verification/process-ownership.json. Test retains tiny diagnostic helper files under its uniquely named .runtime directory; it does not touch live services or data. This directly substantiates startup ownership and is separate from unresolved native geodata-worker cancellation.


### Provider cache integrity — 12 September

Shared fetch now verifies cached byte length and SHA-256 before reuse, reacquires malformed/mismatched entries, respects smaller per-call download budgets, and publishes data/metadata using unique temporary files and atomic replacement. Concurrent writers can still produce a mismatched pair, but subsequent reads reject it rather than returning corrupt data. Five focused cache tests and all 93 contract tests passed. No existing cache was reset. Server deadlines remain unfinished.


### Bounded native context acquisition integrated — 12 September

Supersedes earlier disconnected prototype notes. API now uses two-slot process-isolated acquisition with a 35-second deadline and up to five seconds to reap the worker. The actual base interpreter receives the current import path, avoiding the Windows venv redirector. Worker publishes a closed result atomically; parent stops/reaps its directly owned process even when native shutdown stalls. Error and saturation paths return 503 for the existing browser retry UI. Five tests cover completed-but-stalled worker cleanup, stalled timeout, partial result rejection, process failure, and capacity rejection; all 95 contract tests pass. Live neighbourhood browser journey passed (38.9 seconds). Repeat real-source samples returned expected counts and 100% WorldCover coverage in 2.25/2.38/2.52 seconds with retained caches; evidence: artifacts/verification/context-isolation.json, reproducible via python -m scripts.verify_context_isolation. Browser abort does not immediately cancel server work, but its context job has bounded lifetime. Other geodata endpoints are not covered by this deadline.


### Hardware-backed browser verification

Installed Chrome uses Intel UHD / Direct3D11 while bundled Chromium uses SwiftShader. Added SPONGE_BROWSER=chrome for reproducible tests and benchmarks, without changing system graphics preferences. Nine prepared hardware samples: first 5.13 seconds, remaining eight 0.80–1.02 seconds to observed controls; no FPS or cold API claims. Full hardware suite: 26 passed, one coastal report exact-rerun comparison failed at 1.49e-8 m. Targeted rerun plus two diagnostic repeats passed without tolerance changes; diagnostic checksums matched and both original/packed reruns had zero error. Retain intermittent discrepancy as unresolved, not a clean full-suite pass. Coastal independent refinement passed at all three resolutions. Evidence: artifacts/verification/hardware-validation.json and prepared-landscape-hardware-speed.json. First-load initialization, interactive frame timing and NVIDIA execution remain unverified.


### Recurring Docker socket failure reproduced and recovered

Docker 4.90.0 log identifies inaccessible sailor-ingest.sock at startup. Non-destructive runtime-directory isolation restored Engine 29.7.2. Docker desktop restart --timeout 60 then reproduced the identical failure; no SPONGE shutdown script was involved. Guarded Repair-DockerSockets.ps1 was implemented and successfully used to recover again. Docker reports latest version. Four containers and six volumes retained; SPONGE PostgreSQL/Redis healthy and API database/queue ready after restart. Earlier logs preserved under artifacts/verification/docker-recovery. Permanent cause/remediation inside Docker/Windows remains unresolved; do not claim crash recurrence eliminated.


## 2026-09-14 — Full-scope architecture v2

The user explicitly retains all SPONGE capabilities including coastal flooding and allows architectural improvements consistent with hackathon rules, including API-key services. Added architecture-v2.md with canonical composable scenarios, engine capability adapters, per-hazard data admission, separate rainfall/coastal validation tracks, optional AI assistance, robust GI planning and evidence-bound valuation.

Audited current source: coastal mode excludes rainfall/inflows in normal scenario assembly; HLL baseline remains; SWMM experiment explicitly fails whole-network continuity and is not coupled. Selected an SFINCS comparison spike rather than immediate replacement, checked the current GPL v3 license and recorded the conflicting older repository wording. Neither engine integration nor new accuracy is claimed.

Updated architecture entry points, scope and PRD; replaced mandatory Claude acceptance with optional provider-neutral assistance. Added pending A43–A49. Existing acceptance evidence remains unchanged. No solver, credentials, paid services, deployment or historical observation files changed in this architecture pass. Next implementation: ScenarioSpecV2 plus exact migration tests for existing presets, followed by capability admission and composed forcing verification. Demo/release tasks remain separately paused.
