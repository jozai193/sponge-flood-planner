import {test,expect,vi} from 'vitest';
import {loadBundleResources} from '../../apps/web/src/bundle-loader';

const bundle={grid:{nx:2,ny:2,dx_m:3,dy_m:4}};
const arrayResponse=(url:string)=>new Response(url.endsWith('/solid')?new Uint8Array(4):new Float32Array([1,2,3,4]));

test('raster requests start before metadata resolves and retain solver inputs',async()=>{
  let resolveMetadata!:(value:typeof bundle)=>void;
  const metadata=new Promise<typeof bundle>(resolve=>{resolveMetadata=resolve;});
  const fetchArray=vi.fn(async(url:RequestInfo|URL)=>arrayResponse(String(url))) as unknown as typeof fetch;
  const loading=loadBundleResources('example','token',()=>metadata,new AbortController().signal,fetchArray);
  expect(fetchArray).toHaveBeenCalledTimes(3);
  resolveMetadata(bundle);
  const result=await loading;
  expect(fetchArray).toHaveBeenCalledTimes(6);
  expect(result.bundle).toBe(bundle);
  expect(result.input).toMatchObject({nx:2,ny:2,dx:3,dy:4,boundary:'closed',saturation:.25,spatialOrder:2});
  expect([...result.input.z]).toEqual([1,2,3,4]);
  expect(result.input.solid).toBeInstanceOf(Uint8Array);
  expect(result.fetchMs).toBeGreaterThanOrEqual(0);
});

test('superseded loads abort metadata and all raster requests',async()=>{
  const controller=new AbortController(),signals:AbortSignal[]=[];
  const pending=(signal:AbortSignal)=>new Promise<never>((_,reject)=>{
    signals.push(signal);signal.addEventListener('abort',()=>reject(signal.reason),{once:true});
  });
  const fetchArray=((_:RequestInfo|URL,options?:RequestInit)=>pending(options!.signal!)) as typeof fetch;
  const loading=loadBundleResources('old','token',pending,controller.signal,fetchArray);
  expect(signals).toHaveLength(4);
  controller.abort();
  await expect(loading).rejects.toMatchObject({name:'AbortError'});
  expect(signals.every(signal=>signal.aborted)).toBe(true);
});

test('an unavailable raster cancels remaining downloads and identifies the failed array',async()=>{
  const signals:AbortSignal[]=[];
  const fetchArray=((url:RequestInfo|URL,options?:RequestInit)=>{
    const signal=options!.signal!;signals.push(signal);
    if(String(url).endsWith('/z'))return Promise.resolve(new Response('',{status:503}));
    return new Promise<Response>((_,reject)=>signal.addEventListener('abort',()=>reject(signal.reason),{once:true}));
  }) as typeof fetch;
  await expect(loadBundleResources('bad','token',async()=>bundle,new AbortController().signal,fetchArray))
    .rejects.toThrow('Terrain array z unavailable (503)');
  expect(signals.every(signal=>signal.aborted)).toBe(true);
});

test('transient gateway failures are retried before failing a bundle load',async()=>{
  let attempts=0;
  const fetchArray=(async(url:RequestInfo|URL)=>{
    if(String(url).endsWith('/z')&&attempts++<4)return new Response('',{status:502});
    return arrayResponse(String(url));
  }) as typeof fetch;
  const result=await loadBundleResources('retry','token',async()=>bundle,new AbortController().signal,fetchArray);
  expect(attempts).toBe(5);
  expect([...result.input.z]).toEqual([1,2,3,4]);
});

test('transient network failures are retried before failing a bundle load',async()=>{
  let attempts=0;
  const fetchArray=(async(url:RequestInfo|URL)=>{
    if(String(url).endsWith('/z')&&attempts++<4)throw new TypeError('Failed to fetch');
    return arrayResponse(String(url));
  }) as typeof fetch;
  const result=await loadBundleResources('retry-network','token',async()=>bundle,new AbortController().signal,fetchArray);
  expect(attempts).toBe(5);
  expect([...result.input.z]).toEqual([1,2,3,4]);
});

test('a truncated raster cannot become a simulation input',async()=>{
  const fetchArray=(async()=>new Response(new Uint8Array(1))) as typeof fetch;
  await expect(loadBundleResources('short','token',async()=>bundle,new AbortController().signal,fetchArray))
    .rejects.toThrow('Terrain array z does not match the grid');
});
