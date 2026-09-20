# Devpost draft — SPONGE

## Tagline

See how a neighbourhood holds water, test green infrastructure with live physics, and export the evidence—not just the animation.

## Inspiration

Flood-resilience planning is full of disconnected inputs: terrain, building footprints, rainfall evidence, drainage assumptions, candidate projects and budgets. Communities need an understandable way to explore those relationships without pretending that incomplete public data is an engineering survey. SPONGE was built to make early stormwater tradeoffs visible, reproducible and honest.

The problem is concrete in the prepared Philadelphia example. The Philadelphia Water Department says dense urban development needs decentralized, creative green-stormwater planning, and its Green City, Clean Waters program combines green infrastructure with conventional upgrades to reduce stormwater entering combined sewers. SPONGE does not claim to replace that engineering workflow; it makes the early alternatives easier to question and compare.

## Earth Forward impact

SPONGE follows a defensible impact pathway: make neighbourhood-scale runoff visible, screen several green-infrastructure portfolios under identical storms, expose adverse changes and missing evidence, then hand an auditable shortlist to the people who can survey and engineer it. The environmental outcome is not claimed in advance. A real pilot must still measure whether this workflow reduces analysis time or improves which sites advance to professional review.

## What it does

SPONGE loads a sourced neighbourhood terrain bundle and renders simplified 3D buildings, streets, vegetation and mapped water. A user can configure rainfall, external inflow, prescribed coastal levels or supported combinations, then run a WebGL2 shallow-water simulation in the browser.

Users can add rain gardens, bioswales, permeable pavement and detention basins with finite storage, infiltration, clogging and optional release assumptions. A bounded physics search evaluates feasible portfolios under a budget against the same baseline storm. The synchronized comparison preserves remaining flooding and local worsening rather than hiding them.

The evidence export contains readable HTML, exact reproducible scenario JSON, selected-design GeoJSON, assumed cost CSV and a SHA-256 manifest. If building values, first-floor elevations or validation data are absent, SPONGE says the estimate is unavailable instead of manufacturing one.

## Why it is original

Flood dashboards and stormwater models already exist, so our claim is deliberately narrow. EPA SWMM is a powerful professional drainage model, and prior hackathons have produced flood digital twins and risk dashboards. SPONGE's distinctive contribution is the interaction between five things in one judge-accessible workflow:

1. live browser shallow-water physics rather than a prerecorded flood overlay or opaque score;
2. editable finite-capacity green infrastructure whose saturation, overflow and return flows remain in the ledger;
3. budget search that evaluates every alternative against the same disclosed rainfall-sensitivity ensemble;
4. synchronized baseline/planned replay that preserves residual risk and local worsening; and
5. tamper-checked exports that distinguish software correctness from missing real-world validation.

We do not claim that flood simulation, green infrastructure or digital twins are new by themselves.

## How we built it

- React, TypeScript, Vite and Deck.gl for the interface and city view.
- WebGL2 fragment-shader HLL shallow-water solver in a worker, with first- and second-order reconstruction.
- Python/NumPy reference solver and independent numerical fixtures.
- FastAPI, PostgreSQL/PostGIS, Redis and RQ for sessions, immutable bundles and preparation jobs.
- Rasterio, PyProj and Shapely for geospatial ingestion and validation.
- Docker Compose production stack with migrations, persistent data and an offline hero bundle.

The planner is deterministic and simulation-backed; no runtime LLM or model API key is required.

## Challenges

The hardest challenge was keeping the visual experience honest. Water could not simply disappear into a “green” polygon, so every intervention needed finite storage, overflow and ledger accounting. Baseline and proposed runs also had to share identical forcing and initial conditions. We added exact input hashes, report reconciliation and rejection paths for incomplete or altered runs.

Real geospatial data introduced a second challenge: coverage, resolution, survey dates and vertical references are not interchangeable. SPONGE reports these separately and keeps observed accuracy unvalidated unless evidence supports it.

## Accomplishments

- Live browser shallow-water physics with CPU parity and conservation checks.
- Four intervention types, nonlinear controls, bounded budget search and synchronized replay.
- Rainfall, external-inflow, coastal and compound scenario contracts.
- Interrupted-storm recovery, GPU-context recovery and duplicated-tab isolation.
- Reproducible, tamper-checked evidence exports.
- Clean production deployment with a non-root image, migrations, persistent storage, worker-aware readiness, request limits and security headers.
- Final verification: 334 Python tests, 136 TypeScript tests and 46 real-browser/GPU tests, plus dependency audits, schema checks and a rebuilt production-container smoke test.

## What we learned

Numerical correctness, agreement with a reference and agreement with real observations are three different claims. A conservative ledger and a passing dam-break fixture are important, but neither proves a neighbourhood forecast. We learned hydrodynamic finite-volume methods, WebGL2 shader constraints, CRS and vertical-datum handling, robust optimisation, accessible 2D/3D interaction, browser recovery semantics and production operations. The most important product lesson was that saying “unknown” is often harder—and more useful—than displaying a confident-looking number.

## What is next

Next steps are a pilot with a community or stormwater practitioner, observed-event calibration, surveyed catchments and drainage, parcel/utility eligibility, dated local construction quotes, defensible building inventories and engineered facility geometry. The pilot success measure is whether SPONGE shortens early alternatives review or changes which candidate sites are sent to professional study without raising false confidence.

## Work-period disclosure

SPONGE began during the NextStep Hacks build period. Product architecture and planning started on September 10, 2026, followed by implementation, numerical verification, browser QA, production hardening, and submission preparation through September 20. No SPONGE implementation existed before the event. Earlier files in the workspace concerned a separate product-research concept and were not reused as SPONGE code or presented as this submission.

The project was built by Aditya Jevoor with Codex as an AI engineering collaborator. Codex assisted with planning, implementation, debugging, auditing, testing, and documentation; the entrant directed product decisions and accepts responsibility for the submitted work and claims.

## Submission fields still requiring the entrant

- 3–5 minute narrated video URL;
- team members and individual eligibility confirmation;
- final screenshots and acceptance of Devpost terms.

Prepared links:

- repository: https://github.com/jozai193/sponge-flood-planner
- judge tour: https://susan-absorption-sand-implied.trycloudflare.com/?tour=1
