import type {GPUInput} from '../simulation/src/gpu';

export interface ExposureBuilding {id:string;exterior_cells:number[]}
export interface ExposureFrame {maxDepth:Float32Array;ledger:Record<string,number>}

/** Deterministic replay metrics from stored maxima; display interpolation is never used. */
export function replayMetrics(input:GPUInput,frame:ExposureFrame,buildings:ExposureBuilding[],thresholdM:number){
 if(!Number.isFinite(thresholdM)||thresholdM<0||frame.maxDepth.length!==input.z.length)throw new Error('Invalid exposure threshold or frame');
 let affectedBuildings=0,peakDepthM=0,areaAboveThresholdM2=0;
 for(let cell=0;cell<frame.maxDepth.length;cell++){
  const depth=frame.maxDepth[cell];if(!Number.isFinite(depth)||depth<0)throw new Error('Invalid replay depth');
  if(input.solid[cell])continue;peakDepthM=Math.max(peakDepthM,depth);if(depth>=thresholdM)areaAboveThresholdM2+=input.dx*input.dy;
 }
 for(const building of buildings){
  if(building.exterior_cells.some(cell=>Number.isInteger(cell)&&cell>=0&&cell<frame.maxDepth.length&&frame.maxDepth[cell]>=thresholdM))affectedBuildings++;
 }
 return {affectedBuildings,peakDepthM,areaAboveThresholdM2,
  surfaceM3:frame.ledger.surface_m3??0,subsurfaceM3:frame.ledger.subsurface_m3??0,
  deepPercolationM3:frame.ledger.deep_percolation_m3??0,outflowM3:frame.ledger.outflow_m3??0};
}

export function localWorseningArea(input:GPUInput,baseline:Float32Array,planned:Float32Array,deltaM=.05){
 if(baseline.length!==input.z.length||planned.length!==input.z.length||!Number.isFinite(deltaM)||deltaM<0)throw new Error('Invalid local-worsening comparison');
 let area=0;for(let i=0;i<baseline.length;i++)if(!input.solid[i]&&!input.planningWaterMask?.[i]&&planned[i]-baseline[i]>=deltaM)area+=input.dx*input.dy;
 return area;
}
