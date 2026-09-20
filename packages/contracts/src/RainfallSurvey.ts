/* Generated from canonical schema. Run scripts/generate-types.mjs. */

export type Kind = "rainfall";
export type Title = string;
export type Attribution = string;
export type ObservedAt = string;
export type HorizontalCrs = string;
export type VerticalDatum = string;
export type License = string;
export type Provenance = "surveyed" | "provider_estimate" | "user_assumption";
export type SchemaVersion = "sponge.v1";
export type Name = string;
export type DurationS = number;
export type RecessionS = number;
export type DepthM = number;
/**
 * @minItems 1
 * @maxItems 10000
 */
export type Intervals = [RainInterval, ...RainInterval[]];
export type StartS = number;
export type EndS = number;
export type RateMS = number;
export type ReturnPeriodYears = number | null;
export type SourceIds = string[];
export type Distribution = string;
export type AntecedentSaturation = number;

export interface RainfallSurvey {
  kind?: Kind;
  source: SurveySource;
  storm: Storm;
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
export interface Storm {
  schema_version?: SchemaVersion;
  name: Name;
  duration_s: DurationS;
  recession_s: RecessionS;
  depth_m: DepthM;
  intervals: Intervals;
  return_period_years?: ReturnPeriodYears;
  source_ids?: SourceIds;
  distribution?: Distribution;
  antecedent_saturation?: AntecedentSaturation;
}
export interface RainInterval {
  start_s: StartS;
  end_s: EndS;
  rate_m_s: RateMS;
}
