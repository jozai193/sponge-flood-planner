import {spawn} from 'node:child_process';
import {access,writeFile,readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const root='artifacts/validation/matthew-2016-domain4km',python=resolve('.venv/Scripts/python.exe');
const status=(stage,extra={})=>writeFile(root+'/job-status.json',JSON.stringify({stage,updated_at:new Date().toISOString(),...extra}));
async function command(executable,args){await new Promise((yes,no)=>{const child=spawn(executable,args,{windowsHide:true,stdio:'inherit'});child.on('error',no);child.on('close',code=>code===0?yes():no(Error(args.join(' ')+' exited '+code)));});}
try{
 let completed=false;try{await access(root+'/simulation-128.json');completed=true;}catch(e){if(e.code!=='ENOENT')throw e;}
 if(!completed){await status('simulating');await command(process.execPath,['scripts/run-historical-validation.mjs',root]);}
 await status('assessing');await command(python,['-m','scripts.assess_historical_validation',root]);
 await status('comparing');await command(python,['-m','scripts.compare_domain_experiment',root]);
 await command(python,['scripts/plot_historical_validation.py',root]);
 await command(python,['scripts/render_historical_validation.py',root]);
 const comparison=JSON.parse(await readFile(root+'/domain-comparison.json','utf8'));
 await status('completed',{decision:comparison.decision,production_enabled:false});
}catch(error){await status('failed',{error:String(error),production_enabled:false});throw error;}
