import {test,expect} from 'vitest';
import {terrainSurface,displayHeight} from '../../apps/web/src/terrain-surface';
import {roofImageryMesh} from '../../apps/web/src/imagery';

const input=()=>({nx:4,ny:4,dx:1,dy:1,z:Float32Array.from({length:16},(_,i)=>i%4+Math.floor(i/4)*2),solid:new Uint8Array(16),rainWeights:new Float32Array(16).fill(1),roughness:new Float32Array(16),capacity:new Float32Array(16),infiltration:new Float32Array(16)});
test('continuous display terrain preserves the numerical raster and samples its cell centres',()=>{
 const grid=input(),before=grid.z.slice(),mesh=terrainSurface(grid);
 for(let y=0;y<4;y++)for(let x=0;x<4;x++)expect(displayHeight(grid,x-1.5,y-1.5)).toBe(grid.z[y*4+x]);
 expect(mesh.attributes.positions.value.length).toBe(25*3);
 expect(mesh.indices.value.length).toBe(4*4*6);
 expect([...mesh.attributes.normals.value].every(Number.isFinite)).toBe(true);
 expect(grid.z).toEqual(before);
});
test('projected roof imagery preserves courtyard holes and source roof elevation',()=>{
 const grid=input(),roof=[[[ -2,-2,12],[2,-2,12],[2,2,12],[-2,2,12],[-2,-2,12]],[[ -1,-1,12],[-1,1,12],[1,1,12],[1,-1,12],[-1,-1,12]]];
 const mesh=roofImageryMesh(grid,[{roof}],[[0,1],[1,1],[1,0],[0,0]]),p=mesh.attributes.positions.value,indices=mesh.indices.value;
 let area=0;for(let i=0;i<indices.length;i+=3){const a=indices[i]*3,b=indices[i+1]*3,c=indices[i+2]*3;area+=Math.abs((p[b]-p[a])*(p[c+1]-p[a+1])-(p[c]-p[a])*(p[b+1]-p[a+1]))/2;}
 expect(area).toBeCloseTo(12,8);
 for(let i=2;i<p.length;i+=3)expect(p[i]).toBe(12);
 expect([...mesh.attributes.texCoords.value].every(v=>v>=0&&v<=1)).toBe(true);
});
