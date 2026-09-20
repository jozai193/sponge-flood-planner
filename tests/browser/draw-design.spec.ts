import {test,expect} from '@playwright/test';

test('user can draw, edit, lock and delete an eligible candidate footprint',async({page})=>{
 await page.goto('/?intro=0');
 await expect(page.getByRole('button',{name:'Run storm',exact:true})).toBeEnabled({timeout:30000});
 await page.getByRole('button',{name:'Draw candidate',exact:true}).click();
 await page.getByRole('button',{name:'Place candidate near map centre',exact:true}).click();
 const sites=page.getByRole('combobox',{name:'Candidate area'});await expect(sites).toContainText('drawn-');
 const drawnValue=await sites.locator('option').last().getAttribute('value');if(!drawnValue?.startsWith('drawn-'))throw new Error('Drawn candidate not last');await sites.selectOption(drawnValue);
 await page.getByLabel('Assume this site is eligible',{exact:false}).check();
 await page.getByRole('button',{name:'Apply to area'}).click();
 await expect(page.locator('.design-row')).toHaveCount(1);
 await page.getByRole('combobox',{name:/Planning constraint/}).selectOption('locked');
 await page.getByRole('button',{name:'Edit',exact:true}).click();
 await expect(page.getByText('Editing drawn-',{exact:false})).toBeVisible();
 await page.getByRole('button',{name:'Remove',exact:true}).click();
 await expect(page.locator('.design-row')).toHaveCount(0);
});
