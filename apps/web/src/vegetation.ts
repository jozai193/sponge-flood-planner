/** Shared instanced meshes. Tree dimensions and crown shape are illustrative. */
function meshBuilder(){
 const positions:number[]=[],normals:number[]=[];
 function ellipsoid(center:number[],scale:number[],segments=12,rings=8){
  const point=(u:number,v:number)=>{
   const t=u*Math.PI*2,p=v*Math.PI;
   const n=[Math.sin(p)*Math.cos(t),Math.sin(p)*Math.sin(t),Math.cos(p)];
   const normal=n.map((x,i)=>x/scale[i]),length=Math.hypot(...normal);
   return {p:n.map((x,i)=>center[i]+x*scale[i]),n:normal.map(x=>x/length)};
  };
  for(let y=0;y<rings;y++)for(let x=0;x<segments;x++){
   const a=point(x/segments,y/rings),b=point((x+1)/segments,y/rings),c=point((x+1)/segments,(y+1)/rings),d=point(x/segments,(y+1)/rings);
   for(const q of [a,c,b,a,d,c]){positions.push(...q.p);normals.push(...q.n);}
  }
 }
 return {ellipsoid,finish:()=>({attributes:{positions:{size:3,value:new Float32Array(positions)},normals:{size:3,value:new Float32Array(normals)}},topology:'triangle-list' as const})};
}
const crown=meshBuilder();
crown.ellipsoid([0,0,5.5],[2.25,2.1,2.6]);
crown.ellipsoid([-1.15,.4,4.9],[1.6,1.55,1.8]);
crown.ellipsoid([1.1,.5,5.2],[1.7,1.6,2]);
crown.ellipsoid([.15,-1.1,5.25],[1.7,1.65,1.9]);
export const canopyMesh=crown.finish();
const wood=meshBuilder();
wood.ellipsoid([0,0,2],[.2,.2,2.1],8,6);
wood.ellipsoid([-.35,.1,3.2],[.15,.15,1],8,6);
wood.ellipsoid([.4,.2,3.4],[.14,.14,.9],8,6);
export const trunkMesh=wood.finish();
export function treeStyle(id:string){
 let hash=2166136261;for(const char of id)hash=Math.imul(hash^char.charCodeAt(0),16777619)>>>0;
 const scale=.8+(hash%41)/100;
 return {scale:[scale,scale*(.9+(hash%17)/100),scale] as [number,number,number],rotation:hash%360,color:[45+hash%16,91+hash%25,51+hash%19] as [number,number,number]};
}
