import type {CoastalBoundary} from '../simulation/src/coastal';

export function assessCoastalReadiness(boundary:CoastalBoundary,simulationEndS:number){
 const checks=[
  {id:'segments',ok:!!boundary.segment_ids?.length,detail:boundary.segment_ids?.length?`${boundary.segment_ids.length} boundary segment IDs supplied`:'Boundary segment identity is missing'},
  {id:'datum_epoch',ok:!!boundary.datum.trim()&&!!boundary.source_epoch&&boundary.source_epoch!=='unknown'&&!!boundary.vertical_transform&&boundary.vertical_transform!=='unverified',detail:'Datum transformation and source epoch must both be explicit'},
  {id:'time_coverage',ok:boundary.coverage_start_s===0&&boundary.coverage_end_s!=null&&boundary.coverage_end_s>=simulationEndS,detail:'Source coverage must span the complete run'},
  {id:'bathymetry',ok:boundary.bathymetry_status==='verified'||boundary.bathymetry_status==='not_required',detail:'Bathymetry need must be verified or explicitly not required'},
  {id:'channels',ok:boundary.channel_support_status==='verified'||boundary.channel_support_status==='not_required',detail:'Channel/structure support must be verified or explicitly not required'},
  {id:'provenance',ok:!!boundary.source.trim()&&['measured','modelled','assumed'].includes(boundary.source_kind??'assumed'),detail:`Source is ${(boundary.source_kind??'assumed')}`},
 ];
 const missing=checks.filter(c=>!c.ok).map(c=>c.id);
 return {productionEligible:missing.length===0,executionClass:missing.length?'exploratory':'evidence_ready',checks,missing,
  closedBoundaryPolicy:'Only listed cells receive levels. Unsupported wet boundary segments are not filled from nearest nodes and must be screened before decision use.'};
}
