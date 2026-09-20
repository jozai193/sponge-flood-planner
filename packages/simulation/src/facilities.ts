/** SI rating curves. Coefficients and dimensions remain explicit site assumptions. */
export type ControlRating = {kind:'orifice';areaM2:number;coefficient:number}|{kind:'weir';widthM:number;coefficient:number};
export function ratingFlow(rating:ControlRating,head:number,tailHead=0){
 if(head<=0||tailHead>=head)return 0;
 return rating.kind==='orifice'?rating.coefficient*rating.areaM2*Math.sqrt(2*9.80665*(head-Math.max(0,tailHead))):rating.coefficient*rating.widthM*head**1.5*Math.max(0,1-(Math.max(0,tailHead)/head)**1.5)**.385;
}
export interface FacilityLink {
  rating?:ControlRating;
  cell:number;
  targetCell:number | null;
  reservoir:'surface'|'subsurface';
  crestDepthM:number;
  ratePerS:number;
  maxFlowM3S:number;
  source:string;
}
export function validateFacilityLinks(input:{z:Float32Array;solid:Uint8Array;capacity:Float32Array;facilityLinks?:FacilityLink[]}) {
  const used=new Set<string>();
  if((input.facilityLinks?.length??0)>4096)throw new Error('At most 4096 facility links are supported');
  for(const link of input.facilityLinks??[]){
    const validCell=(cell:number)=>Number.isInteger(cell)&&cell>=0&&cell<input.z.length&&!input.solid[cell];
    if(!validCell(link.cell)||(link.targetCell!==null&&!validCell(link.targetCell)))throw new Error('Invalid facility receiver or source cell');
    if(!['surface','subsurface'].includes(link.reservoir)||!link.source?.trim()||![link.crestDepthM,link.ratePerS,link.maxFlowM3S].every(v=>Number.isFinite(v)&&v>=0))throw new Error('Invalid facility control');
    if(link.reservoir==='surface'&&link.targetCell===link.cell)throw new Error('Surface outlet cannot return to itself');
    if(link.reservoir==='subsurface'&&input.capacity[link.cell]<=0)throw new Error('Underdrain requires subsurface storage');
    if(link.rating){const r=link.rating;
      if(link.reservoir!=='surface')throw new Error('Hydraulic ratings require a surface reservoir with an elevation head');
      if(!['orifice','weir'].includes(r.kind)||!Number.isFinite(r.coefficient)||r.coefficient<=0||r.coefficient>(r.kind==='orifice'?1:4))throw new Error('Invalid rating coefficient');
      const size=r.kind==='orifice'?r.areaM2:r.widthM;
      if(!Number.isFinite(size)||size<=0)throw new Error('Invalid rating dimension');
    }
    const key=link.cell+':'+link.reservoir;
    if(used.has(key))throw new Error('Only one control per cell reservoir is supported');
    used.add(key);
  }
}

/** Independent float64 reference for a simultaneous, conservative control exchange.
 * Surface controls stop against receiver head. Subsurface controls represent a
 * prescribed storage recession to a free outlet, without pressure/backflow physics.
 */
export function exchangeFacilities(depth:Float64Array,storage:Float64Array,z:Float32Array,area:number,links:FacilityLink[],dt:number){
  const surface=depth.slice(),soil=storage.slice();let exportedM3=0;
  for(const link of links){
    let available=Math.max(0,(link.reservoir==='surface'?depth:storage)[link.cell]-link.crestDepthM);
    if(link.reservoir==='surface'&&link.targetCell!==null)available=Math.min(available,Math.max(0,(z[link.cell]+depth[link.cell]-z[link.targetCell]-depth[link.targetCell])/2));
    const head=Math.max(0,depth[link.cell]-link.crestDepthM);
    const tail=link.targetCell===null?0:Math.max(0,z[link.targetCell]+depth[link.targetCell]-z[link.cell]-link.crestDepthM);
    const amount=link.rating?Math.min(available,ratingFlow(link.rating,head,tail)/area*dt,link.maxFlowM3S/area*dt):Math.min(available*-Math.expm1(-link.ratePerS*dt),link.maxFlowM3S/area*dt);
    (link.reservoir==='surface'?surface:soil)[link.cell]-=amount;
    if(link.targetCell===null)exportedM3+=amount*area;else surface[link.targetCell]+=amount;
  }
  return {depth:surface,storage:soil,exportedM3};
}
