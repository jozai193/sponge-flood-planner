import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
const sha=async path=>createHash('sha256').update(await readFile(path)).digest('hex');
const cpu='artifacts/validation/coastal-reference/float64.json',gpu='artifacts/validation/coastal-reference/nvidia.json';
const c=JSON.parse(await readFile(cpu,'utf8')),g=JSON.parse(await readFile(gpu,'utf8'));
const manifest={schema:'sponge.cross-engine-evidence.v1',createdAt:new Date().toISOString(),claim:'Implementation agreement for shared prescribed-boundary assumptions only; not observed flood accuracy or equation equivalence.',commonDisplayGrid:false,
 engines:[
  {id:'cpu-hll-float64-reference',buildSource:'services/reference/solver.py',buildSha256:await sha('services/reference/solver.py'),result:cpu,resultSha256:await sha(cpu),nativeGrids:[...new Set(c.cases.map(x=>`${Math.sqrt(x.depth.length)} cells represented by each native fixture`))]},
  {id:'webgl2-hll-order2',buildSource:'packages/simulation/src/gpu.ts',buildSha256:await sha('packages/simulation/src/gpu.ts'),result:gpu,resultSha256:await sha(gpu),nativeGrids:[...new Set(g.results.map(x=>`${x.case_name}: ${x.renderer.engine} allocation ${x.renderer.allocatedBytes} bytes`))]},
 ],comparison:{passed:g.passed,maxPeakErrorM:Math.max(...g.results.map(x=>x.max_peak_error_m)),caseCount:g.results.length},limitations:['Each result retains its engine-native arrays/grid metadata; no interpolation onto a common scoring grid is performed.','Agreement verifies two implementations of shared assumptions, not that different specialist equations are equivalent.']};
await mkdir('artifacts/verification',{recursive:true});await writeFile('artifacts/verification/cross-engine-manifest.json',JSON.stringify(manifest,null,2)+'\n');console.log(JSON.stringify(manifest.comparison));
