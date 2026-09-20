import type {GPUInput} from '../../../packages/simulation/src/gpu';
/** Cell-centred elevation interpolation for display only. Solver arrays are untouched. */
export function displayHeight(input:GPUInput,x:number,y:number){
 const gx=Math.max(0,Math.min(input.nx-1,x/input.dx+input.nx/2-.5)),gy=Math.max(0,Math.min(input.ny-1,y/input.dy+input.ny/2-.5));
 const ix=Math.floor(gx),iy=Math.floor(gy),jx=Math.min(ix+1,input.nx-1),jy=Math.min(iy+1,input.ny-1),u=gx-ix,v=gy-iy;
 return (1-v)*((1-u)*input.z[iy*input.nx+ix]+u*input.z[iy*input.nx+jx])+v*((1-u)*input.z[jy*input.nx+ix]+u*input.z[jy*input.nx+jx]);
}
export function terrainSurface(input:GPUInput){
 const n=Math.min(input.nx,256),m=Math.min(input.ny,256),positions=new Float32Array((n+1)*(m+1)*3),normals=new Float32Array(positions.length),indices=new Uint32Array(n*m*6);
 for(let y=0;y<=m;y++)for(let x=0;x<=n;x++){
  const i=y*(n+1)+x,px=(x/n-.5)*input.nx*input.dx,py=(y/m-.5)*input.ny*input.dy;
  positions.set([px,py,displayHeight(input,px,py)],i*3);
  const gx=(displayHeight(input,px+input.dx/2,py)-displayHeight(input,px-input.dx/2,py))/input.dx;
  const gy=(displayHeight(input,px,py+input.dy/2)-displayHeight(input,px,py-input.dy/2))/input.dy,l=Math.hypot(gx,gy,1);
  normals.set([-gx/l,-gy/l,1/l],i*3);
 }
 let k=0;for(let y=0;y<m;y++)for(let x=0;x<n;x++){const a=y*(n+1)+x,b=a+1,c=a+n+1,d=c+1;indices.set([a,b,c,b,d,c],k);k+=6;}
 return {n,m,attributes:{positions:{size:3,value:positions},normals:{size:3,value:normals}},indices:{size:1,value:indices},topology:'triangle-list' as const};
}
