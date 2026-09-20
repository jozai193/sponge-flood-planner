> Current decision (2026-09-14): [Architecture v2](architecture-v2.md) governs full rainfall, coastal and compound scope, composable scenarios, engine adapters and optional authenticated/AI services. It supersedes conflicting v1 restrictions and mandatory Claude requirements. Runtime capabilities must still be verified; this notice does not mark them implemented.

# SPONGE product requirements

All twelve epics are required for the full product. IDs are stable references for implementation and tests. Numerical tolerances live in [validation.md](validation.md), not in UI components.

## E01 — Address and neighbourhood preparation

User submits an address or selects a point/extent; sees location candidates, data preparation progress, and a real neighbourhood.

- A01: A non-hero address goes through geocoding, coverage lookup, data retrieval and a new versioned bundle without editing source code.
- A02: Display terrain native resolution, simulation resolution, survey date when known, footprint coverage and input gaps. Upsampling never changes native-resolution claims.
- A03: GeoTIFF terrain and GeoJSON geometry imports pass CRS, unit, bounds, validity and size checks; incomplete coverage returns actionable input requests.
- A04: An immutable hero bundle opens without live third-party tile or GIS API availability. Global search is not confused with global high-resolution modelling coverage.

## E02 — Real 3D scene and inspection

- A05: Terrain, water and buildings share the same horizontal/vertical reference; map picks resolve to the expected cell/building/site.
- A06: Building footprints are real sourced geometry. Assumed display heights are distinguished from measured heights and never affect damage exposure implicitly.
- A07: Orbit, zoom, pan, terrain inspection, address search and readable 2D mode work. Colour is accompanied by numeric depth and accessible labels.

## E03 — Storm scenarios

- A08: User selects return period, duration, temporal distribution and antecedent wetness; can import a rainfall time series. The 100-year option is fully implemented.
- A09: Show source, location, depth, duration, annual exceedance probability and confidence interval where supplied. Inputs conserve the published rainfall total after discretisation.
- A10: A before/after pair has exactly the same forcing, initial conditions, boundary assumptions and material baseline except for explicit interventions.

## E04 — GPU surface hydrodynamics

- A11: WebGL2 solver evolves depth and momentum from terrain, rain, roughness, infiltration, infrastructure and boundaries. Numerical verification gates pass.
- A12: Wetting/drying, roof runoff, edge fluxes, inlet limits and GI overflow preserve the water ledger. Instability invalidates results instead of producing a plausible-looking scene.
- A13: Live progress, pause/cancel/reset, full storm and recession run, device capability reporting and CPU reference fallback work.

## E05 — Four infrastructure models and manual design

- A14: Rain gardens, bioswales, permeable pavement and detention basins each have finite capacity, distinct material/geometry effects, source-backed parameter ranges and cost line items.
- A15: Draw/place/edit/delete/lock infrastructure; reject prohibited overlap, slopes, dimensions, budget violations and missing eligibility with clear reasons.
- A16: Saturation, overflow and maintenance/clogging scenarios change modelled performance. Identical physical designs produce identical compiled intervention inputs independent of UI history.

## E06 — Eligible parcels and constrained optimisation

- A17: Candidate IDs link to geometry, parcel/eligibility evidence, physical design, costs and mutually exclusive alternatives.
- A18: Search evaluates nonlinear combined plans against the same baseline; honours budget, locked sites, exclusions and protected-area constraints.
- A19: Report feasible/best-found/exhaustive-small-set status, elapsed time and evaluations. No submodularity or global-optimum claim without proof.
- A20: Disabling a selected site triggers a new valid plan or explains infeasibility. Zero budget returns no purchases and baseline-equivalent physics.

## E07 — Planning proposals and optional AI assistance

- A21: A provider-neutral proposal interface accepts catalogue IDs, constraints and source references. Deterministic/manual planning is the default; optional live AI proposals disclose provider/model and remain distinct from evaluated plans.
- A22: Deterministic validation checks IDs, dimensions, arithmetic and constraints; invalid proposals never execute.
- A23: Actual solver results guide bounded search or optional AI revision. Every revised candidate is evaluated with identical scenario inputs; no generated explanation supplies metrics.
- A24: Missing credentials, timeouts or quotas preserve manual and deterministic planning. If an AI feature is enabled, its live path, provenance and failure behavior must be verified; a specific AI vendor is not required.

## E08 — Damage and decision metrics

