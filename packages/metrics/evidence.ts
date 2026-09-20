import type {buildReport} from './report';
import {selectedGeoJSON} from './geojson';
import {unpackInput} from './report';
import {modelSourceSha256} from './build-info';
export async function evidenceFiles(report:Awaited<ReturnType<typeof buildReport>>){
 const scenario=report.scenario;
 const spatial=selectedGeoJSON(unpackInput(scenario.baselineInput),scenario.selectedDesigns,scenario.provenance.grid,scenario.evidence.budgetMinor);
 const files:Record<string,string>={
  'sponge-planning-report.html':report.html,
  'sponge-assumed-costs.csv':report.csv,
  'sponge-reproducible-comparison.json':JSON.stringify(scenario),
  'sponge-selected-designs.geojson':JSON.stringify({...spatial,evidence:scenario.evidence})
 };
 const artifacts=await Promise.all(Object.entries(files).map(async([name,content])=>{
  const bytes=new TextEncoder().encode(content);
  const hash=await crypto.subtle.digest('SHA-256',bytes);
  return {name,bytes:bytes.byteLength,sha256:Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join('')};
 }));
 const manifest={schema:'sponge-export-manifest',version:1,encoding:'UTF-8',artifacts,
  run:{id:scenario.evidence.runId??null,createdAt:scenario.evidence.createdAt??null},
  simulation:{baselineInputHash:scenario.evidence.baselineInputHash,plannedInputHash:scenario.evidence.plannedInputHash,engine:scenario.evidence.engine,storm:scenario.evidence.storm},
  model:{sourceTreeSha256:modelSourceSha256,scope:'packages/simulation + packages/domain + packages/optimizer + packages/metrics'},
  bundleId:scenario.provenance.bundle_id??null,sources:scenario.provenance.sources??[],
  limitations:['Checksums detect changed files relative to this manifest; they do not authenticate the publisher or validate the model.','Provider source hashes are retained metadata; original provider bytes are not included.','The model source-tree hash identifies the built implementation scope; source files are not duplicated inside the export.']};
 return {files,manifest};
}
