> Architecture amendment (2026-09-10): Claude integration is superseded by the user. Codex performs development; the application currently uses simulation-backed search with no runtime LLM or model API key. Claude-specific requirements below are historical and no longer release gates. Planning, validation, alternatives and evidence-bound reporting remain required.

# SPONGE verification and performance gates

Historical acceptance targets below are tracked against implementation checks recorded in build-notes.md and data-expansion.md; passing numerical checks does not establish observed-event accuracy. If a tolerance changes, record the scientific reason and retain the old result; never loosen it merely to turn a failure green.

## 1. Validation levels

1. Contract/data checks: the inputs are internally interpretable and correctly transformed.
2. Numerical verification: the implementation conserves water and solves controlled cases acceptably.
3. Reference comparison: selected outcomes agree within stated tolerances with an independent analytical/published/established-engine case.
4. Observational validation: a specific location/event is compared with measured evidence.

Passing levels 1–3 does not imply level 4. The release requires 1–3; level 4 is pursued for the hero case where observations are available and is otherwise explicitly unvalidated. No site receives a calibration badge based on visually plausible flooding.

## 2. Data and coordinate gates

- Transform known control points and grid corners forward/backward within 0.1 cell horizontally; test row orientation and longitude/latitude order.
- Test at least three known Terrarium encoded heights, negative elevations and unit conversion. Resampling metadata retains original native resolution.
- Reject unknown/mixed vertical datum for quantitative building comparisons unless a declared supported transform resolves it.
- Geometry: holes, multipolygons, overlaps, invalid rings, narrow passages, roofs fully enclosed by obstacles and small footprints.
- Rain interval integration error <=0.01% against declared total; no negative rain or overlapping intervals. Check metre/millimetre/hour/second conversion explicitly.
- Source hash, raster shape/bytes, mask coverage, footprint-to-terrain alignment and no-double-count roof area must pass before bundle publication.
- A non-hero address must build a new bundle; one coverage-deficient location must display the missing-data path correctly.

## 3. Numerical test matrix

| Case | Required evidence and initial acceptance |
| --- | --- |
| Dry/no-rain domain | h and q remain zero within roundoff; no artificial storage/loss |
| Lake at rest over variable bed | Spurious speed <1e-5 m/s; water-level drift <1e-4 m on the controlled metre-scale fixture |
| Closed flat box with uniform rain | Stored volume matches integrated rain; depth RMSE <1 mm |
| Bounded infiltration | Analytical constant-capacity case matches volume within 0.1%; dry soil cannot consume unavailable water |
| Horton/CN fixtures | Match hand-derived/reference cumulative outputs within 0.1%; CN and Horton are never double-applied |
| Wet/dry dam-break | Compare with analytic/published solution away from discontinuities; normalised L1 depth error <=5% at declared resolution; refinement reduces error |
| Bed step and steep slope | No negative/non-finite state; hydrostatic balance and refinement trend; document reconstruction limitations |
| Roughness flow | Uniform/channel test approaches analytical or trusted reference velocity/depth within 5% |
| Solid block and roofs | No flux through solid faces; all roof precipitation appears in routed input/storage/outflow |
| Open/inflow/stage boundaries | Correct flux sign and prescribed hydrograph volume; distinguish free outflow and backwater |
| GI unit tests | Stage-storage, infiltration, underdrain and overflow match hand cases; no extra capacity or double-counted excavation |
| Drainage saturation | Shared inlet/network capacity and surcharge conserve total-system water |
| Reset/checkpoint | Full reset reproduces baseline; resumed full-state run matches uninterrupted result within GPU tolerance |
| CPU/GPU parity | Small-grid depth RMSE <=1 mm and volume/peak metrics within 0.1% where analytic behaviour is smooth |

Whole-run water residual targets: <=0.1% for controlled fixtures and <=0.5% for complex neighbourhood cases, plus absolute residual reporting. Normalisation is total initial storage + external input with a documented 1 m³ floor for near-dry tests. Tiny fixtures also use an absolute bound so the floor cannot conceal loss. Material negative depth or any NaN/Inf fails regardless of residual percentage.

Use at least three grid sizes (e.g. 4/2/1 m when source geometry supports them) and two timestep ceilings for the hero reference study. Primary peak-depth, flooded-area and exposure metrics should change less than 5% between the two finest acceptable runs; threshold-sensitive exceptions must be displayed and investigated. Do not claim a strict uniform error bound for arbitrary cities from these tests.

