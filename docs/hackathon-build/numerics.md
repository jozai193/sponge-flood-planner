> Current decision (2026-09-14): [Architecture v2](architecture-v2.md) governs full rainfall, coastal and compound scope, composable scenarios, engine adapters and optional authenticated/AI services. It supersedes conflicting v1 restrictions and mandatory Claude requirements. Runtime capabilities must still be verified; this notice does not mark them implemented.

# SPONGE numerical and decision model

Version 1. Implements E03–E09. Units are metres, seconds, cubic metres and explicitly declared currency. All constants, catalog versions and tolerances are persisted. This document selects the method; [validation.md](validation.md) determines whether its implementation is acceptable.

## 1. State and governing equations

Use a uniform Cartesian finite-volume grid within each run. Canonical state per active surface cell is `U = (h, qx, qy)`, where h is water depth and qx=hu, qy=hv are discharge per unit width. Bed elevation is z. Continuity is `dh/dt + dqx/dx + dqy/dy = rain + roof_runon + returns - infiltration - captured_drainage`; momentum contains advective and hydrostatic fluxes, bed slope, roughness and explicitly modelled exchange terms.

Retain cumulative infiltration/wetting state, soil/LID storage and drainage storage as additional physical state. Derived eta=z+h, velocity and running maxima are not substitutes for canonical state. Store non-finite counts and budget residuals as diagnostics.

Use conservative finite-volume HLL numerical fluxes with hydrostatic reconstruction and corresponding bed-source corrections. Begin with first-order spatial reconstruction as a documented baseline; add limited MUSCL reconstruction and second-order SSP Runge–Kutta once baseline tests pass. Full release requires the higher-order path to pass tests; the first-order path remains a diagnostic/fallback numerical option with its order disclosed. Do not implement virtual-pipes animation and describe it as this solver.

