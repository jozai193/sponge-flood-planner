# SPONGE judge-perspective scorecard

Audit date: 2026-09-20. Official event pages currently show a deadline of **September 20, 2026 at 5:00 PM EDT** and six unweighted criteria: Originality, Adherence to Track, Completion, Learning, Design and Technology. The rules require a 3–5 minute demo video and completed Devpost page; the overview also requires viewable code and a live-app link when applicable.

Official references: [overview and rubric](https://nextstep2026.devpost.com/), [rules](https://nextstep2026.devpost.com/rules).

These scores are a candid readiness estimate, not organizer scores.

| Criterion | Current estimate | What a judge is likely to see | Action taken / remaining risk |
|---|---:|---|---|
| Originality | 4.0 / 5 | Flood simulators, EPA SWMM and digital-twin hacks already exist. SPONGE is strongest when framed as a reproducible intervention-comparison workflow, not “the first flood simulator.” | Added explicit incumbent comparison and the five-part differentiation claim. Never claim the component technologies are novel. |
| Earth Forward | 4.5 / 5 | Direct climate-resilience and green-infrastructure fit, with a clear Philadelphia use case. | Added an explicit impact pathway tied to Philadelphia Water Department practice. Real practitioner/community validation is still missing. |
| Completion | 4.5 / 5 technically; submission gate open | The full prepared journey, recovery, exports and production stack work. | 333 Python, 134 TypeScript and 46 browser/GPU checks after this audit. Startup retries brief connection resets and renews expired sessions once across concurrent requests. A clean-room browser audit also found and fixed a production-only CSP blank-page failure; the rebuilt image now passes with zero console/page errors. Public repository, hosted judge URL, final narrated video, team eligibility and Devpost completion remain entrant-owned gates. |
| Learning | 4.0 / 5 | The work spans hydrodynamics, GPU programming, GIS, optimisation, accessible UX and production operations. | Devpost copy now states the concrete learning. Entrant must add personal starting point, prior projects and exact division of work; those facts cannot be inferred. |
| Design | 4.5 / 5 | The city view is polished and the controls are accessible, but the first screen previously looked like a dense expert tool. | Added a keyboard-accessible Judge tour and shareable `?tour=1` entry point explaining problem, workflow, differentiation and boundaries. |
| Technology | 5.0 / 5 | Real WebGL2 shallow-water physics, independent CPU reference, robust constrained planning, geospatial validation, recovery, evidence manifests and a production stack provide clear technical depth. | Lead the demo with one live run and one before/after comparison. Keep the details subordinate to the decision story. |

## Highest-risk submission gap

`output/playwright/sponge-demo-4m59.webm` is 4:58.72 and 1440×960, but has **no audio stream**. Its sampled frames also do not clearly demonstrate a completed before/after replay and evidence export. It is useful as raw capture, not as the final pitch video.

The replacement video must:

1. state the community decision and Earth Forward impact in the first 20 seconds;
2. show a live storm, an eligible intervention, completed comparison/replay and evidence export;
3. explain the narrow originality claim against SWMM, static risk maps and flood-dashboard hacks;
4. include personal learning and exact before/during-hackathon disclosure;
5. use narration or deliberate captions and remain under five minutes.

## Evidence boundary

The strongest judging strategy is candour. SPONGE is release-engineered exploratory screening software; it is not yet calibrated for neighbourhood flood prediction and has not yet been validated with a practitioner. Do not turn these limitations into false accuracy, monetary-savings or adoption claims. A judge can still reward the working technology, honest decision design and unusually strong verification.