## 4. Independent reference strategy

The float64 CPU implementation helps detect GPU/programming errors but shares modelling assumptions. Add analytic fixtures and at least one independently configured surface-flood benchmark or HEC-RAS 2D case with available geometry, inputs and results. Record reference version, mesh, source/boundary mapping and sampling method. Compare depth maps, hydrographs, peak timing and mass balance, not screenshots alone.

Use SWMM to compare compatible rainfall-runoff/LID/storage submodels; SWMM alone is not a direct validation of every 2D street-flow cell. If imported-network coupling is enabled, test conservation and convergence of the coupled system separately. Numerical test result artifacts are small, licensed and reproducible in the repository.

## 5. Economics and optimisation gates

- Depth-damage interpolation endpoints, first-floor offsets, different currencies/price years, contents/structure separation, missing inventory and zero depth.
- Running counter equals sum of per-building running maxima; replay/scrubbing never adds damage repeatedly. Final UI, JSON and report tables agree to one currency minor unit before display rounding.
- A negative avoided-loss outcome remains negative and visible; unvalued buildings are counted.
- Enumerate all feasible subsets on tiny candidate sets (e.g. 8 candidates) and compare search output. Heuristic may miss optimum; report its measured gap, not false optimal status.
- Pair-synergy fixture: two individually weak sites can be discovered as useful together. Negative-interaction fixture: individually beneficial sites can be worse in combination.
- Hard budget, locked sites, exclusive variants, prohibited overlaps, no-benefit plan, no-feasible plan and zero-budget baseline identity.
- Coarse-versus-fine ranking check; final declared metrics always come from the final declared grid.
- Paired wetness/rainfall samples use identical seeds and input variants. Test a holdout scenario not used to select the plan.

## 6. AI and report gates

Validate unknown candidate/evidence IDs, out-of-budget proposals, attempted constraint relaxation, truncated output, provider refusal, timeout and stale revision. No test uses arbitrary generated code execution. A live integration test with configured credentials must demonstrate proposal → evaluation → feedback → evaluated revision; deterministic fixtures test failure handling offline.

Compare Claude-only proposal, simple deterministic heuristic and final search-assisted plan on the same scenario. Record differences without claiming Claude always wins. Report numeric tables are generated from result artifacts; detect unsupported numeric narrative claims and fall back to a deterministic narrative template if needed, labelled accordingly. Inspect PDF pagination, legends, source labels and before/after consistency before delivery.

## 7. Device and performance protocol

Record OS, CPU, RAM, GPU/driver, browser/version, viewport/DPR, WebGL extensions, OffscreenCanvas support and measured allocation budget. Default benchmark profile: a prepared 1 km square physical domain at 2 m cells (500x500 active cells, padded allocations allowed), 1-hour storm plus at least 1-hour recession, 24 candidate design variants and fully specified material/drainage inputs. Also measure 1 m, larger domain, 6/24-hour storms and a lower-capability laptop profile. Profiles are benchmark inputs, not limits on architecture scope.

Measure separately:

| Measurement | Target/requirement |
| --- | --- |
| Warm prepared-bundle usable scene | Target <=3 s on reference hardware/network |
| Replay | Target 60 fps; publish p50/p95 frame times and dropped frames |
| Warm Plan-to-paired-result | Target <=8 s including Claude, search and final required output |
| New address preparation | Publish cold duration by stage; no invented eight-second promise |
| Simulation | Full physical duration, cell updates/s, elapsed time, substeps and output cost |
| Search | Evaluated candidates/plans, resolution, incumbent improvement and termination reason |
| Live interaction | No long UI freeze; cancel acknowledged target <=250 ms between batches |
| Memory | Measured peak CPU/GPU estimate, replay storage and cleanup after repeated runs |

Run five warm repeats and at least three cold/provider runs when quotas permit, publish median/range and failures. Separate exact-cache hits, warmed inputs with fresh computation, and cold end-to-end execution. An eight-second cached replay does not establish eight-second fresh planning. Numerical dt/grid cannot be silently changed to pass a speed target.

If targets fail, profile shader pass count, allocation churn, readback, candidate caching, batching, source preparation and rendering. Preserve completion correctness and report measured latency. The final release can be functionally complete with a documented unmet performance target; it cannot advertise that target as achieved.

