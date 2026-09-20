import {test,expect} from '@playwright/test';
test('independent tabs cannot overwrite or discard each others storm checkpoints',async({context})=>{
 const first=await context.newPage(),second=await context.newPage();
 await first.goto('/');await second.goto('/');
 for(const [page,label] of [[first,'first'],[second,'second']] as const){
  await page.evaluate(async(label)=>{
   const harness='/src/testing/gpu-harness.ts',recovery='/src/recovery.ts';
   const {GPUSolver}=await import(harness);const {saveRecovery}=await import(recovery);
   const input={nx:4,ny:4,dx:1,dy:1,z:new Float32Array(16),solid:new Uint8Array(16),rainWeights:new Float32Array(16).fill(1),roughness:new Float32Array(16),capacity:new Float32Array(16),infiltration:new Float32Array(16),maxStepS:10};
   const solver=new GPUSolver(input);solver.step(.1,.001);const checkpoint=await solver.checkpoint();solver.dispose();
   const storm={duration:1,depth:.001,recession:1};
   await saveRecovery({version:1,savedAt:new Date().toISOString(),run:{input,...storm,checkpoint:{solver:checkpoint,stormIdentity:JSON.stringify(storm)}},context:{bundle:{bundle_id:label},input,designs:[],flood:{},rain:1,minutes:1,importedStorm:null,budget:0,city:null,contextStatus:''}});
  },label);
 }
 const read=async(page:typeof first)=>page.evaluate(async()=>{const path='/src/recovery.ts';return (await (await import(path)).readRecovery())?.context.bundle.bundle_id??null;});
 expect(await read(first)).toBe('first');expect(await read(second)).toBe('second');
 // Reproduce Duplicate Tab's copied sessionStorage while the original is live.
 const originalKey=await first.evaluate(()=>sessionStorage.getItem('sponge-recovery-key'));
 const duplicate=await context.newPage();
 await duplicate.addInitScript(key=>{
  if(!sessionStorage.getItem('sponge-recovery-key'))sessionStorage.setItem('sponge-recovery-key',key!);
 },originalKey);
 await duplicate.goto('/');
 expect(await read(duplicate)).toBe('first');
 expect(await duplicate.evaluate(()=>sessionStorage.getItem('sponge-recovery-key'))).not.toBe(originalKey);
 await duplicate.reload();expect(await read(duplicate)).toBe('first');
 await duplicate.evaluate(async()=>{const path='/src/recovery.ts';await (await import(path)).saveRecovery(null);});
 expect(await read(duplicate)).toBeNull();expect(await read(first)).toBe('first');
 await duplicate.close();
 await second.evaluate(async()=>{const path='/src/recovery.ts';await (await import(path)).saveRecovery(null);});
 expect(await read(second)).toBeNull();expect(await read(first)).toBe('first');
 await first.reload();expect(await read(first)).toBe('first');
 // Simulate the older shared format, then race both tabs to claim it.
 await first.evaluate(async()=>{
  const path='/src/recovery.ts';const saved=await (await import(path)).readRecovery();
  await (await import(path)).saveRecovery(null);
  await new Promise<void>((resolve,reject)=>{
   const request=indexedDB.open('sponge-recovery',1);
   request.onerror=()=>reject(request.error);
   request.onsuccess=()=>{const db=request.result,tx=db.transaction('checkpoints','readwrite');tx.objectStore('checkpoints').put(saved,'latest');tx.oncomplete=()=>{db.close();resolve();};tx.onerror=()=>{db.close();reject(tx.error);};};
  });
 });
 const claimed=await Promise.all([read(first),read(second)]);
 expect(claimed.filter(value=>value==='first')).toHaveLength(1);
 expect(claimed.filter(value=>value===null)).toHaveLength(1);
 await first.close();await second.close();
});
