/* Generated from canonical schema. Run scripts/generate-types.mjs. */

export type Engine = "cpu-hll" | "webgl2-hll";
export type Version = "0.1.0";
export type Cfl = number;
export type DtMaxS = number;
export type DryDepthM = number;
export type SpatialOrder = 1 | 2;
export type Boundary = "closed" | "open";
export type OutputIntervalS = number;

export interface SolverConfig {
  engine?: Engine;
  version?: Version;
  cfl?: Cfl;
  dt_max_s?: DtMaxS;
  dry_depth_m?: DryDepthM;
  spatial_order?: SpatialOrder;
  boundary?: Boundary;
  output_interval_s?: OutputIntervalS;
}
