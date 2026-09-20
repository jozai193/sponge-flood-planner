# SPONGE final demo narration

## 00:02 — Problem and product

Urban stormwater decisions are often split across maps, spreadsheets, rainfall tables, site proposals, and budgets. SPONGE turns those disconnected inputs into an interactive screening workflow. It loads a sourced neighbourhood, runs shallow-water physics in the browser, lets a user test green infrastructure, and exports the evidence behind the result. This is exploratory planning software, not a calibrated forecast or an engineering design. That boundary stays visible because the goal is to make early tradeoffs easier to understand without creating false confidence.

## 00:39 — Data and assumptions

This prepared Spring Garden neighbourhood works without a live mapping service. The Data and assumptions panel separates terrain resolution, building and landscape sources, model assumptions, and missing evidence. SPONGE does not invent a surveyed sewer network, parcel ownership, building values, or observed-event accuracy. A new location can be searched and prepared, and users can import validated terrain or survey data, but every bundle retains its source and integrity record. The same distinction appears in reports: numerical correctness, reference agreement, and real-world validation are three different claims.

## 01:20 — Live physics

The water shown here is computed by a Web G L 2 shallow-water solver, not a prerecorded flood overlay. Physical time advances while the interface reports water depth, exposed area, and the water-balance residual. The production engine supports rainfall, external inflow, prescribed coastal levels, and admitted combinations. A Python reference implementation and numerical fixtures check conservation, still water, wetting and drying, dry fronts, restart behavior, and coastal refinement. If a run is unstable, incomplete, or outside its admitted inputs, it cannot silently become a successful result.

## 02:02 — Interventions and planning

The design editor supports rain gardens, bioswales, permeable pavement, and detention basins. Each has finite surface and subsurface capacity, infiltration, saturation, overflow, maintenance or clogging assumptions, and optional controlled releases. Eligibility and costs are explicit user or source-backed assumptions. They are never inferred from a green polygon. A manual design can be compared directly, or Plan with physics can search a bounded set of feasible portfolios under a budget. Every alternative uses the same storm, initial conditions, and disclosed rainfall-sensitivity ensemble. The search is reproducible and can report no improvement; it does not claim a global optimum.

## 02:52 — Comparison and evidence

This synchronized replay compares the baseline and planned design at the same physical time. It keeps remaining flooding and local worsening visible instead of presenting only a favorable headline. The intervention cards show configured storage, water at the footprint, deep percolation, and explicit exported flow. Visual arrows explain the modelled mechanism, but they do not pretend to be measured field discharge. Here the result can even show an adverse local change, which is exactly the kind of warning an early screening tool should preserve.

The planning report carries the scenario, assumptions, selected designs, line-item costs, residual risk, and next data needs. Companion files include exact scenario JSON, selected-design GeoJSON, a cost table, and a SHA two fifty six manifest. Altered inputs, stale hashes, failed conservation, or changed costs are rejected. Monetary damage remains unavailable when defensible building value, floor elevation, and damage-curve inputs are absent.

## 03:58 — Reliability, learning, and close

SPONGE recovers interrupted storms, isolates saved work across browser tabs, and ships as a hardened Docker stack with PostgreSQL, Redis, durable jobs, migrations, request limits, and expiring sessions. The audited release passed three hundred thirty-three Python tests, one hundred thirty-four TypeScript tests, and forty-six real-browser and G P U tests, plus type checks, dependency audits, and a clean production deployment smoke test.

The project began during NextStep Hacks on September tenth. The hardest lesson was that a visually convincing flood is not automatically a trustworthy one. SPONGE makes neighbourhood stormwater tradeoffs visible and reproducible while naming the surveys, calibration, and professional review still required before a real municipal decision.
