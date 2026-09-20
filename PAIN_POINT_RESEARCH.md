# Environmental pain-point research: new directions

Research date: 10 September 2026. Status: desk research, not interviews, partnerships, or validated product demand. No implementation or external outreach performed. This replaces the earlier recommendation to build ShadeShift; the user's objections about repeat use and existing products control the selection.

## Decision

Update after focused validation: see SEEDPROOF_GAP_VALIDATION.md. The workflow problem is supported, but an unmet product gap and adoption demand remain unvalidated. Hold the build pending practitioner evidence; the ranking below is a research priority only.

**SeedProof is the strongest candidate to validate next. CleanPath is second. No third candidate clears the novelty bar yet.** This is a ranking of research opportunities, not a claim that either product is unique or proven useful. The strongest evidence establishes real operational requirements. The remaining uncertainty is whether existing tools and ordinary spreadsheets already meet them well enough.

The search covered repair communities, native-plant gardening discussions, restoration organizations, government field protocols, conservation technology communities, research papers, and existing software documentation. It deliberately tested competitors early. A public complaint is evidence that someone experienced a problem; it is not evidence of widespread demand, willingness to adopt software, or collaboration with us. Search visibility cannot establish that a product does not exist.

## 1. SeedProof: check a restoration seed delivery before it is sown

**Pitch:** Upload the approved planting specification, supplier quote, and seed-bag labels. See which requirements are met, which conflict, and which cannot be verified before a restoration team accepts the delivery.

### Evidence for the task

Biodiversa+'s June 2026 policy brief stresses advance seed planning, suitable origins, and documented species composition. This establishes why sourcing matters environmentally; it does not establish demand for our proposed software. [Biodiversa+ brief](https://www.biodiversa.eu/2026/07/08/restoration-materials/)

A Napa County restoration specification includes inspection of incoming seed and seed-bag documentation. Minnesota's native seed design guidance also addresses origin information on tags. These are concrete document-checking tasks, rather than a generic wish to help biodiversity. Requirements differ across projects and jurisdictions. A prototype should use one explicitly selected specification, not merge these into a universal standard. [Napa County specification](https://www.napacounty.gov/DocumentCenter/View/37248/RDS-21-06-Attachment-II-Addendum-1-Resto-Plan-Special-Provisions-C-PDF), [Minnesota design manual](https://dot.state.mn.us/environment/erosion/pdf/native-seed-mix-dm.pdf)

The NRCS seed-tag guide explains information used in interpreting seed lots. Penn State explains pure live seed calculations. These provide a basis for deterministic quantity checks, subject to the selected specification's treatment of dormant or hard seed. [NRCS guide](https://www.nrcs.usda.gov/plantmaterials/ndpmctn12317.pdf), [Penn State explanation](https://extension.psu.edu/calculating-the-price-of-pure-live-seed)

### Proposed workflow

1. Import a project specification and have the user confirm extracted species, quantities, units, origin requirements, and allowed substitutions.
2. Import quote and lot labels; retain the source page or image region for every extracted value.
3. Reconcile species names and lot identifiers. Flag uncertain matches instead of silently accepting them.
4. Run arithmetic and requirement checks in code. Separate contradiction, missing documentation, and confirmed match.
5. Export an exception list and questions for the supplier. A qualified project reviewer makes acceptance decisions.

**Illustrative demo, not a real incident:** a specification requests 10 kg of pure live seed. A lot has 80% purity and 75% germination, with no other relevant viable-seed category in the example. Ten kilograms of bulk seed provides 6 kg PLS; obtaining 10 kg PLS requires about 16.67 kg bulk. The app points to both labels, exposes the calculation, and identifies the discrepancy. A second example lacks source-origin documentation and is marked unknown, not unsuitable. A third delivery passes, preventing a demo that merely flags everything.

### Existing solutions and the possible gap

