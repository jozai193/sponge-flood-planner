import proj4 from 'proj4';
import type {GPUInput} from '../simulation/src/gpu';
import {compileDesign,type PhysicalDesign} from '../domain/interventions';
export interface ExportGrid {nx:number;ny:number;dx_m:number;dy_m:number;origin_x_m:number;origin_y_m:number;crs:string;row_direction:string}
/** One polygon per simulated cell; installation costs occur once in the design catalogue. */
export function selectedGeoJSON(input:GPUInput,designs:PhysicalDesign[],grid:ExportGrid,budgetMinor:number){
 if(!grid||grid.nx!==input.nx||grid.ny!==input.ny||grid.dx_m!==input.dx||grid.dy_m!==input.dy||grid.row_direction!=='north'||![grid.origin_x_m,grid.origin_y_m].every(Number.isFinite))throw new Error('Export grid does not match the simulation');
 if(!/^EPSG:32[67](0[1-9]|[1-5][0-9]|60)$/.test(grid.crs))throw new Error('GeoJSON export requires a supported WGS84 UTM grid');
 compileDesign(input,designs,budgetMinor);
 const transform=proj4(grid.crs,'EPSG:4326');
 const coordinate=(x:number,y:number)=>{const p=transform.forward([x,y]);if(!p.every(Number.isFinite)||Math.abs(p[0])>180||Math.abs(p[1])>90)throw new Error('Invalid geographic export coordinates');return p;};
 const features=designs.flatMap(design=>design.cells.map(cell=>{
  const x=grid.origin_x_m+(cell%input.nx)*input.dx,y=grid.origin_y_m+Math.floor(cell/input.nx)*input.dy;
  const ring=[[x,y],[x+input.dx,y],[x+input.dx,y+input.dy],[x,y+input.dy],[x,y]].map(([e,n])=>coordinate(e,n));
  if(ring.some((p,i)=>i>0&&Math.abs(p[0]-ring[i-1][0])>180))throw new Error('Antimeridian-crossing exports require polygon splitting');
  return {type:'Feature' as const,id:design.id+':'+cell,geometry:{type:'Polygon' as const,coordinates:[ring]},properties:{design_id:design.id,kind:design.kind,cell_index:cell,model_area_m2:input.dx*input.dy,eligibility:design.eligibility,parameter_source:design.parameterSource}};
 }));
 return {type:'FeatureCollection' as const,features,designs:designs.map(d=>({...d,currency:'USD',cost_basis:'assumed installation cost'})),source_grid:grid,note:'WGS84 longitude/latitude. Polygons are simulated intervention cells, not surveyed construction boundaries. Installation cost is recorded once per design in the designs catalogue; do not multiply it by cell count.'};
}
