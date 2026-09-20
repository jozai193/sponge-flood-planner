import type {GIKind} from './interventions';

export interface InterventionCatalogEntry {
  kind:GIKind; label:string;
  defaults:{excavationM:number;storageDepthM:number;conductivityMmH:number;percolationMmH:number;roughness:number;swaleSlopePercent:number;cloggingPercent:number};
  limits:{excavationM:[number,number];storageDepthM:[number,number];conductivityMmH:[number,number];percolationMmH:[number,number];swaleSlopePercent:[number,number]};
  sourceIds:string[]; note:string;
}

export const INTERVENTION_SOURCES={
  'epa-swmm':{title:'EPA Storm Water Management Model — LID controls',url:'https://www.epa.gov/water-research/storm-water-management-model-swmm'},
  'epa-gi-types':{title:'EPA Types of Green Infrastructure',url:'https://www.epa.gov/green-infrastructure/types-green-infrastructure'},
  'epa-rain-garden':{title:'EPA Green Infrastructure Toolbox — Rain Gardens',url:'https://www.epa.gov/system/files/documents/2022-04/green-infrastructure-toolbox_raingardens.pdf'},
  'nrcs-rain-garden':{title:'USDA NRCS Stream Restoration Field Guide — Rain Gardens',url:'https://www.nrcs.usda.gov/sites/default/files/2024-10/Stream%20Restoration%20Field%20Guide_july%202012.pdf'},
  'nrcs-infiltration':{title:'USDA NRCS Infiltration Basins plant materials guidance',url:'https://www.nrcs.usda.gov/plantmaterials/idpmcar2261.pdf'},
} as const;

const shared={conductivityMmH:[0,3600] as [number,number],percolationMmH:[0,3600] as [number,number],swaleSlopePercent:[0,6] as [number,number]};
export const INTERVENTION_CATALOG:Record<GIKind,InterventionCatalogEntry>={
  rain_garden:{kind:'rain_garden',label:'Rain garden',defaults:{excavationM:.15,storageDepthM:.15,conductivityMmH:20,percolationMmH:0,roughness:.1,swaleSlopePercent:0,cloggingPercent:0},limits:{excavationM:[0,.3],storageDepthM:[0,2],...shared},sourceIds:['epa-rain-garden','nrcs-rain-garden','epa-swmm'],note:'NRCS describes about 6 in (0.1524 m) maximum surface ponding and EPA notes site infiltration and maintenance screening. The wider 0–0.3 m software bound supports sensitivity tests and is not a recommendation.'},
  bioswale:{kind:'bioswale',label:'Bioswale',defaults:{excavationM:.2,storageDepthM:.15,conductivityMmH:20,percolationMmH:0,roughness:.1,swaleSlopePercent:1,cloggingPercent:0},limits:{excavationM:[0,3],storageDepthM:[0,2],...shared},sourceIds:['epa-gi-types','epa-swmm'],note:'EPA recognizes vegetated swales as conveyance and treatment controls. Cross-section, grade and media must be engineered for the site.'},
  permeable_pavement:{kind:'permeable_pavement',label:'Permeable pavement',defaults:{excavationM:0,storageDepthM:.15,conductivityMmH:20,percolationMmH:0,roughness:.03,swaleSlopePercent:0,cloggingPercent:0},limits:{excavationM:[0,0],storageDepthM:[0,2],...shared},sourceIds:['epa-gi-types','epa-swmm'],note:'EPA/SWMM distinguish pavement and storage layers. Surface grade is preserved here; clogging is an explicit sensitivity assumption.'},
  detention_basin:{kind:'detention_basin',label:'Detention basin',defaults:{excavationM:.2,storageDepthM:0,conductivityMmH:20,percolationMmH:0,roughness:.1,swaleSlopePercent:0,cloggingPercent:0},limits:{excavationM:[0,3],storageDepthM:[0,0],...shared},sourceIds:['epa-swmm','nrcs-infiltration'],note:'Resolved surface depression is the only storage counted for this screening basin. Outlet sizing and drawdown must be checked by an engineer.'},
};

export function catalogSourceText(kind:GIKind){
  const entry=INTERVENTION_CATALOG[kind];
  return `${entry.sourceIds.map(id=>INTERVENTION_SOURCES[id as keyof typeof INTERVENTION_SOURCES].title).join('; ')}. ${entry.note}`;
}
