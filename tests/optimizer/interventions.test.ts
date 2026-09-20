import {test,expect} from 'vitest';
import {compileDesign,type PhysicalDesign} from '../../packages/domain/interventions';
const base=()=>({nx:4,ny:4,dx:1,dy:1,z:new Float32Array(16).fill(1),solid:new Uint8Array(16),rainWeights:new Float32Array(16).fill(1),roughness:new Float32Array(16).fill(.03),capacity:new Float32Array(16),infiltration:new Float32Array(16)});
const garden:PhysicalDesign={id:'garden',kind:'rain_garden',cells:[5,6],eligibility:'user_assumed',excavationM:.2,storageDepthM:.15,conductivityMS:.00001,percolationMS:0,roughness:.1,costMinor:1000,parameterSource:'Controlled fixture'};
test('physical edits preserve baseline and do not duplicate excavation storage',()=>{
 const input=base(),out=compileDesign(input,[garden],1000);expect(input.z[5]).toBe(1);expect(out.z[5]).toBeCloseTo(.8);expect(out.capacity[5]).toBeCloseTo(.15);
 expect(()=>compileDesign(input,[{...garden,kind:'detention_basin'}],1000)).toThrow('subsurface');
 expect(()=>compileDesign(input,[{...garden,kind:'permeable_pavement'}],1000)).toThrow('grade');
});
test('unsafe or infeasible designs cannot reach solver',()=>{
 expect(()=>compileDesign(base(),[garden],999)).toThrow('budget');
 expect(()=>compileDesign(base(),[garden,{...garden,id:'other'}],5000)).toThrow('Overlapping');
 expect(()=>compileDesign(base(),[{...garden,eligibility:'unverified'}],5000)).toThrow('eligibility');
 expect(()=>compileDesign(base(),[{...garden,eligibility:'unknown' as any}],5000)).toThrow('eligibility');
 const input=base();input.solid[5]=1;input.rainWeights[5]=0;expect(()=>compileDesign(input,[garden],5000)).toThrow('building');
});
test('itemised costs reconcile and protected candidate evidence blocks execution',()=>{
const costBreakdown={sitePreparationMinor:100,materialsMinor:200,installationMinor:300,contingencyMinor:400,annualMaintenanceMinor:50,currency:'USD' as const,priceYear:2026,basis:'Controlled dated estimate'};
 expect(()=>compileDesign(base(),[{...garden,costMinor:1000,costBreakdown}],1000)).not.toThrow();
 expect(()=>compileDesign(base(),[{...garden,costMinor:999,costBreakdown}],1000)).toThrow('do not equal');
 expect(()=>compileDesign(base(),[{...garden,costMinor:1000,costBreakdown:{...costBreakdown,currency:'INR'}}],1000)).not.toThrow();
 expect(()=>compileDesign(base(),[{...garden,costMinor:1000,costBreakdown:{...costBreakdown,currency:'rupees'}}],1000)).toThrow('currency');
 expect(()=>compileDesign(base(),[{...garden,candidateEvidence:{parcelIds:[],sourceNote:'fixture',geometryId:'garden',protectedReasons:['wetland']}}],1000)).toThrow('protected');
});
