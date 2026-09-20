import {test,expect} from 'vitest';
import {assessDesignCapabilities} from '../../packages/domain/scenario-wire';
test('engine capability gate covers all four public intervention types without fallback',()=>{
 expect(assessDesignCapabilities('webgl2-hll',['rain_garden','bioswale','permeable_pavement','detention_basin'])).toMatchObject({compatible:true,unsupported_designs:[]});
 const missing=assessDesignCapabilities('sfincs',['rain_garden']);expect(missing.compatible).toBe(false);expect(missing.reasons[0]).toContain('no design fallback');
});
