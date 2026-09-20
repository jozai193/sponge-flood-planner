"""SWMM dynamic-wave network with finite surface-cell storage interfaces.

EXPERIMENTAL: not connected to the production surface solver.
The fixed-step lateral integration correction removes the startup deficit.
Whole-network residual is reported separately and still fails validation;
this is not yet a conservative two-way coupling. Run only in a dedicated process.

Each interface is a cell-sized storage node linked by a supplied head-flow curve.
Surface transport changes its volume through an explicit lateral source; the
resulting storage is returned to the 2-D solver. Reverse link flow is enabled.
"""
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

from swmm.toolkit import solver as swmm
from swmm.toolkit.shared_enum import LinkResult, NodeResult, ObjectType


def compile_model(nodes,pipes,interfaces,duration):
    end=datetime(2024,1,1,tzinfo=UTC)+timedelta(seconds=math.ceil(duration)+10)
    sections={'OPTIONS':['FLOW_UNITS CMS','FLOW_ROUTING DYNWAVE','START_DATE 01/01/2024','START_TIME 00:00:00',
        f'END_DATE {end:%m/%d/%Y}',f'END_TIME {end:%H:%M:%S}','REPORT_STEP 00:00:01',
        'ROUTING_STEP 0.1','VARIABLE_STEP 0','LENGTHENING_STEP 0','MIN_SURFAREA 1.167',
        'ALLOW_PONDING NO','INERTIAL_DAMPING PARTIAL','NORMAL_FLOW_LIMITED BOTH','MAX_TRIALS 20','HEAD_TOLERANCE 0.0001'],
        'JUNCTIONS':[],'OUTFALLS':[],'STORAGE':[],'CONDUITS':[],'XSECTIONS':[],'OUTLETS':[],'CURVES':[],'REPORT':['INPUT NO','CONTINUITY YES','FLOWSTATS YES']}
    ids={n['id']:f'N{i}' for i,n in enumerate(nodes)}
    for node in nodes:
        name=ids[node['id']];invert=node['invert_m'];depth=max(.001,node['ground_m']-invert)
        if node['kind']=='outfall':
            kind='FIXED' if node.get('tailwater_m') is not None else 'FREE'
            sections['OUTFALLS'].append(f'{name} {invert} {kind} '+(f"{node['tailwater_m']} " if kind=='FIXED' else '')+'NO')
        else:
            area=node.get('storage_area_m2')
            if area is None or not math.isfinite(area) or area<=0:raise ValueError('Network nodes require surveyed storage_area_m2 for explicit surcharge storage')
            sections['STORAGE'].append(f"{name} {invert} {depth+100} {node.get('initial_depth_m',0)} FUNCTIONAL 0 0 {area} 0 0")
    for i,pipe in enumerate(pipes):
        sections['CONDUITS'].append(f"P{i} {ids[pipe['from_node']]} {ids[pipe['to_node']]} {pipe['length_m']} {pipe['manning_n']} 0 0 0 0")
        sections['XSECTIONS'].append(f"P{i} CIRCULAR {pipe['diameter_m']} 0 0 0 1")
    for i,interface in enumerate(interfaces):
        sections['STORAGE'].append(f"S{i} {interface['bed_m']} 100 {interface.get('depth_m',0)} FUNCTIONAL 0 0 {interface['area_m2']} 0 0")
        for j,node_id in enumerate(interface['nodes']):
            node=next(n for n in nodes if n['id']==node_id)
            offset=node['ground_m']-interface['bed_m']
            if offset<-.001:raise ValueError('Inlet crest is below the surface cell bed; align terrain/survey elevations before coupling')
            curve=node.get('inlet_curve')
            if not curve:raise ValueError('Every coupled inlet needs a head-flow curve')
            curve_id=f'C{i}_{j}'
            sections['OUTLETS'].append(f'O{i}_{j} S{i} {ids[node_id]} {max(0,offset)} TABULAR/HEAD {curve_id} NO')
            for k,(head,flow) in enumerate(curve):
                cap=node.get('inlet_capacity_m3_s')
                sections['CURVES'].append(f"{curve_id} {'RATING' if k==0 else ''} {head} {min(flow,cap) if cap is not None else flow}")
    return '\n\n'.join('['+name+']\n'+'\n'.join(lines) for name,lines in sections.items() if lines)+'\n'


