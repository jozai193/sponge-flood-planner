/* Generated from canonical schema. Run scripts/generate-types.mjs. */

export type Version = 2;
export type Engine = string;
export type Nx = number;
export type Ny = number;
export type DxM = number;
export type DyM = number;
export type HorizontalCrs = string;
export type VerticalDatum = string;
export type ElevationOriginM = number | null;
export type BundleId = string | null;
export type Version1 = 2;
export type Rainfall = boolean;
export type External = boolean;
export type Coastal = boolean;
export type Duration = number;
export type Recession = number;
export type Depth = number;
export type Intervals = [Interval, ...Interval[]] | null;
export type StartS = number;
export type EndS = number;
export type RateMS = number;
export type Edge = "west" | "east" | "south" | "north";
/**
 * @minItems 1
 * @maxItems 2048
 */
export type Cells = [number, ...number[]];
/**
 * @minItems 1
 * @maxItems 10000
 */
export type Levels = [Level, ...Level[]];
export type Times = number;
export type Elevationm = number;
export type Source = string;
export type Datum = string;
/**
 * @maxItems 2048
 */
export type SegmentIds = string[];
export type SourceKind = "measured" | "modelled" | "assumed";
export type SourceEpoch = string;
export type VerticalTransform = string;
export type CoverageStartS = number | null;
export type CoverageEndS = number | null;
export type BathymetryStatus = "verified" | "missing" | "not_required";
export type ChannelSupportStatus = "verified" | "missing" | "not_required";
export type Cell = number;
export type Flowm3S = number;
export type Starts = number;
export type Ends = number;
export type Source1 = string;
/**
 * @maxItems 4194304
 */
export type Inflows = Inflow[];
export type Cell1 = number;
export type Crestdepthm = number;
export type Ratepers = number;
export type Maxflowm3S = number;
export type Tailwaterelevationm = number | null;
export type Source2 = string;
/**
 * @maxItems 4194304
 */
export type Outlets = Outlet[];
/**
 * @maxItems 32
 */
export type RequiredCapabilities = string[];
export type ExecutionInputHash = string | null;

export interface ScenarioSpecV2 {
  version: Version;
  engine: Engine;
  domain: ScenarioDomain;
  forcing: ScenarioForcing;
  required_capabilities: RequiredCapabilities;
  execution_input_hash?: ExecutionInputHash;
}
export interface ScenarioDomain {
  nx: Nx;
  ny: Ny;
  dx_m: DxM;
  dy_m: DyM;
  horizontal_crs: HorizontalCrs;
  vertical_datum: VerticalDatum;
  elevation_origin_m?: ElevationOriginM;
  bundle_id?: BundleId;
}
export interface ScenarioForcing {
  version: Version1;
  components: Components;
  storm: ScenarioStorm;
  coastal?: Coast | null;
  inflows: Inflows;
  outlets: Outlets;
}
export interface Components {
  rainfall: Rainfall;
  external: External;
  coastal: Coastal;
}
export interface ScenarioStorm {
  duration: Duration;
  recession: Recession;
  depth: Depth;
  intervals?: Intervals;
}
export interface Interval {
  start_s: StartS;
  end_s: EndS;
  rate_m_s: RateMS;
}
export interface Coast {
  edge: Edge;
  cells: Cells;
  levels: Levels;
  source: Source;
  datum: Datum;
  segment_ids?: SegmentIds;
  source_kind?: SourceKind;
  source_epoch?: SourceEpoch;
  vertical_transform?: VerticalTransform;
  coverage_start_s?: CoverageStartS;
  coverage_end_s?: CoverageEndS;
  bathymetry_status?: BathymetryStatus;
  channel_support_status?: ChannelSupportStatus;
}
export interface Level {
  timeS: Times;
  elevationM: Elevationm;
}
export interface Inflow {
  cell: Cell;
  flowM3S: Flowm3S;
  startS: Starts;
  endS: Ends;
  source: Source1;
}
export interface Outlet {
  cell: Cell1;
  crestDepthM: Crestdepthm;
  ratePerS: Ratepers;
  maxFlowM3S: Maxflowm3S;
  tailwaterElevationM?: Tailwaterelevationm;
  source: Source2;
}
