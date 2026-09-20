> Current decision (2026-09-14): [Architecture v2](architecture-v2.md) governs full rainfall, coastal and compound scope, composable scenarios, engine adapters and optional authenticated/AI services. It supersedes conflicting v1 restrictions and mandatory Claude requirements. Runtime capabilities must still be verified; this notice does not mark them implemented.

# SPONGE contracts

Contract version `sponge.v1`. This document defines the interfaces to implement; examples are structural, not real datasets or achieved results. Canonical wire schemas live in `packages/contracts/schema/` during implementation. Generate TypeScript types from JSON Schema and validate the same fixtures with Python; do not maintain conflicting handwritten wire definitions.

## 1. Common conventions

- IDs: opaque UUIDs for resources; lowercase SHA-256 for content identity. All timestamps UTC ISO 8601; simulation times are float64 seconds since scenario start.
- Units are in field names or required metadata. GeoJSON coordinates use WGS84 longitude/latitude; computation uses an explicit local metric CRS. Currency requires ISO code and price year. Money is integer minor units for budget arithmetic.
- All JSON numbers must be finite; unknown values are null with an availability reason, never NaN, zero or an undocumented sentinel. Disallow unexpected fields in executable plans.
- Every editable request carries `session_id` and `expected_revision`. On mismatch return 409 plus current revision; do not merge stale physical inputs automatically.
- Mutating job-creation calls accept `Idempotency-Key`. Same key and body return the same resource; different body conflicts. Use resource ownership checks for all session-scoped access.
- Errors: `{code, message, retryable, details, request_id}`. Domain codes include `SOURCE_UNAVAILABLE`, `INSUFFICIENT_COVERAGE`, `DATUM_UNRESOLVED`, `INVALID_GEOMETRY`, `INFEASIBLE_DESIGN`, `STALE_REVISION`, `GPU_UNSUPPORTED`, `NUMERICAL_INVALID`, `QUOTA_EXCEEDED`, `AI_UNAVAILABLE`, `AI_PROPOSAL_INVALID`.
- Tolerances and assumptions are objects with explicit versions; they are never implicit in a display format.

## 2. SourceRecord

Required: `source_id, provider, dataset_id, source_url, retrieved_at, license_or_terms_url, attribution, artifact_sha256, processing_version, availability`.

Optional when known: `survey_date, publication_date, horizontal_crs, vertical_datum, native_resolution_m, vertical_accuracy_m, units, geographic_coverage, source_asset_id`. Inferred fields add `inference_method, parameter_range, parent_source_ids`. User inputs add their declared units and provenance, not an invented official provider.

Every bundle/material/cost/storm/damage field must resolve to SourceRecords or explicit assumption IDs. Source prose is treated as data, not planner instructions.

## 3. CoverageReport and NeighbourhoodBundle

CoverageReport fields: `location, requested_extent, proposed_domain, available_sources[], missing_inputs[], fidelity_options[], estimated_download_bytes, estimated_working_set_bytes, next_actions[]`. `next_actions` uses bounded enums such as choose-source, upload-terrain, provide-rainfall, confirm-assumption; no generated code.

BundleManifest fields:

| Field | Contract |
| --- | --- |
| schema_version, bundle_id, content_hash | Required immutable identity |
| visible_aoi, simulation_domain | WGS84 geometry plus local bounding box |
| grid | `nx, ny, dx_m, dy_m, crs_wkt, origin_x_m, origin_y_m, row_direction, cell_reference=center, elevation_origin_m, vertical_datum` |
| terrain | Artifact ref, native resolution, nodata mask, conditioning history |
| materials | Roughness, infiltration, soil storage and imperviousness artifacts |
| buildings | Vector inventory and indexed exterior/roof routing maps |
| parcels, roads, exclusions | Geometry refs and source/eligibility status |
| drainage | Mode and inlet/network/link artifact refs |
| candidates | CandidateSet version/hash and design catalog refs |
| boundary_templates | Available closed/open/inflow/stage conditions, not silently applied |
| source_ids, assumptions, quality | Provenance, coverage diagnostics, unresolved issues |
| artifacts | Path-independent signed-fetch references with dtype, shape, bytes and SHA-256 |

