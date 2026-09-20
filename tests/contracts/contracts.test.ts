import {describe,it,expect} from 'vitest';
import Ajv from 'ajv';
import schema from '../../packages/contracts/schema/Grid.json';
describe('shared grid contract',()=>{
  const validate=new Ajv({strict:false}).compile(schema);
  it('accepts metric finite grid and rejects invalid dimensions',()=>{
    expect(validate({nx:32,ny:32,dx_m:2,dy_m:2})).toBe(true);
    expect(validate({nx:3000,ny:32,dx_m:2,dy_m:2})).toBe(false);
    expect(validate({nx:32,ny:32,dx_m:-1,dy_m:2})).toBe(false);
  });
});
