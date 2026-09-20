import type {ControlRating} from '../simulation/src/facilities';
import {validateGPUInput,type GPUInput} from '../simulation/src/gpu';
import {INTERVENTION_CATALOG} from './intervention-catalog';
export type GIKind='rain_garden'|'bioswale'|'permeable_pavement'|'detention_basin';
export interface DesignControl {rating?:ControlRating;targetCell:number|null;crestDepthM:number;ratePerS:number;maxFlowM3S:number}
export interface CostBreakdown {sitePreparationMinor:number;materialsMinor:number;installationMinor:number;contingencyMinor:number;annualMaintenanceMinor:number;currency:'USD';priceYear:number;basis:string}
export interface CandidateEvidence {parcelIds:string[];sourceNote:string;geometryId:string;protectedReasons?:string[]}
export interface PhysicalDesign {id:string;kind:GIKind;planningConstraint?:'optional'|'locked'|'excluded';surfaceControl?:DesignControl;underdrain?:DesignControl;cloggingFraction?:number;swaleSlope?:number;swaleAxis?:'x'|'y';cells:number[];eligibility:'confirmed'|'user_assumed'|'unverified';excavationM:number;storageDepthM:number;conductivityMS:number;percolationMS:number;roughness:number;costMinor:number;costBreakdown?:CostBreakdown;candidateEvidence?:CandidateEvidence;parameterSource:string}
/** Compile immutable physical edits. Surface excavation is not subsurface capacity. */
export function compileDesign(base:GPUInput,designs:PhysicalDesign[],budgetMinor:number):GPUInput{
  validateGPUInput(base);if(!Number.isSafeInteger(budgetMinor)||budgetMinor<0)throw new Error('Invalid budget');
  const out:GPUInput={...base,facilityLinks:[...(base.facilityLinks??[])],z:base.z.slice(),capacity:base.capacity.slice(),infiltration:base.infiltration.slice(),roughness:base.roughness.slice(),percolation:base.percolation?.slice()??new Float32Array(base.nx*base.ny)};
  const occupied=new Set<number>(),ids=new Set<string>();let cost=0;
  for(const design of designs){
    if(!['rain_garden','bioswale','permeable_pavement','detention_basin'].includes(design.kind))throw new Error('Unknown intervention type');
    if(design.planningConstraint!==undefined&&!['optional','locked','excluded'].includes(design.planningConstraint))throw new Error('Invalid planning constraint');
    if(ids.has(design.id))throw new Error('Duplicate design');ids.add(design.id);
    if(!['confirmed','user_assumed'].includes(design.eligibility))throw new Error('Site eligibility must be confirmed or explicitly assumed');
    if(!design.parameterSource.trim())throw new Error('Parameter source or assumption required');
    if(!Number.isSafeInteger(design.costMinor)||design.costMinor<0)throw new Error('Invalid installation cost');
    if(design.candidateEvidence?.protectedReasons?.length)throw new Error('Candidate is protected: '+design.candidateEvidence.protectedReasons.join(', '));
    if(design.costBreakdown){const c=design.costBreakdown,values=[c.sitePreparationMinor,c.materialsMinor,c.installationMinor,c.contingencyMinor,c.annualMaintenanceMinor];if(values.some(v=>!Number.isSafeInteger(v)||v<0))throw new Error('Invalid cost line item');if(c.currency!=='USD'||!Number.isInteger(c.priceYear)||c.priceYear<2000||c.priceYear>2100||!c.basis.trim())throw new Error('Cost currency, price year and basis are required');if(c.sitePreparationMinor+c.materialsMinor+c.installationMinor+c.contingencyMinor!==design.costMinor)throw new Error('Capital cost line items do not equal design cost');}
    cost+=design.costMinor;
    if(cost>budgetMinor)throw new Error('Design exceeds budget');
    for(const [value,max] of [[design.excavationM,3],[design.storageDepthM,2],[design.conductivityMS,.001],[design.percolationMS,.001],[design.roughness,.5]])if(!Number.isFinite(value)||value<0||value>max)throw new Error('Invalid physical parameter');
    if(!design.cells.length)throw new Error('Empty design');
    if(design.kind==='detention_basin'&&design.storageDepthM!==0)throw new Error('Resolved detention storage cannot also count as subsurface storage');
    if(design.kind==='permeable_pavement'&&design.excavationM!==0)throw new Error('Pavement preserves surface grade; reservoir is below ground');
    const limits=INTERVENTION_CATALOG[design.kind].limits,conductivityMmH=design.conductivityMS*3_600_000,percolationMmH=design.percolationMS*3_600_000;
    if(design.excavationM<limits.excavationM[0]||design.excavationM>limits.excavationM[1]||design.storageDepthM<limits.storageDepthM[0]||design.storageDepthM>limits.storageDepthM[1]||conductivityMmH<limits.conductivityMmH[0]||conductivityMmH>limits.conductivityMmH[1]||percolationMmH<limits.percolationMmH[0]||percolationMmH>limits.percolationMmH[1])throw new Error('Physical dimensions fall outside the catalogue safety bounds');
    const clogging=design.cloggingFraction??0,slope=design.swaleSlope??0;
    if(!Number.isFinite(clogging)||clogging<0||clogging>1||!Number.isFinite(slope)||slope<limits.swaleSlopePercent[0]/100||slope>limits.swaleSlopePercent[1]/100)throw new Error('Invalid clogging or swale slope');
    if(clogging&&design.kind!=='permeable_pavement')throw new Error('Clogging applies to pavement only');
    if(slope&&design.kind!=='bioswale')throw new Error('Channel grading applies to bioswales only');
    if(design.swaleAxis!==undefined&&!['x','y'].includes(design.swaleAxis))throw new Error('Invalid swale axis');
    if(design.underdrain&&design.storageDepthM<=0)throw new Error('Underdrain requires subsurface storage');
    const axis=design.swaleAxis??'x';
    const coordinate=(cell:number)=>axis==='x'?(cell%base.nx)*base.dx:Math.floor(cell/base.nx)*base.dy;
    const origin=Math.min(...design.cells.map(coordinate));
    const gradeLevel=Math.min(...design.cells.map(cell=>base.z[cell]));
    for(const cell of design.cells){if(!Number.isInteger(cell)||cell<0||cell>=base.z.length||base.solid[cell])throw new Error('Invalid or building-covered site');if(base.planningWaterMask?.[cell])throw new Error('Intervention overlaps mapped permanent water');if(occupied.has(cell))throw new Error('Overlapping designs');occupied.add(cell);
      out.z[cell]=design.kind==='bioswale'&&slope>0?gradeLevel-design.excavationM-slope*(coordinate(cell)-origin):base.z[cell]-design.excavationM;out.capacity[cell]=design.storageDepthM;out.infiltration[cell]=design.conductivityMS*(1-clogging);out.percolation![cell]=design.percolationMS;out.roughness[cell]=design.roughness;
      for(const [reservoir,control] of [['surface',design.surfaceControl],['subsurface',design.underdrain]] as const)if(control){
        if(control.targetCell!==null&&design.cells.includes(control.targetCell))throw new Error('Choose a discharge receiver outside the facility');
        out.facilityLinks!.push({...control,rating:control.rating?(control.rating.kind==='orifice'?{...control.rating,areaM2:control.rating.areaM2/design.cells.length}:{...control.rating,widthM:control.rating.widthM/design.cells.length}):undefined,cell,reservoir,maxFlowM3S:control.maxFlowM3S/design.cells.length,source:design.parameterSource});
      }
    }
  }
  if(designs.some(d=>d.surfaceControl?.rating))out.maxStepS=Math.min(out.maxStepS??10,.2);
  validateGPUInput(out);return out;
}
