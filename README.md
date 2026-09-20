# SPONGE

SPONGE is a deployable neighbourhood stormwater screening application. It combines sourced terrain and building footprints, an in-browser WebGL2 shallow-water solver, editable green-infrastructure assumptions, budgeted physics search, synchronized comparison replay, and reproducible planning exports. Full design and scientific boundaries: [architecture package](docs/hackathon-build/README.md).

The software is release-engineered for an **exploratory screening** use case. It is not a calibrated flood forecast, an engineering design, or a substitute for surveyed drainage, parcel eligibility, observed-event validation, or professional review.

**Public judge demo:** https://alt-lay-executed-casual.trycloudflare.com/?tour=1

## Run locally

Prerequisites: Node.js, pnpm, Python 3.11 for the bootstrap, and Docker Desktop with Linux containers. Setup installs a project-local Python 3.12 runtime and locked dependencies.

```powershell

./Setup-SPONGE.ps1

./Start-SPONGE.ps1

```

Open http://127.0.0.1:5173. On a fresh workspace, prepare a public sample:

The root URL opens the cinematic project landing page. Direct bundle links open
the simulator; append `?intro=1` to replay the landing or `?intro=0` to skip it.

```powershell

.venv/Scripts/python.exe -m scripts.prepare_neighbourhood --public-sample

```

`Stop-SPONGE.ps1` stops only processes recorded by the launcher. `Doctor-SPONGE.ps1` checks dependencies without printing keys. Docker volumes and prepared datasets are preserved.

## Production container

The production image serves the compiled web app and API from one origin, runs preparation work in a separate worker, runs durable-job reconciliation and reference-safe retention in a maintenance service, applies database migrations, and includes the immutable Spring Garden demo bundle. Set a strong database password before starting it:

```powershell

$env:SPONGE_DB_PASSWORD = '<generate-a-long-random-password>'
$env:SPONGE_TRUSTED_HOSTS = 'sponge.example.org'
docker compose -f infra/compose/compose.production.yaml up --build -d --wait
$env:SPONGE_BASE_URL = 'http://127.0.0.1:8080'
pnpm smoke:production

```

The default published port is restricted to `127.0.0.1:8080`; put an HTTPS reverse proxy in front of it for internet access. See [production deployment](docs/production-deployment.md) for backups, host/origin configuration, health checks and the remaining scientific limits.

The verified judge route currently fronts the isolated production stack with HTTPS.
An AWS reference deployment with a static Elastic IP, encrypted storage, and automatic
TLS is documented in [AWS judge deployment](docs/aws-judge-deployment.md).

## Verified release functionality

- Python reference HLL solver with first-/second-order reconstruction, rainfall, finite infiltration, roof allocation, coastal/external boundaries and a complete water ledger.

- Browser WebGL2 first-/second-order HLL engine and worker; CPU parity, closed-wall conservation, nonlinear control convergence, coastal refinement and restart checks.

- General address search and queued preparation, country-derived ISO planning currency, real terrain/building ingestion, versioned bundles, validated GeoTIFF/GeoJSON/rainfall imports, and an immutable offline demo bundle.

- Interactive 3D terrain/buildings, rainfall/external/coastal/combined scenarios, physical-time progress, recovery checkpoints and exposure metrics.

- Four finite-capacity intervention models, source-linked parameter guidance, draw/place/edit/delete/lock controls, protected-area screens, itemised user-sourced costs, controlled releases/underdrains, robust bounded budget search, paired replay and tamper-checked evidence exports.

- Production container, non-root runtime, migrations, PostgreSQL/Redis persistence, live-worker readiness, session-scoped access, request limits, security headers, locked dependencies and CI.
- Expiring sessions with transparent browser renewal, a PostgreSQL-backed job outbox, atomic content-addressed bundle publication, stale-job reconciliation and reference-safe artifact retention.
- CSP-safe precompiled scenario validation and a production-browser smoke gate that rejects blank pages, console errors, missing judge-tour content and an unusable prepared demo.

NOAA Atlas 14 point-frequency storms are available with explicit confidence, temporal-pattern and antecedent-wetness assumptions; see [design storms](docs/design-storms.md). Robust planning applies the identical disclosed rainfall-sensitivity ensemble to every alternative, and the report can be printed/saved as PDF with a companion evidence manifest. Surveyed drainage/parcel constraints, defensible valuations, observed-event accuracy and engineered facility sizing remain location-specific evidence needs rather than hidden defaults. Current terrain materials, costs and eligibility are explicit assumptions; monetary damage is unavailable unless a building has the required value, floor elevation and curve. See [release evidence](docs/release-evidence.md) and [current implementation status](docs/hackathon-build/implementation-status.json).

## Checks

```powershell

.venv/Scripts/python.exe -m pytest tests/contracts tests/numerics -q

.venv/Scripts/python.exe -m ruff check services scripts tests

.venv/Scripts/python.exe -m mypy

pnpm test:contracts

pnpm test:optimizer

pnpm test:gpu

pnpm test:e2e

pnpm test:browser

pnpm build

pnpm audit --prod

```

Browser tests require the local API/data services and Playwright Chromium (`pnpm exec playwright install chromium`). Numerical verification does not establish observed site accuracy. Consult [build notes](docs/hackathon-build/build-notes.md) for implementation history and evidence.

## Current planner mode

Codex is the development agent. The application requires no Claude or other runtime LLM and no model API key. Add explicitly assumed candidate designs in the editor, then use **Plan with physics** to search subsets within the budget (24 completed evaluations maximum). **Compare selected design** compares all applied designs against the baseline. Both paths record an identical storm and recession at 121 shared timestamps and provide two linked cameras and one replay slider.

