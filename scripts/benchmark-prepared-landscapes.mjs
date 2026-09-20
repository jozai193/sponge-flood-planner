import {chromium} from '@playwright/test';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
const ids=process.argv.slice(2);
if(!ids.length||ids.some(id=>! /^[a-f0-9]{64}$/.test(id)))throw new Error('Provide prepared bundle IDs');
const hardware=process.env.SPONGE_BROWSER==='chrome';
const browser=await chromium.launch(hardware?{channel:'chrome'}:{args:['--enable-webgl','--ignore-gpu-blocklist']});
const results=[];
const profiling=process.env.SPONGE_PROFILE==='1';
try{
 for(const id of ids){
  const folder=join('data/local/bundles',id);
  const manifest=JSON.parse(await readFile(join(folder,'manifest.json'),'utf8'));
  await mkdir('artifacts/verification/landscape-fixtures',{recursive:true});
  const contextPath=join('artifacts/verification/landscape-fixtures',id+'.json');
  const context=JSON.parse(await readFile(contextPath,'utf8'));

  for(let repeat=0;repeat<(profiling?1:3);repeat++){
   const page=await browser.newPage({viewport:{width:1440,height:960}});
   await page.addInitScript(()=>{
    sessionStorage.setItem('sponge-session','prepared-benchmark-only');
    const timing={sceneMs:null,controlsMs:null,detailReadyMs:null,longTasks:[]};
    window.__spongeTiming=timing;
    new MutationObserver(()=>{
     if(timing.sceneMs===null&&document.documentElement?.dataset.sceneLoadMs)timing.sceneMs=performance.now();
     if(timing.detailReadyMs===null&&document.documentElement?.dataset.sceneDetailReadyMs)timing.detailReadyMs=performance.now();
     const button=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Run storm');
     if(timing.controlsMs===null&&button&&!button.disabled)timing.controlsMs=performance.now();
    }).observe(document,{subtree:true,childList:true,attributes:true});
    new PerformanceObserver(list=>{for(const e of list.getEntries())timing.longTasks.push({start:e.startTime,duration:e.duration});}).observe({type:'longtask',buffered:true});
   });
   const cdp=profiling?await page.context().newCDPSession(page):null;
   if(cdp){await cdp.send('Profiler.enable');await cdp.send('Profiler.start');}
   const errors=[];page.on('pageerror',e=>errors.push(e.message));
   await page.route('**/api/v1/bundles/**',async route=>{
    const pathname=new URL(route.request().url()).pathname;
    if(pathname.endsWith('/context'))return route.fulfill({json:context});
    const array=pathname.match(/\/arrays\/([a-z_]+)$/);
    if(array)return route.fulfill({body:await readFile(join(folder,array[1]+'.bin')),contentType:'application/octet-stream'});
    if(pathname.endsWith('/'+id))return route.fulfill({json:manifest});
    return route.fulfill({status:503,json:{detail:'Imagery excluded from prepared model-view benchmark'}});
   });
   const start=performance.now();
   await page.goto('http://127.0.0.1:5173/?bundle='+id);
   await page.waitForFunction(()=>document.documentElement.dataset.sceneLoadMs,undefined,{timeout:45000});
   const sceneCallbackMs=performance.now()-start;
   await page.getByRole('button',{name:'Run storm',exact:true}).waitFor();
   await page.waitForFunction(()=>{const button=[...document.querySelectorAll('button')].find(b=>b.textContent.trim()==='Run storm');return button&&!button.disabled;},undefined,{timeout:45000});
   const controlsReadyMs=performance.now()-start;
   if(process.env.SPONGE_WAIT_SCENE_DETAIL==='1')await page.waitForFunction(()=>document.documentElement.dataset.sceneDetailReadyMs,undefined,{timeout:45000});
   const renderer=await page.evaluate(()=>{const gl=document.querySelector('canvas')?.getContext('webgl2');const ext=gl?.getExtension('WEBGL_debug_renderer_info');return ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):'unavailable';});
   const inPageTiming=await page.evaluate(()=>window.__spongeTiming);
   if(cdp){const {profile}=await cdp.send('Profiler.stop');await writeFile('artifacts/verification/landscape-profile-'+id+'.json',JSON.stringify(profile));}
   let orbitTiming=null;
   if(process.env.SPONGE_ORBIT==='1'){
    await page.evaluate(()=>{window.__orbitTimes=[];window.__orbitActive=true;function tick(t){if(!window.__orbitActive)return;window.__orbitTimes.push(t);requestAnimationFrame(tick);}requestAnimationFrame(tick);});
    await page.mouse.move(900,450);await page.mouse.down();
    for(let step=0;step<60;step++){await page.mouse.move(900+160*Math.sin(step/12),450+60*Math.cos(step/12));await page.waitForTimeout(16);}
    await page.mouse.up();
    orbitTiming=await page.evaluate(()=>{window.__orbitActive=false;const t=window.__orbitTimes,d=t.slice(1).map((x,i)=>x-t[i]).sort((a,b)=>a-b);return {samples:d.length,medianRafIntervalMs:d[Math.floor(d.length*.5)],p95RafIntervalMs:d[Math.floor(d.length*.95)],maxRafIntervalMs:d.at(-1),note:'RAF scheduling during synthetic orbit; not GPU draw throughput'};});
   }
   if(errors.length)throw new Error(errors.join('\n'));
   results.push({id,label:manifest.label,repeat,sceneCallbackMs,controlsReadyMs,trees:context.trees.length,waterCells:context.water?.length??0,renderer,inPageTiming,orbitTiming});
   console.log(manifest.label+' sample '+(repeat+1)+': '+Math.round(controlsReadyMs)+' ms');
   await page.close();
  }
 }
}finally{await browser.close();}
await mkdir('artifacts/verification',{recursive:true});
const result={browserChannel:hardware?'installed Chrome':'bundled Chromium',measuredAt:new Date().toISOString(),conditions:'Prepared local arrays and generated landscape supplied through browser test routes. Context generation occurs before timing. Imagery excluded. Fresh browser context per sample, 1440x960, local Vite development server. Scene callback and enabled controls are not GPU completion or FPS. No API/download/cold preparation performance measured.',results};
await writeFile(process.env.SPONGE_BENCHMARK_OUTPUT??(hardware?'artifacts/verification/prepared-landscape-hardware-speed.json':profiling?'artifacts/verification/prepared-landscape-profile-timing.json':'artifacts/verification/prepared-landscape-speed.json'),JSON.stringify(result,null,2));
console.log(JSON.stringify(results));
