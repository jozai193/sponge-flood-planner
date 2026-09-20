import {test,expect} from '@playwright/test';

test('judge tour explains impact, workflow, differentiation and evidence boundaries',async({page})=>{
  await page.goto('/?tour=1');
  const dialog=page.getByRole('dialog',{name:'Turn a flood map into a testable neighbourhood decision.'});
  await expect(dialog).toBeVisible();
  await expect(dialog.getByText('EARTH FORWARD',{exact:false})).toBeVisible();
  await expect(dialog.getByText('Compare—not just animate',{exact:true})).toBeVisible();
  await expect(dialog.getByText('more than 480 automated checks',{exact:false})).toBeVisible();
  await expect(dialog.getByText('not a calibrated forecast',{exact:false})).toBeVisible();
  await dialog.getByRole('button',{name:'Explore the prepared neighbourhood'}).click();
  await expect(dialog).toHaveCount(0);
  await page.getByRole('button',{name:'Judge tour'}).click();
  await expect(dialog).toBeVisible();
});
