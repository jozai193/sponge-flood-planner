import type {GPUInput} from './gpu';
/** Hash metadata and exact array bytes; optional arrays have an explicit absent marker. */
export async function inputIdentity(input:GPUInput){
 const digest=async(bytes:Uint8Array)=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes as Uint8Array<ArrayBuffer>)),b=>b.toString(16).padStart(2,'0')).join('');
 const arrays:Record<string,string>={};
 for(const key of ['z','solid','rainWeights','roughness','infiltration','capacity','percolation','depth','planningWaterMask'] as const){const value=input[key];arrays[key]=value?await digest(new Uint8Array(value.buffer,value.byteOffset,value.byteLength)):'absent';}
 return digest(new TextEncoder().encode(JSON.stringify({version:6,coastal:input.coastal??null,spatialOrder:input.spatialOrder??1,maxStepS:input.maxStepS??1,facilityLinks:input.facilityLinks??[],inflows:input.inflows??[],outlets:input.outlets??[],nx:input.nx,ny:input.ny,dx:input.dx,dy:input.dy,boundary:input.boundary??'closed',saturation:input.saturation??0,arrays})));
}
