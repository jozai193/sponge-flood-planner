/* Generated from canonical schema. Run scripts/generate-types.mjs. */

export type Title = string;
export type Attribution = string;
export type ObservedAt = string;
export type HorizontalCrs = string;
export type VerticalDatum = string;
export type License = string;
export type Provenance = "surveyed" | "provider_estimate" | "user_assumption";

export interface SurveySource {
  title: Title;
  attribution: Attribution;
  observed_at: ObservedAt;
  horizontal_crs: HorizontalCrs;
  vertical_datum: VerticalDatum;
  license: License;
  provenance: Provenance;
}
