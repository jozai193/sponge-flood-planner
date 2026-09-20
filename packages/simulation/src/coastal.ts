export interface CoastalBoundary {edge:'west'|'east'|'south'|'north';cells:number[];levels:{timeS:number;elevationM:number}[];source:string;datum:string;
 segment_ids?:string[];source_kind?:'measured'|'modelled'|'assumed';source_epoch?:string;vertical_transform?:string;coverage_start_s?:number|null;coverage_end_s?:number|null;bathymetry_status?:'verified'|'missing'|'not_required';channel_support_status?:'verified'|'missing'|'not_required'}
/** Fill only below-level cells connected to the prescribed ocean boundary. */
export function coastalInitialDepth(input:{nx:number;ny:number;z:Float32Array;solid:Uint8Array},boundary:CoastalBoundary){
 const depth=new Float32Array(input.z.length),seen=new Uint8Array(depth.length),queue:number[]=[];
 const level=coastalLevel(boundary,0);
 const visit=(i:number)=>{if(!seen[i]&&!input.solid[i]&&input.z[i]<level){seen[i]=1;depth[i]=level-input.z[i];queue.push(i);}};
 boundary.cells.forEach(visit);
 for(let j=0;j<queue.length;j++){const i=queue[j],x=i%input.nx,y=Math.floor(i/input.nx);if(x>0)visit(i-1);if(x<input.nx-1)visit(i+1);if(y>0)visit(i-input.nx);if(y<input.ny-1)visit(i+input.nx);}
 return depth;
}
export function coastalLevel(boundary:CoastalBoundary,time:number){
 const a=boundary.levels;
 if(time<=a[0].timeS)return a[0].elevationM;
 for(let i=1;i<a.length;i++)if(time<a[i].timeS){const t=(time-a[i-1].timeS)/(a[i].timeS-a[i-1].timeS);return a[i-1].elevationM+t*(a[i].elevationM-a[i-1].elevationM);}
 return a[a.length-1].elevationM;
}
export function validateCoastal(input:{nx:number;ny:number;solid:Uint8Array;coastal?:CoastalBoundary}){
 const b=input.coastal;if(!b)return;
 if(!['west','east','south','north'].includes(b.edge)||!b.source?.trim()||!b.datum?.trim()||!b.cells.length||!b.levels.length)throw new Error('Coastal boundary needs edge, cells, datum and source');
 const seen=new Set<number>();for(const cell of b.cells){const x=cell%input.nx,y=Math.floor(cell/input.nx);
  if(!Number.isInteger(cell)||cell<0||cell>=input.solid.length||input.solid[cell]||seen.has(cell)||!(b.edge==='west'?x===0:b.edge==='east'?x===input.nx-1:b.edge==='south'?y===0:y===input.ny-1))throw new Error('Invalid coastal boundary cell');seen.add(cell);
 }
 for(let i=0;i<b.levels.length;i++){const k=b.levels[i];if(!Number.isFinite(k.timeS)||!Number.isFinite(k.elevationM)||k.timeS<0||(i===0?k.timeS!==0:k.timeS<=b.levels[i-1].timeS))throw new Error('Invalid coastal level series');}
 if(b.coverage_start_s!=null&&(!Number.isFinite(b.coverage_start_s)||b.coverage_start_s<0)||b.coverage_end_s!=null&&(!Number.isFinite(b.coverage_end_s)||b.coverage_end_s<0||(b.coverage_start_s!=null&&b.coverage_end_s<b.coverage_start_s)))throw new Error('Invalid coastal source time coverage');
}
