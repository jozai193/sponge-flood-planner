import {test,expect} from '@playwright/test';
test('real neighbourhood loads with explicit assumptions',async({page})=>{
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'Spring Garden, Philadelphia'})).toBeVisible({timeout:30000});
  await expect(page.getByText('685 buildings')).toBeVisible({timeout:30000});
  await expect(page.getByRole('button',{name:'Run storm'})).toBeEnabled({timeout:30000});
  await page.getByRole('button',{name:'Data & assumptions'}).click();
  await expect(page.getByText('Development model.',{exact:false})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Terrain and obstacle integrity · checked'})).toBeVisible();
  await expect(page.getByRole('heading',{name:'Drainage network · unverified'})).toBeVisible();
  await page.getByRole('button',{name:'Close',exact:true}).click();
  await page.getByLabel('Assume this site is eligible',{exact:false}).check();
  await page.getByRole('button',{name:'Apply to area'}).click();
  await expect(page.locator('.design-row')).toHaveCount(1);
  await expect(page.getByRole('button',{name:'Compare selected design'})).toBeEnabled();
  await page.getByRole('button',{name:'Plan with physics'}).click();
  await expect(page.getByRole('button',{name:'Stop simulation'})).toBeVisible();
  await page.getByRole('button',{name:'Stop simulation'}).click();
  await expect(page.getByRole('button',{name:'Run storm'})).toBeVisible({timeout:20000});
  await page.getByRole('button',{name:'Remove',exact:true}).click();
  await expect(page.locator('.design-row')).toHaveCount(0);
  await expect(page.getByText('City of Philadelphia street centerlines',{exact:true})).toBeVisible({timeout:20000});
  const imageryAttribution=page.getByText('Satellite imagery · capture date varies',{exact:true});
  const imageryUnavailable=page.getByText('Satellite imagery unavailable · model view shown',{exact:true});
  await expect.poll(async()=>await imageryAttribution.isVisible()||await imageryUnavailable.isVisible(),{timeout:30000}).toBe(true);
  if(await imageryAttribution.isVisible()){
   await page.getByRole('button',{name:'Model view',exact:true}).click();
   await expect(page.getByRole('button',{name:'Satellite view',exact:true})).toBeVisible();
   await page.getByRole('button',{name:'Satellite view',exact:true}).click();
  }else await expect(imageryUnavailable).toBeVisible();
  await page.locator('aside').evaluate(el=>el.scrollTo(0,0));
  await page.screenshot({path:'artifacts/verification/terrain-view.png'});
  await page.getByRole('button',{name:'Run storm'}).click();
  await expect(page.getByRole('button',{name:'Stop simulation'})).toBeVisible();
  await expect(page.locator('.metrics>div').first()).not.toContainText('0 min',{timeout:60000});
  await page.getByRole('button',{name:'Stop simulation'}).click();
  await expect(page.getByRole('button',{name:'Run storm'})).toBeVisible({timeout:20000});
  await expect(page.getByText('Stopped storm saved on this browser.',{exact:true})).toBeVisible();
  await page.reload();
  await expect(page.getByRole('button',{name:'Restore saved storm'})).toBeVisible();
  await page.getByRole('button',{name:'Restore saved storm'}).click();
  await expect(page.getByRole('button',{name:'Resume stopped storm'})).toBeVisible();
  await page.getByRole('button',{name:'Resume stopped storm'}).click();
  await expect(page.getByRole('button',{name:'Stop simulation'})).toBeVisible();
  await expect(page.locator('.metrics>div').first()).not.toContainText('0 min',{timeout:60000});
  await page.getByRole('button',{name:'Stop simulation'}).click();
  await expect(page.getByRole('button',{name:'Run storm'})).toBeVisible({timeout:20000});
  await expect(page.getByRole('alert')).toHaveCount(0);
  await page.getByLabel('Flood scenario').selectOption('external');
  await page.getByLabel('Source or assumption').fill('Browser test: exploratory upstream inflow');
  await page.getByRole('button',{name:'Apply inflow',exact:true}).click();
  await expect(page.getByText('configured inflow cells.',{exact:false})).not.toContainText('0 configured');
  await page.getByRole('button',{name:'Run storm'}).click();
  await expect(page.getByRole('button',{name:'Stop simulation'})).toBeVisible();
  await page.getByRole('button',{name:'Stop simulation'}).click();
  await expect(page.getByRole('button',{name:'Run storm'})).toBeVisible({timeout:20000});
  await expect(page.getByRole('alert')).toHaveCount(0);
  expect(errors).toEqual([]);
});

for(const outcome of ['ready','unavailable'] as const){
 test(`water screening finishes before edits and simulation (${outcome})`,async({page})=>{
  let release!:()=>void;
  const pending=new Promise<void>(resolve=>{release=resolve;});
  await page.route('**/api/v1/bundles/*/context',async route=>{
   await pending;
   if(outcome==='unavailable')await route.fulfill({status:503,json:{detail:'Controlled provider outage'}});
   else await route.fulfill({json:{roads:[],green:[],trees:[],water:[],assumptions:[],attribution:'Controlled water screening'}});
  });
  await page.goto('/');
  await expect(page.getByText('685 buildings')).toBeVisible({timeout:30000});
  await expect(page.getByRole('button',{name:'Run storm',exact:true})).toBeDisabled();
  await expect(page.getByLabel('Assume this site is eligible',{exact:false})).toBeDisabled();
  await expect(page.getByText('Loading vegetation and water coverage before simulation…',{exact:true})).toBeVisible();
  release();
  await expect(page.getByRole('button',{name:'Run storm',exact:true})).toBeEnabled();
  await expect(page.getByLabel('Assume this site is eligible',{exact:false})).toBeEnabled();
  if(outcome==='unavailable')await expect(page.getByText('Street detail unavailable',{exact:true})).toBeVisible();
 });
}

 test('stalled landscape request releases controls with unavailable coverage',async({page})=>{
  await page.route('**/api/v1/bundles/*/context',()=>{});
  await page.goto('/');
  await expect(page.getByText('685 buildings')).toBeVisible({timeout:30000});
  await expect(page.getByRole('button',{name:'Run storm',exact:true})).toBeDisabled();
  await expect(page.getByRole('button',{name:'Run storm',exact:true})).toBeEnabled({timeout:55000});
  await expect(page.getByText('Street detail unavailable',{exact:true})).toBeVisible();
  await expect(page.getByText('Water screening unavailable or loading; eligibility remains unverified.',{exact:false})).toBeVisible();
 });

test('landscape outage can be retried without reloading terrain',async({page})=>{
 let requests=0,terrainRequests=0;
 page.on('request',r=>{if(r.url().includes('/arrays/z'))terrainRequests++;});
 await page.route('**/api/v1/bundles/*/context',route=>{
  requests++;
  return requests===1?route.fulfill({status:503,json:{detail:'Controlled outage'}}):route.fulfill({json:{roads:[],green:[],trees:[],water:[],assumptions:[],attribution:'Recovered landscape'}});
 });
 await page.goto('/');
 const retry=page.getByRole('button',{name:'Retry landscape coverage',exact:true});
 await expect(retry).toBeVisible();
 await retry.click();
 await expect(page.getByText('Recovered landscape',{exact:true})).toBeVisible();
 await expect(retry).toHaveCount(0);
 await expect(page.getByRole('button',{name:'Run storm',exact:true})).toBeEnabled();
 expect(requests).toBe(2);expect(terrainRequests).toBe(1);
});
