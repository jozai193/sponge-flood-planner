// Complete the authorized fresh-event comparison from already frozen inputs.
import {spawn} from 'node:child_process';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
const folder=process.argv[2],python=resolve('.venv/Scripts/python.exe');
if(!folder)throw Error('Frozen event directory required');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
async function command(args){await new Promise((yes,no)=>{const p=spawn(python,args,{windowsHide:true,stdio:'inherit'});p.on('error',no);p.on('close',c=>c===0?yes():no(Error(args.join(' ')+' failed: '+c)));});}
async function status(stage,extra={}){await writeFile(folder+'/holdout-status.json',JSON.stringify({stage,updated_at:new Date().toISOString(),...extra}));}
try{
 const frozen=JSON.parse(await readFile(folder+'/assessment-plan-freeze.json','utf8'));
 const deadline=Date.now()+6*3600000;await status('waiting_for_both_frozen_simulations');
 while(true){
  if(Date.now()>deadline)throw Error('Six-hour limit reached; checkpoints retained');
  const s=JSON.parse(await readFile(folder+'/job-status.json','utf8'));
  if(s.stage==='failed')throw Error(s.error);
  if(s.stage==='completed')break;
  await new Promise(r=>setTimeout(r,10000));
 }
 for(const [path,expected] of Object.entries(frozen.sha256))if(sha(await readFile(path))!==expected)throw Error('Frozen assessment criteria changed: '+path);
 await status('assessing_new_event');
 await command(['-m','scripts.assess_new_event_holdout',folder]);
 await command(['scripts/diagnose_michael_points.py',folder]);
 await command(['scripts/diagnose_access_threshold.py',folder]);
 await command(['scripts/diagnose_event_timing.py',folder]);
 await command(['scripts/plot_grid_comparison.py',folder,folder,'64','128']);
 await command(['scripts/freeze_historical_result.py',folder,'matthew-2016-completed']);
 await command(['-m','scripts.audit_saved_replays']);
 await command(['scripts/summarize_historical_experiments.py']);
 await command(['scripts/update_validation_registry.py']);
 await command(['scripts/render_new_event_report.py',folder]);
 await command(['scripts/render_validation_dashboard.py']);
 const result=JSON.parse(await readFile(folder+'/holdout-comparison.json','utf8'));
 await status('completed',{decision:result.decision,general_flood_accuracy_validated:false});
}catch(e){await status('failed',{error:String(e)});throw e;}
