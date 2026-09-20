import {test,expect} from 'vitest';
import {assessCoastalReadiness} from '../../packages/domain/coastal-readiness';

const base={edge:'west' as const,cells:[0],levels:[{timeS:0,elevationM:0}],source:'NOAA gauge',datum:'NAVD88'};
test('missing coastal support remains explicit and cannot become decision eligible',()=>{
 const result=assessCoastalReadiness(base,3600);
 expect(result.productionEligible).toBe(false);expect(result.missing).toEqual(expect.arrayContaining(['segments','datum_epoch','time_coverage','bathymetry','channels']));
 expect(result.closedBoundaryPolicy).toContain('not filled');
});
test('complete measured metadata can clear the readiness metadata gate',()=>{
 const result=assessCoastalReadiness({...base,segment_ids:['west-1'],source_kind:'measured',source_epoch:'2026-01-01T00:00:00Z',vertical_transform:'NOAA VDatum job abc',coverage_start_s:0,coverage_end_s:7200,bathymetry_status:'verified',channel_support_status:'not_required'},3600);
 expect(result.productionEligible).toBe(true);expect(result.missing).toEqual([]);
});