## 8. Reliability and public-demo checks

Test reload during prepare/run, worker/API restart, duplicate idempotent requests, lost SSE connection, old AI reply, quota exhaustion, upload corruption, database migration mismatch, GPU context loss and IndexedDB quota. Session A cannot read private session B resources; public sample artifacts stay accessible without login. Credentials and arbitrary user uploads are absent from static bundles and logs.

Live public acceptance: fresh browser opens hero case, changes budget, runs Claude, excludes a site, computes a new plan, replays both cases and exports a report. Offline acceptance: prepared terrain/replay opens with saved-plan provenance and clearly identified unavailable live services. Both paths are required and labelled correctly.

## 9. Commands to implement

The following are the intended stable command contract, not existing scripts:

```text
pnpm typecheck
pnpm test:contracts
uv run pytest tests/contracts tests/numerics
pnpm test:gpu
pnpm test:optimizer
pnpm test:e2e
pnpm benchmark -- --profile reference
pnpm verify:release
```

`verify:release` must aggregate genuine outputs, source/access checks, acceptance IDs, required live checks and unmet targets. It cannot simply check that files exist. Write machine-readable evidence to `artifacts/verification/<revision>/` and a short linked release report. Run checks appropriate to each change; reserve broad release checks for an integrated candidate.


## Current observed-event candidate and blockers

USGS supplies a suitable independent evidence candidate: **High-Water Marks in the Five Boroughs of New York City from Flash Flooding Caused by the Remnants of Hurricane Ida, September 1, 2021**, DOI https://doi.org/10.5066/P9OMBJPQ (83 locations, published 2023). Primary catalog: https://data.usgs.gov/datacatalog/data/USGS%3A618975c8d34ec04fc9c5a049 . This is identified source evidence, not a completed comparison. A reproducible case still needs event-matched rainfall, a matching surveyed terrain datum, boundary forcing and usable measured depths; high-water elevations cannot be substituted for depth above ground.

The new services/reference/observations.py comparator checks explicit event equality, CRS/row orientation, finite nonnegative peak depths and point measurements, excludes points outside the simulation extent, and reports bias, MAE and RMSE. Its tests are synthetic. No calibration badge or real-world accuracy result has been earned.

## September 11 numerical/performance work

GPU maximum timestep is configurable (default solver 1 s; ordinary and comparison workers request up to 10 s). CFL constraints, post-source checks, rollback and forcing knots continue to limit actual steps. On a controlled 8x8 sloped rainfall/infiltration case, 120 simulated seconds took 240 reference steps versus 14 adaptive steps; maximum depth difference 7.36e-6 m, with both mass residuals below 0.1%. This is a controlled example, not universal temporal-convergence evidence. All seven existing GPU tests passed. Ordinary worker frames now enforce the same 0.1% residual rejection gate as comparison runs.

SWMM's fixed ten-by-0.1-second window now compensates the trapezoidal carryover from the preceding inlet rate. The 2.5 m3 startup transfer is accounted for, but a 60-second test still shows about 0.064 m3 whole-network imbalance. The bridge requires explicit node storage areas and reports its total residual; coupling_eligible remains false. Inlet exchange, surcharge and backflow are therefore not enabled in the public simulation.


## Dorian benchmark readiness follow-up, September 14

NCDOT's relocated B-5610 archive supplied a July 2019 environmental review, a May 21, 2019 survey cited in later permit profiles, project control specifying NAVD88/GEOID G12NC, cross sections, and an underwater inspection report preserving June 10, 2019 downstream streambed soundings. The pre-Dorian curve was extracted from native PDF vectors into 13 vertices. Calibration against nine tabulated 2023 soundings gives a maximum extraction discrepancy of 0.0015 ft; this does not estimate survey accuracy. The old rail reference has no established NAVD88 elevation, so the soundings are retained as relative geometry and have not modified terrain. Proposed replacement construction is not used as 2019 geometry. Benchmark BM1 agrees between records; BM2 differs by 0.01 ft and is retained explicitly.

The fixed 2 km domain's negative-bed screening finds 176–179 potentially submerged boundary faces across reviewed datum offsets; 79–82 lack complete 73-hour CORA forcing. This is a terrain screening proxy, not an admitted shoreline mask. Changing a datum offset does not repair missing regional data. Missing faces cannot silently become walls or use nearest-node levels across the island.