class SwmmNetwork:
    def __init__(self,folder,nodes,pipes,interfaces,duration):
        self.interfaces=interfaces;self.previous_rates=[0.]*len(interfaces);self.integrated_exchange=0.;self.time=0.;self.imposed_positive=0.;self.imposed_negative=0.
        self.path=Path(folder)/'network.inp';self.path.parent.mkdir(parents=True,exist_ok=True)
        self.path.write_text(compile_model(nodes,pipes,interfaces,duration),encoding='utf-8')
        self.open=False
        try:
            swmm.swmm_open(str(self.path),str(self.path.with_suffix('.rpt')),str(self.path.with_suffix('.out')));self.open=True
            swmm.swmm_start(False)
            self.surface_nodes=[swmm.project_get_index(ObjectType.NODE,f'S{i}') for i in range(len(interfaces))]
            self.all_nodes=range(swmm.project_get_count(ObjectType.NODE));self.all_links=range(swmm.project_get_count(ObjectType.LINK))
            self.initial_volume=self.physical_storage()
        except Exception:
            swmm.swmm_close();raise

    def surface_volumes(self):return [swmm.node_get_result(i,NodeResult.VOLUME) for i in self.surface_nodes]

    def physical_storage(self):
        return sum(swmm.node_get_result(i,NodeResult.VOLUME) for i in self.all_nodes if i not in self.surface_nodes)+sum(swmm.link_get_result(i,LinkResult.VOLUME) for i in self.all_links)

    def step(self,depths,dt):
        if len(depths)!=len(self.interfaces) or dt!=1 or any(not math.isfinite(h) or h<0 for h in depths):raise ValueError('Invalid network interface step')
        before=self.surface_volumes()
        for i,(depth,interface,volume) in enumerate(zip(depths,self.interfaces,before)):
            change=depth*interface['area_m2']-volume
            self.imposed_positive+=max(0,change);self.imposed_negative+=max(0,-change)
            # SWMM integrates node volume trapezoidally. With ten fixed 0.1 s
            # routing steps, the previous lateral rate contributes 0.05 s and
            # the newly held rate contributes 0.95 s over this 1 s window.
            rate=(change-.05*self.previous_rates[i])/.95
            self.integrated_exchange+=.05*self.previous_rates[i]+.95*rate
            self.previous_rates[i]=rate
            swmm.node_set_total_inflow(self.surface_nodes[i],rate)
        elapsed=swmm.swmm_stride(1)*86400
        if abs(elapsed-self.time-dt)>1e-4:raise ValueError('SWMM and surface clocks diverged')
        self.time=elapsed
        volumes=self.surface_volumes()
        totals=swmm.system_get_routing_totals()
        initial_surface=sum(f.get('depth_m',0)*f['area_m2'] for f in self.interfaces)
        supplied=self.initial_volume+initial_surface+totals.exInflow
        residual=supplied-totals.outflow-totals.flooding-totals.evapLoss-totals.seepLoss-self.physical_storage()-sum(volumes)
        relative=abs(residual)/max(supplied,1)
        return {'network_residual_m3': residual,'network_relative_residual': relative,'coupling_eligible': False,'time_s': self.time,'depths': [max(0,v)/f['area_m2'] for v,f in zip(volumes,self.interfaces)],
            'network_stored_m3': self.physical_storage(),'initial_network_m3': self.initial_volume,
            'routing_totals': {k:getattr(totals,k) for k in ('exInflow','outflow','flooding','evapLoss','seepLoss')},
            'interface_integration_error_m3': self.imposed_positive-self.imposed_negative-self.integrated_exchange,
            'experimental': True,'imposed_positive_m3': self.imposed_positive,'imposed_negative_m3': self.imposed_negative,
            'engine': f'SWMM {swmm.swmm_get_version()} dynamic wave'}

    def close(self):
        if self.open:
            try:swmm.swmm_end();swmm.swmm_report()
            finally:swmm.swmm_close();self.open=False
