# Spring Garden drainage audit — 2026-09-10

The public data contains useful asset locations, but the application does not yet represent a functioning sewer network. No inlet capacities or connections have been inferred from asset positions.

## Inventory actually queried

Query envelope: west -75.16752, south 39.96229, east -75.16048, north 39.96771. This is the geographic bounding envelope around the 600 m scene, not an exact clipped catchment. Boundary features can lie outside the local square.

| Official PASDA/PWD layer | Returned features | Interpretation |
|---|---:|---|
| Philadelphia Water INLETS 2025 | 145 | Mapped assets with type, system, identifiers and GPS metadata; capacity not provided in the queried schema |
| Philadelphia Water OUTFALLS 2025 | 0 | No inventory records intersected this envelope; this does not mean the neighbourhood has no downstream drainage |
| Philadelphia Water GSI SMP TYPES 2025 | 23 | Mapped stormwater-management polygons; not 23 verified independent, operational facilities |

Reproduce with `.venv/Scripts/python.exe -m scripts.audit_drainage`. Raw geometry, available field names, retrieval times, URLs and response hashes are saved in `artifacts/verification/drainage-inventory.json`. Responses are cached by the provider adapter. A 2025 publication label is not proof that every asset was surveyed in 2025.

Sources:

- [PASDA inlet dataset](https://www.pasda.psu.edu/uci/DataSummary.aspx?dataset=7117)
- [Inlet metadata](https://pasda.psu.edu/uci/FullMetadataDisplay.aspx?file=PhillyWater_INLETS2025.xml)
- [Queryable water asset layers](https://mapservices.pasda.psu.edu/server/rest/services/pasda/CityPhillyWater/MapServer)
- [PWD combined and separate sewer explanation](https://water.phila.gov/stormwater/)
- [PWD sewer service area and release-rate maps](https://water.phila.gov/development/stormwater-plan-review/manual/appendices/d-watershed-and-phs-release-rate-maps/)
- [Sewershed dataset](https://opendataphilly.org/datasets/pwd-sewersheds/)
- [PWD inlet controls guidance](https://water.phila.gov/development/stormwater-plan-review/manual/chapter-4/4-11-inlet-controls/)

The service-area maps explicitly describe approximate boundaries. Neither administrative sewersheds nor the rectangular demo extent are sufficient hydraulic boundary conditions.

## Data still needed

Inlet capture rating and blockage condition; inlet rim and pipe invert elevations; connected conduits and dimensions; slope/roughness; downstream head and surcharge; control structures; facility storage, soil and underdrain specifications. Need authoritative datum reconciliation and flow/observed-flood validation before activating calibrated sinks or network exchange. The queried asset service does not contain a conduit-network layer; this audit does not prove no public conduit dataset exists elsewhere.

## Implemented numerical outlet primitive

Both CPU and GPU now support a capped linear-reservoir outlet source. For depth h, local crest depth c and recession coefficient k, candidate removal over dt is `max(h-c,0) * (1-exp(-k*dt))`, limited by `Qmax*dt/cellArea`. This is an explicit screening parameterisation, not a physical grate/orifice rating or a pipe solver. The exponential is exact for the uncapped isolated reservoir; taking the minimum with the capacity bound is a split-step approximation when the limiting regime changes within a step.

Removed momentum scales with remaining depth, and all exported volume enters `outflow_m3`. GPU outlet history is restored with state on timestep rollback. One outlet per non-solid cell, finite nonnegative parameters and an explicit source are required. Input hashes include outlet configuration. Source steps run on either side of the conservative surface update.

Verified: isolated analytical recession on CPU and GPU; CPU capacity limitation and below-crest non-drainage; mass balance. The primitive exports to an external sink and does not represent downstream retention, surcharge, backflow, underdrain return to the surface, or coupled network routing. It must not be used for an internal transfer between cells. Broad open GPU edge boundaries remain disabled pending their own flux-ledger verification.

The default website remains closed-boundary with no active outlets because the required hydraulic parameters are missing. The new primitive is available to simulation inputs and tests; mapped inlets are not silently activated.

## Follow-up: downstream conditions and access
PWD's Development Services FAQ (https://water.phila.gov/development/faq/, Information Requests) directs infrastructure-location requests through Pennsylvania One Call and describes requesting review records through Development Services; some records cannot be publicly shared. No requests have been submitted. Public asset records still lack verified capacity/topology needed for the live neighbourhood. Imported parameterised outlets now accept a constant downstream water elevation in local model datum; available drainage head is limited by both crest and downstream level. This suppresses discharge into high tailwater but does not implement reverse flow or pressure routing. The default scenario remains uncalibrated.
