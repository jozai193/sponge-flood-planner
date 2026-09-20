import type {GPUInput} from '../../../packages/simulation/src/gpu';
import type {CityContext} from './city-scene';

/** Conservative overlap with WorldCover display cells; never changes hydraulic terrain. */
export function waterPlanningMask(input:GPUInput,context:CityContext|null){
 const mask=new Uint8Array(input.nx*input.ny),west=-input.nx*input.dx/2,south=-input.ny*input.dy/2;
 for(const water of context?.water??[]){
  const xs=water.polygon.map(p=>p[0]),ys=water.polygon.map(p=>p[1]);
  const x0=Math.max(0,Math.floor((Math.min(...xs)-west)/input.dx)),x1=Math.min(input.nx-1,Math.ceil((Math.max(...xs)-west)/input.dx-1e-9)-1);
  const y0=Math.max(0,Math.floor((Math.min(...ys)-south)/input.dy)),y1=Math.min(input.ny-1,Math.ceil((Math.max(...ys)-south)/input.dy-1e-9)-1);
  for(let y=y0;y<=y1;y++)for(let x=x0;x<=x1;x++)mask[y*input.nx+x]=1;
 }
 return mask;
}

export function dryCandidates<T extends {cells:number[];eligibility?:string;protected?:boolean;protected_reasons?:string[]}>(sites:T[],mask:Uint8Array){
 return sites.filter(site=>site.eligibility!=='prohibited'&&!site.protected&&!site.protected_reasons?.length&&site.cells.length>0&&site.cells.every(cell=>Number.isInteger(cell)&&cell>=0&&cell<mask.length&&!mask[cell]));
}
