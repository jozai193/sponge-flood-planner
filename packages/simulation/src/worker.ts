import {GPUSolver,type GPUInput} from './gpu';
import {rainfallAt,validateRainfall,type RainInterval} from './rainfall';
let cancelled=false;let busy=false;
self.onmessage=async(event:MessageEvent)=>{
  if(event.data.type==='CANCEL'){cancelled=true;return;}
  if(event.data.type!=='RUN'||busy)return;busy=true;
  const {input,duration,depth,recession,intervals,runId}=event.data as {input:GPUInput;duration:number;depth:number;recession:number;intervals?:RainInterval[];runId:string};
  const storm={duration,depth,recession,intervals};
  cancelled=false;let solver:GPUSolver|undefined;
  try{
    validateRainfall(storm);
    solver=new GPUSolver({...input,maxStepS:input.maxStepS??10});if(event.data.checkpoint){if(event.data.checkpoint.stormIdentity!==JSON.stringify(storm))throw new Error('Checkpoint storm mismatch');await solver.restore(event.data.checkpoint.solver);}self.postMessage({type:'INFO',runId,info:solver.info()});
    const end=duration+recession;let next=0,lastCheckpoint=-Infinity;
    const checkpoint=async(reason:'automatic'|'stopped')=>{
      const state=await solver!.checkpoint();
      self.postMessage({type:'CHECKPOINT',runId,reason,checkpoint:{solver:state,stormIdentity:JSON.stringify(storm)}},[state.state.buffer,state.history.buffer]);
      lastCheckpoint=performance.now();
    };
    while(solver.time<end-1e-7){
      if(cancelled){await checkpoint('stopped');self.postMessage({type:'CANCELLED',runId});return;}
      const limit=Math.min(end,solver.time+10);
      while(solver.time<limit-1e-7){
        const {rate:rain,knot}=rainfallAt(storm,solver.time);
        // Bound dry-start wave speed using rain added over the proposed step.
        const dt=Math.min(limit-solver.time,knot-solver.time,input.maxStepS??10);
        solver.step(dt,rain);
      }
      if(solver.time>=next||solver.time>=end){const frame=solver.frame();if(frame.ledger.relative_residual>.001)throw new Error('Water balance exceeds 0.1%; run rejected');self.postMessage({type:'FRAME',runId,frame},[frame.depth.buffer,frame.maxDepth.buffer]);next=solver.time+30;}
      if(solver.time<end-1e-7&&performance.now()-lastCheckpoint>=15000){const ledger=solver.frame().ledger;if(ledger.relative_residual>.001)throw new Error('Water balance exceeds 0.1%; checkpoint rejected');await checkpoint('automatic');}
      await new Promise(resolve=>setTimeout(resolve,0));
    }
    self.postMessage({type:'DONE',runId});
  }catch(error){self.postMessage({type:'ERROR',runId,error:String(error)});}
  finally{solver?.dispose();busy=false;}
};
