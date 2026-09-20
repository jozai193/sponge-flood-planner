import {SimpleMeshLayer} from '@deck.gl/mesh-layers';
import {COORDINATE_SYSTEM} from '@deck.gl/core';
import type {GPUInput} from '../../../packages/simulation/src/gpu';
import {terrainSurface} from './terrain-surface';
import earcut,{deviation} from 'earcut';
export interface ImageryDescriptor {width:number;height:number;cornersUV:number[][];tiles:{x:number;y:number;url:string}[]}
export async function loadImagery(d:ImageryDescriptor){const canvas=document.createElement('canvas');canvas.width=d.width;canvas.height=d.height;const ctx=canvas.getContext('2d')!;let next=0;await Promise.all(Array.from({length:4},async()=>{while(next<d.tiles.length){const tile=d.tiles[next++];const image=new Image();image.crossOrigin='anonymous';await new Promise<void>((resolve,reject)=>{image.onload=()=>resolve();image.onerror=()=>reject(new Error('Imagery tile unavailable'));image.src=tile.url;});ctx.drawImage(image,tile.x,tile.y);}}));return canvas;}
/** Same local projected square as the simulation. North maps to image top. */
export function imageryMesh(input:GPUInput,corners:number[][]){
 const mesh=terrainSurface(input),{n,m}=mesh,uv=new Float32Array((n+1)*(m+1)*2);
 for(let y=0;y<=m;y++)for(let x=0;x<=n;x++){const i=y*(n+1)+x,u=x/n,v=y/m;mesh.attributes.positions.value[i*3+2]+=.001;uv.set([0,1].map(k=>(1-v)*((1-u)*corners[0][k]+u*corners[1][k])+v*((1-u)*corners[3][k]+u*corners[2][k])),i*2);}
 return {...mesh,attributes:{...mesh.attributes,texCoords:{size:2,value:uv}}};
}
export function imageryLayer(mesh:ReturnType<typeof imageryMesh>,texture:HTMLCanvasElement){return new SimpleMeshLayer({id:'satellite-terrain',coordinateSystem:COORDINATE_SYSTEM.CARTESIAN,data:[{position:[0,0,0]}],getPosition:d=>d.position as [number,number,number],mesh,texture,getColor:[255,255,255],material:false,pickable:false});}

/** Overhead imagery projected onto flat source-footprint roofs, never onto facades. */
export function roofImageryMesh(input:GPUInput,blocks:{roof:number[][][]}[],corners:number[][]){
 const positions:number[]=[],normals:number[]=[],uv:number[]=[],indices:number[]=[];
 for(const block of blocks){
  const xy:number[]=[],vertices:number[][]=[],holes:number[]=[];
  for(const ring of block.roof){if(vertices.length)holes.push(vertices.length);for(const p of ring){xy.push(p[0],p[1]);vertices.push(p);}}
  const triangles=earcut(xy,holes,2);
  if(!triangles.length||deviation(xy,holes,2,triangles)>1e-6)continue;
  const start=positions.length/3;
  for(const p of vertices){
   positions.push(...p);normals.push(0,0,1);
   const u=p[0]/(input.nx*input.dx)+.5,v=p[1]/(input.ny*input.dy)+.5;
   uv.push(...[0,1].map(k=>(1-v)*((1-u)*corners[0][k]+u*corners[1][k])+v*((1-u)*corners[3][k]+u*corners[2][k])));
  }
  indices.push(...triangles.map(i=>i+start));
 }
 return {attributes:{positions:{size:3,value:new Float32Array(positions)},normals:{size:3,value:new Float32Array(normals)},texCoords:{size:2,value:new Float32Array(uv)}},indices:{size:1,value:new Uint32Array(indices)},topology:'triangle-list' as const};
}
export function roofImageryLayer(mesh:ReturnType<typeof roofImageryMesh>,texture:HTMLCanvasElement){return new SimpleMeshLayer({id:'satellite-roofs',coordinateSystem:COORDINATE_SYSTEM.CARTESIAN,data:mesh.indices.value.length?[{position:[0,0,0]}]:[],getPosition:d=>d.position as [number,number,number],mesh,texture,getColor:[255,255,255],material:false,pickable:false});}
