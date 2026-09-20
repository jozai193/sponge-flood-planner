import type {assessScenarioData} from '../../../packages/domain/data-admission';

export default function ScenarioDataStatus({assessment,error}:{assessment?:ReturnType<typeof assessScenarioData>;error?:string}){
 return <section aria-label="Scenario data suitability" className="note">
  <div className="eyebrow">SCENARIO DATA SUITABILITY</div>
  {error?<p>Complete the flood setup to assess its data: {error}</p>:assessment?<>
   <p><strong>{assessment.exploratory_allowed?'Data gaps — exploratory use only':'Scenario and terrain do not match'}</strong></p>
   <p>{assessment.exploratory_allowed?'Simulation remains available. These data checks do not establish flood accuracy.':'Reload matching terrain before running this scenario.'}</p>
   <details><summary>{assessment.checks.filter(c=>c.status==='needs_data').length} data gaps · view checks and next steps</summary>
    {assessment.checks.map(c=><div key={c.id}><p><strong>{c.id.replaceAll('_',' ')}:</strong> {c.reason}</p>{c.action&&<p>{c.action}</p>}</div>)}
   </details>
  </>:<p>Load a terrain bundle to assess the selected scenario.</p>}
 </section>;
}
