import numpy as np
import pytest

from services.api.contracts import SolverConfig, Storm
from services.reference.solver import Solver, Surface, curve_number_excess


@pytest.mark.parametrize('axis', [0, 1])
def test_reconstructed_closed_faces_have_zero_mass_flux(axis):
    y, x = np.mgrid[:8, :8]
    sim = Solver(Surface(np.zeros((8, 8)), 1, 1, roughness=0), SolverConfig(spatial_order=2), depth=.2)
    sim.u[..., 1] = .01 * (1 + np.minimum(x, 7 - x))
    sim.u[..., 2] = .01 * (1 + np.minimum(y, 7 - y))
    flux, *_ = sim._faces(sim.u, axis)
    np.testing.assert_allclose(np.take(flux[..., 0], [0, -1], axis=axis), 0, atol=1e-15)


@pytest.mark.parametrize('corner', [(0, 0), (0, 3), (3, 0), (3, 3)])
def test_closed_excavated_corner_retains_all_rain(corner):
    z = np.zeros((4, 4)); z[corner] = -.1
    sim = Solver(Surface(z, 1, 1, roughness=.03), SolverConfig(spatial_order=2))
    sim.advance(1, .2); sim.advance(2)
    assert sim.storage() == pytest.approx(3.2, abs=1e-10)


@pytest.mark.parametrize("order", [1, 2])
def test_lake_at_rest(order):
    y, x = np.mgrid[:20, :30]
    z = .25 * np.exp(-((x-15)**2+(y-10)**2)/40)
    sim = Solver(Surface(z, 1, 1, roughness=0), SolverConfig(spatial_order=order), depth=1-z)
    sim.advance(3)
    assert np.max(np.abs(sim.u[..., 0]+z-1)) < 1e-10
    assert np.max(np.abs(sim.u[..., 1:])) < 1e-10
    assert abs(sim.ledger()["residual_m3"]) < 1e-9


def test_dry_and_uniform_rain():
    sim = Solver(Surface(np.zeros((8, 8)), 2, 2))
    sim.advance(5)
    assert np.max(np.abs(sim.u)) == 0
    sim.advance(105, 1e-4)
    np.testing.assert_allclose(sim.u[..., 0], .01, atol=1e-12)
    assert abs(sim.ledger()["residual_m3"]) < 1e-10


def test_finite_infiltration_and_percolation():
    s = Surface(np.zeros((8, 8)), 1, 1, infiltration_f0=.001, infiltration_fc=.001,
                soil_capacity=.005, percolation=0)
    sim = Solver(s, depth=.01)
    sim.advance(20)
    np.testing.assert_allclose(sim.soil, .005, atol=1e-12)
    np.testing.assert_allclose(sim.u[..., 0], .005, atol=1e-12)
    assert abs(sim.ledger()["residual_m3"]) < 1e-12


@pytest.mark.parametrize("order", [1, 2])
def test_dam_break_positive_conservative(order):
    h = np.zeros((8, 80)); h[:, :40] = 1
    sim = Solver(Surface(np.zeros_like(h), .25, .25, roughness=0), SolverConfig(spatial_order=order), h)
    sim.advance(1)
    assert sim.u[..., 0].min() >= 0
    assert abs(sim.ledger()["residual_m3"]) < 1e-8
    # Ritter dry-bed solution: interior fan h=(2-sqrt(1/g)*x/t)^2/9.
    x = (np.arange(80)+.5)*.25-10
    c = np.sqrt(9.80665)
    exact = np.where(x < -c, 1., np.where(x < 2*c, (2-x/c)**2/9, 0))
    assert np.mean(np.abs(sim.u[4, :, 0]-exact)) < .035


def test_wall_and_roof_water():
    solid = np.zeros((12, 12), bool); solid[4:8, 4:8] = True
    weights = (~solid).astype(float); weights[3, 4:8] += 4
    sim = Solver(Surface(np.zeros((12, 12)), 1, 1, solid=solid, rain_weights=weights))
    sim.advance(20, .0001)
    assert np.all(sim.u[solid] == 0)
    assert abs(sim.storage() - 144*.002) < 1e-9


def test_checkpoint_and_rain_knots():
    storm = Storm(name="pulse", duration_s=20, recession_s=10, depth_m=.002,
                  intervals=[{"start_s": 0,"end_s":10,"rate_m_s":.0002}])
    a = Solver(Surface(np.zeros((8, 8)), 1, 1), SolverConfig(output_interval_s=7))
    frames = list(a.run(storm))
    assert frames[-1]["time_s"] == 30
    assert abs(a.rain_volume-.002*64) < 1e-10
    checkpoint = a.checkpoint()
    a.advance(40)
    b = Solver(a.surface, a.config); b.restore(checkpoint); b.advance(40)
    np.testing.assert_array_equal(a.u, b.u)


def test_cn_boundaries():
    assert curve_number_excess(.1, 100) == pytest.approx(.1)
    assert curve_number_excess(.001, 50) == 0
    assert 0 < curve_number_excess(.1, 75) < .1


def test_outlet_exact_reservoir_and_capacity_limit():
    sim = Solver(Surface(np.zeros((4,4)),2,3,roughness=0,outlet_crest=.1,outlet_rate=.2,outlet_capacity_m3_s=100),depth=.5)
    sim.advance(2)
    np.testing.assert_allclose(sim.u[...,0], .1+.4*np.exp(-.4),atol=1e-12)
    assert sim.ledger()['outflow_m3']>0
    assert sim.ledger()['relative_residual']<1e-12
    limited = Solver(Surface(np.zeros((4,4)),2,3,roughness=0,outlet_rate=10,outlet_capacity_m3_s=.006),depth=.5)
    limited.advance(2)
    np.testing.assert_allclose(limited.u[...,0],.498,atol=1e-12)
    assert limited.ledger()['outflow_m3']==pytest.approx(.006*16*2)


def test_outlet_cannot_drain_below_crest_or_create_water():
    sim=Solver(Surface(np.zeros((4,4)),1,1,outlet_crest=.2,outlet_rate=100,outlet_capacity_m3_s=100),depth=.1)
    sim.advance(1)
    np.testing.assert_allclose(sim.u[...,0],.1)
    assert sim.ledger()['outflow_m3']==0


def test_external_inflow_and_tailwater():
    sim=Solver(Surface(np.zeros((4,4)),1,1,roughness=0,inflow_m3_s=.01,inflow_start_s=.5,inflow_end_s=1.5,outlet_rate=100,outlet_capacity_m3_s=100,outlet_tailwater=1))
    sim.advance(2)
    np.testing.assert_allclose(sim.u[...,0],.01,atol=1e-12)
    assert sim.ledger()['inflow_m3']==pytest.approx(.16)
    assert sim.ledger()['outflow_m3']==0
    assert sim.ledger()['relative_residual']<1e-12
