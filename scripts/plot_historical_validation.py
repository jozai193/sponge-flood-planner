"""Plot sourced forcing and completed point errors; omit uncomputed predictions."""
import sys
from pathlib import Path

sys.path.insert(0,str(Path('.runtime/validation-plot-libs').resolve()))
import json

import matplotlib
import numpy as np

matplotlib.use('Agg')
import matplotlib.pyplot as plt

root=Path(sys.argv[1]);audit=json.loads((root/'accuracy.json').read_text())
protocol=json.loads((root/'protocol.json').read_text())
run=protocol['bundles'][-1];result=audit['runs'][-1]
manifest=json.loads((Path('data/local/bundles')/run['bundle_id']/'manifest.json').read_text())
offset=manifest['grid']['elevation_origin_m']
fig,axes=plt.subplots(1,2,figsize=(11,4.8),constrained_layout=True)
t=[k['timeS']/3600 for k in run['levels']];h=[k['elevationM']+offset for k in run['levels']]
axes[0].plot(t,h,color='#16778a');axes[0].set(xlabel='Hours since '+protocol['start_utc'][:16].replace('T',' ')+' UTC',
    ylabel='Water elevation (m NAVD88)',title='Measured NOAA boundary forcing')
axes[0].grid(alpha=.25)
samples=result['samples'];wet=[s for s in samples if s['status']=='compared']
if wet:
    obs=np.array([s['observed_elevation_m'] for s in wet]);pred=np.array([s['predicted_elevation_m'] for s in wet])
    lo=min(obs.min(),pred.min())-.1;hi=max(obs.max(),pred.max())+.1
    axes[1].plot([lo,hi],[lo,hi],color='#697b7b',ls='--',label='Equal elevations')
    axes[1].scatter(obs,pred,color='#177b85',label='Comparable wet points')
    for s in wet:axes[1].annotate(str(s['observation_id']),(s['observed_elevation_m'],s['predicted_elevation_m']),xytext=(6,5),textcoords='offset points',fontsize=9)
    axes[1].set(xlim=(lo,hi),ylim=(lo,hi));axes[1].legend(fontsize=8)
else:
    axes[1].text(.5,.5,'No comparable wet predictions\nSee dry and unresolved locations in the assessment',ha='center',va='center',transform=axes[1].transAxes)
axes[1].set(xlabel='USGS observed peak (m NAVD88)',ylabel='Model peak water elevation (m NAVD88)',
    title=f'{len(wet)}/{len(samples)} comparable marks; {result["missed_flood_count"]} dry misses')
axes[1].grid(alpha=.25)
fig.suptitle(protocol['city']+' · '+protocol['event_id']+'\nHistorical screening; point agreement does not validate flood extent',fontsize=12)
fig.savefig(root/'forcing-and-errors.png',dpi=150)
print((root/'forcing-and-errors.png').resolve())
