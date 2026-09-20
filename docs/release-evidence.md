# SPONGE release evidence

Verified 20 September 2026. This is an engineering release-candidate record, not a claim of observed flood accuracy.

## Release profile

- Product boundary: public, no-login neighbourhood stormwater **exploratory screening**.
- Runtime: one-origin React application and FastAPI API, separate RQ worker and maintenance process, PostgreSQL/PostGIS, Redis and persistent bundle storage.
- Deployment: multi-stage production image, non-root UID 10001, locked Node/Python dependencies, automatic migrations, live worker readiness and localhost-only default publishing for a TLS reverse proxy.
- Demo data: immutable Spring Garden bundle seeded into a clean volume; live third-party GIS services are not required to open it.
- Safety boundary: results remain explicitly unvalidated for general real-world flood accuracy; incomplete valuation returns “unavailable.”

## Final verification matrix

| Gate | Result | Direct evidence |
| --- | --- | --- |
| Python contracts and numerics | 333 passed | `pytest -q` |
| TypeScript contracts, optimizer and metrics | 134 passed | `pnpm test` |
| Real browser/GPU journeys | 46 passed | `pnpm test:browser` |
| TypeScript safety and production assets | passed; largest JS chunk 219 kB | `pnpm build` |
| Python service-package typing | passed, 61 source files | `mypy` |
| Python lint | passed, all enabled rules | `ruff check services scripts tests` |
| JavaScript production dependency audit | no known vulnerabilities | `pnpm audit --prod` |
| Locked Python dependency audit | no known vulnerabilities | `pip-audit --no-deps --disable-pip` over the frozen `uv` export |
| Production clean-room deployment | healthy | `infra/compose/compose.production.yaml` on port 18080 |
| Production API readiness | database, queue and worker ready | `GET /api/v1/ready` |
| Production security posture | verified | strict CSP without `unsafe-eval`, CSP-safe precompiled contract validation, trusted hosts/proxies, explicit CORS, streaming body limits, expiring sessions, frame denial, MIME sniffing denial, referrer/permissions policy, session creation limit, docs disabled |
| Production browser smoke | passed, zero console/page errors | rebuilt clean-room image; judge tour rendered and prepared Spring Garden demo became interactive under the shipped CSP |
| Production demo data | verified | session creation, hero metadata, 688 buildings and 65,536-byte terrain array served from a fresh persistent volume |
| Visual functional check | verified | `output/playwright/sponge-functional.png` shows live simulation, sourced city context and 0.000% water-balance residual |
| Intervention cause-and-effect check | verified | `output/playwright/intervention-effects-comparison.png` shows planned rain-garden, bioswale, permeable-pavement and detention-basin footprints and labels, live paired effect counters, intervention storage status, configured routes and explicit visual-cue boundaries |
| Purposeful-motion check | verified | `output/playwright/storm-intro-polish.png`, `output/playwright/storm-intro-mobile.png` and `output/playwright/design-placement-polish.png` show the replayable full-screen storm-to-response sequence, integrated dark workspace, real intervention footprint and placement confirmation; narrow-screen composition and reduced-motion behavior are browser-tested |
| Demo capture | raw capture only: 4:58.72, 1440 × 960 VP8, no audio | `output/playwright/sponge-demo-4m59.webm`; replace with the narrated/captioned story in `docs/demo-script.md` before upload |

The browser matrix includes live bundle loading, forced startup connection-reset recovery, single-flight expired-session renewal, provider outage/retry behavior, automatic recovery, cross-tab isolation, rainfall evidence import, enriched revisions, geographic export, GPU/CPU parity, checkpoint integrity, nonlinear outlets, four intervention models, planner search, coastal refinement, external inflow, context loss, the judge tour, intervention cause-and-effect visualization, purposeful motion with reduced-motion fallback, and reproducible report/export checks.

## Deployment smoke contract

The production smoke test requires all of the following:

1. migrations exit successfully;
2. PostgreSQL and Redis are healthy;
3. the worker is registered with the `prepare` queue;
4. `/api/v1/health` and `/api/v1/ready` return success;
5. `/` serves the compiled application with the production content-security policy;
6. `/docs` is unavailable;
7. a 43-character anonymous session token can access the immutable hero manifest and terrain arrays.

## Scientific and external-action boundaries

All 49 software/product acceptance criteria have direct release evidence. That does not turn missing site evidence into model skill. Do not market this release as a calibrated municipal flood model. The remaining real-world and external-action boundaries are:

- no surveyed catchment, vertical-datum transformation, drainage network, parcel/utility eligibility or observed-event calibration for the demo;
- facility geometry and eligibility remain exploratory until site-verified; cost line items require a dated local basis;
- damage valuation is deliberately unavailable without first-floor elevations, inventories and versioned curves;
- the disclosed robust ensemble is a deterministic sensitivity set, not a probability model, and no global optimum is claimed;
- a hosted public URL, individual hackathon eligibility, video narration/upload, repository publication and Devpost submission require the user.

These limits are visible in the application and exports. Passing numerical and software tests establishes implementation correctness for their stated fixtures, not real-world predictive accuracy.