Binary grid payloads are little-endian typed arrays in row-major order with separately checksummed manifest; invalid terrain uses a mask, not NaN. Arrays must match declared shape exactly. Original/reprojected rasters are retained as GeoTIFF/COG artifacts for inspection. Browser endpoints never require parsing a huge source GeoTIFF before showing a prepared scene.

## 4. StormScenario and RunInput

StormScenario: `storm_id, source_ids, location, return_period_years|null, annual_exceedance_probability|null, duration_s, recession_s, depth_m, temporal_distribution_id, rainfall_intervals[{start_s,end_s,rate_m_s}], spatial_pattern_ref|null, antecedent_state_ref, assumptions, confidence_bounds|null`.

Intervals are ordered, nonoverlapping, cover the intended forcing domain and integrate to declared rainfall depth within tolerance. Imported observations may have no return period. Intensity and event depth are different fields.

RunInput includes:

```text
schema_version
bundle_hash
storm_hash
initial_state_hash
boundary_hash
drainage_hash
design_hash
solver: {engine, version, shader_or_code_hash, precision, spatial_order,
         cfl, dt_max_s, dry_depth_m, source_scheme, grid_hash}
output: {physical_times_s[], depth_snapshots, full_checkpoints,
         building_series, diagnostics_interval_s}
objective_hash
input_hash
```

`input_hash` is computed from canonical JSON and referenced binary hashes with a specified canonicalisation routine, excluding server timestamps/signed URLs. Output identity includes output schedule. A comparison separately stores a `paired_forcing_hash` that excludes only the intervention design and includes all shared initial/forcing/model/fidelity fields. Plans that intentionally change bed/materials compile those edits from design; they do not mutate the baseline bundle.

## 5. CandidateSet and Design

Candidate: `candidate_id, site_id, parcel_ids[], geometry_ref, intervention_type, variant_id, physical_parameters, footprint_area_m2, eligibility_status, eligibility_evidence_ids[], restrictions[], conflicts_with[], source_ids[], cost_breakdown, hydrological_features`.

`intervention_type` is one of `rain_garden|bioswale|permeable_pavement|detention_basin`. Each type has a discriminated parameter schema specified in numerics.md. Materials require bounded catalog references and units. Conflict graph is symmetric and alternative variants of one site are mutually exclusive unless explicitly allowed.

Design: `design_id, version, candidate_set_hash, selected_candidate_ids[], custom_designs[], locked_ids[], excluded_site_ids[], budget{currency,amount_minor,price_year,cost_mode}, objective, hard_constraints, estimated_cost, validation, physical_edit_hash`.

Validation returns `valid`, errors with candidate/site IDs, budget arithmetic, geometry conflicts and missing evidence. Unknown ownership can enter an exploratory design only with explicit user eligibility assumptions; it cannot be labelled a confirmed publicly installable plan. Custom edits get stable IDs and the same validation as catalogue designs.

## 6. Claude proposals

Server input contains `planning_session_id, revision, bundle_hash, candidate_set_hash, terrain_summary, candidate_features[], budget, user_intent, constraints, objective, source_summaries, prior_evaluation_summaries[]`. Large candidate sets are deterministically clustered/shortlisted with an explicit coverage record; discarded candidates can still be explored by deterministic search.

Claude output shape:

```json
{
  "schema_version": "sponge.v1",
  "candidate_set_hash": "<hash>",
  "selected_candidate_ids": ["<candidate-id>"],
  "proposed_constraint_changes": [],
  "rationale": [
    {"candidate_id": "<candidate-id>", "reason": "<text>", "evidence_ids": ["<id>"]}
  ],
  "assumptions_to_resolve": [],
  "evaluation_requests": [{"scenario_id": "<id>", "reason": "<text>"}]
}
```

