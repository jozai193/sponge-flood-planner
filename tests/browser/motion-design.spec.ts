import {test,expect} from '@playwright/test';

test('storm arrival and intervention placement use purposeful motion',async({page})=>{
 await page.goto('/?intro=1');
 const opening=page.locator('.launch-experience');
 await expect(opening).toContainText('One storm.',{timeout:30000});
 await expect(opening).toContainText('Two futures.');
 await expect(opening).toContainText('Built for any neighbourhood');
 await expect(opening).not.toContainText('Spring Garden');
 await expect(page.getByRole('group',{name:'Two-image rainy street comparison'})).toBeVisible();
 await expect(page.getByRole('img',{name:/conventional city street/i})).toBeVisible();
 await expect(page.getByRole('img',{name:/matching city street/i})).toBeVisible();
 await expect(page.locator('.launch-photo-conventional')).toContainText('Water runs off and pools');
 await expect(page.locator('.launch-photo-permeable')).toContainText('Water filters through the edge');
 await expect(page.locator('.launch-flood')).toBeVisible();
 await expect(page.locator('.launch-permeable')).toBeVisible();
 await expect(page.locator('.launch-comparison')).toContainText('Runoff accumulates');
 await expect(page.locator('.launch-comparison')).toContainText('Permeable + planted');
 const divider=page.getByRole('separator',{name:'Before and after comparison divider'});
 await expect(divider).toHaveAttribute('aria-valuenow','52');
 await divider.press('ArrowRight');
 await expect(divider).toHaveAttribute('aria-valuenow','54');
 await page.getByRole('button',{name:'downpour'}).click();
 await expect(opening).toHaveAttribute('data-rain','downpour');
 await expect(page.getByRole('button',{name:'downpour'})).toHaveAttribute('aria-pressed','true');
 await expect(page.getByRole('button',{name:'Take the guided tour'})).toBeVisible();
 await page.waitForTimeout(7200);
 await expect(opening).toBeVisible();
 await page.screenshot({path:'output/playwright/storm-intro-polish.png'});
 await page.getByRole('button',{name:'Enter the live model'}).click();
 await expect(opening).toBeHidden({timeout:5000});
 await expect(page.getByRole('button',{name:'Run storm',exact:true})).toBeEnabled({timeout:30000});
 await page.getByLabel('Intervention').selectOption('bioswale');
 await expect(page.locator('.design-kind-story')).toContainText('A graded planted channel');
 await page.getByLabel('Assume this site is eligible',{exact:false}).check();
 await page.getByRole('button',{name:'Apply to area'}).click();
 await expect(page.locator('.design-stage-toast')).toContainText('Bioswale placed');
 await page.screenshot({path:'output/playwright/design-placement-polish.png'});
 await expect(page.locator('.design-row')).toContainText('bioswale');
 await page.locator('.storm-atmosphere').evaluate(element=>{
  const recordRunning=()=>{
   if(element.classList.contains('is-running'))element.setAttribute('data-observed-running','true');
  };
  recordRunning();
  new MutationObserver(recordRunning).observe(element,{attributeFilter:['class']});
 });
 await page.getByRole('button',{name:'Run storm',exact:true}).click();
 await expect(page.locator('.storm-atmosphere')).toHaveAttribute('data-observed-running','true');
 const stop=page.getByRole('button',{name:'Stop simulation',exact:true});
 if(await stop.isVisible())await stop.click();
});

test('reduced-motion preference removes decorative storm animation',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'});
 await page.goto('/?intro=1');
 await expect(page.locator('.launch-experience')).toBeVisible({timeout:30000});
 await expect(page.locator('.launch-rain-canvas')).toHaveAttribute('data-motion','reduced');
 await expect(page.locator('.launch-lightning')).toHaveCSS('display','none');
 await page.getByRole('button',{name:'Enter the live model'}).click();
});

test('opening remains composed on a narrow screen',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/?intro=1');
 const opening=page.locator('.launch-experience');
 await expect(opening).toContainText('Two futures.',{timeout:30000});
 await expect(opening).not.toContainText('Spring Garden');
 await expect(page.getByRole('button',{name:'Enter the live model'})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBe(true);
 await page.waitForTimeout(1500);
 await page.screenshot({path:'output/playwright/storm-intro-mobile.png'});
 await page.getByRole('button',{name:'Enter the live model'}).click();
 await expect(opening).toBeHidden({timeout:5000});
});
