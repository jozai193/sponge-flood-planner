# SeedProof gap validation

10 September 2026 — public-source validation only. No interviews, vendor demonstrations, outreach, or product tests were performed.

## Verdict

**The workflow problem is supported. Demand for a separate product, and an unserved competitive gap, are not validated.** Do not commit to SeedProof as a high-novelty hackathon entry on this evidence alone. This narrows the earlier recommendation in PAIN_POINT_RESEARCH.md: SeedProof remains a candidate for practitioner testing, not an established missing product.

| Test | Result | Interpretation |
|---|---|---|
| Do practitioners encounter difficult or incomplete labels? | Supported by explicit technical guidance | Stronger than inferring paperwork problems from seed shortages |
| Does comparing delivered/planted seed to a plan already happen? | Yes; an existing certification worksheet supports it | We would automate an established workflow |
| Is there existing seed quality software? | Yes, substantial adjacent capabilities | Broad seed QA and traceability are not novel |
| Did this search find a verified identical buyer-side document importer? | No confirmed exact match | This does not establish absence |
| Do target users spend enough time on this to adopt another tool? | Unknown | No measured workload, error rate, or adoption evidence |
| Can software remedy missing tests or unavailable seed? | No | It can identify missing evidence, not create it |

## Strongest evidence: a concrete workflow, with an existing solution

NRCS Technical Note MT-125 (revision 2, March 2022), for Montana and Wyoming, explicitly describes confusing or incomplete mixture labels. Pages 3–4 explain a certification worksheet, comparison with planned quantities, and vendor follow-up when information is missing. Its examples distinguish a species' share of a mixture from species purity. A label reader that merges those fields could generate plausible but incorrect results. This supports a real interpretation task, while showing that the calculation and comparison already have an established method. It is regional guidance, not a universal current standard. [NRCS technical note](https://www.nrcs.usda.gov/plantmaterials/mtpmctn13828.pdf)

The important product hypothesis is therefore **assisted transfer of heterogeneous source documents into an existing review workflow**, with explicit unresolved fields and provenance. It is not “AI discovers whether restoration seed is good.”

## Competitor findings

| Existing option | Publicly documented capability | What remains unverified |
|---|---|---|
| ERP for Seed | Lot genealogy; germination, purity and viability results; approvals; inspection and certification records | Import and reconciliation of arbitrary external restoration specifications and label photos |
| Strinos ERP | Seed-lot quality details, unit equivalents, blends, tags and lot/laboratory documents | The exact buyer-side cross-document workflow |
| PAT Horticulture | Seed QA thresholds and automatic stock release/blocking | External restoration-project rules and document extraction |
| Seed-Spec | Site-specific native seed-blend design | Delivery-document auditing; public positioning alone does not settle all features |
| Diversity Native Seeds | Customer quality/provenance portal and mix design | Cross-supplier procurement review |

Sources: [ERP for Seed](https://erpforseed.com/quality-traceability-compliance/), [Strinos](https://www.strinos.com/industries/seed), [PAT](https://pat-horticulture.com/seed-production/), [Seed-Spec](https://seedspec.com/), [Diversity Native Seeds](https://diversitynativeseeds.com.au/portal/).

These are vendor descriptions, not independently tested capabilities. Supplier production software is not necessarily accessible or appropriate for a small restoration buyer. Conversely, “it serves suppliers” is insufficient evidence that buyers lack a solution. Procurement systems, consultants, spreadsheets, and generic document extraction also compete for this task.

## What users say they need may be a different problem

River Partners described difficulties finding and affording high-quality native seed when announcing its supply initiative in February 2022. That supports a supply problem, not evidence that document reconciliation is the bottleneck. [River Partners](https://riverpartners.org/news/native-seed-and-plants-its-in-our-dna/)

The Australian Native Seed Survey, conducted in 2016–2017 and reported in 2020, documents variable testing practices and buyer expectations. This is useful historical, jurisdiction-specific evidence about quality information; it cannot establish present demand for a U.S. document tool. Missing laboratory data cannot be recovered through OCR. [ANPC report](https://www.anpc.asn.au/wp-content/uploads/2020/03/ANPC_NativeSeedSurveyReport_WEB.pdf)

The Tallgrass Prairie Center's March 2020 stakeholder meeting brought together consumers, producers, researchers and analysts. It identified needs around restoration performance, quality assurance, research and communication. It is a summarized meeting record, not a transcript or a request for SeedProof. [Meeting report](https://tallgrassprairiecenter.org/sites/default/files/inline-uploads/Plant%20Materials/report-on-nssm-2020.pdf)

## Decision and remaining validation

**Hold the build.** There is enough evidence to justify a focused interview, but not enough to claim a novel unmet need. The surviving proposition is a convenience/accuracy improvement whose value must be measured.

Use the existing outreach drafts to seek a practitioner who actually accepts restoration seed deliveries. Ask for their last difficult case before presenting the concept. Obtain a redacted specification, relevant label, and the completed review. Establish what they did, how long it took, how often it occurs, and which tool they use. Ask vendors explicitly about external-document import rather than inferring feature absence from marketing pages.

A proposed validation threshold—not a scientific market-size test—is two independent practitioners describing recurring reconciliation work, at least one usable redacted case, and a correct assisted review that materially improves their existing process without adding false alarms. Passing would justify a scoped prototype; it would not prove a market or ecological impact. Stop if the main obstacle is physical seed supply/testing, if the incumbent workflow is quick, or if an available product already meets the need.

Accurate public wording today: “Published guidance identifies seed-label interpretation and documentation challenges; we are investigating whether assisted document review would help.” No collaboration, endorsement, customer validation, or verified market gap may be claimed from this research.
