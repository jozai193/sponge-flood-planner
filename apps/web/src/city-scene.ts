import {SimpleMeshLayer} from '@deck.gl/mesh-layers';
import {waterGeometry,type WaterFrame} from './water';
import {canopyMesh,trunkMesh,treeStyle} from './vegetation';
import {displayHeight,terrainSurface} from './terrain-surface';
import {AmbientLight,DirectionalLight,LightingEffect,COORDINATE_SYSTEM} from '@deck.gl/core';
import {PolygonLayer,PathLayer,LineLayer,ScatterplotLayer,TextLayer} from '@deck.gl/layers';
import type {GPUInput} from '../../../packages/simulation/src/gpu';
export type CityContext={roads:{id:string;name:string;kind:string;path:number[][]}[];green:{id:string;name:string;geometry:{type:string;coordinates:any}}[];water?:{id:string;name:string;polygon:number[][]}[];landscape_status?:string;trees:{id:string;position:number[];basis?:string}[];assumptions:string[]};
export type CityBuilding={id:string;geometry:{type:string;coordinates:any};height_m:number;base_elevation_m:number;exterior_cells:number[];
 first_floor_elevation_m?:number|null;structure_value_minor?:number|null;damage_curve?:{id:string;source:string;points:[number,number][]}|null};
