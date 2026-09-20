> Current decision (2026-09-14): [Architecture v2](architecture-v2.md) governs full rainfall, coastal and compound scope, composable scenarios, engine adapters and optional authenticated/AI services. It supersedes conflicting v1 restrictions and mandatory Claude requirements. Runtime capabilities must still be verified; this notice does not mark them implemented.

# SPONGE scope

## Product commitment

Build the complete original SPONGE experience: type an address, see real 3D terrain and building footprints, configure sourced design storms and coastal/compound scenarios, watch water move and buildings change exposure colour while a damage estimate rises, plan within a budget with simulation-backed search and optional AI assistance, optimise feasible green infrastructure, replay identical forcing side by side, and export a municipal planning report.

Rain gardens, bioswales, permeable pavement and detention basins are all required. Users can place, edit, remove, lock and exclude sites. Automatic siting must account for parcel and physical constraints. The final product includes provenance, uncertainty, reproducible runs, device fallbacks, and judge-ready access.

## Intended users and decisions

Primary workflow: a municipal planner or community resilience team compares early intervention portfolios and explains their tradeoffs. Secondary workflow: a resident or student explores how terrain and stormwater management interact. The interface supports both without exposing shader settings in the normal flow.

The first user-visible question is: “Where could this budget make the largest modelled improvement, and what flooding would remain?” Practitioner demand is still a product hypothesis; architecture does not establish adoption.

## Geography and completeness

Address search is general, not a hard-coded single-site selector. For each address the system produces a coverage result before declaring a neighbourhood ready. It can fetch known data, accept GeoTIFF/GeoJSON/rainfall/building-inventory uploads, and reuse versioned prepared bundles. A verified hero neighbourhood is required for the demo, but does not replace the general ingestion path.

An address without parcel records cannot silently acquire fabricated parcel ownership. It can show estimated candidate areas and accept user-supplied eligibility; its parcel status remains explicit. An address without NOAA coverage uses a supported regional source or an explicit user-supplied storm. Lack of an input is a state the product handles, not a reason to manufacture that input.

## Scientific scope

Rainfall-driven surface flooding and coastal inundation are required hazard workflows. Supplied river/external inflows and combined rainfall, inflow and coastal scenarios remain in the full scope. Tide, surge, wind and wave effects require explicit engine capabilities and appropriate forcing; a prescribed reservoir level does not establish that all these processes are simulated. Groundwater and structural engineering are not inferred from surface flooding. See architecture v2 for capability-specific admission and validation.

Supported drainage modes are explicit: surface-only; parameterised inlet/network capacity with finite storage; imported SWMM network via the reference execution service. None is silently selected as a complete surveyed sewer network. Imported-network coupling is an engineering extension, while the surface and parameterised modes are core product requirements.

Verification has three distinct meanings: software correctness on numerical tests, agreement with a reference model, and comparison with observations for a specific site. Store these separately. No “verified” badge may collapse them into a claim of real-world certainty.

## User decisions already supplied

- Full original feature scope; improvements are authorised.
- Architecture and implementation sequence first; implementation comes afterwards.
- Desired implementation model: Astra, low reasoning.
- Proposed React/TypeScript/Vite, geospatial GPU client, Claude planning, public hosted demo retained where technically appropriate.
- Wow moment: synchronised before/after storm replay, visibly reduced exposure and computed damage.
- Planning delegated to this task. No additional preference interview is needed to write the architecture.

## Explicit completion boundaries

Do not replace address ingestion with only a dropdown, physics with an animated shader, optimisation with hard-coded placements, infrastructure with unlimited water deletion, or damage economics with fixed numbers. Prepared assets are supported for reliability and are labelled with their source and run identity. Optional AI proposals and saved plans must be labelled; no runtime AI provider is a mandatory release gate.

Success can include an intervention that improves flooding only partially or finds no beneficial feasible plan. The product must let physics return that outcome. Simulation, data quality, benchmark status and monetary assumptions travel with every exported result.
