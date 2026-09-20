import {openDB} from 'idb';
import type {GPUCheckpoint,GPUInput} from '../../../packages/simulation/src/gpu';
import {inputIdentity} from '../../../packages/simulation/src/identity';
import {validateGPUInput} from '../../../packages/simulation/src/gpu';
import {validateRainfall,type RainInterval} from '../../../packages/simulation/src/rainfall';
export interface PausedStorm {checkpoint:{solver:GPUCheckpoint;stormIdentity:string};input:GPUInput;duration:number;recession:number;depth:number;intervals?:RainInterval[]}
export interface RecoveryRecord {version:1;savedAt:string;run:PausedStorm;context:{bundle:any;input:GPUInput;designs:any[];flood:any;rain:number;minutes:number;importedStorm:any;antecedentSaturation?:number;budget:number;city:any;contextStatus:string}}
const database=()=>openDB('sponge-recovery',1,{upgrade(db){db.createObjectStore('checkpoints');}});
// Duplicate Tab copies sessionStorage. Hold an origin-wide lock for this document's
// lifetime so a copied session forks its checkpoint instead of sharing write access.
async function claimRecoveryKey():Promise<string>{
 let storedKey:string|null=null;
 try{storedKey=sessionStorage.getItem('sponge-recovery-key');}catch{/* Storage may be disabled. */}
 const requested=storedKey??'tab:'+crypto.randomUUID();
 if(!navigator.locks)throw new Error('Safe recovery requires browser Web Locks support');
 const claim=(key:string)=>new Promise<boolean>((resolve,reject)=>{
  navigator.locks.request('sponge-recovery:'+key,{ifAvailable:true},lock=>{
   resolve(!!lock);
   // The browser releases this lock when the document is destroyed.
   if(lock)return new Promise<void>(()=>{});
  }).catch(reject);
 });
 let key=requested;
 if(!await claim(key)){
  key='tab:'+crypto.randomUUID();
  if(!await claim(key))throw new Error('Could not isolate saved storm');
  const db=await database();
  try{
   const tx=db.transaction('checkpoints','readwrite');
   const previous=await tx.store.get(requested);
   if(previous)await tx.store.put(previous,key);
   const comparison=await tx.store.get('comparison:'+requested);
   if(comparison)await tx.store.put(comparison,'comparison:'+key);
   await tx.done;
  }finally{db.close();}
 }
 try{sessionStorage.setItem('sponge-recovery-key',key);}catch{/* In-tab saves still work. */}
 return key;
}
// Lazy initialization also avoids an unhandled rejection before the UI can report it.
let keyPromise:Promise<string>|undefined;
const getRecoveryKey=()=>keyPromise??=claimRecoveryKey();
export async function readSavedComparison():Promise<unknown>{
 await pending.catch(()=>{});const key=await getRecoveryKey(),db=await database();
 try{return await db.get('checkpoints','comparison:'+key);}finally{db.close();}
}
export function writeSavedComparison(record:unknown){
 pending=pending.catch(()=>{}).then(async()=>{
  const key=await getRecoveryKey(),db=await database();
  try{if(record)await db.put('checkpoints',record,'comparison:'+key);else await db.delete('checkpoints','comparison:'+key);}finally{db.close();}
 });return pending;
}
// Serialize operations so an older checkpoint write cannot resurrect a discarded run.
let pending:Promise<unknown>=Promise.resolve();
export function saveRecovery(record:RecoveryRecord|null){
 pending=pending.catch(()=>{}).then(async()=>{const recoveryKey=await getRecoveryKey();const db=await database();try{if(record)await db.put('checkpoints',record,recoveryKey);else await db.delete('checkpoints',recoveryKey);}finally{db.close();}});
 return pending;
}
export async function readRecovery():Promise<RecoveryRecord|null>{
 await pending.catch(()=>{});const recoveryKey=await getRecoveryKey();const db=await database();let record:RecoveryRecord|undefined;try{
  // Claim a legacy checkpoint atomically: only one tab may migrate the old shared slot.
  const tx=db.transaction('checkpoints','readwrite');
  record=await tx.store.get(recoveryKey);
  if(!record){
    const legacy=await tx.store.get('latest');
    if(legacy){record=legacy;await tx.store.put(legacy,recoveryKey);await tx.store.delete('latest');}
  }
  await tx.done;
 }finally{db.close();}
 if(!record)return null;
 if(record.version!==1||!record.context?.bundle?.bundle_id)throw new Error('Unsupported saved run');
 const r=record.run;validateGPUInput(r.input);validateGPUInput(record.context.input);validateRainfall(r);
 if(r.checkpoint.solver.inputHash!==await inputIdentity({...r.input,maxStepS:r.input.maxStepS??10}))throw new Error('Saved run input identity failed');
 if(r.checkpoint.stormIdentity!==JSON.stringify({duration:r.duration,depth:r.depth,recession:r.recession,intervals:r.intervals}))throw new Error('Saved storm identity failed');
 return record;
}
