import type {GPUInput} from '../../../packages/simulation/src/gpu';
import {coastalInitialDepth} from '../../../packages/simulation/src/coastal';
import {forcingComponents,type FloodConfiguration} from '../../../packages/domain/scenario';
import type {CityContext} from './city-scene';
import {waterPlanningMask} from './water-planning';

export function scenarioInput(base:GPUInput,flood:FloodConfiguration,context:CityContext|null,antecedentSaturation=base.saturation??0):GPUInput{
 const components=forcingComponents(flood),coastal=components.coastal?flood.coastal:undefined;
 return {...base,planningWaterMask:context?.water!==undefined?waterPlanningMask(base,context):base.planningWaterMask,
  coastal,depth:coastal?coastalInitialDepth(base,coastal):base.depth,
  inflows:components.external?flood.inflows:[],outlets:flood.outlets,saturation:antecedentSaturation};
}
