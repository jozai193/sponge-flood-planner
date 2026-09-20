/* Generated from canonical schema. Run scripts/generate-types.mjs. */

export type Kind = "drainage";
export type Title = string;
export type Attribution = string;
export type ObservedAt = string;
export type HorizontalCrs = string;
export type VerticalDatum = string;
export type License = string;
export type Provenance = "surveyed" | "provider_estimate" | "user_assumption";
/**
 * @minItems 1
 * @maxItems 10000
 */
export type Nodes = [DrainNode, ...DrainNode[]];
export type Id = string;
export type X = number;
export type Y = number;
export type InvertM = number;
export type GroundM = number;
export type Kind1 = "inlet" | "junction" | "outfall";
export type InletCapacityM3S = number | null;
export type TailwaterM = number | null;
export type StorageAreaM2 = number | null;
export type InitialDepthM = number;
export type InletCurve = [[unknown, unknown], [unknown, unknown], ...[unknown, unknown][]] | null;
export type Id1 = string;
export type FromNode = string;
export type ToNode = string;
export type DiameterM = number;
export type LengthM = number;
export type ManningN = number;
/**
 * @maxItems 20000
 */
export type Pipes = DrainPipe[];

export interface DrainageSurvey {
  kind?: Kind;
  source: SurveySource;
  nodes: Nodes;
  pipes: Pipes;
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
export interface DrainNode {
  id: Id;
  x: X;
  y: Y;
  invert_m: InvertM;
  ground_m: GroundM;
  kind: Kind1;
  inlet_capacity_m3_s?: InletCapacityM3S;
  tailwater_m?: TailwaterM;
  storage_area_m2?: StorageAreaM2;
  initial_depth_m?: InitialDepthM;
  inlet_curve?: InletCurve;
}
export interface DrainPipe {
  id: Id1;
  from_node: FromNode;
  to_node: ToNode;
  diameter_m: DiameterM;
  length_m: LengthM;
  manning_n: ManningN;
}
