# SPONGE submission-readiness goal

Active goal established by user request on 2026-09-11. Continue autonomously through implementation, verification and submission preparation; public submission and terms acceptance are separate actions.

## Current event check

Official overview and rules rechecked 2026-09-19:
- https://nextstep2026.devpost.com/
- https://nextstep2026.devpost.com/rules

The overview announces a one-week extension. Both pages show September 20, 2026 at 17:00 EDT (September 21, 02:30 IST). Older September 13 dates in project research are superseded. Rules require a 3–5 minute video and project page; overview requires viewable code and a live application link if applicable. Rules list ages 13–24 as of August 21 and teams up to five; overview says students only. The published rubric is Originality, Adherence to Track, Completion, Learning, Design and Technology, with no published weights. Individual eligibility remains unverified.

## Readiness gates

1. Numerical integrity: full-state checkpoint/restart, higher-order GPU parity, controlled references, conservation and honest limitations.
2. Complete decision flow: real neighbourhood, editable storm and four intervention models, completed constrained search, replay, source/assumption inspection and deterministic report/export.
3. Reliability: stale-result prevention, session/data isolation, durable recovery, input validation and usable failure paths.
4. Measured performance: actual hardware profile, cold/warm ingestion and complete optimisation time; no unmeasured speed claims.
5. Submission evidence: feature-to-test matrix, reproducible setup, public-access/deployment package, demo recording, screenshots, attribution and accurate Devpost draft.

Preserve the full agreed specification. Do not mark all 42 original acceptance criteria passed simply because a partial demo works. Distinguish submission eligibility, demo readiness, full product completion and scientific validation.

## Current work

All 49 internal acceptance requirements are evidence-verified. The release passes 333 Python tests, 134 TypeScript tests and 46 real-browser/GPU tests after the lifecycle, queue-durability and startup-resilience audit, plus schema, full-project Python lint, typing across all 61 Python service modules, dependency and production-container smoke checks. The prepared judge flow now has a shareable `?tour=1` entry point; transient reads retry, expired browser sessions renew once across concurrent bundle requests, and contract validation is precompiled so the strict production CSP does not blank the deployed page. The database-backed job outbox, maintenance process, reference-safe retention and content-addressed atomic publication close the identified local durability gaps. The rebuilt production image renders the tour and prepared demo with zero browser errors. The remaining gates are external or factual: publish a viewable repository, deploy a public URL, replace the silent raw capture with a narrated/captioned 3–5 minute video, add truthful personal learning and before/during-work disclosure, confirm entrant eligibility, complete the Devpost fields and accept its terms.

Scientific validation remains separate from submission readiness: SPONGE is not calibrated for site-specific prediction, and practitioner/community validation has not been completed.
