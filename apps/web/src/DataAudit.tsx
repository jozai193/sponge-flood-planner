import {useEffect,useState} from 'react';

type SourceDates={title:string;source_url:string|null;observation_dates:{kind:string;date:string}[];product_period:string|null;published_date:string|null;release:string|null;retrieved_date:string|null};
type Audit={bundle_id:string;scope:string;checks:{key:string;title:string;status:string;detail:string}[];source_dates?:SourceDates[]};
export default function DataAudit({bundleId,load}:{bundleId:string;load:(path:string)=>Promise<Audit>}){
  const [audit,setAudit]=useState<Audit|null>(null);
  const [error,setError]=useState('');
  useEffect(()=>{
    let active=true;
    setAudit(null);setError('');
    void (async()=>{
      for(let attempt=0;attempt<3;attempt++){
        try{
          const result=await load('/bundles/'+bundleId+'/audit');
          if(active)setAudit(result);
          return;
        }catch{
          if(attempt<2)await new Promise(resolve=>setTimeout(resolve,250*(attempt+1)));
        }
      }
      if(active)setError('Audit unavailable. Data quality has not been verified.');
    })();
    return()=>{active=false;};
  },[bundleId,load]);
  return <section aria-label="Neighbourhood data audit"><h3>Neighbourhood data audit</h3>
    {error?<p role="alert">{error}</p>:!audit?<p>Checking source evidence…</p>:<>
      <p>{audit.scope}</p>
      {audit.checks.map(check=><div key={check.key}><h4>{check.title} · {check.status}</h4><p>{check.detail}</p></div>)}
      {!!audit.source_dates?.length&&<details><summary>Inspect source dates</summary>
        <p>A recent download does not make an older survey current. Dates below are source metadata, not independent verification.</p>
        <div style={{overflowX:'auto'}}><table><thead><tr><th>Source</th><th>Observed or acquired</th><th>Product period</th><th>Published / released</th><th>Downloaded</th></tr></thead><tbody>
          {audit.source_dates.map((s,i)=><tr key={i}><td>{s.source_url?<a href={s.source_url} target="_blank" rel="noreferrer">{s.title}</a>:s.title}</td>
            <td>{s.observation_dates.length?s.observation_dates.map(d=>d.kind+' '+d.date).join('; '):'Not reported'}</td><td>{s.product_period??'Not reported'}</td>
            <td>{[s.published_date,s.release].filter(Boolean).join(' / ')||'Not reported'}</td><td>{s.retrieved_date??'Not reported'}</td></tr>)}
        </tbody></table></div>
      </details>}
    </>}
  </section>;
}
