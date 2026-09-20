> Current decision (2026-09-14): [Architecture v2](architecture-v2.md) governs full rainfall, coastal and compound scope, composable scenarios, engine adapters and optional authenticated/AI services. It supersedes conflicting v1 restrictions and mandatory Claude requirements. Runtime capabilities must still be verified; this notice does not mark them implemented.



# SPONGE architecture package

Latest runtime increment: [scenario data suitability screening](data-admission-v1.md), September 15, 2026. Metadata mismatches are rejected and per-hazard data gaps appear in the app and exports. Verified physical admission, specialist adapters and observed accuracy remain pending. The [shared scenario contract](scenario-contract-v2.md) supports combined forcing and legacy scenarios.



Status: v1 design retained as a detailed reference; architecture v2 adopted September 14, 2026. Product implementation is partial, with local verification artifacts; general observed flood accuracy remains unvalidated.



SPONGE targets real-neighbourhood rainfall, coastal and combined flood scenarios, budget-constrained green-infrastructure planning, and synchronised comparisons with evidence-bound exposure and loss estimates. The current app has separate rainfall and exploratory coastal modes; v2 defines the migration to composed scenarios.



The user explicitly requested the complete original product, with engineering improvements, and architecture before implementation. This package preserves that scope. Build order is dependency order, not permission to delete later features. The original September 10 planning pass preceded implementation. For current capabilities and proposed upgrades, read architecture v2 first.



## Read order

Start with [Architecture v2](architecture-v2.md): current decisions, capability audit, migration gates and event alignment. The numbered documents below retain detailed requirements.



1. [Scope](scope.md): full product commitment and claim boundaries.

2. [Requirements](prd.md): twelve epics and acceptance criteria.

3. [System architecture](spec.md): stack, component ownership, data flow, runtime, deployment, and file layout.

4. [Numerical model](numerics.md): solver, water accounting, infrastructure, optimisation, damage, and uncertainty.

5. [Contracts](contracts.md): schemas, HTTP routes, jobs, worker messages, and persisted artifacts.

6. [Verification](validation.md): correctness gates, device benchmarks, and acceptance evidence.

7. [Build checklist](checklist.md): ordered work packages and completion gates.

8. [Astra Low handoff](astra-low-handoff.md): implementation instructions and resumption contract.

9. [Sources and access](sources.md): verified references, access limits, and remaining integration checks.

10. [Build notes](build-notes.md): decisions, open dependencies, and future implementation journal.



## Architectural decisions at a glance



| Concern | Decision |

| --- | --- |

| Product | Full address-to-plan-to-comparison experience, plus manual editing and report export |

| Client | React, TypeScript, Vite; deck.gl terrain/water/buildings; MapLibre context map |

| Physics | Retain HLL production baseline; explicit adapter capabilities for rainfall/coastal composition and independently verified specialist engines |

| Execution | Worker-owned OffscreenCanvas GPU; renderer receives bounded depth snapshots; same model has CPU reference execution |

| Geography | Global address discovery; automatic capability assessment; direct USGS high-resolution path in covered US areas; explicit lower-resolution/global inputs elsewhere |

| Preparation | Python FastAPI + geospatial worker for terrain, buildings, parcels, land materials, rainfall and manifests |

| AI | Optional provider-neutral proposals and explanation; deterministic validation, simulation and reports remain authoritative |

| Search | Feasible candidate library, greedy insertion and pair/swap search with full nonlinear resimulation; no unproven submodular guarantee |

| Economics | Building-specific depth-damage estimates with provenance and uncertainty; actual computed counters |

| Data | Immutable content-addressed bundles and run artifacts; PostgreSQL/PostGIS metadata; S3-compatible objects |

| Jobs | Redis + RQ preparation/reference/report jobs; browser evaluation scheduler for GPU planning |

| Deployment | Portable Docker Compose stack; optional static CDN frontend; no dependency on serverless GIS execution |

| Completion | Every original feature must pass its acceptance criteria; numerical and data failures remain visible |



The eight-second planning sequence and 60 fps presentation remain performance targets to measure on an identified device. Neither is represented as already achieved. The illustrative $48M/$19M numbers never become constants in application logic.
