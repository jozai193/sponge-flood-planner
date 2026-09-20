/* Generated from canonical schema. Run scripts/generate-types.mjs. */

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
