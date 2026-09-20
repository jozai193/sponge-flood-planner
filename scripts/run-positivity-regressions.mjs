import {spawn} from 'node:child_process';
import {writeFile,readFile,access} from 'node:fs/promises';
import {resolve} from 'node:path';
const python=resolve('.venv/Scripts/python.exe');
async function command(executable,args){await new Promise((yes,no)=>{const p=spawn(executable,args,{windowsHide:true,stdio:'inherit'});p.on('error',no);p.on('close',c=>c===0?yes():no(Error(args.join(' ')+' exited '+c)));});}
const allowed=['sandy-2012-positivity-v1','matthew-2016-positivity-v1'];
const selected=process.argv.slice(2).length?process.argv.slice(2):allowed;
if(selected.some(name=>!allowed.includes(name)))throw Error('Unknown candidate experiment');
for(const name of selected){
 const root='artifacts/validation/'+name;
 const status=async(stage,extra={})=>writeFile(root+'/job-status.json',JSON.stringify({stage,updated_at:new Date().toISOString(),...extra}));
 try{
  const protocol=JSON.parse(await readFile(root+'/protocol.json','utf8'));
  let complete=true;
  for(const run of protocol.bundles){try{await access(`${root}/simulation-${run.grid_cells}.json`);}catch(error){if(error.code!=='ENOENT')throw error;complete=false;}}
  if(!complete){await status('simulating');await command(process.execPath,['scripts/run-positivity-historical.mjs',root]);}
  await status('assessing');await command(python,['-m','scripts.assess_historical_validation',root]);
  await status('comparing');await command(python,['-m','scripts.compare_positivity_replay',root]);
  await status('completed',{production_enabled:false});
 }catch(error){await status('failed',{error:String(error),production_enabled:false});console.error(error);}
}
