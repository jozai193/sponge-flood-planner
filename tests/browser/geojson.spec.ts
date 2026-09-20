import {test,expect} from '@playwright/test';
import {mkdir,writeFile} from 'node:fs/promises';
test('browser exports selected cells as geographic polygons',async({page})=>{
 await page.goto('/');
 const result=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {selectedGeoJSON}=await import(path);
  const input={nx:4,ny:4,dx:5,dy:5,z:new Float32Array(16),solid:new Uint8Array(16),rainWeights:new Float32Array(16).fill(1),roughness:new Float32Array(16),capacity:new Float32Array(16),infiltration:new Float32Array(16)};
  const design={id:'garden',kind:'rain_garden',cells:[0,1,4],eligibility:'user_assumed',excavationM:.2,storageDepthM:.1,conductivityMS:.00001,percolationMS:0,roughness:.05,costMinor:10000,parameterSource:'Controlled export fixture'};
  return selectedGeoJSON(input,[design],{nx:4,ny:4,dx_m:5,dy_m:5,origin_x_m:500000,origin_y_m:2800000,crs:'EPSG:32644',row_direction:'north'},10000);
 });
 expect(result.features).toHaveLength(3);expect(result.features[0].geometry.coordinates[0][0][0]).toBeCloseTo(81,8);
 await mkdir('artifacts/verification',{recursive:true});await writeFile('artifacts/verification/selected-designs.geojson',JSON.stringify(result));
});
