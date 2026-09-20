# NextStep Hacks 2026 — strategy checkpoint

Researched September 8, 2026. Strategy only; no implementation or Devpost edits performed.

## Decision

Choose **ShadeShift**, a school-scale shade intervention planner. Given a measured site, an aggregate occupancy schedule, feasible intervention sites and a budget, compare existing shade against a computed plan. Recompute when lunch moves, a site becomes unavailable or the budget changes. Report modeled additional shaded person-minutes, assumptions and solver status. Do not claim measured temperature reduction, health outcomes or global novelty.

The competitive advantage is the complete, understandable decision workflow: site and schedule -> constrained allocation -> visible result -> sensitivity check -> usable plan. Shadow simulation and tree placement optimization already exist. Product execution, mixed immediate/longer-term interventions and honest verification must carry the entry.

## Verified event picture

- Host: HackAlphaX. Online. Theme: Earth Forward.
- Submission window: August 21, 2026 04:00 UTC to September 13, 2026 21:00 UTC.
- India deadline: September 14, 2026 02:30 IST. Internal target: September 13, 20:00 IST.
- Judging: September 14, 21:00 UTC to September 17, 21:00 UTC.
- Winners scheduled: September 18, 13:00 UTC / 18:30 IST.
- Formal eligibility: age 13–24 on August 21; teams up to five. Structured eligibility additionally says students only and excludes companies. India is absent from the listed geographic exclusions. Individual age and student status have not been verified.
- Six criteria, scale five: Originality, Adherence to Track, Completion, Learning, Design, Technology. Weights not supplied. Configured tracks array is empty.
- Cash: first $1,000, second $500, third $250. Claude credits: $500/$250/$100 respectively. Other rewards include AoPS coupons, XYZ domains and one-year NordVPN/NordPass/Saily/Incogni benefits. First place also lists a final-round interview at an unspecified YC startup; this is not a job offer.
- A participation prize listing describes Wolfram access and XYZ domains. Its quantities and configured winner count differ; allocation, redemption and access timing are not verified. Winner Claude credits are not assumed available for building.
- Current sponsor logos: Claude, Wolfram, Saily, Incogni, XYZ, Kinetik, AoPS, NordPass, NordVPN. No sponsor technology mandate or sponsor-specific competition confirmed.
- Rules require a 3–5 minute video. Overview asks for a video no longer than five minutes, viewable code/repository and live link if applicable. Use a 3:30–4:30 video and public repository plus no-login demo.
- Prose video requirement overrides the form's unenforced video_required=false setting.
- Overview allows continued projects with before/during disclosure, while rules disqualify work outside the window. Build fresh and attribute dependencies. Cross-entry is conditional on both events allowing it and the stated same-month restriction.
- No explicit AI-use policy was found in the reviewed requirements. Preserve human learning and an honest account of AI assistance.
- Live user form: Untitled, DRAFT, 1/4 steps done. No submission was made.

## Coverage and unresolved information

Read live Devpost MCP overview/resources, rules, judging, prizes, dates, submission fields and announcements. Announcements were empty. Public gallery was unpublished. The only public discussion asked about eligibility and had no replies. Read organizer website, FAQ, team, sponsor prospectus description and official YouTube listing. Website contains stale 2022/2025 references and age 13–21; do not apply those over the 2026 rules. Latest visible YouTube live recordings were from 2025. No detailed 2026 workshop timetable or individual judge biographies were verified. Public judge listing names HackAlphaX Team. No Discord membership was joined or message sent; private Discord announcements remain unchecked.

## Ranked shortlist after critique

1. ShadeShift — constrained shade allocation for school outdoor schedules. Best expected execution and rubric balance.
2. LoopForge — calibrated scrap inventory to feasible small-object design, cutting layout and assembly. Highest visual transformation; physical fit and fabrication validation are risks.
3. RainPatch — compare green infrastructure retrofits under multiple storms using SWMM. Highest technical ceiling; site parameters and scientific credibility are risks.
4. GridWeave — carbon-aware, deadline-constrained flexible-load scheduling. Strong engineering; avoid mistaking average grid intensity for proven marginal avoided emissions.
5. LeakLens — leak hypothesis ranking plus next-best measurement in a modeled water network. Strong inference demo; synthetic network success is not field validation.
6. CanopyBridge — choose habitat restoration parcels for connectivity under budget and land-availability constraints. Ecology assumptions limit claims.
7. ReuseRelay — allocate reusable assets and route pickups under time, compatibility and capacity constraints. Strong operations value; real participation is unverified.
8. WildEar — acoustic survey comparison with effort normalization and human review. Bird identification alone is crowded; recordings do not establish abundance or recovery.
9. PlumeTrace — show uncertainty in simplified pollution source hypotheses and recommend additional sampling. No accusation or operational forecast from a toy model.
10. RepairProof — source-grounded repair workflow with visual step evidence for one benign device class. Broad repair assistants are crowded and unsafe guidance must be excluded.

