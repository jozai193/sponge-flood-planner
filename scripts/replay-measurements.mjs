/** Draw callbacks measure submitted states; they are not display presentation times. */
export function summarizeReplayDraws(draws, expectedStates, targetIntervalMs = 150, playbackStartTime = -Infinity) {
 if (!Number.isInteger(expectedStates) || expectedStates < 2) throw Error('Expected at least two replay states');
 if (!Number.isFinite(targetIntervalMs) || targetIntervalMs <= 0) throw Error('Invalid replay cadence');
 const percentile = (values, fraction) => {
  const sorted = [...values].sort((a,b) => a-b);
  return sorted.length ? sorted[Math.min(sorted.length-1, Math.ceil(sorted.length*fraction)-1)] : null;
 };
 return Object.fromEntries(['Baseline','Planned'].map(label => {
  const samples = draws.filter(d => d.label === label);
  if (samples.some(d => !Number.isInteger(d.index) || d.index < 0 || d.index >= expectedStates || !Number.isFinite(d.time))) throw Error(`Invalid ${label} draw`);
  const ordered = [...samples].sort((a,b) => a.time-b.time);
  const first = new Map();
  for (const sample of ordered) if (!first.has(sample.index)) first.set(sample.index, sample);
  const unique = [...first.values()];
  // State zero can already be visible while the user has not pressed Play.
  // Retain its coverage, but don't label that idle hold as playback stutter.
  const intervals = unique.slice(1).map((d,i) => d.time-Math.max(unique[i].time,playbackStartTime));
  const missing = Array.from({length:expectedStates},(_,i)=>i).filter(i=>!first.has(i));
  const outOfOrderTransitions = unique.slice(1).filter((d,i)=>d.index<=unique[i].index).length;
  const latencies = unique.filter(d=>!d.fenceFailed && Number.isFinite(d.gpuObservedMs) && d.gpuObservedMs>=d.time).map(d=>d.gpuObservedMs-d.time);
  return [label, {
   expectedStates, renderedStates:first.size, missingStateIndices:missing,
   allStatesRenderedInOrder:missing.length===0 && outOfOrderTransitions===0,
   outOfOrderTransitions, duplicateDraws:samples.length-first.size,
   p50StateIntervalMs:percentile(intervals,.5), p95StateIntervalMs:percentile(intervals,.95),
   maxStateIntervalMs:intervals.length?Math.max(...intervals):null,
   gapsOverTwiceTarget:intervals.filter(ms=>ms>2*targetIntervalMs).length,
   p95GpuCompletionObservedDelayMs:percentile(latencies,.95),
   firstDrawsWithCompletionObserved:latencies.length,
   fenceFailures:samples.filter(d=>d.fenceFailed).length,
  }];
 }));
}
