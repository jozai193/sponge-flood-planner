"""Experimental, named coastal segments. Not wired into production execution."""
import hashlib
import json
from dataclasses import dataclass

import numpy as np

from services.reference.coastal import CoastalBoundary


@dataclass(frozen=True)
class CoastalSegments:
    segments: tuple[tuple[str, CoastalBoundary], ...]

    def validate(self, surface):
        if not self.segments:
            raise ValueError('At least one named boundary required')
        names, faces, datums = set(), set(), set()
        for name, boundary in self.segments:
            if not isinstance(name, str) or not name.strip() or name in names:
                raise ValueError('Unique nonempty boundary names required')
            names.add(name)
            boundary.validate(surface)
            datums.add(boundary.datum)
            for cell in boundary.cells:
                face = (boundary.edge, cell)
                if face in faces:
                    raise ValueError('Overlapping boundary face')
                faces.add(face)
        if len(datums) != 1:
            raise ValueError('Boundary vertical datums must match explicitly')

    def initial_depth(self, surface):
        self.validate(surface)
        levels = [b.level(0) for _, b in self.segments]
        if len(set(levels)) != 1:
            raise ValueError('Different initial boundary levels require an explicit initial state')
        return np.maximum.reduce([b.initial_depth(surface) for _, b in self.segments])

    def fingerprint(self):
        rows = [(name, b.edge, b.cells, b.levels, b.datum, b.source) for name, b in self.segments]
        return hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
