import {chromium} from '@playwright/test';
import {mkdir,writeFile} from 'node:fs/promises';
const examples=await (await fetch('http://127.0.0.1:8787/api/v1/examples')).json();
const browser=await chromium.launch({args:['--enable-webgl','--ignore-gpu-blocklist']});
const results=[];
try{for(const example of examples){for(let repeat=0;repeat<3;repeat++){
 const page=await browser.newPage({viewport:{width:1440,height:960}});
 await page.route('**/api/v1/examples',route=>route.fulfill({json:[example]}));
 const start=performance.now();await page.goto('http://127.0.0.1:5173/');
 await page.waitForFunction(()=>document.documentElement.dataset.sceneLoadMs,{},{timeout:30000});
 const navigationToSceneMs=performance.now()-start;
 await page.waitForFunction(()=>document.querySelector('.maplabel')?.textContent?.includes('City of Philadelphia street centerlines'),{},{timeout:30000});
 const navigationToStreetContextMs=performance.now()-start;
 const sample=await page.evaluate(async()=>{
  const path='/src/testing/gpu-harness.ts';const {GPUSolver}=await import(path);
  const n=16;const s=new GPUSolver({nx:4,ny:4,dx:1,dy:1,z:new Float32Array(n),solid:new Uint8Array(n),rainWeights:new Float32Array(n).fill(1),roughness:new Float32Array(n),capacity:new Float32Array(n),infiltration:new Float32Array(n)});const renderer=s.info().renderer;s.dispose();
  const times=[];await new Promise(resolve=>{function tick(t){times.push(t);if(times.length>=61)resolve();else requestAnimationFrame(tick);}requestAnimationFrame(tick);});
  return {renderer,sceneLoadMs:Number(document.documentElement.dataset.sceneLoadMs),rafCadenceFps:60000/(times[60]-times[0])};
 });
 results.push({location:example.label??example.bundle_id,repeat,navigationToSceneMs,navigationToStreetContextMs,...sample});await page.close();
}}
}finally{await browser.close();}
await mkdir('artifacts/verification',{recursive:true});
await writeFile('artifacts/verification/location-speed.json',JSON.stringify({measuredAt:new Date().toISOString(),conditions:'Local Vite development server, preprepared bundles, fresh page per sample, provider caches retained. RAF cadence is not GPU draw throughput. No cold geodata preparation or storm simulation measured.',results},null,2));
console.log(JSON.stringify(results));
