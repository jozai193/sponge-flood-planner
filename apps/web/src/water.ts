import type {GPUInput} from '../../../packages/simulation/src/gpu';
export interface WaterFrame {depth:Float32Array;maxDepth:Float32Array;velocityX?:Float32Array;velocityY?:Float32Array;time_s?:number}
export const WATER_THRESHOLD_M=.005;
/** Display-only interpolation. Never writes to solver arrays or changes metrics. */
export function waterGeometry(input:GPUInput,frame:WaterFrame|null,heightScale=1){
 if(!Number.isFinite(heightScale)||heightScale<1||heightScale>10)throw new Error("Invalid display water height");
 const wallPositions:number[]=[],wallNormals:number[]=[];
 const walls=()=>({attributes:{positions:{size:3,value:new Float32Array(wallPositions)},normals:{size:3,value:new Float32Array(wallNormals)}},topology:'triangle-list' as const});
 const cells:{i:number;depth:number;polygon:number[][];color:[number,number,number,number]}[]=[],shore:number[][][]=[],flow:{source:number[];target:number[]}[]=[];
 if(!frame)return {cells,shore,flow,walls:walls()};
 const {nx,ny,dx,dy}=input;
 const wet=(x:number,y:number)=>x>=0&&y>=0&&x<nx&&y<ny&&!input.solid[y*nx+x]&&frame.depth[y*nx+x]>WATER_THRESHOLD_M;
 const vertex=(x:number,y:number)=>{
  let sum=0,count=0;for(const cy of [y-1,y])for(const cx of [x-1,x])if(wet(cx,cy)){const i=cy*nx+cx;sum+=input.z[i]+frame.depth[i]*heightScale;count++;}
  return [x*dx-nx*dx/2,y*dy-ny*dy/2,sum/Math.max(1,count)+.006];
 };
 const stride=Math.max(1,Math.ceil(nx*ny/700));
 for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){
  if(!wet(x,y))continue;const i=y*nx+x,h=frame.depth[i],t=Math.min(1,h/.6);
  const polygon=[vertex(x,y),vertex(x+1,y),vertex(x+1,y+1),vertex(x,y+1)];
  cells.push({i,depth:h,polygon,color:[Math.round(49-32*t),Math.round(190-95*t),Math.round(218-53*t),Math.round(145+85*Math.min(1,h/.15))]});
  [[x,y-1],[x+1,y],[x,y+1],[x-1,y]].forEach(([cx,cy],edge)=>{if(!wet(cx,cy)){
   const a=polygon[edge],b=polygon[(edge+1)%4];shore.push([a,b]);
   const bottomA=[a[0],a[1],Math.min(a[2],input.z[i])],bottomB=[b[0],b[1],Math.min(b[2],input.z[i])];
   const length=Math.hypot(b[0]-a[0],b[1]-a[1]),normal=[(b[1]-a[1])/length,(a[0]-b[0])/length,0];
   for(const p of [a,b,bottomA,b,bottomB,bottomA]){wallPositions.push(...p);wallNormals.push(...normal);}
  }});
  const vx=frame.velocityX?.[i]??0,vy=frame.velocityY?.[i]??0,speed=Math.hypot(vx,vy);
  if(i%stride!==0||speed<.02||!Number.isFinite(speed))continue;
  // Arrow direction and visibility come from real velocity. No decorative currents.
  const length=Math.min(dx,dy)*.65*Math.min(1,speed/.5),ux=vx/speed,uy=vy/speed;
  const cx=(x+.5)*dx-nx*dx/2,cy=(y+.5)*dy-ny*dy/2,z=polygon.reduce((s,p)=>s+p[2],0)/4+.012;
  const tip=[cx+ux*length/2,cy+uy*length/2,z];
  flow.push({source:[cx-ux*length/2,cy-uy*length/2,z],target:tip});
  for(const side of [-1,1])flow.push({source:tip,target:[tip[0]-ux*length*.3+side*uy*length*.2,tip[1]-uy*length*.3-side*ux*length*.2,z]});
 }
 return {cells,shore,flow,walls:walls()};
}
