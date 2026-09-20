/** Nonlinear black-box search: no submodularity or approximation guarantee. */
export interface Candidate {id:string;costMinor:number;conflicts:string[]}
export interface SearchOptions {budgetMinor:number;locked:string[];excluded:string[];maxEvaluations:number;signal?:AbortSignal;onProgress?:(result:SearchResult)=>void}
export interface SearchResult {selected:string[];score:number;costMinor:number;evaluations:number;elapsedMs:number;status:'best_found'|'exhaustive'|'cancelled'|'budget_exhausted';terminationReason:string;evaluated:{selected:string[];score:number}[]}
export function feasible(ids:string[],catalog:Candidate[],options:Pick<SearchOptions,'budgetMinor'|'locked'|'excluded'>):boolean{
  const index=new Map(catalog.map(c=>[c.id,c]));if(new Set(ids).size!==ids.length)return false;
  if(options.locked.some(id=>!ids.includes(id))||ids.some(id=>options.excluded.includes(id)||!index.has(id)))return false;
  let cost=0;for(const id of ids){const c=index.get(id)!;if(!Number.isSafeInteger(c.costMinor)||c.costMinor<0)return false;cost+=c.costMinor;if(c.conflicts.some(other=>ids.includes(other)))return false;}
  return cost<=options.budgetMinor;
}
export async function search(catalog:Candidate[],evaluate:(ids:string[])=>Promise<number>,options:SearchOptions,seeds:string[][]=[]):Promise<SearchResult>{
  const started=performance.now();
  if(new Set(catalog.map(c=>c.id)).size!==catalog.length)throw new Error('Duplicate candidate IDs');
  if(!Number.isSafeInteger(options.budgetMinor)||options.budgetMinor<0||options.maxEvaluations<1)throw new Error('Invalid search budget');
  if(!feasible(options.locked,catalog,options))throw new Error('Locked plan is infeasible');
  const cache=new Map<string,number>(),eligible=catalog.filter(c=>!options.excluded.includes(c.id)).sort((a,b)=>a.id.localeCompare(b.id));
  const cost=(ids:string[])=>ids.reduce((s,id)=>s+catalog.find(c=>c.id===id)!.costMinor,0);
  let best:string[]=options.locked.slice().sort(),score=Infinity,stopped=false;
  const results:{selected:string[];score:number}[]=[];
  const snapshot=(status:SearchResult['status']='best_found'):SearchResult=>({selected:[...best],score,costMinor:cost(best),evaluations:cache.size,elapsedMs:performance.now()-started,status,
    terminationReason:status==='exhaustive'?'Every feasible subset in the small catalogue was evaluated.':status==='budget_exhausted'?'The configured evaluation limit was reached; this is the best completed plan found.':status==='cancelled'?'Search was cancelled; this is the best completed plan found.':'Local add, pair and swap search reached no further improvement; global optimality is not claimed.',evaluated:results.slice()});
  async function attempt(ids:string[]){ids=[...new Set(ids)].sort();if(!feasible(ids,catalog,options))return;
    const key=JSON.stringify(ids);if(cache.has(key))return;
    if(options.signal?.aborted||cache.size>=options.maxEvaluations){stopped=true;return;}
    // Only completed finite evaluations enter the cache. A failure is not a good score.
    const value=await evaluate(ids);if(!Number.isFinite(value))throw new Error('Incomplete or non-finite simulation score');
    cache.set(key,value);results.push({selected:ids,score:value});
    if(value<score-1e-12||(Math.abs(value-score)<=1e-12&&cost(ids)<cost(best))){best=ids;score=value;options.onProgress?.(snapshot());}
  }
  await attempt(best);for(const seed of seeds)await attempt([...options.locked,...seed]);
  if(eligible.length<=12){for(let mask=0;mask<2**eligible.length&&!stopped;mask++)await attempt(eligible.filter((_,i)=>mask&(1<<i)).map(c=>c.id));
    return snapshot(options.signal?.aborted?'cancelled':stopped?'budget_exhausted':'exhaustive');}
  let changed=true;
  while(changed&&!stopped){const previous=JSON.stringify(best),base=best.slice(),remaining=eligible.filter(c=>!base.includes(c.id));
    for(const c of remaining){await attempt([...base,c.id]);if(stopped)break;}
    // Pair additions discover complementary facilities with no singleton benefit.
    for(let i=0;i<remaining.length&&!stopped;i++)for(let j=i+1;j<remaining.length&&!stopped;j++)await attempt([...base,remaining[i].id,remaining[j].id]);
    for(const id of base.filter(id=>!options.locked.includes(id))){const removed=base.filter(x=>x!==id);await attempt(removed);for(const c of remaining){await attempt([...removed,c.id]);if(stopped)break;}if(stopped)break;}
    changed=JSON.stringify(best)!==previous;
  }
  return snapshot(options.signal?.aborted?'cancelled':stopped?'budget_exhausted':'best_found');
}
