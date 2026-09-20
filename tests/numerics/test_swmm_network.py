import json

import pytest

from services.geodata.imports import DrainNode
from services.reference.swmm_network import SwmmNetwork, compile_model


def fixture():
    nodes=[{'id': 'inlet','kind': 'inlet','storage_area_m2': 1.167,'invert_m': -1,'ground_m': 0,'inlet_curve': [(0,0),(1,.1)]},
           {'id': 'outfall','kind': 'outfall','invert_m': -2,'ground_m': 0}]
    pipes=[{'from_node': 'inlet','to_node': 'outfall','length_m': 20,'manning_n': .013,'diameter_m': .5}]
    interfaces=[{'cell': 0,'bed_m': 0,'area_m2': 25,'nodes': ['inlet']}]
    return nodes,pipes,interfaces

def test_experimental_exchange_corrects_startup_and_keeps_coupling_disabled(tmp_path):
    engine=SwmmNetwork(tmp_path,*fixture(),60)
    try:
        result=engine.step([.1],1)
        json.dumps(result,allow_nan=False)
        assert result['experimental'] is True
        assert result['coupling_eligible'] is False
        assert result['routing_totals']['exInflow']==pytest.approx(2.5)
        assert 0<result['depths'][0]<.1
        assert result['interface_integration_error_m3']==pytest.approx(0,abs=1e-12)
        with pytest.raises(ValueError):engine.step([.1],.5)
    finally:engine.close()

def test_network_requires_inlet_curve_and_aligned_crest():
    nodes,pipes,interfaces=fixture()
    nodes[0]['inlet_curve']=None
    with pytest.raises(ValueError,match='head-flow'):compile_model(nodes,pipes,interfaces,60)
    nodes,pipes,interfaces=fixture();interfaces[0]['bed_m']=1
    with pytest.raises(ValueError,match='align terrain'):compile_model(nodes,pipes,interfaces,60)

def test_survey_curve_rejects_decreasing_head():
    with pytest.raises(ValueError,match='head must increase'):
        DrainNode(id='a',x=0,y=0,invert_m=0,ground_m=1,kind='inlet',inlet_curve=[(0,0),(1,.1),(.5,.2)])


def test_long_exchange_reports_actual_network_imbalance(tmp_path):
    engine=SwmmNetwork(tmp_path,*fixture(),120)
    try:
        depths=[.1]
        for _ in range(60):
            result=engine.step(depths,1)
            depths=result['depths']
        assert result['interface_integration_error_m3']==pytest.approx(0,abs=1e-12)
        # A corrected imposed transfer must not be mistaken for network closure.
        assert result['network_relative_residual']>.001
        assert result['coupling_eligible'] is False
    finally:engine.close()


@pytest.mark.parametrize('tailwater',[None,.5])
def test_direct_exchange_conserves_forward_and_reverse_flow(tmp_path,tailwater):
    nodes,_pipes,interfaces=fixture()
    nodes=nodes[1:]
    nodes[0]['inlet_curve']=[(0,0),(1,.1)]
    nodes[0]['tailwater_m']=tailwater
    interfaces[0]['nodes']=['outfall']
    engine=SwmmNetwork(tmp_path,nodes,[],interfaces,120)
    try:
        initial=.1 if tailwater is None else 0
        depths=[initial]
        for _ in range(60):
            result=engine.step(depths,1)
            depths=result['depths']
        assert result['network_relative_residual']<.001
        if tailwater is None:assert 0<depths[0]<initial
        else:assert depths[0]>initial
        assert result['coupling_eligible'] is False
    finally:engine.close()


def test_direct_inlet_capacity_bounds_surface_transfer(tmp_path):
    nodes,_pipes,interfaces=fixture()
    nodes=nodes[1:];nodes[0]['inlet_curve']=[(0,0),(1,1)]
    nodes[0]['inlet_capacity_m3_s']=.001
    interfaces[0]['nodes']=['outfall'];interfaces[0]['depth_m']=.1
    engine=SwmmNetwork(tmp_path,nodes,[],interfaces,120)
    try:
        depths=[.1]
        for _ in range(60):result=engine.step(depths,1);depths=result['depths']
        assert 0<2.5-depths[0]*25<=.001*60+1e-4
        assert result['network_relative_residual']<.001
    finally:engine.close()
