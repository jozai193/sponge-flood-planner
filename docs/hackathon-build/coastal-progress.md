# Coastal and water-aware planning implementation

> Historical checkpoint. The milestones described as “next” below were subsequently implemented and are covered by `docs/release-evidence.md`; this file is retained as an engineering decision record.

Goal: keep the implementation general across locations, and make coastal water interactive without claiming a validated tsunami model.

Implemented in this milestone:
- Conservative overlap between classified permanent-water cells and planning cells; whole candidate footprints that overlap water are excluded.
- The design compiler rejects mapped-water interventions even when eligibility is user-assumed; exact masks survive scenario packing and enter the input checksum.
- Permanent water is excluded from the flood score and land-area-above-threshold indicator.
- One selected coastal edge may prescribe a time-varying water elevation at mapped-water boundary cells. HLL fluxes use a prescribed-depth, extrapolated-velocity exterior state; remaining edges remain closed.
- Boundary exchange is integrated from both Runge-Kutta stages, split into positive incoming and outgoing volumes. Retry attempts do not commit their flux ledger. Outgoing coastal volume survives checkpoints.
- Connected below-level initial water does not fill isolated basins behind high ground or buildings. No seabed elevation is invented.
- Coastal level knots clip timesteps; midpoint levels drive the flux. A peak boundary-depth wave-speed bound protects initially dry domains.
- UI requires a local vertical reference, source/assumption and explicit exploratory acknowledgement. A rise-and-return hydrograph is available. Data are carried into report exports and restored comparisons.

Evidence so far: four-edge reservoir tests preserve equal-level water, exchange water in both directions, and reproduce checkpoint continuations exactly. Chennai's 600 m preview excludes 30 water-overlapping candidates. A synthetic rise from local elevation 2 m to 4 m over 60 seconds visibly propagated inland, with displayed balance residual around 0.001%; this is a functional demonstration, not a Chennai hazard estimate.

Scientific limits: imported terrain has not been verified as nearshore bathymetry, and mixed terrain source datums remain unresolved. The implemented boundary is a reservoir approximation, not a non-reflecting wave boundary. No tsunami source, offshore propagation, tide calibration, wave benchmark, or site-specific validation exists. Do not label this a validated storm-surge or tsunami simulation.

References consulted:
- https://www.clawpack.org/dev/bc.html (ghost states, wall and extrapolation boundary concepts)
- https://www.gebco.net/data-products-gridded-bathymetry-data/gebco2026-grid (15 arc-second global topobathymetry; heterogeneous source datums and shallow-water exceptions). This resolution does not establish building-scale bathymetric detail and is not silently substituted for surveyed nearshore data.

Verification completed: production build; 31 TypeScript tests; 81 Python contract tests; 21 app/GPU/report regressions plus the dedicated coastal save/export/replay test. The dry-front coastal test preserves a solid barrier, exchanges water in both directions and passes the mass-balance bound. UI now shows the terrain offset formula and hydrates applied coastal controls on restoration. Terrain source metadata supports explicit bare_earth or topobathymetry, with signed elevations and no-data rejection tested. No site-specific hazard accuracy claim follows from these checks.

Historical next milestone (subsequently completed): independent coastal benchmark/refinement and measured performance, plus local startup and source-failure reliability.


Independent linear-wave benchmark passed on 12 September: at 100/200/400 longitudinal cells, surface-elevation RMSE fell from 0.375 to 0.189 to 0.086 mm. Mass residual stayed below 1.1e-7. Eight simulated seconds took 3.15/5.06/7.94 seconds on SwiftShader software WebGL (single samples). This confirms refinement toward a small-amplitude flat-channel reference, not real-coast accuracy or tsunami runup. Raw metrics: artifacts/verification/coastal-refinement.json.
