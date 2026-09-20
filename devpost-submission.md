# SPONGE

## One-line Summary

See how a neighbourhood holds water, test green infrastructure with live physics, and export the evidence—not just the animation.

## Problem

Flood-resilience planning is split across terrain, building footprints, rainfall evidence, drainage assumptions, candidate projects, and budgets. Communities need a way to explore how those inputs interact without treating incomplete public data as an engineering survey or hiding uncertainty behind a confident-looking risk score.

## Solution

SPONGE is a neighbourhood stormwater screening application. It loads sourced terrain and building data, runs a WebGL2 shallow-water simulation in the browser, and lets users test rain gardens, bioswales, permeable pavement, and detention basins under identical storm conditions.

Users can manually edit designs or run a bounded, simulation-backed budget search. A synchronized baseline/planned replay preserves residual flooding and local worsening. The export package includes readable HTML, exact scenario JSON, selected-design GeoJSON, assumed cost CSV, and a SHA-256 evidence manifest.

When a required input is missing—such as surveyed drainage, parcel eligibility, building values, or observed-event validation—SPONGE reports that limitation instead of inventing a value.

## Why This Matters

SPONGE follows an Earth Forward impact pathway: make neighbourhood-scale stormwater behavior visible, screen green-infrastructure alternatives under the same forcing, expose adverse changes and evidence gaps, and hand an auditable shortlist to the people who can survey and engineer it.

The project does not claim to replace professional flood modelling or guarantee environmental outcomes. Its practical hypothesis is that transparent, reproducible screening can shorten early alternatives review and improve which sites advance to professional study.

## How We Used AI

SPONGE does not require a runtime language model, API key, or generated numerical result. Its planner is deterministic and every candidate is evaluated by the same disclosed physics workflow.

AI-assisted development was used to analyze requirements, inspect source material, propose implementation options, identify edge cases, review security and lifecycle behavior, and help create tests and documentation. Generated suggestions were accepted only after repository inspection and automated or browser verification. Physics, metrics, constraints, and reports remain reproducible code paths rather than model-generated claims.

## How We Used Codex

Codex was the engineering collaborator throughout the project. It helped:

- turn the product concept into a scoped architecture, PRD, numerical specification, contracts, and verification plan;
- implement and debug the React/WebGL2, Python/FastAPI, geospatial, queue, persistence, and container layers;
- exercise the real browser workflow and inspect visual results;
- build numerical, contract, optimizer, recovery, security, and browser regression coverage;
- audit every repository file, resolve correctness and durability defects, type-check all Python services, and verify a clean production Compose deployment; and
- maintain explicit boundaries between software correctness, reference comparisons, and unproven real-world flood accuracy.

The process was iterative: claims were reduced when evidence was insufficient, failed assumptions were retained in the record, and the final release was rebuilt and tested from the exact committed source.

## Key Features

- Sourced terrain, footprints, streets, vegetation, and explicit data-quality screens.
- Address search, prepared offline demonstration data, and validated terrain/survey imports.
- Live WebGL2 shallow-water simulation with CPU-reference and conservation checks.
- Rainfall, external-inflow, coastal-level, and supported combined scenarios.
- Four finite-capacity green-infrastructure models with saturation, overflow, clogging, and explicit outlet assumptions.
- Manual design editing and bounded budget search using identical scenario ensembles.
- Synchronized before/after replay with remaining flooding and local worsening visible.
- Interrupted-storm recovery, GPU-context recovery, and isolated saved records across tabs.
- Tamper-checked planning exports with input, source, model, run, and cost evidence.
- Hardened Docker deployment with migrations, PostgreSQL/PostGIS, Redis/RQ, request limits, expiring sessions, durable jobs, and reference-safe retention.

## Architecture

- **Client:** React 19, TypeScript, Vite, Deck.gl, MapLibre, and a WebGL2 HLL solver running in a worker.
- **Reference and preparation:** Python 3.12, NumPy, Rasterio, PyProj, Shapely, and an independently testable CPU solver.
- **API and jobs:** FastAPI, PostgreSQL/PostGIS, Redis, RQ, durable database-backed job state, and isolated CPU processes.
- **Deployment:** Docker Compose, Alembic migrations, non-root containers, persistent storage, strict security headers, and an immutable prepared demonstration bundle.
- **Evidence:** content-addressed data bundles, generated contracts, reproducible scenarios, hashes, manifests, and scoped validation records.

