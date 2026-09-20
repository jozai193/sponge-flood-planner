// Durable local computation wrapper: simulation, assessment, then inspection.
import {spawn} from 'node:child_process';
import {writeFile,access,readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
const root=process.argv[2];if(!root)throw Error('Experiment directory required');
async function status(stage,extra={}){await writeFile(`${root}/job-status.json`,JSON.stringify({stage,updated_at:new Date().toISOString(),...extra}));}
async function command(executable,args){await new Promise((resolve,reject)=>{const p=spawn(executable,args,{windowsHide:true,stdio:'inherit'});p.on('error',reject);p.on('close',code=>code===0?resolve():reject(Error(`${args[0]} exited ${code}`)));});}
try{
 const protocol=JSON.parse(await readFile(`${root}/protocol.json`,'utf8'));
 let complete=true;for(const run of protocol.bundles){try{await access(`${root}/simulation-${run.grid_cells}.json`);}catch(e){if(e.code!=='ENOENT')throw e;complete=false;}}
 if(!complete){await status('simulating');await command(process.execPath,['scripts/run-historical-validation.mjs',root]);}
 const python=resolve('.venv/Scripts/python.exe');
 await status('assessing');await command(python,['-m','scripts.assess_historical_validation',root]);
 await status('plotting');await command(python,['scripts/plot_historical_validation.py',root]);
 await status('rendering');await command(python,['scripts/render_historical_validation.py',root]);
 await status('completed');
}catch(e){await status('failed',{error:String(e)});throw e;}