- A25: Building loss derives from exterior water level relative to first-floor elevation, sourced or explicit assumed building attributes and versioned depth-damage curves.
- A26: Animated counter uses running maximum per-building loss, not sums of repeated instantaneous damage. Final totals match exported calculations.
- A27: Show affected buildings, area above configurable depth, peak depths, storage/infiltration/outflow and local adverse changes alongside losses.
- A28: Monetary ranges show scenario/assumption sensitivity and valuation coverage. Insufficient inventory returns partial or unavailable totals, never an invented complete estimate.

## E09 — Synchronised comparison

- A29: Both viewports share camera, storm clock, colour/depth scale, rainfall and exposure thresholds; replay can scrub and pause.
- A30: Building colours and losses correspond to stored results at that time. Display interpolation is never used to recompute quantitative metrics.
- A31: Compare baseline, submitted proposal and best evaluated plan; label AI origin when applicable. Preserve remaining flooding and locally worsened outcomes.

## E10 — Evidence and report export

- A32: Export readable municipal planning HTML/PDF, selected GeoJSON, line-item costs, scenario JSON and an evidence manifest with source/run/model hashes.
- A33: Templates or optional AI write narrative from verified metric IDs; deterministic tables supply numbers. Failed/incomplete runs cannot appear as successful results.
- A34: Grant-style report has assumptions, alternatives, residual risk, maintenance and next data needs. It does not assert grant eligibility or act as a submitted application.

## E11 — Persistence, reliability and access

- A35: Reload restores prepared neighbourhoods, inputs, plans and completed runs; hashes prevent stale AI/results replacing edited scenarios.
- A36: Interrupted preparation and computation are resumable or restartable; completed immutable artifacts remain consistent.
- A37: Public judge session needs no account for the prepared demo. Private imports and editable sessions remain scoped; API keys stay server-side and public compute has quotas.
- A38: Local launcher and hosted configuration reproduce the core journey; unavailable GPU/provider services explain their state and expose valid alternatives.

## E12 — Performance, quality and presentation

- A39: Record loading, simulation, optimisation, API latency, memory and frame-rate measurements on identified devices, using the protocol in validation.md.
- A40: Target smooth 60 fps replay and an eight-second warm planning comparison. Show measured progress when a new location or higher-fidelity job takes longer; cached replay is labelled.
- A41: Run a live non-default edit during the demo. No fabricated savings, hidden simulation failure or predetermined “winning” plan.
- A42: Deliver documented installation, reproducible datasets, test evidence, demo recording/script, third-party attribution and Devpost-ready draft materials. Public submission is a separate user action.

## Submission proof points

Address-to-terrain ingestion; live GPU solver; all four GI types; evaluated proposals and solver feedback; budget/exclusion edit; synchronised replay; computed economic and physical outcomes; limitations and reference checks; accessible no-login demo. Every statement is tied to an acceptance test or labelled a target.

## E13 — Coastal and combined hazards (architecture v2)

- A43: Retain the exploratory coastal workflow and add a versioned scenario composition for rainfall, external inflows and coastal stages. Unsupported combinations produce explicit errors; no source is silently dropped.
- A44: Coastal inputs identify boundary segments, datum/epoch transformation, time coverage, bathymetry/channel needs and measured/modelled/assumed provenance. Missing support cannot silently become a closed wall or nearest-node fill.
- A45: Engine capabilities govern runnable scenarios and designs. Cross-engine reference comparisons retain native grids, engine/build hashes and separate validation claims; a common display does not imply equivalent equations.
- A46: Numerical, reference, observed-event and intervention evidence is scoped by hazard/model/input cohort. Retain dry misses and unresolved observations; independent extent and timing evidence is required for those claims.
- A47: Two-way drainage/network exchange must conserve whole-system water, count each storage once, and pass reversal, tailwater and timestep checks before production use. Existing experimental coupling is not assumed eligible.
- A48: Robust planning compares identical scenario ensembles, exposes local worsening and no-benefit plans, and preserves all four GI types. Coastal risk reduction is never assumed from rainfall intervention performance.
- A49: Data availability, API access, geographic coverage and validation status are independently reported in the UI and exports. Keys remain server-side; authenticated services are optional adapters with explicit quotas and failure behavior.

A43–A49 are new pending requirements, not completed capabilities. Existing A01–A42 evidence is retained. Implementation priority follows architecture v2; paused release work remains separate.
