import rules from '../contracts/data-admission-rules.json';
import {parseScenarioSpec} from './scenario-wire';
import type {ScenarioSpecV2} from '../contracts/src/ScenarioSpecV2';

const record=(v:unknown):Record<string,any>=>v!==null&&typeof v==='object'&&!Array.isArray(v)?v:{};
const text=(v:unknown)=>typeof v==='string'&&v.trim().length>0;
const finite=(v:unknown):v is number=>typeof v==='number'&&Number.isFinite(v);
export type DataState='exploratory'|'needs_data'|'unsupported';

/** Metadata screening only: never promote labels or self-reported quality to site validation. */
export function assessScenarioData(scenario:ScenarioSpecV2,manifest:unknown){
 const spec=parseScenarioSpec(scenario),m=record(manifest),g=record(m.grid),q=record(m.quality),d=spec.domain,f=spec.forcing;
 const sources=Array.isArray(m.sources)?m.sources.filter(s=>Object.keys(record(s)).length>0):[];
 const sameGrid=['nx','ny','dx_m','dy_m'].every(k=>finite(g[k])&&g[k]===(d as any)[k]);
 const datumKnown=text(g.vertical_datum)&&!/unknown|unspecified|unresolved|mixed/i.test(g.vertical_datum);
 const facts:Record<string,boolean>={
  domain_identity:sameGrid&&text(m.bundle_id)&&m.bundle_id===d.bundle_id&&g.crs===d.horizontal_crs&&
   (g.vertical_datum??'unspecified')===d.vertical_datum&&(g.elevation_origin_m??null)===(d.elevation_origin_m??null),
  terrain_source:text(q.terrain_provider)&&sources.length>0,
  terrain_resolution:finite(q.native_resolution_m)&&q.native_resolution_m>0,
  coastal_datum:datumKnown&&finite(g.elevation_origin_m),
  coastal_tail:!!f.coastal&&f.coastal.levels.at(-1)!.timeS<f.storm.duration+f.storm.recession
 };
 const enabled=new Set(['all',...Object.entries(f.components).filter(([,v])=>v).map(([k])=>k),...(f.outlets.length?['drainage']:[])]);
 const checks=rules.checks.filter(r=>enabled.has(r.hazard)).map(r=>({id:r.id,hazard:r.hazard,status:(facts[r.id]?r.pass:r.fail) as DataState,reason:facts[r.id]?r.yes:r.no,action:r.id==='domain_identity'&&facts[r.id]?'':r.action}));
 const status:DataState=checks.some(c=>c.status==='unsupported')?'unsupported':checks.some(c=>c.status==='needs_data')?'needs_data':'exploratory';
 return {version:rules.version,status,exploratory_allowed:status!=='unsupported',assessment_basis:'bundle_metadata_only',observed_accuracy:'unvalidated',
  bundle_id:d.bundle_id??null,checks,recorded:{terrain_provider:text(q.terrain_provider)?q.terrain_provider:null,native_resolution_m:facts.terrain_resolution?q.native_resolution_m:null,
   terrain_datum:text(g.vertical_datum)?g.vertical_datum:null,coastal_datum:f.coastal?.datum??null,source_record_count:sources.length,
   configured_coastal_cells:f.coastal?.cells.length??0,coastal_series_end_s:f.coastal?.levels.at(-1)!.timeS??null,simulation_end_s:f.storm.duration+f.storm.recession},
  limitations:['This screen does not inspect terrain arrays, authenticate provenance, verify datum transformations or establish observed flood accuracy.','Needs-data scenarios remain available for explicit exploratory use. Unsupported identity mismatches must be corrected.']};
}
