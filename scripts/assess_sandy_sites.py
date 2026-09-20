"""Supplement the preserved baseline; do not replace its original mark-weighted score."""
import json
from pathlib import Path

from services.reference.site_metrics import site_balanced_errors

root=Path('artifacts/validation/sandy-2012')
audit=json.loads((root/'accuracy.json').read_text())
runs=[{'grid_cells': r['grid_cells'],'original_mark_rmse_m': r['rmse_m'],
    'site_balanced': site_balanced_errors(r['samples'],r['gauge_only_baseline']['peak_navd88_m'])} for r in audit['runs']]
(root/'site-balanced-assessment.json').write_text(json.dumps({'runs': runs,
    'limitation': 'Supplementary weighting diagnostic. Original wet, dry, unresolved and mark-weighted results are preserved; this is not evidence of a model improvement.'},indent=2))
print(json.dumps(runs,indent=2))
