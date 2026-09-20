/** Experimental bound matches the float64 reference's accepted negative-depth bound.
 * It is deliberately much tighter than the production GPU's 1e-6 m tolerance.
 * This is a numerical guard, not a statement of terrain or flood accuracy.
 */
export const NEGATIVE_DEPTH_ROUNDOFF_M = 1e-10;
export const MAX_RELATIVE_ROUNDOFF_VOLUME = 1e-8;

/** Validate the entire state before changing anything; never repair material negatives. */
export function correctDepthRoundoff(state:Float32Array, cellArea:number){
  if(state.length%4||!Number.isFinite(cellArea)||cellArea<=0)throw new Error('Invalid roundoff state or cell area');
  for(let i=0;i<state.length;i+=4){
    for(let k=0;k<4;k++)if(!Number.isFinite(state[i+k]))throw new Error('NUMERICAL_INVALID: non-finite GPU state');
    if(state[i]<-NEGATIVE_DEPTH_ROUNDOFF_M||state[i+3]<0)throw new Error('NUMERICAL_INVALID: material negative GPU state');
  }
  let volumeM3=0,cells=0,minDepthM=0;
  for(let i=0;i<state.length;i+=4)if(state[i]<0){
    volumeM3-=state[i]*cellArea;minDepthM=Math.min(minDepthM,state[i]);cells++;
    state[i]=0;state[i+1]=0;state[i+2]=0;
  }
  return {volumeM3,cells,minDepthM};
}

export function validateRoundoffBudget(volume:number,suppliedVolume:number){
  if(!Number.isFinite(volume)||volume<0||!Number.isFinite(suppliedVolume)||suppliedVolume<0||volume>Math.max(suppliedVolume,1)*MAX_RELATIVE_ROUNDOFF_VOLUME)
    throw new Error('NUMERICAL_INVALID: cumulative roundoff correction budget exceeded');
}
