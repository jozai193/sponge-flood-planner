# Nonlinear ratings and water display

Implemented 2026-09-11. This extends the earlier linear-control milestone; it does not complete the entire numerical roadmap.

## Hydraulic equations

Surface controls offer linear storage, an orifice outlet or a rectangular sharp-crested weir. All dimensions and coefficients remain user assumptions. For an orifice, the supplied elevation is the opening centre, the opening is assumed sufficiently submerged, and `Q = Cd * Ao * sqrt(2 g (H1 - H2))`. The opening area is in m² and Cd is dimensionless. Partial-opening transitions, pipe losses and reverse flow are not represented. See the [USACE hydraulic reference](https://www.hec.usace.army.mil/confluence/rasdocs/ras1dtechref/latest/modeling-pipe-networks/pipe-network-hydraulic-structures).

For the sharp-crested rectangular weir, `Qfree = Cw * L * H1^1.5`. Cw is in m^0.5/s and width L is in metres. Positive receiver head above the crest reduces this flow using `Q = Qfree * (1 - (H2/H1)^1.5)^0.385`, the Villemonte correction described in the [EPA SWMM hydraulics reference, section 6](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=P100S9AS.txt). This is specifically a sharp-crested rating, not a broad-crested or ogee spillway model.

Both ratings stop when receiver head reaches donor head. Explicit discharge capacity, available donor water and the existing pairwise head limiter bound each transfer. Internal discharge remains in the surface model; external discharge enters the outflow ledger. Underdrains retain the earlier free-outlet linear storage model, because water-equivalent subsurface storage is not a hydraulic pressure head.

Opening area or width and discharge capacity are divided across facility cells. This is a distributed screening representation of a whole-facility rating; it does not resolve a single physical outlet. One surface rating per cell remains the limit: simultaneous separate low-level orifice and high-level spillway controls are not yet implemented. Layout, losses, calibration and applicability require site-specific validation.

Nonlinear designs use a maximum 0.2-second step. Search/comparison uses that same limit for baseline and all alternatives. This can increase runtime substantially; it is a conservative default from controlled tests, not a universal site-accuracy guarantee.

## Verification evidence

For 4 seconds of isolated recession with 100 m² storage area and initial depth 0.5 m, errors against independent analytic solutions were:

| Maximum GPU step | Orifice depth error | Weir depth error |
| --- | --- | --- |
| 0.8 s | 0.06937 mm | 0.29709 mm |
| 0.4 s | 0.03468 mm | 0.14781 mm |
| 0.2 s | 0.01733 mm | 0.07378 mm |

Halving timestep approximately halves error, consistent with the explicit rating exchange. The maximum relative mass residual among these runs was approximately 1.05e-7. Additional coupled donor/receiver tests converge against a float64 reference using 0.001-second exchange steps. These establish controlled numerical behavior, not observed flood accuracy. Browser tests used SwiftShader, not hardware performance measurements.

## Water rendering

- Removed the 20 cm display lift; the surface now has a 6 mm anti-flicker offset.
- Shared wet-cell corners interpolate water-surface elevation for a continuous appearance. This interpolation affects drawing only; wet extent, numeric depth and metrics come from original cells.
- A fixed 0–0.6 m depth color ramp runs from pale cyan to deep blue; both replay views use the same scale.
- Shorelines mark transitions at the existing 5 mm display threshold. Buildings and dry cells are excluded.
- Sparse arrows follow solver velocity; length scales with speed and zero/near-zero velocities do not create decorative currents. Arrows update with physical snapshots, not an independent animation clock.
- Road/green display offsets were reduced so raised illustrative layers do not conceal shallow water. Water hover reports cell depth in centimetres.

The model arrays remain unchanged by rendering. Unit checks cover shared corners, wet/solid masking, velocity direction and array preservation. The real Philadelphia browser journey passes; a live storm was visually inspected and captured at `artifacts/verification/water-upgrade.png` (8 simulated minutes, 100 mm custom rainfall over 10 minutes). This capture is a development scenario, not a historical observed flood.