const system={coordinateSystem:COORDINATE_SYSTEM.CARTESIAN};
export function cityLighting(shadows=true){const effect=new LightingEffect({ambient:new AmbientLight({color:[220,235,255],intensity:.75}),sun:new DirectionalLight({color:[255,239,207],intensity:1.35,direction:[-2,-3,-5],_shadow:shadows})});effect.shadowColor=[.07,.12,.15,.32];return effect;}
export function cityGeometry(input:GPUInput,extent:number,buildings:CityBuilding[],context:CityContext|null,ground=terrainSurface(input)){
 const elevation=(x:number,y:number)=>displayHeight(input,x,y);
 const blocks=buildings.flatMap(b=>(b.geometry.type==='MultiPolygon'?b.geometry.coordinates:[b.geometry.coordinates]).map((rings:number[][][])=>({...b,polygon:rings.map(r=>r.map(p=>[p[0],p[1],b.base_elevation_m])),roof:rings.map(r=>r.map(p=>[p[0],p[1],b.base_elevation_m+b.height_m+.035])),tone:Array.from(b.id).reduce((s,c)=>s+c.charCodeAt(0),0)%5})));
 const windows:{source:number[];target:number[]}[]=[],edges:number[][][]=[];
 for(const b of blocks){for(const ring of b.polygon){edges.push(ring.map((p:number[])=>[p[0],p[1],p[2]+b.height_m+.08]));
   let area=0;for(let i=1;i<ring.length;i++)area+=ring[i-1][0]*ring[i][1]-ring[i][0]*ring[i-1][1];
   for(let i=1;i<ring.length;i++){const a=ring[i-1],c=ring[i],dx=c[0]-a[0],dy=c[1]-a[1],length=Math.hypot(dx,dy);if(length<3)continue;const nx=dy/length*Math.sign(area)*.06,ny=-dx/length*Math.sign(area)*.06;
     for(let z=2;z<b.height_m-1;z+=3)for(let d=1.5;d<length-1;d+=3){if(windows.length>=45000)break;const width=Math.min(1,length-d-.3);windows.push({source:[a[0]+dx*d/length+nx,a[1]+dy*d/length+ny,a[2]+z],target:[a[0]+dx*(d+width)/length+nx,a[1]+dy*(d+width)/length+ny,a[2]+z]});}
   }
 }}
 // Densify mapped centre lines to follow the terrain rather than bridge over hills.
 const roads=(context?.roads??[]).map(r=>{const path:number[][]=[];for(let i=1;i<r.path.length;i++){const a=r.path[i-1],b=r.path[i],steps=Math.max(1,Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1])/input.dx));for(let s=0;s<steps;s++){const x=a[0]+(b[0]-a[0])*s/steps,y=a[1]+(b[1]-a[1])*s/steps;path.push([x,y,elevation(x,y)+.002]);}}const last=r.path.at(-1)!;path.push([last[0],last[1],elevation(last[0],last[1])+.002]);return {...r,path,width:['footway','path','steps'].includes(r.kind)?2:r.kind==='service'?4:['primary','secondary','tertiary'].includes(r.kind)?12:7};});
 const green=(context?.green??[]).flatMap(g=>(g.geometry.type==='MultiPolygon'?g.geometry.coordinates:[g.geometry.coordinates]).map((rings:number[][][])=>({...g,polygon:rings.map(r=>r.map(p=>[p[0],p[1],elevation(p[0],p[1])+.002]))})));
 const trees=(context?.trees??[]).map(t=>({...t,...treeStyle(t.id),name:t.basis==='classified-cover'?'Illustrative tree from satellite-classified cover · position, crown and height are not surveyed':'Mapped tree position · illustrative 3D crown and height',position:[t.position[0],t.position[1],elevation(t.position[0],t.position[1])]}));
 const names=new Set<string>();const labels=roads.filter(r=>{if(!r.name||names.has(r.name)||r.path.length<5)return false;names.add(r.name);return true;}).map(r=>({...r,position:r.path[Math.floor(r.path.length/2)].map((v,i)=>i===2?v+1:v)}));
 const boundary:number[][]=[];const steps=input.nx;for(let edge=0;edge<4;edge++)for(let i=0;i<steps;i++){const t=i/steps;const x=edge===0?-extent/2+t*extent:edge===1?extent/2:edge===2?extent/2-t*extent:-extent/2;const y=edge===0?-extent/2:edge===1?-extent/2+t*extent:edge===2?extent/2:extent/2-t*extent;boundary.push([x,y,elevation(x,y)+.3]);}boundary.push(boundary[0]);
 const mappedWater=(context?.water??[]).map(w=>({...w,polygon:w.polygon.map(p=>[p[0],p[1],elevation(p[0],p[1])+.004])}));
 return {ground,blocks,windows,edges,roads,green,trees,labels,boundary,mappedWater};
}
export function cityLayers(g:ReturnType<typeof cityGeometry>,input:GPUInput,frame:WaterFrame|null,sites:any[]=[],detail=true,waterHeightScale=1){
 const water=waterGeometry(input,frame,waterHeightScale);
 const palette=[[167,139,113],[189,171,147],[153,119,99],[198,187,166],[163,158,141]];
 return [
 new PathLayer({...system,id:'domain-boundary',data:[g.boundary],getPath:d=>d as any,getColor:[222,243,190],getWidth:2,widthUnits:'pixels'}),
 new SimpleMeshLayer({...system,id:'terrain-surface',data:[{position:[0,0,0]}],mesh:g.ground,getPosition:d=>d.position as [number,number,number],getColor:[153,166,143],material:{ambient:.7,diffuse:.5,shininess:1}}),
 new PolygonLayer({...system,id:'green-space',data:g.green,getPolygon:d=>d.polygon,getFillColor:[104,143,95],stroked:false}),
 new PolygonLayer({...system,id:'mapped-water',data:g.mappedWater,getPolygon:d=>d.polygon,getFillColor:[29,112,145],stroked:false,pickable:true,parameters:{depthBias:-1,depthBiasSlopeScale:-1}}),
 new PathLayer({...system,id:'sidewalks',parameters:{depthBias:-2,depthBiasSlopeScale:-2},data:g.roads,getPath:d=>d.path as any,getWidth:d=>d.width+3,widthUnits:'meters',getColor:[204,199,180],jointRounded:true}),
 new PathLayer({...system,id:'streets',parameters:{depthBias:-3,depthBiasSlopeScale:-3},data:g.roads,getPath:d=>d.path.map((p:number[])=>[p[0],p[1],p[2]+.002]) as any,getWidth:d=>d.width,widthUnits:'meters',getColor:d=>d.width<=2?[182,174,150]:[78,91,91],jointRounded:true,pickable:true}),
 new PolygonLayer({...system,id:'buildings',data:g.blocks,getPolygon:d=>d.polygon,getElevation:d=>d.height_m,extruded:true,getFillColor:d=>{const h=Math.max(0,...d.exterior_cells.map((i:number)=>frame?.maxDepth[i]??0));return (h>.3?[237,102,75]:h>.1?[234,181,67]:palette[d.tone]) as any;},material:{ambient:.5,diffuse:.7,shininess:12,specularColor:[50,50,40]},pickable:true,updateTriggers:{getFillColor:frame?.maxDepth}}),
 new PolygonLayer({...system,id:'roofs',data:g.blocks,getPolygon:d=>d.roof,getFillColor:d=>[113+d.tone*8,119+d.tone*7,113+d.tone*7],stroked:false}),
 new PathLayer({...system,id:'roof-edges',data:g.edges,getPath:d=>d as any,getWidth:.22,widthUnits:'meters',widthMinPixels:.5,getColor:[215,209,187],visible:detail}),
 new LineLayer({...system,id:'facade-windows',data:g.windows,getSourcePosition:d=>d.source as any,getTargetPosition:d=>d.target as any,getColor:[57,79,83],getWidth:.95,widthUnits:'meters',visible:detail}),
 new SimpleMeshLayer({...system,id:'tree-trunks',data:g.trees,mesh:trunkMesh,getPosition:d=>d.position as [number,number,number],getScale:d=>d.scale,getOrientation:d=>[0,d.rotation,0],getColor:[101,77,53],material:{ambient:.35,diffuse:.85,shininess:2},visible:detail}),
 new SimpleMeshLayer({...system,id:'tree-canopies-3d',data:g.trees,mesh:canopyMesh,getPosition:d=>d.position as [number,number,number],getScale:d=>d.scale,getOrientation:d=>[0,d.rotation,0],getColor:d=>d.color,material:{ambient:.4,diffuse:.9,shininess:3,specularColor:[25,40,20]},pickable:true}),
 new TextLayer({...system,id:'street-labels',data:g.labels,getPosition:d=>d.position as any,getText:d=>d.name,getSize:11,getColor:[244,245,224],background:true,getBackgroundColor:[40,61,58,150],fontFamily:'Segoe UI',visible:detail}),
 new SimpleMeshLayer({...system,id:'water-sides',data:water.cells.length?[{position:[0,0,0]}]:[],mesh:water.walls,getPosition:d=>d.position as [number,number,number],getColor:[20,125,170,210],material:{ambient:.65,diffuse:.6,shininess:48,specularColor:[130,210,240]},pickable:false}),
 new PolygonLayer({...system,id:'water',data:water.cells,getPolygon:d=>d.polygon as any,getFillColor:d=>d.color,stroked:false,pickable:true}),
 new PathLayer({...system,id:'water-shore',data:water.shore,getPath:d=>d as any,getColor:[143,233,240,165],getWidth:1,widthUnits:'pixels',widthMinPixels:1}),
 new LineLayer({...system,id:'water-flow',data:water.flow,getSourcePosition:d=>d.source as any,getTargetPosition:d=>d.target as any,getColor:[208,250,255,205],getWidth:1.2,widthUnits:'pixels',visible:detail}),
 new ScatterplotLayer({...system,id:'sites',data:sites.map(site=>({...site,name:`Candidate ${site.id} · ${site.cells.length} simulation cells`})),getPosition:d=>[d.x_m,d.y_m,d.elevation_m+.7],getRadius:4,getFillColor:[187,237,116,130],stroked:true,getLineColor:[223,255,171],lineWidthMinPixels:2,pickable:true})];
}
