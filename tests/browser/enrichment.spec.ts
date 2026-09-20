import {test,expect} from '@playwright/test';
test('acquired rainfall evidence can be selected without a file round trip',async({page})=>{
 const storm={name:'Acquired IMERG fixture',duration_s:1800,recession_s:60,depth_m:.001,
   intervals:[{start_s:0,end_s:1800,rate_m_s:.001/1800}]};
 await page.route('**/api/v1/bundles/*/enrichment',route=>route.fulfill({json:[{
   id:'rainfall-fixture',status:'completed',results:{rainfall:{status:'available',note:'Fixture acquisition'}}}]}));
 await page.route('**/api/v1/enrichment/rainfall-fixture/rainfall',route=>route.fulfill({json:{survey:{kind:'rainfall',storm}}}));
 await page.goto('/');await expect(page.getByRole('button',{name:'Run storm'})).toBeEnabled({timeout:30000});
 await page.getByRole('button',{name:'Data & assumptions'}).click();
 await page.getByRole('button',{name:'Use acquired rainfall event'}).click();
 await page.getByRole('button',{name:'Close',exact:true}).click();
 await expect(page.getByText('Sourced rainfall intervals: Acquired IMERG fixture',{exact:false})).toBeVisible();
});

test('area enrichment creates an isolated revision and preserves access controls',async({request})=>{
 test.setTimeout(120000);
 const session=await (await request.post('/api/v1/sessions',{data:{}})).json();
 const headers={Authorization:'Bearer '+session.token};
 const examples=await (await request.get('/api/v1/examples')).json();const bundle=examples[0].bundle_id;
 const created=await request.post(`/api/v1/bundles/${bundle}/enrichment`,{headers,data:{capabilities:['landcover','terrain','catchments']}});
 expect(created.status()).toBe(202);const job=await created.json();
 let result:any;
 for(let i=0;i<100;i++){
  result=await (await request.get('/api/v1/enrichment/'+job.id,{headers})).json();
  if(!['queued','running'].includes(result.status))break;
  await new Promise(resolve=>setTimeout(resolve,1000));
 }
 expect(result.status).toBe('completed');expect(result.results.landcover.status).toBe('available');
 expect(result.results.terrain.status).toBe('available');expect(result.results.catchments.status).toBe('available');
 const rejected=await request.post('/api/v1/enrichment/'+job.id+'/apply',{headers,data:{buildings:false,landcover:true}});
 expect(rejected.status()).toBe(422);
 const applied=await request.post('/api/v1/enrichment/'+job.id+'/apply',{headers,data:{buildings:false,landcover:true,accept_exploratory_materials:true}});
 expect(applied.ok()).toBeTruthy();const revision=await applied.json();expect(revision.bundle_id).not.toBe(bundle);
 const manifest=await (await request.get('/api/v1/bundles/'+revision.bundle_id,{headers})).json();
 expect(manifest.quality.materials).toBe('source_classified_exploratory_presets');
 const other=await (await request.post('/api/v1/sessions',{data:{}})).json();
 expect((await request.get('/api/v1/enrichment/'+job.id,{headers:{Authorization:'Bearer '+other.token}})).status()).toBe(404);
});

test('rainfall survey can be imported and selected through the browser',async({page})=>{
 const survey={kind:'rainfall',source:{title:'Browser fixture rainfall',attribution:'SPONGE test fixture',observed_at:'2024-01-01T00:00:00Z',horizontal_crs:'EPSG:4326',vertical_datum:'not applicable',license:'test fixture',provenance:'user_assumption'},
 storm:{name:'Nonuniform test event',duration_s:120,recession_s:60,depth_m:.001,intervals:[{start_s:20,end_s:30,rate_m_s:.0001}]}};
 let imported=false;
 await page.route('**/api/v1/bundles/*/imports',route=>{
  if(route.request().method()==='POST'){imported=true;return route.fulfill({json:{id:'rain-import',kind:'rainfall',status:'imported'}});}
  return route.fulfill({json:imported?[{id:'rain-import',kind:'rainfall',source:survey.source}]:[]});
 });
 await page.route('**/api/v1/imports/rain-import',route=>route.fulfill({json:survey}));
 await page.goto('/');await expect(page.getByRole('button',{name:'Run storm'})).toBeEnabled({timeout:30000});
 await page.getByRole('button',{name:'Data & assumptions'}).click();
 await page.getByLabel('Import survey JSON').setInputFiles({name:'rain.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(survey))});
 await page.getByRole('button',{name:'Use rainfall event'}).click();
 await expect(page.getByText('Sourced rainfall intervals: Nonuniform test event',{exact:false})).toBeVisible();
 await page.getByRole('button',{name:'Close',exact:true}).click();
 await expect(page.getByRole('alert')).toHaveCount(0);
});
