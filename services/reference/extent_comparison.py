"""Area diagnostics against mapped inundation; never infer unmapped land is dry."""
import numpy as np
from shapely.geometry import box


def mapped_flood_coverage(grid, peak_depth, solid, mapped_polygon, initial_depth=None,
                          threshold_m=.01):
    shape=(grid['ny'],grid['nx'])
    peak=np.asarray(peak_depth);mask=np.asarray(solid)
    initial=np.zeros(shape) if initial_depth is None else np.asarray(initial_depth)
    if grid.get('row_direction')!='north':raise ValueError('Unsupported row direction')
    if any(a.shape!=shape for a in (peak,mask,initial)) or not np.isfinite(peak).all() or not np.isfinite(initial).all():
        raise ValueError('Invalid model arrays')
    if np.any(peak<0) or np.any(initial<0) or not np.isin(mask,[0,1]).all():raise ValueError('Invalid depths or mask')
    if not np.isfinite(threshold_m) or threshold_m<=0:raise ValueError('Invalid wet threshold')
    if mapped_polygon.is_empty or not mapped_polygon.is_valid:raise ValueError('Valid mapped polygon required')
    dx,dy=grid['dx_m'],grid['dy_m']
    if dx<=0 or dy<=0:raise ValueError('Positive cell dimensions required')
    area=np.zeros(shape)
    for row in range(shape[0]):
        y=grid['origin_y_m']+row*dy
        for col in range(shape[1]):
            x=grid['origin_x_m']+col*dx
            area[row,col]=mapped_polygon.intersection(box(x,y,x+dx,y+dy)).area
    available=mask==0;wet=peak>threshold_m;initially_wet=initial>threshold_m
    total=float(area.sum());scorable=float(area[available].sum())
    conditional=available&~initially_wet
    conditional_area=float(area[conditional].sum())
    return {'mapped_area_m2': total,'building_unresolved_area_m2': float(area[~available].sum()),
        'nonbuilding_mapped_area_m2': scorable,
        'predicted_wet_mapped_area_m2': float(area[available&wet].sum()),
        'predicted_dry_mapped_area_m2': float(area[available&~wet].sum()),
        'model_initially_wet_mapped_area_m2': float(area[available&initially_wet].sum()),
        'initially_dry_nonbuilding_mapped_area_m2': conditional_area,
        'newly_wet_mapped_area_m2': float(area[conditional&wet].sum()),
        'mapped_wet_fraction': float(area[available&wet].sum()/scorable) if scorable else None,
        'conditional_initially_dry_wet_fraction': float(area[conditional&wet].sum()/conditional_area) if conditional_area else None,
        'wet_threshold_m': threshold_m,
        'interpretation': 'Coverage within reference polygons only. No false-positive, precision or IoU score: independent land and surveyed dry-area coverage are unavailable. Initially-dry fractions depend on model initialization. Polygon-derived extent may reuse the point observations and DEM.',
        'cell_reference_area_m2': area.tolist()}
