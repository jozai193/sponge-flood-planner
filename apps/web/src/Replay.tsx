import {validationStatus} from '../../../packages/metrics/validation-status';
import {buildReport} from '../../../packages/metrics/report';
import {useEffect,useState,useMemo} from 'react';
import DeckGL from '@deck.gl/react';
import {OrbitView,COORDINATE_SYSTEM} from '@deck.gl/core';
import {LineLayer,PolygonLayer,ScatterplotLayer,TextLayer} from '@deck.gl/layers';
import {cityGeometry,cityLayers,cityLighting,type CityContext,type CityBuilding} from './city-scene';
import {imageryMesh,imageryLayer,roofImageryMesh,roofImageryLayer,type ImageryDescriptor} from './imagery';
import {INTERVENTION_COLOURS,INTERVENTION_NAMES} from './intervention-style';
import type {GPUInput} from '../../../packages/simulation/src/gpu';
import type {PhysicalDesign} from '../../../packages/domain/interventions';
import {eventLoss} from '../../../packages/metrics';
import {localWorseningArea,replayMetrics} from '../../../packages/metrics/replay';
import {interventionEffects,type DesignEffect} from '../../../packages/metrics/intervention-effects';
type Frame={time_s:number;depth:Float32Array;maxDepth:Float32Array;subsurfaceDepth?:Float32Array;velocityX?:Float32Array;velocityY?:Float32Array;ledger:{relative_residual:number;surface_m3?:number;subsurface_m3?:number;deep_percolation_m3?:number;outflow_m3?:number}};
type ComparisonResult={baselineScore:number;plannedScore:number;designs:PhysicalDesign[];evidence?:{searchResult?:{status:string;evaluations:number;elapsedMs?:number;terminationReason?:string}}};
const system={coordinateSystem:COORDINATE_SYSTEM.CARTESIAN};
const effectLabelOffsets:Record<PhysicalDesign['kind'],[number,number]>={rain_garden:[-105,-42],bioswale:[105,-42],permeable_pavement:[-105,42],detention_basin:[105,42]};
function cellCentre(input:GPUInput,cell:number,zOffset=.08){const x=cell%input.nx,y=Math.floor(cell/input.nx);return [(x+.5)*input.dx-input.nx*input.dx/2,(y+.5)*input.dy-input.ny*input.dy/2,input.z[cell]+zOffset];}
function designCentroid(input:GPUInput,design:PhysicalDesign,zOffset=1){const points=design.cells.map(cell=>cellCentre(input,cell,zOffset));return points.reduce((sum,p)=>sum.map((value,i)=>value+p[i]),[0,0,0]).map(value=>value/Math.max(1,points.length));}
function externalEndpoint(input:GPUInput,start:number[]){const halfX=input.nx*input.dx/2,halfY=input.ny*input.dy/2,candidates=[[halfX+8,start[1],start[2]],[-halfX-8,start[1],start[2]],[start[0],halfY+8,start[2]],[start[0],-halfY-8,start[2]]];return candidates.sort((a,b)=>Math.hypot(a[0]-start[0],a[1]-start[1])-Math.hypot(b[0]-start[0],b[1]-start[1]))[0];}
function interventionLayers(input:GPUInput,frame:Frame,designs:PhysicalDesign[],effects:DesignEffect[]){
 const byId=new Map(effects.map(effect=>[effect.id,effect])),phase=(frame.time_s%3)/3;
 const cells=designs.flatMap(design=>design.cells.map(cell=>{const x=cell%input.nx,y=Math.floor(cell/input.nx),top=input.z[cell]+frame.depth[cell]+.09;return {design,cell,polygon:[[x*input.dx-input.nx*input.dx/2,y*input.dy-input.ny*input.dy/2,top],[(x+1)*input.dx-input.nx*input.dx/2,y*input.dy-input.ny*input.dy/2,top],[(x+1)*input.dx-input.nx*input.dx/2,(y+1)*input.dy-input.ny*input.dy/2,top],[x*input.dx-input.nx*input.dx/2,(y+1)*input.dy-input.ny*input.dy/2,top]]};}));
 const labels=designs.map(design=>{const effect=byId.get(design.id)!;return {design,effect,position:designCentroid(input,design,2.6)};});
 const infiltration=labels.filter(({design,effect})=>design.conductivityMS>0&&effect.surfaceM3>.001).map(item=>({...item,position:[item.position[0],item.position[1],item.position[2]-(phase*1.5)]}));
 const routes=designs.flatMap(design=>[design.surfaceControl,design.underdrain].filter(Boolean).map(control=>{const source=designCentroid(input,design,.65),target=control!.targetCell===null?externalEndpoint(input,source):cellCentre(input,control!.targetCell,.65);return {design,source,target,external:control!.targetCell===null};}));
 const routeMarkers=routes.map(route=>({...route,position:route.source.map((value,i)=>value+(route.target[i]-value)*phase)}));
 return [
  new PolygonLayer({...system,id:'planned-intervention-footprints',data:cells,getPolygon:d=>d.polygon,getFillColor:d=>INTERVENTION_COLOURS[(d as {design:PhysicalDesign}).design.kind],getLineColor:[225,255,194,245],stroked:true,lineWidthMinPixels:2,pickable:true}),
  new ScatterplotLayer({...system,id:'planned-intervention-pulses',data:labels.filter(({effect})=>effect.waterAtFootprintM3>.001),getPosition:d=>d.position,getRadius:d=>4+5*d.effect.fillFraction+2*Math.sin(phase*Math.PI),getFillColor:d=>{const colour=INTERVENTION_COLOURS[(d as {design:PhysicalDesign}).design.kind];return [colour[0],colour[1],colour[2],45] as [number,number,number,number];},getLineColor:d=>INTERVENTION_COLOURS[(d as {design:PhysicalDesign}).design.kind],stroked:true,lineWidthMinPixels:2,radiusUnits:'meters'}),
  new TextLayer({...system,id:'planned-intervention-labels',data:labels,getPosition:d=>d.position,getPixelOffset:d=>effectLabelOffsets[(d as {design:PhysicalDesign}).design.kind],getText:d=>INTERVENTION_NAMES[(d as {design:PhysicalDesign}).design.kind],getSize:13,getColor:[236,255,218,255],background:true,getBackgroundColor:[19,65,58,220],getTextAnchor:'middle',getAlignmentBaseline:'center',billboard:true}),
  new LineLayer({...system,id:'planned-infiltration-cues',data:infiltration,getSourcePosition:d=>[d.position[0],d.position[1],d.position[2]+1],getTargetPosition:d=>[d.position[0],d.position[1],d.position[2]-.7],getColor:[155,255,202,230],getWidth:3,widthUnits:'pixels'}),
  new TextLayer({...system,id:'planned-infiltration-labels',data:infiltration,getPosition:d=>d.position,getText:()=>'↓',getSize:25,getColor:[166,255,207,255],billboard:true}),
  new LineLayer({...system,id:'planned-outlet-routes',data:routes,getSourcePosition:d=>d.source,getTargetPosition:d=>d.target,getColor:d=>d.external?[103,207,255,210]:[151,229,244,190],getWidth:2,widthUnits:'pixels'}),
  new ScatterplotLayer({...system,id:'planned-outlet-route-cues',data:routeMarkers,getPosition:d=>d.position,getRadius:1.8,getFillColor:[177,241,255,235],radiusUnits:'meters'}),
 ];
}
export default function Replay({renderQuality='balanced',waterHeightScale=1,baseline,planned,input,plannedInput,extent,result,provenance,context,satelliteImage,imageryDescriptor,onClose}:{renderQuality?:string;waterHeightScale?:number;baseline:Frame[];planned:Frame[];input:GPUInput;plannedInput:GPUInput;extent:number;result:ComparisonResult;provenance:{buildings:CityBuilding[]};context:CityContext|null;satelliteImage:HTMLCanvasElement|null;imageryDescriptor:ImageryDescriptor|null;onClose:()=>void}){
 const [exportError,setExportError]=useState(''),[exporting,setExporting]=useState(false),[exposureThreshold,setExposureThreshold]=useState(.1);
 const [index,setIndex]=useState(0),[playing,setPlaying]=useState(false),[view,setView]=useState({target:[0,0,Math.min(15,extent*.025)],rotationX:48,rotationOrbit:0,zoom:Math.max(-2,Math.min(2,Math.log2(600/extent)))});
 const length=Math.min(baseline.length,planned.length);
 useEffect(()=>{if(!playing)return;const timer=setInterval(()=>setIndex(i=>{if(i>=length-1){setPlaying(false);return i;}return i+1;}),150);return()=>clearInterval(timer);},[playing,length]);
 const aligned=length>0&&baseline.every((f,i)=>planned[i]&&Math.abs(f.time_s-planned[i].time_s)<1e-5);
 const beforeLighting=useMemo(()=>[cityLighting(renderQuality==='high'&&!satelliteImage)],[renderQuality,satelliteImage]);
 const afterLighting=useMemo(()=>[cityLighting(renderQuality==='high'&&!satelliteImage)],[renderQuality,satelliteImage]);
 const orbitViews=useMemo(()=>new OrbitView({id:'orbit',orbitAxis:'Z'}),[]);
 const beforeGeometry=useMemo(()=>cityGeometry(input,extent,provenance.buildings,context),[input,extent,provenance,context]);
 const afterGeometry=useMemo(()=>cityGeometry(plannedInput,extent,provenance.buildings,context),[plannedInput,extent,provenance,context]);
 const beforeMesh=useMemo(()=>imageryDescriptor?imageryMesh(input,imageryDescriptor.cornersUV):null,[input,imageryDescriptor]);
 const afterMesh=useMemo(()=>imageryDescriptor?imageryMesh(plannedInput,imageryDescriptor.cornersUV):null,[plannedInput,imageryDescriptor]);
 const beforeRoofs=useMemo(()=>imageryDescriptor?roofImageryMesh(input,beforeGeometry.blocks,imageryDescriptor.cornersUV):null,[input,beforeGeometry,imageryDescriptor]);
 const afterRoofs=useMemo(()=>imageryDescriptor?roofImageryMesh(plannedInput,afterGeometry.blocks,imageryDescriptor.cornersUV):null,[plannedInput,afterGeometry,imageryDescriptor]);
 const currentEffects=useMemo(()=>aligned?interventionEffects(input,baseline[index],planned[index],result.designs):null,[aligned,input,baseline,planned,index,result.designs]);
 function layers(base:GPUInput,frame:Frame){
  const city=cityLayers(base===input?beforeGeometry:afterGeometry,base,frame,[],renderQuality!=='eco',waterHeightScale),mesh=base===input?beforeMesh:afterMesh,roofs=base===input?beforeRoofs:afterRoofs;
  const scene=satelliteImage&&mesh&&roofs?[imageryLayer(mesh,satelliteImage),...city.filter(layer=>!['terrain-surface','green-space','sidewalks','streets','roofs','roof-edges'].includes(layer.id)),roofImageryLayer(roofs,satelliteImage)]:city;
  return base===plannedInput&&currentEffects?[...scene,...interventionLayers(plannedInput,frame,result.designs,currentEffects.byDesign)]:scene;
 }
 const beforeLayers=useMemo(()=>aligned?layers(input,baseline[index]):[],[aligned,input,baseline,index,beforeGeometry,beforeMesh,beforeRoofs,satelliteImage,waterHeightScale,renderQuality]);
 const afterLayers=useMemo(()=>aligned?layers(plannedInput,planned[index]):[],[aligned,plannedInput,planned,index,afterGeometry,afterMesh,afterRoofs,satelliteImage,waterHeightScale,renderQuality,currentEffects,result.designs]);
 const reduction=result.baselineScore>0?100*(result.baselineScore-result.plannedScore)/result.baselineScore:null;
 const currentMetrics=aligned?[replayMetrics(input,baseline[index],provenance.buildings,exposureThreshold),replayMetrics(plannedInput,planned[index],provenance.buildings,exposureThreshold)]:null;
 const eta=(base:GPUInput,frame:Frame)=>Float32Array.from(frame.maxDepth,(depth,cell)=>base.z[cell]+depth);
 const assets=provenance.buildings.map(b=>({id:b.id,exteriorCells:b.exterior_cells,firstFloorElevationM:b.first_floor_elevation_m??null,structureValueMinor:b.structure_value_minor??null,curve:b.damage_curve??null}));
 const losses=aligned?[eventLoss(assets,eta(input,baseline[index])),eventLoss(assets,eta(plannedInput,planned[index]))]:null;
 const worsening=aligned?localWorseningArea(input,baseline.at(-1)!.maxDepth,planned.at(-1)!.maxDepth):0;
 async function download(kind:'evidence'|'html'|'csv'|'geojson'|'manifest'){
  setExportError('');setExporting(true);try{const report=await buildReport({input,plannedInput,baseline,planned,result,provenance});
   const spatial=kind==='geojson'?(await import('../../../packages/metrics/geojson')).selectedGeoJSON(input,report.scenario.selectedDesigns,(provenance as any).grid,(report.scenario.evidence as any).budgetMinor):null;
   const manifest=kind==='manifest'?(await (await import('../../../packages/metrics/evidence')).evidenceFiles(report)).manifest:null;
   const content=kind==='manifest'?JSON.stringify(manifest,null,2):kind==='geojson'?JSON.stringify({...spatial,evidence:report.scenario.evidence}):kind==='html'?report.html:kind==='csv'?report.csv:JSON.stringify(report.scenario);
   const url=URL.createObjectURL(new Blob([content],{type:kind==='geojson'?'application/geo+json':kind==='html'?'text/html':kind==='csv'?'text/csv':'application/json'}));const link=document.createElement('a');link.href=url;link.download=kind==='manifest'?'sponge-export-manifest.json':kind==='geojson'?'sponge-selected-designs.geojson':kind==='html'?'sponge-planning-report.html':kind==='csv'?'sponge-assumed-costs.csv':'sponge-reproducible-comparison.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }catch(e){setExportError(String(e));}finally{setExporting(false);}
 }
 async function printReport(){
  const target=window.open('','_blank');if(!target){setExportError('Allow pop-ups to print or save the report as PDF.');return;}
  setExportError('');setExporting(true);try{const report=await buildReport({input,plannedInput,baseline,planned,result,provenance});target.document.open();target.document.write(report.html);target.document.close();target.focus();target.setTimeout(()=>target.print(),250);}catch(error){target.close();setExportError(String(error));}finally{setExporting(false);}
 }
 const statusText:Record<DesignEffect['status'],string>={ready:'ready for runoff',receiving_runoff:'receiving runoff and infiltrating',holding_water:'holding water below the surface',at_capacity:'configured capacity reached; surface water may be overflow'};
 const difference=(value:number,less:string,more:string)=>Math.abs(value)<.005?'No material difference':`${Math.abs(value).toFixed(2)} m³ ${value<0?less:more}`;
 return <section className="replay" role="dialog" aria-label="Storm comparison">
  <div className="replay-heading"><h2>Same storm. Two designs.</h2><div className="replay-actions"><button disabled={exporting} onClick={()=>download('evidence')}>Download evidence</button><button disabled={exporting} onClick={()=>download('html')}>Export report</button><button disabled={exporting} onClick={printReport}>Print / save PDF</button><button disabled={exporting} onClick={()=>download('csv')}>Export costs</button><button disabled={exporting} onClick={()=>download('geojson')}>Export GeoJSON</button><button disabled={exporting} onClick={()=>download('manifest')}>Export manifest</button><button onClick={onClose}>Close comparison</button></div></div>
  {exportError&&<p role="alert">{exportError}</p>}
  <p>Peak excess-depth score outside candidate areas: {result.baselineScore.toFixed(1)} → {result.plannedScore.toFixed(1)} m³ {reduction!==null&&`(${reduction.toFixed(1)}% reduction)`}. Assumed installation cost: ${(result.designs.reduce((s,d)=>s+d.costMinor,0)/100).toLocaleString()}.</p>
  <p className="note">{result.evidence?.searchResult&&`Search: ${result.evidence.searchResult.status.replaceAll('_',' ')} after ${result.evidence.searchResult.evaluations} evaluations in ${Math.round(result.evidence.searchResult.elapsedMs??0)} ms. ${result.evidence.searchResult.terminationReason??''} `}{validationStatus.planning} {validationStatus.damage} {validationStatus.summary} This score sums peak depth above 10 cm × cell area; it is not simultaneous water volume or avoided damage. Building outlines use the same source footprints as the main scene; display heights and facade details are illustrative.</p>
  <label className="replay-threshold">Exposure threshold<select aria-label="Exposure depth threshold" value={exposureThreshold} onChange={e=>setExposureThreshold(+e.target.value)}><option value="0.05">5 cm</option><option value="0.1">10 cm</option><option value="0.3">30 cm</option><option value="0.5">50 cm</option></select></label>
  {waterHeightScale>1&&<p className="note">Water height exaggerated {waterHeightScale}× in both views; numeric depths unchanged.</p>}{satelliteImage&&<p className="note">Imagery: Esri, Vantor, Earthstar Geographics, GIS User Community. Capture date varies.</p>}
  {!aligned||!currentEffects?<p role="alert">Replay timestamps do not match.</p>:<>
   <div className="impact-strip" aria-label="Modelled intervention effects at replay time">
    <div><span>Surface water now</span><strong>{difference(currentEffects.surfaceWaterDifferenceM3,'less than baseline','more than baseline')}</strong></div>
    <div><span>Water at intervention locations</span><strong>{currentEffects.waterAtInterventionsM3.toFixed(2)} m³</strong><small>{Math.abs(currentEffects.footprintWaterDifferenceM3).toFixed(2)} m³ {currentEffects.footprintWaterDifferenceM3>=0?'more':'less'} than baseline at the same cells</small></div>
    <div><span>Area with ≥5 cm lower peak</span><strong>{currentEffects.improvedAreaM2.toFixed(0)} m²</strong></div>
    <div><span>Area with ≥5 cm higher peak</span><strong>{currentEffects.worsenedAreaM2.toFixed(0)} m²</strong></div>
   </div>
   <div className="replay-maps">{([['Baseline',input,baseline],['Planned',plannedInput,planned]] as const).map(([label,base,frames])=><div className="replay-map" key={label}><DeckGL views={orbitViews} viewState={view as any} onViewStateChange={({viewState}:any)=>setView(viewState)} onAfterRender={()=>{if(new URLSearchParams(location.search).has('measure'))window.dispatchEvent(new CustomEvent('sponge-replay-draw',{detail:{label,index,time:performance.now()}}));}} controller useDevicePixels={renderQuality==='high'?true:renderQuality==='eco'?.75:1} effects={label==='Baseline'?beforeLighting:afterLighting} layers={label==='Baseline'?beforeLayers:afterLayers}/><strong>{label}</strong>{label==='Planned'&&<small>Highlighted footprints · ↓ modelled infiltration · route line = configured outlet</small>}</div>)}</div>
   <div className="intervention-effects" aria-label="Selected intervention status">{result.designs.map((design,i)=>{const effect=currentEffects.byDesign[i];return <article key={design.id}><span className={`effect-swatch ${design.kind}`}/><div><strong>{INTERVENTION_NAMES[design.kind]} · {design.id}</strong><p>{statusText[effect.status]} · {effect.waterAtFootprintM3.toFixed(2)} m³ at its footprint, including {effect.belowGroundM3.toFixed(2)} m³ below the surface · approximately {(effect.fillFraction*100).toFixed(0)}% of configured depression plus subsurface capacity occupied.</p></div></article>;})}</div>
   <p className="effect-boundary"><strong>What the cues mean:</strong> footprint colours and storage pulses are driven by the planned solver frame. Down arrows appear only where surface water and configured infiltration coexist. Outlet traces show the configured route; they do not claim a measured per-facility flow. These are modelled screening results, not guaranteed flood prevention.</p>
   <div className="replay-water" aria-label="Exposure and water accounting at replay time">{(['Baseline','Planned'] as const).map((label,i)=>{const metric=currentMetrics![i],loss=losses![i];return <p key={label}><strong>{label}</strong>: {metric.affectedBuildings} buildings at or above {Math.round(exposureThreshold*100)} cm · {metric.areaAboveThresholdM2.toFixed(0)} m² above threshold · peak {metric.peakDepthM.toFixed(3)} m · surface {metric.surfaceM3.toFixed(2)} m³ · soil/facility {metric.subsurfaceM3.toFixed(2)} m³ · deep percolation {metric.deepPercolationM3.toFixed(2)} m³ · exported {metric.outflowM3.toFixed(2)} m³ · monetary loss {loss.totalMinor===null?'unavailable · '+loss.unvaluedBuildings+' buildings lack valuation/floor/curve data':'$'+(loss.totalMinor/100).toLocaleString()+' (valuation coverage '+(loss.valuationCoverage*100).toFixed(1)+'%; ±20% valuation sensitivity $'+(.8*loss.totalMinor/100).toLocaleString()+'–$'+(1.2*loss.totalMinor/100).toLocaleString()+')'}</p>;})}<p><strong>Scenario differences:</strong> {difference(currentEffects.deepPercolationDifferenceM3,'less cumulative deep percolation','more cumulative deep percolation')} · {difference(currentEffects.externalDischargeDifferenceM3,'less external discharge','more external discharge')}. <strong>Final local adverse change:</strong> {worsening.toFixed(0)} m² has at least 5 cm greater peak depth.</p></div>
   <div className="replay-controls"><button onClick={()=>{if(index===length-1)setIndex(0);setPlaying(!playing);}}>{playing?'Pause replay':'Play replay'}</button><input aria-label="Replay time" type="range" min="0" max={length-1} value={index} onChange={e=>{setPlaying(false);setIndex(+e.target.value);}}/><span>{(baseline[index].time_s/60).toFixed(1)} min</span></div>
  </>}
 </section>;
}
