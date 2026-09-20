# Shared scenario contract and capability assessment

Implemented September 15, 2026. This increment adds a canonical Python model,
exported JSON Schema and generated TypeScript interface for `ScenarioSpecV2`.
The browser validates against that schema before scenario dispatch. Both runtimes
also validate the same cross-field physical rules against shared fixtures.

The envelope includes engine ID, grid dimensions/spacing, coordinate and datum
metadata, bundle identity, forcing components, storm intervals, coastal series,
inflows/outlets, requested capabilities and an optional executable input hash.
Unknown datum/provenance remains unknown. Opaque legacy bundle identifiers are
retained separately from the executable SHA-256; neither field grants data access.

Checks reject unknown properties, non-finite or invalid numbers, conflicting
component flags, missing sources, rainfall-integral errors, source times beyond
the run, duplicate/out-of-grid cells and overlapping coastal/inflow cells.
Object key order and optional nulls do not change physical equality.
Actual executable arrays, solid masks and input hashes are checked separately.

## Engine assessment

`packages/contracts/engine-capabilities.json` is the shared registry. Only the
existing `webgl2-hll` adapter is registered for execution. The CPU reference model
exists, but its cross-engine scenario execution adapter is unconnected. SFINCS
and SWMM remain unavailable; unsupported requests cannot silently fall back to
another engine. Required capabilities are derived from physical forcing as well
as explicitly requested features, so omitting a requested flag cannot bypass a check.

Authenticated `POST /api/v1/scenarios/assess` accepts the envelope and returns
compatibility, required/unsupported capabilities and reasons. It starts no jobs,
does not load bundle data and does not validate the supplied hash against storage.
Malformed physical contracts receive 422; valid but unsupported engine requests
receive a 200 assessment with `compatible: false`. No authentication returns 401.

The response explicitly states `data_validation: not_assessed` and
`observed_accuracy: unvalidated`. A compatible engine does not establish terrain
availability, datum alignment, source coverage, measured bathymetry or accuracy.
This endpoint is not a substitute for those forthcoming data admission checks.

## Comparison and export integration

New completed app comparisons attach the envelope to their evidence. The report
builder checks its engine/order, grid, executable input hash, coastal sources,
inflows, outlets and storm against the evaluated result before exporting it.
Legacy comparisons without an envelope still pass their original validation.
A failed evidence assembly clears completion and releases the UI's busy state.

## Verification

- 38 shared fixtures cover valid combinations, legacy identifiers, unsupported
  engines/capabilities and malformed sources in Python and TypeScript.
- 43 focused Python tests and 99 TypeScript contract/optimizer tests pass.
- All 14 exported schemas are synchronized; generated types typecheck.
- Live browser-generated all-source envelope is accepted by the authenticated
  API; the report rejects a changed storm envelope. Three controlled GPU/reference
  cases still agree within 0.0000005 m and restart exactly.
- Actual comparison worker retains all sources and 121 paired frames in the
  610-second controlled comparison. This remains numerical, not observed evidence.
- Three existing browser report regressions pass, including saved comparison
  restoration and exact coastal export reruns. A legacy-ID incompatibility found
  by this regression was corrected without weakening executable hash validation.
- Build passes; the existing large frontend bundle warning remains. The shared
  AJV validator adds frontend code, so no loading-performance improvement is claimed.

Live evidence: `artifacts/verification/scenario-contract-v2/browser-check.log`.
Structured results: `artifacts/verification/scenario-contract-v2/results.json`.
The restarted API also accepts opaque legacy bundle IDs. All five frozen
production solver file hashes still match the stabilization baseline.
Reproduce with the ordinary contract checks and
`scripts/verify_scenario_contract_browser.js` through Playwright CLI against the
running app. The script creates a temporary authenticated session but never logs
its token. It runs controlled verification without altering the selected map.

## Remaining work

This contract supports the current surface engine and prescribed forcing. It does
not yet represent a complete engine-neutral network, spatial rainfall, multi-edge
coastal boundary, UTC event catalogue, initial-state artifact or design catalogue.
Those additions require explicit versioned extensions and per-engine compilation.
The subsequent [data suitability screen](data-admission-v1.md) now checks bundle
metadata consistency and reports per-hazard evidence gaps. Verified physical
admission remains pending for real terrain, datum and forcing support, followed by
the separate rainfall/intervention and coastal validation tracks. No runtime
specialist solver or newly validated real-world accuracy is claimed.
