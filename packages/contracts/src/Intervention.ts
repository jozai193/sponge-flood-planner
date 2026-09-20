/* Generated from canonical schema. Run scripts/generate-types.mjs. */

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
