"""Conservative metadata screening; source labels cannot establish physical validation."""
import json
import math
import re
from pathlib import Path

from services.api.scenario_contract import ScenarioSpecV2

RULES=json.loads((Path(__file__).resolve().parents[2]/'packages/contracts/data-admission-rules.json').read_text(encoding='utf8'))


def assess_scenario_data(spec:ScenarioSpecV2,manifest):
    def record(v):return v if isinstance(v,dict) else {}
    def text(v):return isinstance(v,str) and bool(v.strip())
    def finite(v):return type(v) in (int,float) and math.isfinite(v)
    m=record(manifest);g=record(m.get('grid'));q=record(m.get('quality'));d=spec.domain;f=spec.forcing
    sources=[s for s in m.get('sources',[]) if record(s)] if isinstance(m.get('sources'),list) else []
    same_grid=all(finite(g.get(k)) and g[k]==getattr(d,k) for k in ('nx','ny','dx_m','dy_m'))
    datum_known=text(g.get('vertical_datum')) and not re.search('unknown|unspecified|unresolved|mixed',g['vertical_datum'],re.IGNORECASE)
    facts={
        'domain_identity':same_grid and text(m.get('bundle_id')) and m['bundle_id']==d.bundle_id and g.get('crs')==d.horizontal_crs and (g.get('vertical_datum') if g.get('vertical_datum') is not None else 'unspecified')==d.vertical_datum and g.get('elevation_origin_m')==d.elevation_origin_m,
        'terrain_source':text(q.get('terrain_provider')) and bool(sources),
        'terrain_resolution':finite(q.get('native_resolution_m')) and q['native_resolution_m']>0,
        'coastal_datum':datum_known and finite(g.get('elevation_origin_m')),
        'coastal_tail':bool(f.coastal and f.coastal.levels[-1].timeS<f.storm.duration+f.storm.recession)
    }
    enabled={'all',*(k for k,v in f.components.model_dump().items() if v)}
    if f.outlets:enabled.add('drainage')
    checks=[{'id':r['id'],'hazard':r['hazard'],'status':r['pass'] if facts.get(r['id']) else r['fail'],'reason':r['yes'] if facts.get(r['id']) else r['no'],'action':'' if r['id']=='domain_identity' and facts.get(r['id']) else r['action']} for r in RULES['checks'] if r['hazard'] in enabled]
    status='unsupported' if any(c['status']=='unsupported' for c in checks) else 'needs_data' if any(c['status']=='needs_data' for c in checks) else 'exploratory'
    return {'version':RULES['version'],'status':status,'exploratory_allowed':status!='unsupported','assessment_basis':'bundle_metadata_only','observed_accuracy':'unvalidated',
            'bundle_id':d.bundle_id,'checks':checks,'recorded':{'terrain_provider':q.get('terrain_provider') if text(q.get('terrain_provider')) else None,'native_resolution_m':q['native_resolution_m'] if facts['terrain_resolution'] else None,
            'terrain_datum':g.get('vertical_datum') if text(g.get('vertical_datum')) else None,'coastal_datum':f.coastal.datum if f.coastal else None,'source_record_count':len(sources),
            'configured_coastal_cells':len(f.coastal.cells) if f.coastal else 0,'coastal_series_end_s':f.coastal.levels[-1].timeS if f.coastal else None,'simulation_end_s':f.storm.duration+f.storm.recession},
            'limitations':['This screen does not inspect terrain arrays, authenticate provenance, verify datum transformations or establish observed flood accuracy.','Needs-data scenarios remain available for explicit exploratory use. Unsupported identity mismatches must be corrected.']}
