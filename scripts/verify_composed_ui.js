async page => {
 await page.reload();
 await page.getByRole('combobox',{name:'Flood scenario',exact:true}).waitFor();
 await page.waitForFunction(()=>!document.querySelector('button.primary')?.disabled,{},{timeout:45000});
 await page.getByRole('combobox',{name:'Flood scenario',exact:true}).selectOption('combined');
 await page.getByLabel('Include coastal water level',{exact:true}).waitFor();
 if(!await page.getByLabel('Include rainfall',{exact:true}).isChecked()||!await page.getByLabel('Include coastal water level',{exact:true}).isChecked())throw Error('Missing composition defaults');
 await page.getByRole('button',{name:'Run storm',exact:true}).click();
 await page.getByRole('alert').filter({hasText:'Apply a coastal boundary first'}).waitFor();
 await page.getByLabel('Include external inflow',{exact:true}).check();
 await page.getByRole('combobox',{name:'Inflow edge',exact:true}).selectOption('east');
 await page.getByRole('combobox',{name:'Coastal edge',exact:true}).selectOption('west');
 if(await page.getByRole('combobox',{name:'Inflow edge',exact:true}).inputValue()!=='east')throw Error('Coastal edit overwrote inflow edge');
 await page.getByLabel('Include coastal water level',{exact:true}).uncheck();
 await page.getByLabel('Include external inflow',{exact:true}).uncheck();
 await page.getByLabel('Include rainfall',{exact:true}).uncheck();
 await page.getByRole('button',{name:'Run storm',exact:true}).click();
 await page.getByRole('alert').filter({hasText:'Enable at least one flood source'}).waitFor();
 await page.getByLabel('Include rainfall',{exact:true}).check();
 await page.getByLabel('Include coastal water level',{exact:true}).check();
 await page.locator('section').filter({has:page.getByRole('combobox',{name:'Flood scenario',exact:true})}).scrollIntoViewIfNeeded();
 await page.screenshot({path:'E:/Nextstep Hacks hackathon/output/playwright/scenario-composition-controls.png'});
 // Restore the existing rainfall preset; do not leave an unfinished coastal setup.
 await page.getByRole('combobox',{name:'Flood scenario',exact:true}).selectOption('rain');
 return {defaults:true,missingBoundaryRejected:true,emptySourcesRejected:true,independentEdges:true,legacyRainRestored:true};
}
