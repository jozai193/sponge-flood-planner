# Facility controls: implementation and limits

Implemented 2026-09-11 in the existing GPU, planner and paired replay path.

## User flow

Choose a candidate and intervention in **Exploratory design**. Set storage and infiltration assumptions. Bioswales expose channel slope/direction; pavement exposes permeability lost to clogging. Enable a surface control and/or underdrain, choose a receiving area or explicit external discharge, and set recession time and whole-facility capacity. Apply the design and compare or optimise as before.

The receiving area uses its first cell outside the facility as a concentrated discharge point. It is not a surveyed outfall. Each control's maximum discharge is divided equally among facility cells; surface and subsurface controls have separate capacity allowances. All parameters and resolved links are included in comparison evidence.

## Physical representation

| Facility | Implemented behavior |
| --- | --- |
| Rain garden | Excavated surface, finite infiltration reservoir, native-soil percolation, optional underdrain and surface release |
| Bioswale | Excavated channel graded along a grid axis, roughness and finite infiltration reservoir, optional downstream releases |
| Permeable pavement | Preserved surface grade, permeability reduced by explicit clogging fraction, finite reservoir and optional underdrain |
| Detention basin | Resolved excavation storage, no duplicate subsurface storage, optional controlled surface release |

Surface water above resolved banks moves through the existing HLL solver. Once subsurface capacity fills, uncaptured water remains on the surface. This does not implement pressure-driven groundwater exfiltration. A bioswale's graded bed starts from the lowest original facility elevation minus excavation; additional cut grows with distance along the chosen axis. This is an assumed channel geometry, without engineered cross-section or earthwork costing.

For a cell with area A, available storage depth H above its control crest, rate k and capacity Q:

`release_depth = min(H * (1 - exp(-k * dt)), Q * dt / A)`

For internal surface releases, H is also limited to half the positive donor-minus-receiver water-level difference (equal cell areas). This blocks an initially higher receiver and limits pairwise head overshoot. It is a timestep approximation with snapshot receiver heads, not an orifice/weir equation or network pressure solve. Underdrains use prescribed free-outlet storage recession; downstream pressure and backflow are not modelled. A nonlinear physical spillway rating and separate low/high-stage outlet controls remain future work.

The GPU gathers incoming transfers from immutable state using sparse linked receiver lists. There is at most one control per cell/reservoir and 4096 total links. Multiple donors, cycles and simultaneous surface/subsurface release are supported without order-dependent mutations. Transfers remove donor momentum proportionally; incoming water has zero prescribed momentum. External transfers increment the outflow ledger. Internal returns do not. Source and history ping-pong states participate in existing rollback.

Replay now displays surface storage, subsurface storage, cumulative external discharge and mass residual at the selected physical time. Input identities include link configuration and maximum timestep; planner evidence hashes the effective execution timestep.

## Verification

- Float64 reference exchange: analytic storage recession, shared receivers, link-order invariance, capacity, crests, downstream head and whole-system conservation.
- GPU isolated exchange: analytic underdrain recession, shared surface return, explicit external export and downstream blocking; residual below 0.001% in the checked fixtures.
- Four-facility controlled runs: baseline and planned simulations with small finite reservoirs, rain and recession; retained storage and downstream return accounted for. This fixture isolates transfer behavior and does not establish real-site accuracy or validate bioswale cross-sections.
- Existing GPU rain, lake, dam-break reference, saturation, inflow and planner/replay checks remain passing.
- Existing real-neighbourhood browser journey passes. Editor surface and underdrain controls were manually applied to a Philadelphia candidate with a separate receiving area; screenshot inspected.

Full package 5 acceptance remains open: engineered spillway/underdrain relations, detailed geometry/eligibility/cost inputs, pressure/network coupling, timestep convergence for coupled facilities and observed-site validation are not complete. GPU tests used SwiftShader; hardware performance remains unmeasured.
