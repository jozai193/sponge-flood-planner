// Complete the authorized prior-event computation and retain its acceptance decision.
import {spawn} from 'node:child_process';
import {readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const root='artifacts/validation',folder=root+'/sandy-2012-grid128',python=resolve('.venv/Scripts/python.exe');
async function command(args){await new Promise((yes,no)=>{const p=spawn(python,args,{windowsHide:true,stdio:'inherit'});p.on('error',no);p.on('close',c=>c===0?yes():no(Error(args.join(' ')+' failed: '+c)));});}
async function status(stage,extra={}){await writeFile(root+'/refinement-status.json',JSON.stringify({stage,updated_at:new Date().toISOString(),...extra}));}
try{
 await status('waiting_for_sandy_prior_event_regression');
 const deadline=Date.now()+6*3600000;
 while(true){
  if(Date.now()>deadline)throw Error('Six-hour computation limit; checkpoint retained');
  const s=JSON.parse(await readFile(folder+'/job-status.json','utf8'));
  if(s.stage==='failed')throw Error(s.error);
  if(s.stage==='completed')break;
  await new Promise(r=>setTimeout(r,10000));
 }
 await status('checking_sandy_prior_event_regression');
 await command(['scripts/freeze_historical_result.py',folder,'sandy-2012-grid128-completed']);
 await command(['-m','scripts.compare_sandy_grid_candidate']);
 await command(['scripts/diagnose_event_timing.py',folder]);
 await command(['scripts/diagnose_access_threshold.py',folder]);
 await command(['scripts/plot_grid_comparison.py',root+'/sandy-2012',folder]);
 await command(['-m','scripts.audit_saved_replays']);
 await command(['scripts/update_validation_registry.py']);
 await command(['scripts/summarize_historical_experiments.py']);
 await command(['scripts/render_refinement_report.py']);
 await command(['scripts/render_validation_dashboard.py']);
 const comparisons=await Promise.all(['irma-2017','ian-2022','sandy-2012'].map(async e=>JSON.parse(await readFile(`${root}/${e}-grid128/regression-comparison.json`,'utf8'))));
 const decision=comparisons.every(c=>c.regression_gate_passed)?'passes_three_retained_event_checks_not_general_validation':'reject_general_refinement_claim';
 await writeFile(root+'/refinement-decision.json',JSON.stringify({comparisons,decision,production_default_changed:false,
  limitation:'Sparse development and prior-event checks do not validate general flood accuracy. No production adoption or physical parameter fitting.'},null,2));
 await status('completed',{decision});
}catch(e){await status('failed',{error:String(e)});throw e;}