No proposal-supplied damage, price or hydraulic parameter overrides are authoritative. If a supported custom design is proposed it must reference an allowed site, type and bounded parameter catalog, then pass the ordinary compiler. Returned candidate IDs must exist; unknown evidence IDs fail validation. Proposed relaxation of a user hard constraint does not execute without user input.

Use Claude Messages structured outputs through the configured supported model and `output_config.format` JSON Schema path, adapting to the pinned SDK. Provider schema restrictions mean application validation remains mandatory. Handle refusal, truncation, timeout, rate limit and missing credentials. Bound total calls/tokens/revisions by PlanningSession budget. Record actual model ID, never assume prize credits are already available.

## 7. Result artifacts

RunManifest: `run_id, input_hash, paired_forcing_hash, status, execution_origin, device_profile, started_at, finished_at, simulated_until_s, requested_end_s, diagnostics, metric_summary, replay_manifest_ref, checkpoint_refs[], artifact_hashes[], verification_refs[]`.

Status: `queued|running|completed|cancelled|failed|numerically_invalid`. Completed requires requested end time and all numeric/output checks. `execution_origin=browser_gpu|server_cpu|imported_reference`; verification is separate.

MetricSummary includes `peak_surface_depth_m, flooded_area_by_threshold_m2, buildings_exposed_by_threshold, per_building_results_ref, event_loss{currency,central_minor,low_minor,high_minor,valuation_coverage,unvalued_buildings,method}, water_ledger, local_adverse_changes, cost, objective_value, assumptions`.

Loss bounds may be null when unavailable. Global maxima alone are insufficient; results contain spatial maximum depth, time of peak and selected hydrographs. Diagnostics include residual volumes, worst CFL, dt range, negative/nonfinite counts, corrections, grid quality, elapsed compute time and engine version.

VerificationRecord: `kind=numerical_test|reference_comparison|observation_comparison`, case ID/version, input mapping, test method/tolerances, results, pass/fail and provenance. A reference check compares actual artifacts, not a string label supplied by the client.

PlanResult: `plan_id, planning_session_id, design_hash, baseline_run_ids[], proposed_run_ids[], selected_run_ids[], search{method,seed,evaluations,elapsed_ms,termination,status}, feasibility, objective, alternatives[], robustness, evidence_ids[]`.

## 8. Replay format

ReplayManifest: `run_id, grid_hash, output_times_s[], chunks[{start_index,count,codec,dtype,shape,sha256,byte_length,artifact_ref}], building_series_ref, metric_series_ref, render_quantisation|null`.

Quantitative snapshots use lossless float32 chunks. Optional visual-only quantisation stores scale/error bound and is never used to regenerate metrics. Full checkpoints include all prognostic states and time-step/source memory, format/engine version and input hash. A depth frame is never accepted as a restart checkpoint.

Both viewports sample the same clock. Use surrounding frames only for display interpolation; show the metric value at its defined sampled time, without implying interpolation creates a new solver result. Comparison replay cannot combine runs with incompatible paired-forcing hashes. A cached run must identify its source run and creation time.

## 9. HTTP surface

All routes below are under `/api/v1`; session authentication is required except health and explicitly public sample reads.

