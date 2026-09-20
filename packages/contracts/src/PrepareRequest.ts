/* Generated from canonical schema. Run scripts/generate-types.mjs. */

export type Longitude = number;
export type Latitude = number;
export type ExtentM = number;
export type GridCells = number;
export type Source = "auto" | "terrarium" | "usgs_1m";
export type Label = string;
export type CountryCode = string | null;
export type Currency = string;

export interface PrepareRequest {
  longitude: Longitude;
  latitude: Latitude;
  extent_m?: ExtentM;
  grid_cells?: GridCells;
  source?: Source;
  label?: Label;
  country_code?: CountryCode;
  currency?: Currency;
}
