async page => {
 const folder='E:/Nextstep Hacks hackathon/artifacts/verification/stabilization-v1/export-set';
 for(const name of ['Download evidence','Export report','Export costs','Export GeoJSON','Export manifest']){
  const pending=page.waitForEvent('download');
  await page.getByRole('button',{name,exact:true}).click();
  const download=await pending;
  await download.saveAs(folder+'/'+download.suggestedFilename());
 }
 await page.screenshot({path:'E:/Nextstep Hacks hackathon/output/playwright/stabilization-comparison.png',fullPage:true});
 await page.reload();
 await page.getByRole('button',{name:'Restore saved comparison',exact:true}).click();
 const text=await page.getByRole('dialog',{name:'Storm comparison'}).innerText();
 if(!text.includes('Assumed installation cost: $10,000')||!text.includes('general real-world flood accuracy remains unvalidated'))throw Error('Restored comparison lost assumptions');
}
