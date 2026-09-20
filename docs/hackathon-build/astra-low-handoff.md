> Historical record only (superseded 2026-09-20): this was the pre-implementation handoff. Do not use it as current setup or status guidance. See the root `README.md`, `docs/release-evidence.md` and `docs/hackathon-build/implementation-status.json` for the implemented and verified release.

> Current architecture decision: [Architecture v2](architecture-v2.md) governs full rainfall, coastal and compound scope, composable scenarios, engine adapters and optional authenticated/AI services. It supersedes conflicting v1 restrictions and mandatory Claude requirements.

# Astra Low implementation handoff

## Status and model

Architecture is prepared. No application code exists yet in this workspace. The requested implementation configuration is Astra with low reasoning (`gpt-6-astra`, effort `low` where the app exposes those identifiers). This file is a prepared handoff, not evidence that the model was switched or another task was created.

The user asked to finish architecture before the subsequent build. Start implementation when the user starts that phase. Do not create a separate task or spawn agents unless the user subsequently requests that. Work in `E:\Nextstep Hacks hackathon` and preserve the existing research documents.

## Ready-to-use build instruction

> Build the full SPONGE product from docs/hackathon-build/README.md and its linked scope, PRD, architecture, numerical model, contracts, verification plan and checklist. Use Astra at low reasoning. Preserve every feature in the original pitch: general address ingestion, real 3D terrain/buildings, live GPU flooding, all four infrastructure types, budget-constrained siting, live Claude proposal and solver feedback, calculated damage, synchronised before/after replay, manual edits and report export. Follow the checklist in dependency order, verify each package, and keep build-notes.md current. Do not substitute animations, hard-coded plans, fabricated savings or unlabelled cached runs for implemented features. Make ordinary engineering decisions autonomously within this architecture. Report actual performance and data limitations. Continue through integration and a reviewable deployment package; do not submit to Devpost without explicit authorisation.

## First implementation turn

1. Read README, scope, PRD, spec, numerics, contracts, validation, checklist, sources and build-notes. Read any newly present AGENTS.md and applicable skills. The architecture documents are the current SPONGE specification; older root research files describe previous ideas.
2. Inspect repository state, available Node/Python/container runtime, GPU/browser support and existing secrets by presence only. Do not print credentials. Pin compatible dependencies and record the toolchain.
3. Start checklist package 1. Establish shared units and schemas before UI/solver packages diverge. Keep a functioning doctor/health path early.
4. Begin package 2 data audit and package 3 controlled CPU physics in dependency-aware order. No location has yet been verified as a final hero; do not assume Philadelphia datasets have already been downloaded.
5. Use short verification checkpoints and compact progress updates. When an input/provider is unavailable, continue independent work and record the exact missing dependency; do not mark untested live functionality complete.

## Non-negotiable engineering invariants

- Conservation, nonnegative state, correct units/datum and deterministic resets before dramatic animation.
- Simulation time, wall-clock compute and replay speed are distinct.
- Every intervention has finite storage/capacity and overflow; no silent water deletion.
- Roof rainfall is conserved; domain boundaries and drainage are explicit.
- Optimisation scores completed combined-plan simulations. No unproven submodular or global-optimum claims.
- Claude proposes and explains; validated code owns geometry, budgets, physics and numbers.
- A damage estimate needs source/assumption coverage; fixed $48M/$19M constants are prohibited as real results.
- Coarse screening, cached examples and CPU/server execution are labelled; they do not masquerade as live fine-grid GPU results.
- Every original feature has an acceptance ID; milestone order is not a reduced scope.
- Eight seconds and 60 fps are measured targets. Missing them requires profiling and honest reporting, not fake timers or grid changes hidden from the user.

## Resume and completion format

At meaningful checkpoints update build-notes.md with: package/subtask, changed files, checks run and their outcomes, verified measurements, unresolved dependencies and next concrete command/action. Check off a package only after its acceptance evidence exists.

At release, produce a feature-to-evidence matrix covering A01–A42, a concise architecture deviation log, benchmark results with device/profile, data/provenance inventory, local/hosted instructions and submission draft. Call out any remaining missing live credential, reference, hosting or performance evidence plainly. Do not report the full product finished while required functionality remains unimplemented.
