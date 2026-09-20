"""Spatial provider capabilities, separate from city-independent processing."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Provider:
    id: str
    capability: str
    bounds: tuple[float, float, float, float]
    priority: int

    def covers(self, requested):
        west, south, east, north = requested
        w, s, e, n = self.bounds
        return w <= west < east <= e and s <= south < north <= n


PROVIDERS = (
    Provider('philadelphia_buildings', 'buildings', (-75.30, 39.86, -74.94, 40.14), 100),
    Provider('osm_buildings', 'buildings', (-180, -80, 180, 80), 10),
)


def select_provider(capability, bounds):
    """Configured coverage is routing eligibility, not proof of data completeness."""
    matches = [p for p in PROVIDERS if p.capability == capability and p.covers(bounds)]
    if not matches:
        raise ValueError(f'No configured {capability} provider covers the full extent; split wrapped bounds or choose another provider')
    return max(matches, key=lambda p: p.priority)