The objective is the worst value across the disclosed 80/100/120% rainfall-depth sensitivity ensemble of the sum of peak depth above 10 cm times cell area outside all submitted candidate areas. The replay shows the point storm. These factors are sensitivities, not probabilities, and the score is not monetary damage or simultaneous water volume. Evaluations exceeding 0.1% relative mass-balance error are rejected. Search is bounded and does not guarantee a globally optimal plan. Cost, eligibility and facility parameters remain sourced or explicitly user-entered assumptions.

## Broader location data

**Flood scenario → Combined flood sources** now supports simultaneous rainfall, external inflow and prescribed coastal levels. Previous presets remain available. See [composition behavior and verification](docs/hackathon-build/scenario-composition.md); these combinations remain exploratory.

Use **Data & assumptions → Broaden neighbourhood data** to acquire global evidence, create enriched simulation revisions, or import surveys and terrain. See [data expansion](docs/hackathon-build/data-expansion.md) for source coverage, optional access configuration, server caches, import formats and explicit scientific limits.

For missing addresses, add a city/region or paste latitude, longitude. See [location search](docs/hackathon-build/location-search.md) for the free search providers, coordinate fallback and coverage limits.

Named search results carry their country currency into the prepared bundle,
budget, intervention costs, replay and evidence exports. Amounts are interpreted
as user-entered local values and are never silently exchange-rate converted.
Raw coordinates without country metadata use a clearly labelled USD fallback.

## Facility releases and returns

The exploratory editor now supports graded bioswales, pavement clogging, controlled surface releases and subsurface underdrains. Choose a receiving area or explicit external discharge. Compare runs to inspect surface/subsurface storage and exported water at the replay time. These are assumed linear storage controls, not engineered pipe or spillway sizing. See [facility model and verification](docs/hackathon-build/facility-controls.md).

Surface controls also offer orifice and sharp-crested spillway ratings, with tested timestep convergence and a 0.2-second maximum step for nonlinear designs. Water display now includes depth color, shorelines and solver-velocity arrows. See [equations, verification and graphics limits](docs/hackathon-build/nonlinear-ratings-and-water.md).

## Recovery and solver order

Stopping a storm saves its full state in this browser. After reload, choose **Restore saved storm**, then **Resume stopped storm**. Changing inputs starts a new scenario; use **Discard saved storm** to remove recovery data. Storage failures are reported and in-tab resume remains available. Active storms also save checkpoints at computation-batch boundaries, approximately every 15 wall-clock seconds. After an interruption, restore the last saved state; progress since that snapshot may be lost.

New neighbourhood loads use second-order spatial reconstruction, checked against CPU lake, smooth-wave and dry-front fixtures. Original first-order inputs remain supported. These numerical checks do not establish observed flood accuracy.

## Saved comparisons

Completed comparisons automatically save evaluated inputs, candidate and selected designs, result evidence, neighbourhood context and both replay timelines in this browser. After reload, choose **Restore saved comparison**. **Discard saved comparison** removes that saved comparison without deleting the storm checkpoint. Invalid or inconsistent stored results are rejected. Saving failures leave the current comparison available in the open tab.

Independently opened and duplicated tabs have separate saved records. Reload preserves the tab's records. Browser Web Locks provide exclusive ownership; a duplicated tab copies the last available saved records before continuing separately. Closed-tab discovery, a multi-project library and persistence of unfinished edits remain incomplete.

## Detailed Philadelphia preview

[Open the updated Spring Garden sample](http://127.0.0.1:5173/?bundle=2c607f51e1a064fc76ee6f5585cbc343358d0e9a39ead1a2806643e21cae37ba) after preparing that bundle locally. The current local sample has 686 source-reported approximate building heights and 742 mapped tree positions, with illustrative 3D crowns. Satellite mode projects overhead imagery onto simplified roofs. Model mode uses shaded geometry and directional shadows; Eco reduces graphics work. [Rendering evidence and limits](docs/hackathon-build/city-fidelity.md) distinguish this visualization from an exact textured city reconstruction. Older saved bundles remain available.


## Browser graphics verification

Run `node scripts/check-browser-gpu.mjs` to compare the bundled test browser with installed Chrome. The renderer string identifies software rendering versus a hardware adapter; the presence of a discrete GPU in Windows alone does not prove the browser uses it.

To run tests with installed Chrome in PowerShell:

```powershell
$env:SPONGE_BROWSER='chrome'
node node_modules/@playwright/test/cli.js test tests/browser/gpu.spec.ts tests/browser/app.spec.ts tests/browser/report.spec.ts
Remove-Item Env:SPONGE_BROWSER
```

This selects the browser for the test run only. It does not change Windows GPU settings. Default tests continue to use bundled Chromium. Prepared-location benchmark methodology and both renderer results are recorded in `docs/hackathon-build/location-performance.md`.


## Recurring Docker Windows socket startup error

On this machine Docker Desktop 4.90.0 fails to reopen sailor-ingest.sock even after its own graceful restart. If Docker is unavailable with that specific inaccessible-socket error, run `.\scripts\Repair-DockerSockets.ps1`, wait for Docker readiness, then `.\Start-SPONGE.ps1`. The guarded repair preserves and recreates only runtime socket directories, with timestamped backups; it never resets containers, volumes, images or settings. It exits without changes when Docker is healthy. This is a recovery workaround for an unresolved Docker/Windows defect, not a permanent upstream fix. Stop-SPONGE.ps1 leaves shared Docker running and should be used for routine project shutdown.
