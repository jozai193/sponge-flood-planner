import {useEffect,useRef,useState} from 'react';
type Client=(path:string,body?:unknown)=>Promise<any>;
export default function DataEnrichment({bundleId,api,onLoad,onRainfall,uploadTerrain}:{bundleId:string;api:Client;onLoad:(id:string)=>Promise<void>;onRainfall:(storm:any)=>void;uploadTerrain:(bundleId:string,file:File,source:unknown)=>Promise<any>}){
  const [job,setJob]=useState<any>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const [start,setStart]=useState(''),[end,setEnd]=useState(''),[materials,setMaterials]=useState(false);
  const [surveys,setSurveys]=useState<any[]>([]);
  const [terrainSource,setTerrainSource]=useState<any>(null);
  const alive=useRef(true);
  useEffect(()=>{alive.current=true;api('/bundles/'+bundleId+'/imports').then(value=>{if(alive.current)setSurveys(value);}).catch(()=>{});
    api('/bundles/'+bundleId+'/enrichment').then(async jobs=>{if(alive.current&&jobs.length){setJob(jobs[0]);if(['queued','running'].includes(jobs[0].status)){setBusy(true);await follow(jobs[0].id);}}}).catch(()=>{});
    return()=>{alive.current=false;};},[bundleId,api]);
  async function follow(id:string){
    try{while(alive.current){const result=await api('/enrichment/'+id);if(!alive.current)return;setJob(result);
      if(!['queued','running'].includes(result.status))break;
      await new Promise(resolve=>setTimeout(resolve,1500));
    }}catch(e){if(alive.current)setError(String(e));}finally{if(alive.current)setBusy(false);}
  }
  async function collect(){
    setBusy(true);setError('');
    try{
      const result=await api('/bundles/'+bundleId+'/enrichment',{...(start&&end?{start_date:start,end_date:end}:{})});
      await follow(result.id);
    }catch(e){if(alive.current)setError(String(e));}finally{if(alive.current)setBusy(false);}
  }
  async function download(key:string){
    try{const value=await api('/enrichment/'+job.id+'/'+key);const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));
      const a=document.createElement('a');a.href=url;a.download='sponge-'+key+'.json';a.click();URL.revokeObjectURL(url);
    }catch(e){setError(String(e));}
  }
  async function apply(){
    setBusy(true);setError('');try{const result=await api('/enrichment/'+job.id+'/apply',{
      buildings:job.results.buildings?.status==='available',landcover:materials,accept_exploratory_materials:materials});
      await onLoad(result.bundle_id);
    }catch(e){setError(String(e));}finally{if(alive.current)setBusy(false);}
  }
  async function upload(file?:File){
    if(!file)return;
    try{
      if(file.size>10_000_000)throw new Error('Survey exceeds 10 MB');
      const value=JSON.parse(await file.text());
      await api('/bundles/'+bundleId+'/imports',value);
      if(alive.current)setSurveys(await api('/bundles/'+bundleId+'/imports'));
    }catch(e){setError(String(e));}
  }
  return <section aria-label="Broaden neighbourhood data"><h3>Broaden neighbourhood data</h3>
    <p>Acquire area-specific buildings, elevation, land cover, soils and waterways. Rainfall uses the exact event dates. Dynamic World uses the preceding 90 days through the event end (or today), because storm days may have no clear satellite observations.</p>
    <label>Event start <input type="date" value={start} onChange={e=>setStart(e.target.value)}/></label>
    <label>Event end <input type="date" value={end} onChange={e=>setEnd(e.target.value)}/></label>
    <button disabled={busy} onClick={collect}>{busy?'Acquiring data…':'Find additional data'}</button>
    {job&&<><p aria-live="polite">{job.status} · {job.stage??'waiting for worker'}</p>
      {Object.entries(job.results??{}).map(([key,value]:[string,any])=><div key={key}><h4>{key} · {value.status}</h4>
        <p>{value.reason||value.note}</p>{value.feature_count!=null&&<p>{value.feature_count} features</p>}
        {value.coverage_fraction!=null&&<p>{(value.coverage_fraction*100).toFixed(1)}% valid grid samples</p>}
        {['available','catalog_only'].includes(value.status)&&<button onClick={()=>download(key)}>Download {key} evidence</button>}
        {key==='rainfall'&&value.status==='available'&&<button onClick={async()=>{try{const evidence=await api('/enrichment/'+job.id+'/rainfall');onRainfall(evidence.survey.storm);}catch(e){setError(String(e));}}}>Use acquired rainfall event</button>}</div>)}
      {job.results?.landcover?.status==='available'&&<label><input type="checkbox" checked={materials} onChange={e=>setMaterials(e.target.checked)}/>
        Use land-cover classes with exploratory hydraulic presets; these are not measured infiltration rates.</label>}
      {(job.results?.buildings?.status==='available'||materials)&&<button disabled={busy} onClick={apply}>Create enriched simulation revision</button>}
    </>}
    <h4>Import local evidence</h4><p>Upload a SPONGE survey JSON containing drainage topology, rainfall intervals, buildings, land-cover polygons, catchments, waterways or flood observations. Structural validation does not establish accuracy.</p>
    <button onClick={async()=>{try{const formats=await api('/import-formats');const url=URL.createObjectURL(new Blob([JSON.stringify(formats,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='sponge-survey-schemas.json';a.click();URL.revokeObjectURL(url);}catch(e){setError(String(e));}}}>Download survey formats</button>
    <input aria-label="Import survey JSON" type="file" accept=".json,application/json" onChange={e=>upload(e.target.files?.[0])}/>
    {surveys.map(s=><p key={s.id}>{s.kind}: {s.source.title} · imported
      {s.kind==='rainfall'&&<button onClick={async()=>{try{const survey=await api('/imports/'+s.id);onRainfall(survey.storm);}catch(e){setError(String(e));}}}>Use rainfall event</button>}</p>)}
    <h4>Import surveyed terrain</h4><p>Supply source metadata JSON, then a single-band bare-earth or combined land/seabed GeoTIFF with elevations in metres. Set metadata surface_type to bare_earth or topobathymetry. Coastal rasters must cover the full domain, use negative elevations below their declared datum, and align sea levels to that datum. This creates a new revision and resets scenario edits.</p>
    <label>Terrain source metadata<input type="file" accept=".json" onChange={async e=>{try{const f=e.target.files?.[0];if(f)setTerrainSource(JSON.parse(await f.text()));}catch(err){setError(String(err));}}}/></label>
    <label>Terrain GeoTIFF<input type="file" accept=".tif,.tiff" disabled={!terrainSource||busy} onChange={async e=>{const f=e.target.files?.[0];if(!f)return;setBusy(true);try{if(f.size>100_000_000)throw new Error('Terrain exceeds 100 MB');const r=await uploadTerrain(bundleId,f,terrainSource);await onLoad(r.bundle_id);}catch(err){setError(String(err));}finally{if(alive.current)setBusy(false);}}}/></label>
    {error&&<p role="alert">{error}</p>}
  </section>;
}
