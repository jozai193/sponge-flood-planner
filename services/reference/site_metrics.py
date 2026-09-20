"""Equal-site summaries keep repeated marks from silently dominating a score."""
import math
from typing import Any


def site_balanced_errors(samples, gauge_peak=None):
    groups: dict[tuple[str, object], list[dict[str, Any]]] = {}
    for sample in samples:
        if sample['status']!='compared':continue
        error=sample['error_m']
        observed=sample['observed_elevation_m']
        if not math.isfinite(error) or not math.isfinite(observed):raise ValueError('Finite errors and observations required')
        site=sample.get('site_id')
        key=('site',site) if site is not None else ('unassigned_mark',sample['observation_id'])
        groups.setdefault(key,[]).append(sample)
    if gauge_peak is not None and not math.isfinite(gauge_peak):raise ValueError('Finite gauge peak required')
    count=len(groups)
    mean=lambda a:sum(a)/len(a)
    result={'site_groups': count,'mark_count': sum(len(group) for group in groups.values()),
        'unassigned_site_marks': sum(k[0]=='unassigned_mark' for k in groups),
        'rmse_m': math.sqrt(mean([mean([s['error_m']**2 for s in group]) for group in groups.values()])) if count else None,
        'mae_m': mean([mean([abs(s['error_m']) for s in group]) for group in groups.values()]) if count else None,
        'bias_m': mean([mean([s['error_m'] for s in group]) for group in groups.values()]) if count else None,
        'interpretation': 'Each identified site has equal total weight; marks within it share that weight. Squared errors are averaged before taking the root, so opposite errors do not cancel. Spatial independence is not established.'}
    if gauge_peak is not None:
        result['gauge_only_rmse_m']=math.sqrt(mean([mean([(gauge_peak-s['observed_elevation_m'])**2 for s in group]) for group in groups.values()])) if count else None
    return result