Sixty directions across climate adaptation, water, energy, biodiversity, circular materials, food, sensing, education, infrastructure and environmental evidence were considered. The shortlist favors demonstrable mechanisms and controllable inputs over generic assistants or inaccessible hardware/data.

## ShadeShift engineering plan

Frontend: React/TypeScript, Three.js or an equivalent scene renderer, accessible 2D plan, schedule editor, budget slider, comparison view and assumptions drawer. Static web assets plus a small containerized Python FastAPI service; SQLite for scenario records, files for small geometry fixtures, no account requirement for judge demos. No vector database or microservice fleet.

Input: local metric coordinates, latitude/longitude and timezone, measured building heights, existing vegetation geometry, aggregate zone occupancy by time, candidate shade locations, costs, capacity and exclusion zones. Each value records whether measured, estimated or illustrative. Import versioned JSON/GeoJSON. For an image underlay, require scale and orientation calibration; do not infer reliable geometry from one photograph.

Simulation: solar position at sampled dates/times; cast geometry onto occupied surface samples; compute union of shade so overlaps are not double-counted. Use a shared numeric shadow engine for scoring and an independent verification path for small analytic cases. Renderer shadows are presentation only. Treat initial small trees separately from assumed future canopies. Do not convert shade directly into degrees of cooling.

Optimization: precompute candidate coverage bitsets. Binary intervention selection with budget, incompatible sites, physical footprint, no-build zones and optional minimum zone coverage. Objective: incremental occupied shaded minutes over the baseline, with scenario robustness or zone minimums explicitly disclosed. Use a greedy valid plan first; then a bounded mixed-integer solve. OR-Tools CP-SAT is the default; Wolfram LinearOptimization can be a central alternative if runtime access and deployment rights are verified. Do not assume Wolfram Alpha API calls grant arbitrary Wolfram Language execution.

State: Site, Obstacle, OccupancySlot, Candidate, Constraint, Scenario, Run and Evidence records. Run identity includes input hash, geometry/model version, solver configuration and result status. Stale responses must not replace a newer scenario. Cache only matching inputs; distinguish saved examples from new runs.

API: validate site; compute baseline; generate/select interventions; optimize; obtain run status; export result. Return objective values, per-zone changes, constraint checks, assumptions and feasible/optimal/timeout status. SSE for optimization progress; local worker for animation and light calculations. Cancel superseded runs.

AI: optional Claude adapter to turn a written schedule into a schema-validated proposal and explain computed results. User reviews parsed inputs. The model cannot invent costs, dimensions or environmental outcomes. No autonomous external actions and no multi-agent architecture required.

## Minimum competitive version and verification

One clearly labeled measured or illustrative school site; adjustable occupancy schedule; existing shade; a small library of feasible shade structures; budget-constrained placement; live before/after; changed-constraint rerun; export with assumptions. Tree-growth scenarios are an extension, not necessary for the first demo.

Required evidence: analytic shadow-length/direction fixtures; timezone/date tests; union overlap handling; no shade without occluders; zero-budget behavior; constraint feasibility; exhaustive comparison for tiny candidate sets; noisy height/occupancy sensitivity; no-login browser access; keyboard controls and readable non-color cues. All benchmark and improvement figures remain targets until actually measured.

Do not call a feasible solution globally optimal. If CP-SAT proves optimality, qualify it as optimal for the discrete candidate set and supplied model.

## Core 110-second demo

0–15: Show school courtyard at lunch, occupied zones and current shade.
15–30: Show limited budget and allowed installation locations.
30–50: Compute a plan; show the actual new shadow coverage and incremental modeled occupied shade.
50–70: Move lunch one hour later and recompute.
70–90: Disable a recommended site; show a feasible alternative and the tradeoff.
90–110: Open assumptions and one verification result, then export the plan.