## Testing Instructions

### Fast judge path

1. Open the public application link and choose **Explore prepared neighbourhood**.
2. Follow **Start 90-second judge tour** for the intended workflow.
3. Open **Data & assumptions** to inspect sources and limitations.
4. Run or inspect a storm, add an intervention, and compare the selected design.
5. Scrub the synchronized replay and inspect residual risk and intervention storage.
6. Open the evidence export controls.

No account or API key is required for the prepared demonstration.

### Local reproduction

Requirements: Node.js, pnpm, Python 3.11+ for bootstrap, and Docker Desktop with Linux containers.

```powershell
./Setup-SPONGE.ps1
./Start-SPONGE.ps1
```

Open `http://127.0.0.1:5173` and follow the prepared-demo path. The README includes the full verification commands. The audited release passed 334 Python tests, 136 TypeScript tests, 46 browser/GPU tests, full Ruff and mypy checks, dependency audits, generated-contract verification, a production build, and a clean production-container smoke test.

## Public Demo Link

HTTPS judge tour: https://alt-lay-executed-casual.trycloudflare.com/?tour=1

This temporary HTTPS tunnel serves the isolated production stack and passed a fresh external-browser check with zero console errors. It has no uptime guarantee and remains available only while the local production stack and tunnel connector stay online.

## Public Repository Link

https://github.com/jozai193/sponge-flood-planner

## Demo Video

Public demo video: https://youtu.be/SwiVCAZlYHg

The uploaded 4:53 H.264/AAC, 1440×900 walkthrough uses the current dark UI and Deepgram Aura-2 Orion narration. The final local file is `output/submission/SPONGE-NextStep-demo.mp4`.

## Screenshot Shot List

1. Launch experience with the prepared-neighbourhood action and exploratory-use boundary.
2. Full 3D Spring Garden neighbourhood with terrain, buildings, streets, and vegetation.
3. Data & assumptions panel showing source provenance and unresolved evidence needs.
4. Live storm with advancing physical time, mapped depth, exposure metrics, and water-balance residual.
5. Intervention editor showing a finite-capacity green-infrastructure design and explicit eligibility/cost assumptions.
6. Synchronized baseline/planned replay with the intervention footprint, residual flooding, local changes, and stored/outflow water.
7. Evidence export with reproducible scenario, GeoJSON, cost, report, and manifest outputs.

## Submission Readiness Notes

- Application, production stack, immutable demo data, tests, documentation, screenshots, and a final narrated 4:53 demonstration exist locally.
- The public GitHub repository and externally verified HTTPS judge preview are live.
- The video, custom project thumbnail, public links, story, technology tags, team details, and eligibility details are synchronized to the Devpost project.
- The image gallery is optional and intentionally omitted; the embedded video and custom thumbnail provide the primary visual evidence.
- Devpost records the project as published and submitted to NextStep Hacks 2026.
- Numerical and software verification do not establish calibrated neighbourhood flood accuracy.

## Known Limitations

- SPONGE is an exploratory screening tool, not a calibrated forecast or engineering design.
- Real decisions require surveyed terrain and drainage, datum confirmation, parcel and utility eligibility, observed-event calibration, current local costs, building inventories, and professional review.
- Prepared building heights, vegetation geometry, material behavior, and costs contain clearly labelled assumptions.
- The bounded planner does not guarantee a global optimum.
- Rainfall intervention performance is not presented as proof of coastal-risk reduction.
- Monetary damage remains unavailable where defensible value, floor elevation, and damage-curve inputs are absent.

## Work Completed Before and During the Hackathon

SPONGE began during the NextStep Hacks build period. Product architecture and planning started on September 10, 2026, followed by implementation, numerical verification, browser QA, production hardening, and submission preparation through September 20. No SPONGE implementation existed before the event. Earlier files in the workspace concerned a separate product-research concept and were not reused as SPONGE code or presented as this submission.

The project was built by Aditya Jevoor with Codex as an AI engineering collaborator. Codex assisted with planning, implementation, debugging, auditing, testing, and documentation; the entrant directed product decisions and accepts responsibility for the submitted work and claims.

## Official Form Status

The live NextStep Hacks submission form exposes no custom questions. Devpost records the project as published and submitted to NextStep Hacks 2026.
