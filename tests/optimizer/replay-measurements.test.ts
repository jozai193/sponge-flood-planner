import {expect,test} from 'vitest';
// @ts-expect-error Benchmark helper is executed directly by Node.
import {summarizeReplayDraws} from '../../scripts/replay-measurements.mjs';

test('uses first draw timing and reports missing states and stalled transitions',()=>{
 const result=summarizeReplayDraws([
  {label:'Baseline',index:0,time:0},
  {label:'Baseline',index:0,time:140},
  {label:'Baseline',index:1,time:150},
  {label:'Baseline',index:3,time:500},
 ],4);
 expect(result.Baseline).toMatchObject({renderedStates:3,duplicateDraws:1,missingStateIndices:[2],allStatesRenderedInOrder:false,p50StateIntervalMs:150,maxStateIntervalMs:350,gapsOverTwiceTarget:1});
 expect(result.Planned).toMatchObject({renderedStates:0,p95StateIntervalMs:null,missingStateIndices:[0,1,2,3]});
});

test('counts failed duplicate fences and excludes failures from completion timings',()=>{
 const result=summarizeReplayDraws([
  {label:'Planned',index:0,time:0,gpuObservedMs:10},
  {label:'Planned',index:0,time:5,gpuObservedMs:1000,fenceFailed:true},
  {label:'Planned',index:1,time:150,gpuObservedMs:170,fenceFailed:true},
 ],2);
 expect(result.Planned).toMatchObject({allStatesRenderedInOrder:true,fenceFailures:2,firstDrawsWithCompletionObserved:1,p95GpuCompletionObservedDelayMs:10});
});

test('rejects invalid indices and detects states first rendered out of order',()=>{
 expect(()=>summarizeReplayDraws([{label:'Baseline',index:2,time:0}],2)).toThrow('Invalid');
 expect(summarizeReplayDraws([{label:'Baseline',index:1,time:0},{label:'Baseline',index:0,time:150}],2).Baseline).toMatchObject({allStatesRenderedInOrder:false,outOfOrderTransitions:1});
});

test('does not count the initial user hold as playback stutter',()=>{
 const r=summarizeReplayDraws([{label:'Baseline',index:0,time:100},{label:'Baseline',index:1,time:1150},{label:'Baseline',index:2,time:1300}],3,150,1000);
 expect(r.Baseline).toMatchObject({renderedStates:3,allStatesRenderedInOrder:true,maxStateIntervalMs:150,gapsOverTwiceTarget:0});
});
