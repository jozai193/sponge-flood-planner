import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
const root='artifacts/validation/checkpoint-recovery';
const protocol=JSON.parse(await readFile('artifacts/validation/michael-2018/protocol.json','utf8'));
protocol.event_id='numerical-checkpoint-fixture-not-historical-validation';
protocol.duration_s=120;
protocol.bundles=protocol.bundles.map(r=>({...r,levels:[r.levels[0],{timeS:120,elevationM:r.levels[0].elevationM}]}));
const text=JSON.stringify(protocol,null,2),hash=createHash('sha256').update(text).digest('hex');
for(const name of ['resumed','uninterrupted']){
 await mkdir(`${root}/${name}`,{recursive:true});
 await writeFile(`${root}/${name}/protocol.json`,text,{flag:'wx'});
 await writeFile(`${root}/${name}/protocol.sha256`,hash,{flag:'wx'});
}
async function run(name,stop=false){
 const args=['scripts/run-historical-validation.mjs',`${root}/${name}`];if(stop)args.push('--stop-after-checkpoint');
 return new Promise((resolve,reject)=>{const p=spawn(process.execPath,args,{stdio:['ignore','pipe','pipe'],windowsHide:true});let log='';p.stdout.on('data',b=>log+=b);p.stderr.on('data',b=>log+=b);p.on('error',reject);p.on('close',code=>resolve({code,log}));});
}
const interrupted=await run('resumed',true);
if(interrupted.code===0||!interrupted.log.includes('Intentional checkpoint recovery verification stop'))throw Error('Did not exercise intended interruption: '+interrupted.log);
for(const name of ['resumed','uninterrupted']){const r=await run(name);if(r.code!==0)throw Error(r.log);}
const a=JSON.parse(await readFile(`${root}/resumed/simulation-64.json`,'utf8'));
const b=JSON.parse(await readFile(`${root}/uninterrupted/simulation-64.json`,'utf8'));
const passed=JSON.stringify(a.frames)===JSON.stringify(b.frames)&&JSON.stringify(a.ledger)===JSON.stringify(b.ledger)&&a.steps===b.steps&&a.resumedFromTimeS>0;
const result={passed,resumed_at_s:a.resumedFromTimeS,frames:a.frames.length,steps:a.steps,exact_saved_frame_and_ledger_match:passed};
await writeFile(`${root}/result.json`,JSON.stringify(result,null,2));console.log(JSON.stringify(result));
if(!passed)throw Error('Resumed result differs from uninterrupted run');
