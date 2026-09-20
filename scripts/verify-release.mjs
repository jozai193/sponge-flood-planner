import {existsSync} from 'node:fs';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';

const root=resolve(import.meta.dirname,'..');
const statusPath=resolve(root,'docs/hackathon-build/implementation-status.json');
const prdPath=resolve(root,'docs/hackathon-build/prd.md');
const outputPath=resolve(root,'output/verification/release-audit.json');
const issues=[];
const verifiedEvidence=[];

function evidencePaths(entry){
  const prefix=String(entry).split(': ')[0];
  return prefix.split(' and ').map(value=>value.trim()).filter(value=>value.includes('/'));
}

try{
  const status=JSON.parse(await readFile(statusPath,'utf8'));
  const prd=await readFile(prdPath,'utf8');
  const expected=[...prd.matchAll(/^- (A\d+):/gm)].map(match=>match[1]);
  const seen=new Set();
  if(!expected.length||!Array.isArray(status.acceptance))throw new Error('Missing requirements or acceptance registry');

  for(const row of status.acceptance){
    if(!expected.includes(row.id)||seen.has(row.id)){
      issues.push(`Unknown or duplicate ID: ${row.id}`);
      continue;
    }
    seen.add(row.id);
    if(!['pending','partial','passed'].includes(row.status))issues.push(`${row.id}: invalid status ${row.status}`);
    if(row.status!=='passed'){
      issues.push(`${row.id}: ${row.status}`);
      continue;
    }
    if(!Array.isArray(row.evidence)||!row.evidence.length){
      issues.push(`${row.id}: passing claim has no evidence`);
      continue;
    }
    for(const entry of row.evidence){
      const paths=evidencePaths(entry);
      if(!paths.length){
        issues.push(`${row.id}: evidence has no repository path: ${entry}`);
        continue;
      }
      for(const path of paths){
        if(!existsSync(resolve(root,path)))issues.push(`${row.id}: evidence path missing: ${path}`);
        else verifiedEvidence.push({id:row.id,path});
      }
    }
  }
  for(const id of expected)if(!seen.has(id))issues.push(`${id}: missing entry`);
  for(const blocker of status.runtime_blockers??[])if(blocker.status!=='resolved')issues.push(`Runtime blocker: ${blocker.component}`);

  const report={checkedAt:new Date().toISOString(),releaseReady:issues.length===0,
    requirementCount:expected.length,passedCount:status.acceptance.filter(row=>row.status==='passed').length,
    verifiedEvidenceCount:verifiedEvidence.length,issues};
  await mkdir(resolve(outputPath,'..'),{recursive:true});
  await writeFile(outputPath,JSON.stringify(report,null,2)+'\n');
  if(issues.length){
    console.error(`Release incomplete (${report.passedCount}/${report.requirementCount} accepted):\n${issues.join('\n')}`);
    process.exitCode=1;
  }else console.log(`Release evidence verified: ${report.requirementCount} requirements, ${verifiedEvidence.length} evidence paths.`);
}catch(error){
  console.error(`Release audit failed: ${error.message}`);
  process.exitCode=1;
}
