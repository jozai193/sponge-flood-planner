"""Experimental static refinement of initially dry compartments.

This changes spatial resolution, not the local-inertial momentum equations.
No dynamic remeshing, bed-sill support, or historical/production admission.
"""
import numpy as np

from services.reference.compartment_flow_candidate import Graph, build_graph


def build_refined_graph(bed, solid, factor, initial_depth, dx=1., dy=1., dry_tolerance=1e-6):
    coarse = build_graph(bed, solid, factor, dx, dy)
    fine = build_graph(bed, solid, 1, dx, dy)
    depth = np.asarray(initial_depth, dtype=float)
    if (depth.shape != coarse.labels.shape or not np.isfinite(depth).all()
            or np.any(depth < 0) or not np.isfinite(dry_tolerance) or dry_tolerance < 0):
        raise ValueError('Invalid initial depths or dry tolerance')
    # Refine dry blocks plus a one-block von Neumann buffer on the wet side.
    ny, nx = depth.shape
    blocks = ((depth <= dry_tolerance) & (fine.labels >= 0)).reshape(
        ny//factor, factor, nx//factor, factor).any(axis=(1, 3))
    buffered = blocks.copy()
    buffered[1:] |= blocks[:-1]; buffered[:-1] |= blocks[1:]
    buffered[:, 1:] |= blocks[:, :-1]; buffered[:, :-1] |= blocks[:, 1:]
    refined = buffered.repeat(factor, 0).repeat(factor, 1)
    labels = np.full(depth.shape, -1, dtype=int)
    ids = {}
    for r, c in np.argwhere(fine.labels >= 0):
        key = ('fine', int(fine.labels[r, c])) if refined[r, c] else ('coarse', int(coarse.labels[r, c]))
        labels[r, c] = ids.setdefault(key, len(ids))
    count = len(ids)
    mapped = labels[fine.labels >= 0]
    area = np.bincount(mapped, weights=fine.area, minlength=count)
    center = np.column_stack([np.bincount(mapped, weights=fine.center[:, k]*fine.area,
                                        minlength=count)/area for k in (0, 1)])
    beds = np.bincount(mapped, weights=fine.bed*fine.area, minlength=count)/area
    contacts = {}
    for a, b, width, length, sill in fine.links:
        aa, bb = int(mapped[a]), int(mapped[b])
        if aa == bb:
            continue
        axis = int(np.argmax(np.abs(fine.center[b]-fine.center[a])))
        # Different fine contacts can meet the same mixed-resolution face.
        key = (aa, bb, axis)
        contacts[key] = contacts.get(key, 0.) + width
    links = []
    for (a, b, axis), width in contacts.items():
        distance = abs(center[b, axis]-center[a, axis])
        if distance <= 0:
            raise ValueError('Degenerate mixed-resolution face')
        links.append((a, b, width, distance, max(beds[a], beds[b])))
    faces = {}
    for edge, axis, position in (('west', 0, 0.), ('east', 0, nx*dx),
                                  ('south', 1, 0.), ('north', 1, ny*dy)):
        widths = {}
        for a, _, width, _, _ in fine.boundary_faces[edge]:
            aa = int(mapped[a]); widths[aa] = widths.get(aa, 0.) + width
        faces[edge] = [(a, -1, width, abs(center[a, axis]-position), beds[a])
                       for a, width in widths.items()]
    graph = Graph(labels, area, beds, center, links, faces)
    # Volume-preserving initialization; no interpolation from observed levels.
    volume = np.bincount(mapped, weights=depth[fine.labels >= 0]*fine.area, minlength=count)
    return graph, beds + volume/area
