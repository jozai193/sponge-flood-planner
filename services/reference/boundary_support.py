"""Metadata/geometry diagnostics; this module does not admit physical boundaries."""
from typing import Any

import numpy as np


def boundary_support(terrain, points, offsets, samples):
    z = np.asarray(terrain, dtype=float)
    if z.ndim != 2 or min(z.shape) < 2 or not np.isfinite(z).all():
        raise ValueError('Finite rectangular terrain required')
    if samples < 1:
        raise ValueError('Positive sample count required')
    edges = {'west': z[:,0], 'east': z[:,-1], 'south': z[0,:], 'north': z[-1,:]}
    index: dict[tuple[str, int], bool] = {}
    for point in points:
        edge, i = point['edge'], point['face_index']
        if edge not in edges or not isinstance(i,int) or not 0 <= i < len(edges[edge]) or (edge,i) in index:
            raise ValueError('Invalid or duplicate perimeter point')
        levels = point['levels_m_model_msl']
        if len(levels) != samples:
            raise ValueError('Forcing sample count mismatch')
        index[edge,i] = all(v is not None and np.isfinite(v) for v in levels)
    if len(index) != sum(len(v) for v in edges.values()):
        raise ValueError('Incomplete perimeter inventory')
    rows = []
    for offset in offsets:
        if not np.isfinite(offset): raise ValueError('Finite datum offset required')
        detail: list[dict[str, Any]] = []
        for edge, bed in edges.items():
            low = bed < offset
            unsupported = [i for i in range(len(bed)) if low[i] and not index[edge,i]]
            detail.append({'edge': edge,'below_reference_faces': int(low.sum()),
                               'unsupported_faces': unsupported,'count': len(unsupported)})
        rows.append({'reference_navd88_m': float(offset),'edges': detail,
                         'below_reference_faces': sum(d['below_reference_faces'] for d in detail),
                         'unsupported_faces': sum(d['count'] for d in detail)})
    return rows
