import {GPUSolver,type GPUInput} from './gpu';
export type Frame=ReturnType<GPUSolver['frame']>;
import {rainfallAt,validateRainfall,type StormRun} from './rainfall';
export type {StormRun} from './rainfall';
export async function simulate(input:GPUInput,storm:StormRun,signal:AbortSignal,onFrame?:(frame:Frame)=>void){
  validateRainfall(storm);
  const solver=new GPUSolver({...input,maxStepS:input.maxStepS??10}),end=storm.duration+storm.recession,interval=end/120;
  try{
    onFrame?.(solver.frame());let next=interval;
    while(solver.time<end-1e-7){
      signal.throwIfAborted();const limit=Math.min(end,next,solver.time+10);
      while(solver.time<limit-1e-7){const rain=rainfallAt(storm,solver.time);
        solver.step(Math.min(input.maxStepS??10,limit-solver.time,rain.knot-solver.time),rain.rate);
      }
      if(solver.time>=next-1e-7){const frame=solver.frame();if(frame.ledger.relative_residual>.001)throw new Error('Water balance exceeds 0.1%; evaluation rejected');onFrame?.(frame);next+=interval;}
      await new Promise(resolve=>setTimeout(resolve,0));
    }
    const frame=solver.frame();if(frame.ledger.relative_residual>.001)throw new Error('Water balance exceeds 0.1%; evaluation rejected');return frame;
  }finally{solver.dispose();}
}
/** Fixed assessment mask across every alternative; storage sites are not damage receptors. */
export function floodScore(frame:{maxDepth:Float32Array},input:GPUInput,excluded:Set<number>){
  let score=0;for(let i=0;i<frame.maxDepth.length;i++){const h=frame.maxDepth[i];if(!Number.isFinite(h)||h<0)throw new Error('Invalid flood score');if(!input.solid[i]&&!input.planningWaterMask?.[i]&&!excluded.has(i))score+=Math.max(0,h-.1)*input.dx*input.dy;}return score;
}
