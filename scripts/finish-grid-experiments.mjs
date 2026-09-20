// Finish the two explicitly authorized, frozen experiments and record decisions.
import {spawn} from 'node:child_process';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const root='artifacts/validation';
const python=resolve('.venv/Scripts/python.exe');
const experiments=['irma-2017','ian-2022','irma-2017-grid128','ian-2022-grid128'];
const done=new Set();
async function command(args){await new Promise((yes,no)=>{const p=spawn(python,args,{windowsHide:true,stdio:'inherit'});p.on('error',no);p.on('close',c=>c===0?yes():no(Error(args.join(' ')+' failed: '+c)));});}
async function status(stage,extra={}){await writeFile(root+'/refinement-status.json',JSON.stringify({stage,completed:[...done],updated_at:new Date().toISOString(),...extra}));}
try{
 await status('waiting_for_frozen_runs');
 const deadline=Date.now()+6*3600000;
 while(done.size<experiments.length){
  if(Date.now()>deadline)throw Error('Six-hour computation limit reached; inspect retained job checkpoints');
  for(const name of experiments){
   if(done.has(name))continue;
   const job=JSON.parse(await readFile(`${root}/${name}/job-status.json`,'utf8'));
   if(job.stage==='failed')throw Error(name+': '+job.error);
   if(job.stage!=='completed')continue;
   await command(['scripts/diagnose_michael_points.py',`${root}/${name}`]);
   await command(['scripts/diagnose_access_threshold.py',`${root}/${name}`]);
   await command(['scripts/freeze_historical_result.py',`${root}/${name}`,name+'-completed']);
   done.add(name);await status('collecting_completed_runs');
  }
  if(done.size<experiments.length)await new Promise(r=>setTimeout(r,10000));
 }
 for(const event of ['irma-2017','ian-2022'])await command(['-m','scripts.compare_grid_candidate',`${root}/${event}`,`${root}/${event}-grid128`]);
 await command(['-m','scripts.audit_saved_replays']);
 await command(['scripts/update_validation_registry.py']);
 await command(['scripts/summarize_historical_experiments.py']);
 const comparisons=await Promise.all(['irma-2017','ian-2022'].map(async e=>JSON.parse(await readFile(`${root}/${e}-grid128/regression-comparison.json`,'utf8'))));
 const passes= comparisons.every(c=>c.regression_gate_passed);
 await writeFile(root+'/refinement-decision.json',JSON.stringify({comparisons,
  decision:passes?'passes_two_events_pending_prior_event_regression':'reject_general_refinement_claim',
  production_default_changed:false,
  limitation:'Sparse event screening is not general flood validation. No solver parameter tuning or production adoption performed. Even a two-event pass requires prior-event refinement regression before adoption.'},null,2));
 await status('completed',{decision:passes?'passes_two_events_pending_prior_event_regression':'reject_general_refinement_claim'});
}catch(e){await status('failed',{error:String(e)});throw e;}