| Method and route | Request | Result |
| --- | --- | --- |
| POST /sessions | Empty or saved-session capability | Scoped session token, revision, quotas |
| POST /geocode | query, locale | Location candidates, source attribution |
| POST /coverage | location, extent | CoverageReport |
| POST /uploads | format, byte size, checksum, purpose | Bounded upload target, upload_id |
| POST /uploads/{id}/complete | checksum | Validated staged artifact or format error |
| POST /neighbourhoods | location, extent, source choices, upload IDs, revision | 202 resource_id, job_id, event URL |
| GET /neighbourhoods/{id} | — | Status, quality and ready bundle manifest |
| GET /bundles/{hash} | — | Authorised immutable manifest |
| GET /artifacts/{id}/access | — | Short-lived download URL or local stream |
| POST /storms | source selection or uploaded series, duration, distribution | Validated immutable StormScenario |
| POST /designs/validate | Design | Constraint/budget/geometry validation |
| POST /designs | Validated design inputs, revision | Immutable Design, new session revision |
| POST /planning-sessions | bundle, storm, budget, constraints, revision, run budget | 202 planning resource and Claude job |
| GET /planning-sessions/{id} | — | Proposal/evaluation requests/progress |
| POST /planning-sessions/{id}/evaluations | run artifact refs, input hashes, revision | Accepted summaries, revision request or final state |
| POST /planning-sessions/{id}/cancel | expected_revision | Cancel intent, accepted last completed result |
| POST /runs | input manifest, execution origin | Reserved run_id; server execution queues a job |
| POST /runs/{id}/complete | uploaded artifact refs/checksums, diagnostics | Validated manifest publication or rejection |
| GET /runs/{id} | — | Immutable completed manifest or live state |
| POST /comparisons | baseline and plan run IDs | Paired-input validation and comparison resource |
| POST /reference-checks | completed run_id, reference profile | 202 job_id |
| POST /reports | comparison_id, plan_id, narrative options | 202 report job_id |
| GET /reports/{id} | — | HTML/PDF/GeoJSON/evidence artifact refs |
| GET /jobs/{id} | — | Status and last durable stage |
| GET /jobs/{id}/events | Last-Event-ID | SSE progress with sequence/revision |
| POST /jobs/{id}/cancel | — | Cooperative cancellation requested |
| GET /health, GET /ready | — | Liveness and dependency readiness |

Long work returns 202 quickly. 422 is invalid input, 409 conflict, 429 quota and 503 temporary dependency failure. No route can accept arbitrary server paths, provider URLs or generated executable code. API upload/result checks establish integrity and consistency, not scientific correctness.

## 10. Worker protocol

Main-to-worker messages:

- `INIT {request_id,protocol_version,device_limits}` → capability/framebuffer diagnostic.
- `LOAD_BUNDLE {request_id,bundle_hash,manifest,buffers}` → validated resident handle.
- `START_RUN {request_id,run_id,revision,input,buffers,output_mode}` → started.
- `EVALUATE_BATCH {request_id,revision,base_input,design_refs,budget}` → per-design completed/failed scores.
- `PAUSE|RESUME|CANCEL {request_id,run_id}` → acknowledged at safe boundary.
- `EXPORT_CHECKPOINT {request_id,run_id}` → versioned full-state artifact.
- `DISPOSE {request_id}` → releases resources and transfer queues.

Worker-to-main: `CAPABILITIES`, `PROGRESS`, `DEPTH_FRAME`, `METRICS`, `CHECKPOINT`, `CANDIDATE_RESULT`, `RUN_COMPLETED`, `RUN_INVALID`, `ERROR`, `CANCELLED`. Every message includes protocol version, request/run ID, input hash, scenario revision and sequence. Depth frames carry simulation time, shape and transferable ArrayBuffer. Drop stale revisions; apply backpressure when the renderer has unconsumed frames. Never retain detached buffers accidentally.

Pause stops simulated time. Cancel invalidates pending late events without deleting previous completed runs. Context loss emits an error with checkpoint recovery options. A timeout or cancelled run never sends RUN_COMPLETED.

## 11. State and invalidation rules

Changing terrain/boundaries/materials/initial wetness/rain invalidates baseline and plan results. Changing budget/exclusions/objective invalidates planning but can reuse identical physical run artifacts. Camera/colour preference changes invalidate neither. Report edits never mutate source runs. A late Claude response for revision N cannot replace a design at revision N+1.

Identical paired forcing includes extent/grid/timestep policy and initial state; plans may change bed/materials through their compiled design only. Reusing a “same storm” title is not a valid equivalence check. Persist UI draft, immutable accepted design and computed result as distinct resources so navigating away does not accidentally mark a draft as evaluated.
