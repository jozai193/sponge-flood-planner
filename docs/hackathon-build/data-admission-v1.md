# Scenario data suitability screening

Implemented September 15, 2026. SPONGE now assesses the selected sources against
the loaded terrain bundle before ordinary simulation and planning dispatch. The
sidebar exposes the findings and next data needs. Rainfall, external inflow,
coastal levels and parameterised outlets retain their separate checks; combined
scenarios receive all applicable checks.

This is the first metadata screening increment of physical data admission. It
does not certify a site, inspect new survey data or improve the flood equations.

## What is checked

- Bundle identity, grid dimensions, spacing, horizontal reference, recorded
  terrain datum and local elevation offset must agree with the scenario.
  Mismatches are unsupported and stop app dispatch.
- Terrain provider/source presence and recorded native resolution are reported.
  Fine simulation cells cannot substitute for native source resolution.
- Survey epoch and catchment completeness remain needs-data because this pipeline
  has no admitted evidence for them. A recent download is not a recent survey.
- Coastal scenarios flag unresolved datum/offset metadata, unverified datum
  transformations, spatial boundary coverage, bathymetry and hydraulic structures.
  The screen explicitly reports whether the final level is held after the series
  ends. Configured boundary cell count is not a coverage percentage.
- Rainfall and inflow timing still pass the shared scenario contract. Event
  provenance, spatial representativeness, antecedent wetness and calibration
  remain unverified. Outlet checks describe the current parameterised model.

States are `exploratory`, `needs_data` and `unsupported`. Missing scientific
support allows exploratory use with visible reasons; identity mismatches do not.
There is deliberately no path from self-reported `validated` quality strings to
a ready/accurate verdict. `observed_accuracy` remains `unvalidated`.

## API and exports

Authenticated `POST /api/v1/scenarios/assess-data` takes the existing ScenarioSpecV2.
It resolves the bundle through the existing session ownership checks, reads its
stored manifest and returns separate engine and data assessments. It does not
accept a client-supplied manifest or access arbitrary paths. Missing/inaccessible
bundles return 404, malformed contracts 422 and unauthenticated requests 401.
The older `/assess` endpoint remains a capability-only check.

The browser assesses its loaded manifest locally, so this screen adds no network
round trip before a run. Python and TypeScript use one shared finding registry,
with cross-language fixtures checking identical results. Neither screen replaces
the existing array, solid-cell, storm or executable-hash checks.

Report HTML and scenario JSON recompute the assessment from evaluated scenario
metadata and exported provenance. They reject bundle/grid metadata mismatches
when the scenario identifies a bundle. Legacy reports without an envelope remain
readable and say data suitability was not assessed. Unbound synthetic fixtures
may export an unsupported metadata assessment without pretending to be real sites.

## Verification

- 119 TypeScript contract/optimizer tests and 63 focused Python tests pass.
- 19 shared data cases agree exactly between Python and the browser.
- Live authenticated assessment of the Spring Garden sample agrees with the
  browser. Changed grid spacing is unsupported; a missing bundle returns 404.
- UI panel and incomplete coastal configuration states were exercised through
  Playwright CLI, then rainfall mode was restored.
- A controlled GPU comparison exports data gaps in HTML and JSON; changing its
  exported bundle provenance is rejected.
- Three existing browser report regressions pass, including saved comparison
  restoration and exact coastal export replay.
- Typecheck and production build pass. Existing large frontend chunk warning
  remains; no performance or observed-accuracy improvement is claimed.
- All five frozen production physics files retain their stabilization hashes.

Evidence: `artifacts/verification/data-admission-v1/results.json`,
`python-results.json` and `browser-check.log`. Browser reproduction:
`scripts/verify_data_admission_browser.js` via Playwright CLI against the running
app. The script creates a temporary session without logging credentials.

## Next evidence needed

Add structured, independently checked survey dates, vertical transformations with
uncertainty, event provenance and spatial boundary support, plus terrain/water
geometry inspection. Admission of those sources needs substantive evidence and
tests; setting a metadata flag is insufficient. Historical flood accuracy,
specialist solver adapters and scientific calibration remain separate work.
Demo, release and submission work remain paused.
