import type {PhysicalDesign} from '../domain/interventions';
import type {GPUInput} from '../simulation/src/gpu';

export interface InterventionEffectFrame {
  depth: Float32Array;
  maxDepth: Float32Array;
  subsurfaceDepth?: Float32Array;
  ledger: Record<string, number>;
}
export interface DesignEffect {
  id: string;
  kind: PhysicalDesign['kind'];
  surfaceM3: number;
  belowGroundM3: number;
  waterAtFootprintM3: number;
  baselineWaterAtFootprintM3: number;
  configuredStorageM3: number;
  fillFraction: number;
  status: 'ready'|'receiving_runoff'|'holding_water'|'at_capacity';
}

function finite(value: number|undefined){return Number.isFinite(value)?value!:0;}

/**
 * Derives explanatory replay values from solver output. These values describe
 * water at intervention cells; they do not infer avoided damage or claim that
 * every stored litre came from the intervention.
 */
export function interventionEffects(input:GPUInput,baseline:InterventionEffectFrame,planned:InterventionEffectFrame,designs:PhysicalDesign[],depthDeltaM=.05){
  const count=input.nx*input.ny,area=input.dx*input.dy;
  for(const frame of [baseline,planned]){
    if(frame.depth.length!==count||frame.maxDepth.length!==count||(frame.subsurfaceDepth&&frame.subsurfaceDepth.length!==count))throw new Error('Invalid intervention replay frame');
  }
  if(!Number.isFinite(depthDeltaM)||depthDeltaM<0)throw new Error('Invalid intervention depth threshold');
  const occupied=new Set<number>();
  const byDesign:DesignEffect[]=designs.map(design=>{
    let surfaceM3=0,belowGroundM3=0,baselineWaterAtFootprintM3=0;
    for(const cell of design.cells){
      if(!Number.isInteger(cell)||cell<0||cell>=count||occupied.has(cell))throw new Error('Invalid intervention replay cells');
      occupied.add(cell);
      const surface=planned.depth[cell],below=planned.subsurfaceDepth?.[cell]??0,baselineSurface=baseline.depth[cell],baselineBelow=baseline.subsurfaceDepth?.[cell]??0;
      if(![surface,below,baselineSurface,baselineBelow].every(v=>Number.isFinite(v)&&v>=-1e-6))throw new Error('Invalid intervention replay water');
      surfaceM3+=Math.max(0,surface)*area;belowGroundM3+=Math.max(0,below)*area;
      baselineWaterAtFootprintM3+=(Math.max(0,baselineSurface)+Math.max(0,baselineBelow))*area;
    }
    const configuredStorageM3=design.cells.length*area*(design.excavationM+design.storageDepthM),waterAtFootprintM3=surfaceM3+belowGroundM3;
    const fillFraction=configuredStorageM3>0?Math.min(1,waterAtFootprintM3/configuredStorageM3):0;
    const status:DesignEffect['status']=fillFraction>=.995?'at_capacity':surfaceM3>.001?'receiving_runoff':belowGroundM3>.001?'holding_water':'ready';
    return {id:design.id,kind:design.kind,surfaceM3,belowGroundM3,waterAtFootprintM3,baselineWaterAtFootprintM3,configuredStorageM3,fillFraction,status};
  });
  let improvedAreaM2=0,worsenedAreaM2=0;
  for(let cell=0;cell<count;cell++){
    if(input.solid[cell]||input.planningWaterMask?.[cell]||occupied.has(cell))continue;
    const change=baseline.maxDepth[cell]-planned.maxDepth[cell];
    if(change>=depthDeltaM)improvedAreaM2+=area;
    else if(change<=-depthDeltaM)worsenedAreaM2+=area;
  }
  const baselineSurfaceM3=finite(baseline.ledger.surface_m3),plannedSurfaceM3=finite(planned.ledger.surface_m3);
  return {
    byDesign,
    waterAtInterventionsM3:byDesign.reduce((sum,item)=>sum+item.waterAtFootprintM3,0),
    footprintWaterDifferenceM3:byDesign.reduce((sum,item)=>sum+item.waterAtFootprintM3-item.baselineWaterAtFootprintM3,0),
    surfaceWaterDifferenceM3:plannedSurfaceM3-baselineSurfaceM3,
    deepPercolationDifferenceM3:finite(planned.ledger.deep_percolation_m3)-finite(baseline.ledger.deep_percolation_m3),
    externalDischargeDifferenceM3:finite(planned.ledger.outflow_m3)-finite(baseline.ledger.outflow_m3),
    improvedAreaM2,worsenedAreaM2,
  };
}