- **Seed-Spec** markets site-specific native mix design. A mix designer is not a new idea. Its full page could not be retrieved in this research; product scope needs direct confirmation. [Seed-Spec](https://seedspec.com/)
- **Diversity Native Seeds QA Portal** provides quality and provenance information and a mix-design system. This is a serious adjacent solution, not something to omit from a pitch. [QA portal](https://diversitynativeseeds.com.au/portal/)
- **Oregon Seed Certification Service** already provides tag authentication. SeedProof must not claim to certify seed or authenticate tags by reading an image. [Tag verification](https://w3.oscs.orst.edu/online/verifytag.do)
- Supplier calculators already handle coverage and PLS quantities. A calculator by itself is insufficient differentiation. [Clarity estimator](https://crpseed.com/tools/seeding-estimator)

**Gap hypothesis:** a buyer-side comparison across an independently supplied project specification, multiple vendor quotes, and delivered lot labels, with evidence attached to each exception. This is a narrower workflow than mix design or supplier quality portals. The search did not establish that existing products cannot do it.

### Repeat use, impact, feasibility

The intended user is a restoration contractor, land trust, or conservation procurement team managing multiple lots and projects. Repeat use occurs per quote, delivery, and substitution; it is not a mass-consumer daily app. If these teams inspect few deliveries annually or have an efficient existing process, the adoption argument weakens.

The environmental mechanism is avoiding preventable sourcing or quantity mistakes before sowing. Software cannot establish germination in the field, verify physical bag contents, guarantee restoration success, or quantify biodiversity gains from a document check.

A small prototype is feasible: one project specification, several species, three clearly labeled demonstration document sets, supported calculations, source highlights, correction controls, and an export. The hard work is reliable extraction and handling exceptions, not a large agent network. AI helps interpret documents; code computes checks. Unreadable labels must request manual correction. No replacement-species recommendation without an explicit approved rule.

### Validation and kill criteria

Ask a practitioner to describe their last delivery discrepancy, show a redacted example, and explain the current acceptance workflow. Observe them compare a small document set before showing the prototype. Measure correct discrepancies found, false alarms, and review time against their normal method.

Drop this idea if their existing procurement/QA system already performs the comparison, errors are too rare to justify another tool, source documents are unavailable, or the hard task is laboratory/physical inspection rather than paperwork. A polite positive response is not validation.

## 2. CleanPath: plan field visits without carrying invasive species between sites

**Pitch:** Plan a conservation crew's day around site status and its approved cleaning protocol, then show exactly where an ordinary route would violate that protocol.

### Evidence for the task

The U.S. Department of the Interior explicitly advises arranging work so native habitat is visited before disturbed locations, alongside equipment cleaning and inspection. The University of Connecticut's invasive-plant guidance also addresses moving equipment from non-invaded to invaded sites and cleaning between work areas. These establish that visit order matters. They do not demonstrate that staff need a new route-planning product. [DOI protocol](https://www.doi.gov/node/62811), [UConn guidance](https://cipwg.uconn.edu/bmps-for-movement-of-topsoil-mulch-and-equipment/)

This is a recurring task for crews working across multiple sites, unlike selecting an intervention once for a school. It only has enough complexity to justify software when site status, shared equipment, access times, and cleaning opportunities interact.

### Proposed workflow and demo

Import six fictional sites, their documented status, access windows, crew assignments, travel times, and an approved protocol. Compare a shortest-travel route against a route satisfying the configured constraints. Show a problematic transition, an inserted cleaning stop or changed visit order, and its time cost. Then close a cleaning station and recompute; report an infeasible schedule when appropriate.

Track contamination status separately for relevant equipment, not as one simplistic clean/dirty flag for every biological risk. Unknown site status must remain unknown. The prototype demonstrates compliance with entered rules, not biological safety or a measured probability of invasion. It must not invent chemical treatments or universal drying times.

The technical core is a small constrained routing/state-transition solver with an explainable map. AI can help turn a supplied protocol into draft constraints, which the user confirms. The solver and evidence trace provide substance beyond a chatbot.

### Existing solutions and novelty limit

**Farm Health Guardian Protocol Truck & Trailer already supports biosecurity route review, movement history, wash rules, and breach alerts for livestock operations.** Therefore, the general concept of biosecurity-aware routing is demonstrably not new. [Product documentation](https://farmhealthguardian.com/protocol-truck-trailer/)

**Outway** already supports conservation field operations, invasive-species management, and treatment planning. Its public overview does not settle whether it supports this exact constraint model. Absence from the overview is not proof of absence from the product. [Outway](https://www.outway.io/)

The proposed differentiation is a lightweight conservation-specific workflow for small field crews, shared boots/tools, site access windows, and locally approved protocols. This is a domain adaptation, not a new scientific method. Its visual demo could be stronger than SeedProof, but its competitive novelty is weaker.

### Validation and kill criteria

Ask a field coordinator how their last multi-site day was ordered, what changed when a site became restricted, and whether shared equipment made scheduling difficult. Obtain a nonsensitive example without publishing vulnerable habitat locations. Compare existing planning effort against a prototype.

Drop this idea if staff reliably solve the task with a short checklist, existing field software already handles it, or there is no confirmed recurring multi-site workload. Do not add complexity merely to make a solver look necessary.

## What the searches ruled out

| Candidate | Need signal | Existing overlap | Decision |
|---|---|---|---|
| Native-plant stock finder | Community discussion about nursery availability; nursery inventory caveats | Plant Agents already catalogs nursery inventory | Reject generic finder |
| Repair-cafe matching/pre-registration | Repair communities need information before an event | RepairConnects already registers devices and connects repairers | Reject generic matching |
| Shared spare-parts marketplace | Restarters members discussed parts inventories and data access | Existing community experiments and supplier ecosystems | Reject generic marketplace; no verified compatibility-data gap yet |
| Camera-trap clock/effort checker | Research documents timestamp and deployment problems | camtrapR and Wildlife Insights already address substantial data management and QA | Reject general checker |
| Volunteer water-sample tracking | Documented quality and sample-handling requirements | Water Rangers and SampleServe cover adjacent collection, scheduling, custody and reporting | Reject broad tracking app |
| General seed mix designer | Restoration supply need | Seed-Spec, supplier tools and QA portals | Reject generic mix design |

The Restarters discussion is especially useful because it records actual community experimentation with Partkeepr and concerns about access to component data. It is dated 2022: useful historical evidence, not confirmation of the community's current tooling. [Community discussion](https://talk.restarters.net/t/building-a-spare-parts-marketplace/7091)

Supporting competitor sources: [Plant Agents](https://plantagents.org/), [RepairConnects](https://www.repairconnects.org/), [camtrapR](https://jniedballa.github.io/camtrapR/), [camera-trap workflow research](https://pmc.ncbi.nlm.nih.gov/articles/PMC6953665/), [Water Rangers](https://waterrangers.com/training/protocol/testing-season/), [SampleServe](https://www.sampleserve.com/).

Reddit posts were used as leads, not representative surveys. Some direct Reddit pages and a Wiley conservation-data paper could not be retrieved, so their inaccessible full contents do not support the finalists. The paper about nature-technology integration remains a research lead rather than a validated opportunity.

## Honest collaboration and next decision

At present the accurate claim is: **“Our problem research draws on published restoration guidance and public practitioner discussions.”** We have not interviewed, collaborated with, or received endorsement from any named organization.

An interview supports “informed by feedback from…” when the person agrees to attribution. A reviewed prototype supports a specific claim about that review. “Co-designed with” or “collaborated with” requires actual joint work and agreement about attribution. Never turn reading a group's website or an unanswered message into collaboration. Do not use logos or imply organizational endorsement from one individual's informal reply.

The immediate recommendation is to validate SeedProof's document-reconciliation gap with a practitioner and ask existing vendors whether it is already covered. CleanPath is the backup research direction. There is deliberately no third recommendation: promoting another crowded idea just to fill three slots would repeat the earlier mistake.

See VALIDATION_OUTREACH.md for ready-to-edit messages. These are drafts only; none were sent. User authorization is needed before contacting external people.
