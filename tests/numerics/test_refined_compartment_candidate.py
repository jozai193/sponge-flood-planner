import numpy as np
import pytest

from services.reference.compartment_flow_candidate import CompartmentFlow, build_graph
from services.reference.refined_compartment_candidate import build_refined_graph


def scene():
    z = np.zeros((8, 32)); w = np.ones(z.shape, bool); w[2:4] = False
    h = np.where(w, 0., .2); h[:, 16:] = 0.
    return z, w, h


def test_initial_mass_preserved_with_mixed_cell_sizes():
    z, w, h = scene(); g, stage = build_refined_graph(z, w, 4, h, 2., 3.)
    assert len(g.area) < np.sum(~w)
    assert set(g.area) == {6., 48.}
    assert np.sum((stage-g.bed)*g.area) == pytest.approx(h.sum()*6)


def test_wet_lake_uses_coarse_graph_without_changing_solution():
    z, w, h = scene(); h[~w] = .2
    g, stage = build_refined_graph(z, w, 4, h)
    original = build_graph(z, w, 4)
    assert len(g.area) == len(original.area)
    s = CompartmentFlow(g, stage); s.advance(2)
    np.testing.assert_allclose(s.fine_depth(), h, atol=1e-15)


def test_mixed_interface_mass_and_rotation():
    z, w, h = scene(); g, stage = build_refined_graph(z, w, 4, h)
    rg, rs = build_refined_graph(z.T, w.T, 4, h.T)
    a = CompartmentFlow(g, stage, {'west': lambda t: .25})
    b = CompartmentFlow(rg, rs, {'south': lambda t: .25})
    a.advance(5); b.advance(5)
    assert a.ledger()['relative_residual'] < 1e-12
    assert np.all(a.volume >= 0)
    np.testing.assert_allclose(a.fine_depth().T, b.fine_depth(), atol=1e-13)


def test_no_flux_through_sealed_barrier():
    z, w, h = scene(); w[:, 15] = True; h[w] = 0.
    g, stage = build_refined_graph(z, w, 4, h)
    s = CompartmentFlow(g, stage, {'west': lambda t: .3}); s.advance(10)
    assert np.max(s.fine_depth()[:, 16:]) == 0.


def test_all_dry_resolves_every_open_pixel():
    z, w, h = scene(); h[:] = 0
    g, _ = build_refined_graph(z, w, 4, h)
    assert len(g.area) == np.sum(~w)
    assert np.all(g.area == 1.)


@pytest.mark.parametrize('invalid', [np.nan, -1.])
def test_invalid_depth_rejected(invalid):
    z, w, h = scene(); h[2, 0] = invalid
    with pytest.raises(ValueError): build_refined_graph(z, w, 4, h)