Method reference: [Audusse et al., hydrostatic reconstruction](https://publications.imp.fu-berlin.de/478/). Its properties apply to the specified scheme under its conditions, not automatically to arbitrary shader approximations. Include steep-terrain and wet/dry convergence cases because reconstruction alone does not guarantee accurate topographic flow.

## 2. Discretisation and stability

At a face, reconstruct left/right free-surface and discharge states, choose interface bed `z*=max(zL,zR)`, reconstruct nonnegative depths and consistent velocities, calculate wave-speed bounds and one shared face flux. Store each x/y face flux once; neighbouring cells consume it with opposite signs. Include side-specific bed-pressure corrections. Reflect normal momentum at closed solid boundaries; prescribed open/inflow/stage boundaries use explicit ghost states and source identities.

For the unsplit two-dimensional update, use a conservative initial CFL target of 0.4 and `dt <= CFL / max((abs(u)+sqrt(g*h))/dx + (abs(v)+sqrt(g*h))/dy)`, with dry-cell handling and documented solver-specific restrictions. Additionally limit dt by available-water/source depletion, storage exchange, temporal forcing knots and output times. Initial dt_max is one simulated second, configurable and recorded; convergence tests may require smaller values. Reduce max wave speed on GPU; do not use an old reduction beyond a justified bound. Correctness takes precedence over avoiding a readback.

Each Runge–Kutta stage must preserve nonnegative depth and storage. Use positivity-preserving reconstruction/flux limiting, plus bounded sinks. A donor-cell drainage limiter must scale the same outward shared face flux for both adjacent cells, including advected momentum; arbitrary per-cell clipping breaks conservation. Tiny floating-point roundoff repairs are counted and volume-accounted. Material negative depths, unbounded velocities or non-finite values invalidate the step; retry from the last valid stage with smaller dt up to a bounded limit, then fail the run visibly.

Apply Manning friction in a stable semi-implicit source step with dry-depth regularisation. Rain and roof inflow add mass with specified incoming momentum (default vertical rain has zero horizontal momentum). Removed water carries consistent local momentum. Record source-splitting order and test convergence for source-driven cases. Never fix a numerical instability by multiplying down depths without accounting for the lost volume.

## 3. GPU pass graph

For each stable step:

1. Evaluate forcing interval and boundary values; prepare source rates.
2. Reconstruct states and face fluxes; calculate bed corrections.
3. Reduce wave speeds and outgoing-water limits; determine dt.
4. Apply shared flux limiter where required; update state and source exchanges.
5. Apply friction and bounded soil/GI/drainage updates using the selected stage schedule.
6. Repeat necessary Runge–Kutta stages; verify extrema and finite state.
7. Accumulate physical diagnostics and running exposure maxima.
8. At output times reduce metrics and optionally enqueue depth readback.

Use RGBA32F/R32F renderable textures as supported; feature-test framebuffer completeness and relevant capabilities, not only an extension name. Use nearest sampling and integer texel access for numerical state. Avoid float blending atomics and texture feedback: a pass never samples an image attached for writing. Ragged reductions use neutral padded cells. Store masks/site IDs in integer textures or validated exact numeric representations.

Precision-sensitive volume accounting uses pairwise reductions, stable local elevation origin and periodic CPU float64 summation of checkpoints. A single float32 running global total is insufficient as the reference ledger. Use a tiny deterministic CPU case to compare every pass during development.

## 4. Terrain, buildings and domain boundaries

Building cells are impermeable obstacles. Do not add an arbitrary tall building mound to ground elevation and then infer indoor depth from it. Rain over roofs is collected using real footprint area and routed with precomputed receiver weights; contributed volume is counted once as rainfall, not twice as new rain plus roof inflow. Supplied drainage connections can change routing, with explicit provenance.

V1 cell masks use full-cell solids; rasterisation error and closed-passage checks govern minimum resolution. A narrow real street cannot be represented by simply drawing it over a blocked hydraulic grid. Refinement or documented subgrid structures are needed; unsupported geometry is flagged. No unvalidated fractional cut cells that could introduce tiny unstable volumes.

The visible viewport is not a drainage basin. Preparation examines contributing terrain beyond it, derives a simulation buffer/catchment, and assigns each exterior face closed, outward/open, prescribed inflow or prescribed water level. Open boundaries record discharged volume and backwater treatment. A constant zero-depth outer edge is an assumption, never the automatic answer for every city block. Boundary sensitivity and domain expansion checks are required for the hero case.

Culverts and small connections can use explicit link models with source/destination, invert/crest, geometry, discharge relation and capacity. Every link transfers equal and opposite volume and respects donor availability. If flood behaviour depends on an unobserved river/tidal boundary, request the boundary data or mark the scenario incomplete.

## 5. Rainfall, infiltration and wetness

Rainfall is a piecewise time series in m/s with physical timestamps; spatial patterns are optional versioned rasters. Its integral times receiving area must match total input volume. Sampling handles interval crossings exactly, not by frame-dependent interpolation. Record storm duration, recession duration, annual exceedance probability and temporal distribution separately.

Primary natural-soil mode is modified Horton-style infiltration with capacity decay/recovery, soil storage and available-water limits. Parameters include f0, fc, decay, recovery, maximum soil storage, percolation and initial saturation. Rates never exceed surface water plus simultaneous rain/runon available during the step. Store wetting/drying memory so restart and candidate resets are correct. Parameters are not universal constants inferred by Claude.

Provide an alternative SCS curve-number rainfall-excess mode for compatible source data: compute cumulative excess from cumulative precipitation using the declared CN, potential retention and initial abstraction relation; apply only the nonnegative increment. Do not apply CN rainfall reduction and a second soil-infiltration sink to the same rainfall on the same area. Terrain can still route generated excess, and GI treats incoming runoff using its own storage model. The mode and equivalence assumptions are explicit; Horton and CN scenarios are not assumed interchangeable.

Initial soil/LID/drainage storage is scenario state, not a renderer reset. Wet antecedent scenarios are required. Evaporation may be negligible for the short storm run but if omitted must be recorded; multi-day simulations need a specified evaporation process. Reference model parameters are aligned before comparison with SWMM, using its [LID modelling documentation](https://www.epa.gov/water-research/storm-water-management-model-swmm).

## 6. Four intervention models

Every design compiles to physical edits plus a cost/eligibility record. Geometry changes bed/roughness; storage and infiltration parameters describe the actual facility. Initial storage is consistent across paired runs and reflects scenario assumptions. GI state is fresh for every candidate evaluation.

| Type | Physical representation | Required parameters and overflow |
| --- | --- | --- |
| Rain garden | Depressed surface plus soil and optional aggregate storage | Area, excavation depth, soil depth/porosity/conductivity, initial saturation, native-soil percolation, optional underdrain, overflow crest and recipient |
| Bioswale | Graded vegetated channel/depression that conveys and infiltrates | Width/length/slope, cross section, roughness, soil properties, downstream connection; surface conveyance uses resolved geometry and respects overtopping |
| Permeable pavement | Surface permeability coupled to finite subsurface aggregate reservoir | Pavement thickness/permeability/clogging, reservoir depth/void ratio, subgrade infiltration, underdrain and overflow; saturation can return water to surface |
| Detention basin | Excavated surface storage with outlet and spillway | Stage-storage from geometry, outlet relation, crest/width, max stage and downstream recipient; detention delays/releases water, it does not erase it |

Use either resolved surface depression volume or lumped surface storage for a given facility, never both. Initial implementation uses resolved surface storage and per-cell distributed subsurface states; per-facility underdrain controls use GPU reductions and deterministic receiver maps. Total infiltration/capture cannot exceed inflow or available storage during dt. Transfer to soil/LID reservoirs is internal; deep percolation/outfall discharge is external. Underdrain flow returns to the configured network/surface or crosses an identified domain boundary.

Costs use actual area/volume/length, installed unit prices, mobilisation, excavation/disposal, replacement, contingency and optional annual maintenance. Catalogs include locality, price year, currency, source and uncertainty. The $2M budget is a user input, not a reason to force a certain quantity of infrastructure. Budget constraints use upper cost estimates when a conservative budget mode is selected.

## 7. Drainage exchange

Surface-only mode sets unmodelled sewer exchange to zero and labels it. Parameterised mode represents inlet capture from surface head, finite downstream discharge and storage. Overflow returns to the inlet/defined relief cells and is explicitly counted; multiple inlets share capacity without each receiving the entire network allowance. Specify capture head relation or empirical capacity curve per inlet and test it.

For imported SWMM networks, the reference service exchanges surface water and network flows at fixed coupling boundaries, caps exchange by donor storage, advances SWMM with consistent time, and returns surcharge. Inner substeps may differ; aggregate exchanged volumes over coupling intervals. Perform timestep convergence and combined ledger tests before enabling quantitative comparison. Never couple two solvers by letting both independently remove the same water. This adapter's slower execution does not replace the required browser GPU engine.

## 8. Water accounting

Maintain a total-system ledger:

`initial surface + soil + GI + network storage + precipitation + external inflow = current surface + soil + GI + network storage + boundary outflow + deep percolation + external drainage outfall + evaporation + residual`.

Maintain a separate surface ledger showing infiltration, roof transfers, inlet capture and returns. These are useful process metrics but internal transfers cancel from the total-system ledger. Roof-routed rainfall contributes to precipitation once. Every texture/cell area conversion uses the canonical metric grid and roof allocation rules.

Report absolute residual m³ and relative residual against total water handled with an explicit small-volume floor. Counts of dry-cell corrections and discarded roundoff are exposed in diagnostics. Invalid or incomplete ledger results cannot receive the completed/evaluated status used by the final report.

## 9. Exposure and loss calculation

For each building, map exterior accessible sample cells/entrances. Use exterior water-surface elevation eta and first-floor elevation on the same vertical datum. Indoor-exposure proxy is `max(0, representative_exterior_eta - first_floor_elevation)`. Choose a documented representative statistic (default conservative maximum at valid exterior/entrance samples), retain sample locations, and include statistic sensitivity. Solid building-cell depth is not usable for this calculation.

Evaluate versioned piecewise-linear depth-damage curves by occupancy/foundation/story class. Apply curves separately to structure replacement value and contents value when available, cap fractions to [0,1], and avoid double counting assets. A uniform curve applied to unknown stock is an explicit illustrative assumption, not an inferred authoritative inventory. Missing occupancy/first-floor/value fields produce uncertainty scenarios or excluded/unvalued counts.

Per-building current event loss is based on maximum exposure reached so far. Aggregate this running maximum once per building; do not integrate a dollar loss rate over every timestep. A damage counter may continue increasing during recession if a downstream building floods later. Observed floor heights and measured values are distinguished from regional defaults.

`avoided_event_loss = baseline_final_event_loss - plan_final_event_loss` may be negative. Show it alongside the complete physical exposure map, not only total savings. Point estimate plus low/high assumptions is a sensitivity range; only call it a probabilistic confidence/credible interval when input distributions and method justify that meaning. [FEMA Hazus manual](https://www.fema.gov/sites/default/files/documents/fema_hazus-flood-model-technical-manual-5-1.pdf) is the intended source family; extraction and exact curve licensing/IDs require implementation-time inspection because direct retrieval failed during architecture research.

Economic return is separate from single-event avoided damage. If lifecycle benefit-cost is enabled, integrate losses over a documented probability curve with multiple return periods, then apply horizon, discounting and maintenance. Never label avoided loss from a single 100-year storm as annual savings or realised ROI. The original dollar comparison remains in the product as a calculated, qualified event estimate.

## 10. Candidate generation and feasibility

Generate polygons only from eligible surfaces/parcels and documented user permissions. Candidate designs are discrete variants: location, type, area/geometry, depth, outlet and material properties. Features include contributing area, slope, low-point/storage potential, exposure proximity, upstream/downstream relations, installation cost and source quality. Parcel-level statistics alone cannot tell Claude exact hydrological effects.

Filter slope/dimension limits, setbacks, prohibited uses, buildings, access and utility exclusions before search. Unknown utility/ownership data are marked rather than fabricated. Model overlapping designs with a conflict graph and exclusive alternatives. Lock selections and exclusions as hard constraints. Human edits rerun all validation and produce a new immutable design version.

## 11. Optimisation and Claude loop

No assumption of submodularity, monotonic benefit or global optimality. Objective is a versioned normalised score: modelled event damage where valuation coverage is sufficient; otherwise exposure-depth/area/buildings with explicit weights. Constraints can protect selected assets and limit local worsening. Record objective mode and weights in the plan. Do not let monetary coverage changes silently change the objective halfway through a search.

Algorithm:

1. Compute a reusable baseline for every chosen optimisation scenario.
2. Evaluate locked-only, empty-when-feasible, Claude-proposed and simple hydrological heuristic plans.
3. Enumerate feasible single additions to the current incumbent; evaluate actual combined-plan simulations and choose improvement per incremental cost with stable tie-breaking.
4. Recompute marginal effects after every selection; do not reuse stale lazy-greedy upper bounds.
5. Evaluate feasible removals, swaps and selected pairs, including candidates with weak singleton benefit, to capture interactions. Maintain several diverse feasible incumbents if resources allow.
6. Use a coarse grid only for explicit screening; reevaluate shortlisted candidates and final alternatives on the declared full grid. Track rank reversals and never display coarse-only scores as verified fine results.
7. Send actual results and constraints to Claude for a bounded revision; evaluate the revised design exactly like every other candidate.
8. Rerun the best feasible candidate with full output and wetness/rainfall robustness scenarios; retain the baseline if no plan improves the declared objective.

Search budget limits evaluation count, elapsed time and API cost, not the physical duration of individual completed runs. A timed-out simulation cannot be scored as a completed low-damage run. Deterministic seeds and tie rules enable repeats; cross-device float differences use tolerances. Cache key includes bundle, initial state, rain, boundaries, drainage, solver configuration, design and fidelity—not only selected parcel IDs.

An initial eight-second target profile may use a small candidate pool, prepared data and GPU screening; the final performance report must state pool size/grid/storm duration and include all required final evaluation time. The general product supports larger pools with progress. Quality can be measured against exhaustive enumeration on tiny sets and simple non-AI baselines; no guaranteed approximation ratio is claimed.

## 12. Uncertainty and model checks

At minimum compare dry/base/wet antecedent states, a rainfall-depth sensitivity within sourced bounds, plausible drainage assumptions and cost/first-floor uncertainty. Reuse paired parameter samples between baseline and plan so changes reflect design effects. Provide central/sensitivity outcomes and flag plans whose ranking reverses. Separate optimisation scenarios from held-out stress tests to reveal overfitting.

Track numerical order/grid sensitivity, model-reference agreement and real observation agreement independently. Failure of observational validation does not become success because the GPU agrees with a CPU implementation of the same approximation. Report what was checked, against which case, and with what tolerance.

## 13. Initial implementation defaults

These are explicit project defaults to validate, not universal hydraulic constants or empirical findings. Persist overrides with every run.

- Gravity: 9.80665 m/s². Numerical dry-depth regularisation: initially 1e-5 m; use separate 0.01 m visual wetness threshold. Water below the visual threshold still exists in the physical ledger.
- Exposure view: initial depth thresholds 0.10, 0.30 and 0.50 m; building amber/red defaults use 0.10/0.30 m exterior depth as screening indicators. Actual monetary damage uses first-floor exposure and curves, not these colour thresholds. User may change thresholds with their values always visible.
- Output: 60 simulated seconds per full lossless replay frame by default, plus exact forcing/end times. Run per-cell maximum depth/eta accumulation at every accepted solver step so peaks between replay frames are not lost. Publish running metrics at a bounded wall-clock cadence. Adaptive/finer output is allowed without changing the physical solver.
- Recession: start with at least the storm duration, minimum one hour; continue or flag incomplete drainage when residual storage or late downstream peaks make this insufficient. Never truncate baseline and plan differently to improve the comparison.
- Default objective: if at least 90% of buildings have usable valuation/curve inputs, minimise normalised event loss and use physical exposure then cost as tie-breakers. Otherwise minimise `0.5*D/max(D0,1 m³) + 0.3*B/max(B0,1) + 0.2*A/max(A0,1 m²)`, where D is the sum of cell area times excess peak depth above 0.10 m, B is count of buildings with exterior exposure above 0.10 m, A is area with peak depth above 0.10 m, and suffix 0 denotes baseline. D is an exposure proxy, not instantaneous stored-water volume. Record the automatic choice before planning; users can select a supported alternative objective.
- Local adverse changes: flag increases >=0.05 m in building exterior peak depth and newly crossed screening thresholds. Protection of specific sites is a user-selectable hard constraint with an explicit allowed increase; ordinary flags do not secretly change feasibility.
- Claude: at most two proposal/revision rounds in the default budget; retries are bounded and do not reset the total budget. Optimisation seeds use explicit stored integers and stable candidate-ID ordering.
- Profiles may set candidate-evaluation/time budgets; incomplete simulations have no valid score. The eight-second goal does not impose an eight-second physics truncation or invent a completed robustness result.

Calibrate these engineering defaults through controlled tests and document any change. Local physical/material/design/cost values come from catalogs and sources, not from the defaults above.
