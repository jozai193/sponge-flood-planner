/** Shared claim boundaries for the app and portable comparison evidence. */
export const validationStatus={
 status:'exploratory_screening',
 generalFloodAccuracyValidated:false,
 summary:'Exploratory screening: general real-world flood accuracy remains unvalidated.',
 numericalEvidence:'Conservation, reference comparisons and automated checks support numerical behavior; they do not establish accuracy at this location.',
 planning:'Site eligibility, soil properties, installation costs and maintenance assumptions require verification. Maintenance values are included only where supplied.',
 damage:'Monetary damage estimates are unavailable because defensible building valuations are missing.',
 terrain:'Terrain resolution and survey age can hide small creeks, barriers and drains. Source coverage varies by location.',
} as const;
