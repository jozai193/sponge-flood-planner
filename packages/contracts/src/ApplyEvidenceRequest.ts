/* Generated from canonical schema. Run scripts/generate-types.mjs. */

export type Buildings = boolean;
export type Landcover = boolean;
export type AcceptExploratoryMaterials = boolean;

export interface ApplyEvidenceRequest {
  buildings?: Buildings;
  landcover?: Landcover;
  accept_exploratory_materials?: AcceptExploratoryMaterials;
}
