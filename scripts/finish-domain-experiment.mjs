// Finish evidence archiving for the already-authorized running local computation.
import {spawn} from 'node:child_process';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const root='artifacts/validation/matthew-2016-domain4km',python=resolve('.venv/Scripts/python.exe');
const status=(stage,extra={})=>writeFile(root+'/finish-status.json',JSON.stringify({stage,updated_at:new Date().toISOString(),...extra}));
async function command(args){await new Promise((yes,no)=>{const p=spawn(python,args,{windowsHide:true,stdio:'inherit'});p.on('error',no);p.on('close',code=>code===0?yes():no(Error(args.join(' ')+' exited '+code)));});}
try{
 await status('waiting_for_running_domain_experiment');const deadline=Date.now()+6*3600000;
 while(true){
  if(Date.now()>deadline)throw Error('Six-hour completion limit; saved checkpoints remain available');
  const job=JSON.parse(await readFile(root+'/job-status.json','utf8'));
  if(job.stage==='failed')throw Error(job.error);
  if(job.stage==='completed')break;
  await new Promise(resolve=>setTimeout(resolve,10000));
 }
 await status('preserving_completed_evidence');
 await command(['scripts/diagnose_access_threshold.py',root]);
 await command(['scripts/diagnose_event_timing.py',root]);
 await command(['scripts/freeze_historical_result.py',root,'matthew-2016-domain4km-completed']);
 await command(['-m','scripts.audit_saved_replays']);
 await command(['scripts/update_validation_registry.py']);
 await command(['scripts/render_domain_experiment.py']);
 const comparison=JSON.parse(await readFile(root+'/domain-comparison.json','utf8'));
 await status('completed',{decision:comparison.decision,production_enabled:false});
}catch(error){await status('failed',{error:String(error)});throw error;}
