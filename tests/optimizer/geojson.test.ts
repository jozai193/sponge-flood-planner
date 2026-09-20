import {test,expect} from 'vitest';
import {selectedGeoJSON} from '../../packages/metrics/geojson';
import type {PhysicalDesign} from '../../packages/domain/interventions';
const input={nx:4,ny:4,dx:5,dy:5,z:new Float32Array(16),solid:new Uint8Array(16),rainWeights:new Float32Array(16).fill(1),roughness:new Float32Array(16),capacity:new Float32Array(16),infiltration:new Float32Array(16)};
const design:PhysicalDesign={id:'garden',kind:'rain_garden',cells:[0,1,4],eligibility:'user_assumed',excavationM:.2,storageDepthM:.1,conductivityMS:.00001,percolationMS:0,roughness:.05,costMinor:10000,parameterSource:'Exploratory test'};
const grid={nx:4,ny:4,dx_m:5,dy_m:5,origin_x_m:500000,origin_y_m:2800000,crs:'EPSG:32644',row_direction:'north'};
test('GeoJSON coordinates match independent PROJ fixtures in both hemispheres',()=>{
 for(const [crs,x,y,lon,lat] of [['EPSG:32644',500000,2800000,81,25.31655337266244],['EPSG:32756',330000,6250000,151.16190684586647,-33.87665362206311]] as const){
  const exported=selectedGeoJSON(input,[design],{...grid,crs,origin_x_m:x,origin_y_m:y},10000);
  const ring=exported.features[0].geometry.coordinates[0];expect(ring[0][0]).toBeCloseTo(lon,8);expect(ring[0][1]).toBeCloseTo(lat,8);expect(ring[4]).toEqual(ring[0]);
  expect(exported.features).toHaveLength(3);expect(exported.features.reduce((s,f)=>s+f.properties.model_area_m2,0)).toBe(75);
  expect(exported.designs).toHaveLength(1);expect(exported.designs[0].costMinor).toBe(10000);expect(exported.features[0].properties).not.toHaveProperty('costMinor');
  expect(exported.features[2].geometry.coordinates[0][0][1]).toBeGreaterThan(ring[0][1]);
 }
});
test('invalid coordinates, mismatched grids and invalid designs are rejected',()=>{
 expect(()=>selectedGeoJSON(input,[design],{...grid,crs:'EPSG:4326'},10000)).toThrow('UTM');
 expect(()=>selectedGeoJSON(input,[design],{...grid,row_direction:'south'},10000)).toThrow('grid');
 expect(()=>selectedGeoJSON(input,[design],{...grid,origin_x_m:NaN},10000)).toThrow('grid');
 expect(()=>selectedGeoJSON(input,[design],grid,1)).toThrow('budget');
 expect(()=>selectedGeoJSON(input,[{...design,cells:[16]}],grid,10000)).toThrow();
 expect(selectedGeoJSON(input,[],grid,0).features).toEqual([]);
});
