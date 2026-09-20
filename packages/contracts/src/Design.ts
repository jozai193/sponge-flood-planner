/* Generated from canonical schema. Run scripts/generate-types.mjs. */

export type SchemaVersion = "sponge.v1";
export type Id = string;
export type Kind = "rain_garden" | "bioswale" | "permeable_pavement" | "detention_basin";
/**
 * @minItems 1
 * @maxItems 100000
 */
export type Cells = [number, ...number[]];
export type ExcavationM = number;
export type ConductivityMS = number;
export type StorageDepthM = number;
export type Roughness = number;
export type PercolationMS = number;
export type CostMinor = number;
export type Eligibility = "confirmed" | "user_assumed" | "unverified";
export type SourceIds = string[];
/**
 * @maxItems 100
 */
export type Interventions = Intervention[];
export type BudgetMinor = number;
export type Currency = string;
export type PriceYear = number;
export type LockedIds = string[];
export type ExcludedIds = string[];

export interface Design {
  schema_version?: SchemaVersion;
  interventions?: Interventions;
  budget_minor?: BudgetMinor;
  currency?: Currency;
  price_year?: PriceYear;
  locked_ids?: LockedIds;
  excluded_ids?: ExcludedIds;
}
export interface Intervention {
  id: Id;
  kind: Kind;
  cells: Cells;
  excavation_m?: ExcavationM;
  conductivity_m_s?: ConductivityMS;
  storage_depth_m?: StorageDepthM;
  roughness?: Roughness;
  percolation_m_s?: PercolationMS;
  cost_minor: CostMinor;
  eligibility?: Eligibility;
  source_ids?: SourceIds;
}
