/* Generated from canonical schema. Run scripts/generate-types.mjs. */

export type Kind = "waterways" | "catchments" | "buildings" | "landcover" | "observations";
export type Title = string;
export type Attribution = string;
export type ObservedAt = string;
export type HorizontalCrs = string;
export type VerticalDatum = string;
export type License = string;
export type Provenance = "surveyed" | "provider_estimate" | "user_assumption";
/**
 * @minItems 1
 * @maxItems 20000
 */
export type Features = [
  {
    [k: string]: unknown;
  },
  ...{
    [k: string]: unknown;
  }[]
];

export interface VectorSurvey {
  kind: Kind;
  source: SurveySource;
  features: Features;
}
export interface SurveySource {
  title: Title;
  attribution: Attribution;
  observed_at: ObservedAt;
  horizontal_crs: HorizontalCrs;
  vertical_datum: VerticalDatum;
  license: License;
  provenance: Provenance;
}