`scripts/extract_slash_creek_profile.py` (bundled document Python) and `scripts/audit_dorian_benchmark_readiness.py` (project Python) reproduce the extraction and readiness report. Thirteen targeted tests pass; all five frozen physics hashes match. Evidence: `artifacts/validation/dorian-2019/bridge-geometry-review/report.html`. Dorian remains ineligible for an accuracy run. USGS sensor trace arrays remain unread; an incidental undated highwater note in the bridge inspection is excluded. Resolve the old-rail vertical/geographic tie, continuous creek geometry, physical boundary coverage and regional datum before freezing the scoring protocol. Dorian is development evidence; a distinct untouched event remains required for generalization.

## Dorian nested-domain screen, September 14

`scripts/screen_dorian_domain_boundaries.py` freezes and checks six centred squares (2/3/4 km; 64/128 cells) against actual CORA triangles, 73 hourly levels from September 5–8, and buffered pre-event NOAA terrain. The geometry and policy were frozen before new regional level reads. 111 nodes required 46.75 MiB of verified HTTP ranges from the pinned 127.6 GB source. 80 nodes have all samples, 14 are always missing and 17 have intermittent source fill values.

Every candidate retains unsupported potentially submerged perimeter faces. At 128 cells and the central diagnostic reference of -0.067 m NAVD88, counts are 164/359 (45.7%), 120/420 (28.6%) and 102/461 (22.1%) for 2/3/4 km. All four datum offsets are retained. This is a negative-terrain screening proxy, not a physical shoreline mask. Larger width also coarsens cells at fixed grid count. No forcing is filled, no missing face becomes a wall, and no domain is adopted. `scripts/render_dorian_domain_screen.py` independently reconciles all 2304 perimeter points against cached arrays; all five production physics hashes match. The 2 km terrain re-extraction differs by at most 1.2e-7 m, so changed subset boundaries do not explain the coverage result.

Evidence: `artifacts/validation/dorian-2019/domain-boundary-screen-v1/report.html`. Next assess shoreline-aligned segments and regional wet/dry support, or select a benchmark with better independent inputs. Creek geometry and datum remain unresolved. Sensor target traces remain unread and no accuracy run was performed.

## Completed full-day GPU verification

The stored Spring Garden 128x128 terrain and real IMERG 2024-08-06 event completed 86,400 s rainfall plus 3,600 s recession using the ordinary GPU worker. Elapsed local wall time: 194.25 s; steps: 12436. Rain input: 505.799968239 m3; final combined surface/soil storage: 505.800000670 m3; residual: -0.000032431 m3 (0.000006412%). This confirms completion and numerical mass closure for one low-rainfall case; it does not validate depths against observations or prove timestep convergence for severe storms. Raw local result: .runtime/full-day-result.json. The previous interrupted-run limitation is superseded for this case.

A SWMM refinement experiment using 0.05 s and 0.01 s routing steps, 100 iterations and tighter head tolerance did not resolve whole-network continuity error (approximately 2.4%). It remains explicitly ineligible for production coupling. Sixty Python checks pass, including a regression separating the corrected input transfer from the unresolved network balance.


## Drainage isolation results, September 11

Seven dedicated drainage regression tests pass. New controlled tests cover direct surface-to-outfall exchange, reverse flow from a fixed downstream stage, and a 0.001 m3/s inlet capacity limit. Direct forward exchange residual is 0.00458%; direct reverse exchange residual is 0.00614%, both below the 0.1% gate. These omit the physical conduit and do not establish coupled-pipe accuracy.

The unchanged 20 m, 0.5 m diameter, 5% slope pipe case remains near 2.4% residual after 60 s. A 1 m pipe reduces residual to about 0.0347%, but changes the physical problem and is not a fix. Splitting the same 20 m pipe into 2/5/10/20 segments with tiny intermediary storage areas produces non-convergent residuals (approximately 1.19%, 1.96%, 9.53%, 15.71%); these numerical storage assumptions were experimental only and have not been adopted. Routing steps of 0.1/0.01/0.001 s with very tight head tolerance and 200 maximum iterations still give about 2.4% residual. No acceptance tolerance was relaxed. The evidence localizes the outstanding defect/limitation to conduit routing and its storage accounting rather than direct inlet exchange. Production coupling remains disabled; matched observed-event validation remains incomplete.