Expand into a 3:30–4:30 submission video with the user problem, mechanism, genuine learning, tests and limitations. Never fabricate improvement values or present a stored run as live computation.

## Build order if implementation is authorized later

September 8: lock scope, data provenance and units.
September 9: analytic shadow engine and manually editable site; first visible before/after.
September 10: occupancy objective, valid greedy allocation, bounded optimization and reruns.
September 11: evidence suite, second scenario, sensitivity and optional AI parser.
September 12: product polish, deployed judge flow, README and video.
September 13: feature freeze, access/link audit and upload buffer; submission remains a separate action.

Maximum version: immediate canopy versus future tree scenarios, lifecycle cost and maintenance parameters, Pareto choices, multiple dates, importing site plans, and a real stakeholder review if obtainable. Exclude citywide reconstructions, autonomous construction plans and unsupported thermal models.

## Main fallback decisions

- Inaccurate imagery: measured simple geometry or explicitly illustrative fixture.
- Slow optimization: valid greedy result with feasibility evidence, later bounded solve.
- Misleading school impact: label modeled occupancy assumptions; field validation is future work.
- Cloud failure: shipped static example and local deterministic calculation; label replay.
- Weak GPU: 2D plan with the same numerical results.
- No sponsor credentials: OR-Tools and manual structured input preserve the demo.
- No real site access: transparently use an illustrative case and reduce claims; do not invent a pilot.

## Key sources

- [2026 overview, rubric and prizes](https://nextstep2026.devpost.com/)
- [2026 rules](https://nextstep2026.devpost.com/rules)
- [Resources](https://nextstep2026.devpost.com/resources)
- [Updates](https://nextstep2026.devpost.com/updates)
- [Current gallery](https://nextstep2026.devpost.com/project-gallery)
- [Unanswered eligibility discussion](https://nextstep2026.devpost.com/forum_topics/45088-eligibilty)
- [Organizer website and historical FAQ](https://www.hackalphax.co/)
- [Official YouTube live recordings](https://www.youtube.com/@hackalphax/streams)
- [Official Discord contact path](https://discord.gg/hFxwvgZDsh)
- [2025 first: DyslexicAssist](https://devpost.com/software/dyslexicassist)
- [2025 second: Memora](https://devpost.com/software/memora-t7mfrp)
- [2025 third: Eyelink](https://devpost.com/software/eyelink)
- [2022 first: MusicGenic](https://devpost.com/software/musicgenic)
- [2022 second: Photo Cook](https://devpost.com/software/photo-cook)
- [NASA comparable winners](https://www.spaceappschallenge.org/blog/the-nasa-space-apps-challenge-live-global-winners-announcement/)
- [ShadeMap prior art](https://shademap.app/help/)
- [Shadowmap prior art](https://shadowmap.org/)
- [Penn tree optimization prior art](https://www.design.upenn.edu/yes2025/optimizing-street-tree-placement-maximum-shade-and-pedestrian-benefit)
- [UCL zero-waste fabrication prior art](https://geometry.cs.ucl.ac.uk/projects/2016/zero-waste_design/)
- [EPA shade and vegetation](https://www.epa.gov/heatislands/benefits-trees-and-vegetation)
- [EPA SWMM](https://www.epa.gov/water-research/storm-water-management-model-swmm)
- [EPA EPANET](https://www.epa.gov/water-research/epanet)
- [OR-Tools solver statuses](https://developers.google.com/optimization/cp/cp_solver)
- [Wolfram optimization](https://reference.wolfram.com/language/ref/LinearOptimization.html)
- [SunCalc](https://github.com/mourner/suncalc)
- [Claude vision](https://platform.claude.com/docs/en/build-with-claude/vision)
- [Circuitscape](https://circuitscape.org/)
- [BirdNET](https://birdnet.cornell.edu/)
- [Great Britain carbon intensity API](https://api.carbonintensity.org.uk/)
- [iFixit API](https://www.ifixit.com/api-docs)

Live MCP fetched event data at approximately 17:23–17:28 UTC September 8. Its exact date fields and participation prize details were more complete than indexed public-page snapshots. Sources establish tool capability and prior art; they do not establish tested access, measured prototype performance or a winning probability.
