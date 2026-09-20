import type {GPUInput} from '../../../packages/simulation/src/gpu';

type GridBundle = {grid:{nx:number;ny:number;dx_m:number;dy_m:number}};
const arrayNames = ['z','solid','rain_weights','roughness','soil_capacity','infiltration'] as const;
const transientStatuses=new Set([502,503,504]);
const maxRasterAttempts=5;

function retryDelay(signal:AbortSignal,attempt:number){
  return new Promise<void>((resolve,reject)=>{
    const onAbort=()=>{clearTimeout(timer);reject(signal.reason);};
    const timer=setTimeout(()=>{signal.removeEventListener('abort',onAbort);resolve();},150*(attempt+1));
    signal.addEventListener('abort',onAbort,{once:true});
  });
}

async function fetchRaster(fetchArray:typeof fetch,url:string,options:RequestInit,signal:AbortSignal){
  let response!:Response;
  for(let attempt=0;attempt<maxRasterAttempts;attempt++){
    try{response=await fetchArray(url,options);}
    catch(error){
      signal.throwIfAborted();
      if(attempt===maxRasterAttempts-1)throw error;
      await retryDelay(signal,attempt);
      continue;
    }
    if(response.ok||!transientStatuses.has(response.status)||attempt===maxRasterAttempts-1)return response;
    await retryDelay(signal,attempt);
  }
  return response;
}

/** Fetch metadata and independent rasters together; cancel all remaining work on failure. */
export async function loadBundleResources<T extends GridBundle>(
  id:string,
  token:string,
  getBundle:(signal:AbortSignal)=>Promise<T>,
  signal:AbortSignal,
  fetchArray:typeof fetch=fetch,
){
  signal.throwIfAborted();
  const pending=new AbortController();
  const requestSignal=AbortSignal.any([signal,pending.signal]);
  const started=performance.now();
  try{
    const metadata=getBundle(requestSignal);
    const rasters=(async()=>{
      const arrays:ArrayBuffer[]=[];
      // Stay below common HTTP/1.1 per-origin connection limits. Metadata and
      // context requests may be in flight at the same time on a fresh load.
      for(let start=0;start<arrayNames.length;start+=3){
        const batch=await Promise.all(arrayNames.slice(start,start+3).map(async name=>{
          const response=await fetchRaster(fetchArray,`/api/v1/bundles/${id}/arrays/${name}`,
            {signal:requestSignal,headers:{Authorization:'Bearer '+token}},requestSignal);
          if(!response.ok)throw new Error(`Terrain array ${name} unavailable (${response.status})`);
          return response.arrayBuffer();
        }));
        arrays.push(...batch);
      }
      return arrays;
    })();
    const [bundle,arrays]=await Promise.all([metadata,rasters]);
    requestSignal.throwIfAborted();
    const {nx,ny,dx_m,dy_m}=bundle.grid;
    if(!Number.isSafeInteger(nx)||!Number.isSafeInteger(ny)||nx<=0||ny<=0||
      !Number.isFinite(dx_m)||!Number.isFinite(dy_m)||dx_m<=0||dy_m<=0){
      throw new Error('Terrain grid dimensions are invalid');
    }
    arrays.forEach((array,index)=>{
      if(array.byteLength!==nx*ny*(index===1?1:4)){
        throw new Error(`Terrain array ${arrayNames[index]} does not match the grid`);
      }
    });
    const input:GPUInput={nx,ny,dx:dx_m,dy:dy_m,z:new Float32Array(arrays[0]),
      solid:new Uint8Array(arrays[1]),rainWeights:new Float32Array(arrays[2]),
      roughness:new Float32Array(arrays[3]),capacity:new Float32Array(arrays[4]),
      infiltration:new Float32Array(arrays[5]),boundary:'closed',saturation:.25,spatialOrder:2};
    return {bundle,input,fetchMs:performance.now()-started};
  }catch(error){
    pending.abort(error);
    throw error;
  }
}
