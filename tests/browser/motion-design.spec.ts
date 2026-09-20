import {test,expect} from '@playwright/test';

test('storm arrival and intervention placement use purposeful motion',async({page})=>{
 await page.goto('/?intro=1');
 const opening=page.locator('.launch-experience');
 await expect(opening).toContainText('See the storm.',{timeout:30000});
 await expect(opening).toContainText('Shape the response.');
 await page.waitForTimeout(4700);
 await page.screenshot({path:'output/playwright/storm-intro-polish.png'});
 await page.evaluate(()=>document.querySelector<HTMLButtonElement>('.launch-experience button')?.click());
 await expect(opening).toBeHidden({timeout:5000});
 await expect(page.getByRole('button',{name:'Run storm',exact:true})).toBeEnabled({timeout:30000});
 await page.getByLabel('Intervention').selectOption('bioswale');
 await expect(page.locator('.design-kind-story')).toContainText('A graded planted channel');
 await page.getByLabel('Assume this site is eligible',{exact:false}).check();
 await page.getByRole('button',{name:'Apply to area'}).click();
 await expect(page.locator('.design-stage-toast')).toContainText('Bioswale placed');
 await page.screenshot({path:'output/playwright/design-placement-polish.png'});
 await expect(page.locator('.design-row')).toContainText('bioswale');
 await page.getByRole('button',{name:'Run storm',exact:true}).click();
 await expect(page.locator('.storm-atmosphere')).toHaveClass(/is-running/);
 await page.getByRole('button',{name:'Stop simulation',exact:true}).click();
});

test('reduced-motion preference removes decorative storm animation',async({page})=>{
 await page.emulateMedia({reducedMotion:'reduce'});
 await page.goto('/?intro=1');
 await expect(page.locator('.launch-experience')).toBeVisible({timeout:30000});
 await expect(page.locator('.launch-rain')).toHaveCSS('display','none');
 await page.evaluate(()=>document.querySelector<HTMLButtonElement>('.launch-experience button')?.click());
});

test('opening remains composed on a narrow screen',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.goto('/?intro=1');
 const opening=page.locator('.launch-experience');
 await expect(opening).toContainText('Shape the response.',{timeout:30000});
 await expect(page.getByRole('button',{name:'Enter the live model'})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBe(true);
 await page.waitForTimeout(1500);
 await page.screenshot({path:'output/playwright/storm-intro-mobile.png'});
 await page.getByRole('button',{name:'Enter the live model'}).click();
 await expect(opening).toBeHidden({timeout:5000});
});
