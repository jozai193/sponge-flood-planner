import {test,expect} from '@playwright/test';

test('prepared demo recovers from one transient startup connection failure',async({page})=>{
 let attempts=0;
 await page.route('**/api/v1/examples',async route=>{
  attempts++;
  if(attempts===1)return route.abort('connectionreset');
  return route.continue();
 });
 await page.goto('/?intro=0');
 await expect(page.getByRole('heading',{name:'Spring Garden, Philadelphia'})).toBeVisible({timeout:30000});
 expect(attempts).toBe(2);
 await expect(page.getByRole('button',{name:'Run storm',exact:true})).toBeEnabled({timeout:30000});
});

test('prepared demo starts when session storage is unavailable',async({page})=>{
 await page.addInitScript(()=>{
  const blocked=()=>{throw new DOMException('Storage access is blocked','SecurityError');};
  Object.defineProperty(Storage.prototype,'getItem',{configurable:true,value:blocked});
  Object.defineProperty(Storage.prototype,'setItem',{configurable:true,value:blocked});
 });
 await page.goto('/?intro=0');
 await expect(page.getByRole('heading',{name:'Spring Garden, Philadelphia'})).toBeVisible({timeout:30000});
 await expect(page.getByRole('button',{name:'Run storm',exact:true})).toBeEnabled({timeout:30000});
});

test('an expired stored session is renewed once across concurrent bundle requests',async({page})=>{
 await page.addInitScript(()=>sessionStorage.setItem('sponge-session','expired-token'));
 let sessions=0;
 await page.route('**/api/v1/sessions',async route=>{
  sessions++;
  await route.continue();
 });
 await page.route('**/api/v1/bundles/**',async route=>{
  if(route.request().headers().authorization==='Bearer expired-token'){
   await route.fulfill({status:401,contentType:'application/json',body:'{"detail":"Session expired"}'});
   return;
  }
  await route.continue();
 });
 await page.goto('/?intro=0');
 await expect(page.getByRole('heading',{name:'Spring Garden, Philadelphia'})).toBeVisible({timeout:30000});
 await expect(page.getByRole('button',{name:'Run storm',exact:true})).toBeEnabled({timeout:30000});
 expect(sessions).toBe(1);
 await expect.poll(()=>page.evaluate(()=>sessionStorage.getItem('sponge-session'))).not.toBe('expired-token');
});
