/* Generated from canonical schema. Run scripts/generate-types.mjs. */

export type Nx = number;
export type Ny = number;
export type DxM = number;
export type DyM = number;
export type Crs = string;
export type OriginXM = number;
export type OriginYM = number;
export type ElevationOriginM = number;
export type RowDirection = "north";
export type VerticalDatum = string;

export interface Grid {
  nx: Nx;
  ny: Ny;
  dx_m: DxM;
  dy_m: DyM;
  crs?: Crs;
  origin_x_m?: OriginXM;
  origin_y_m?: OriginYM;
  elevation_origin_m?: ElevationOriginM;
  row_direction?: RowDirection;
  vertical_datum?: VerticalDatum;
}
