async page => {
  const folder='E:/Nextstep Hacks hackathon/artifacts/verification/stabilization-v1/live-export-set';
  await page.getByLabel('Import survey JSON').setInputFiles('E:/Nextstep Hacks hackathon/artifacts/verification/stabilization-v1/live-rainfall.json');
  await page.getByRole('button',{name:'Use rainfall event',exact:true}).click();
  await page.getByRole('button',{name:'Close',exact:true}).click();
  await page.getByLabel('Assume this site is eligible',{exact:false}).check();
  await page.getByRole('button',{name:'Apply to area',exact:true}).click();
  await page.getByRole('button',{name:'Plan with physics',exact:true}).click();
  await page.getByRole('dialog',{name:'Storm comparison'}).waitFor({timeout:120000});
  const text=await page.getByRole('dialog',{name:'Storm comparison'}).innerText();
  if(!text.includes('general real-world flood accuracy remains unvalidated'))throw Error('Missing validation limits');
  for(const name of ['Download evidence','Export report','Export costs','Export GeoJSON','Export manifest']){
    const pending=page.waitForEvent('download');
    await page.getByRole('button',{name,exact:true}).click();
    const download=await pending;
    await download.saveAs(folder+'/'+download.suggestedFilename());
  }
  await page.screenshot({path:'E:/Nextstep Hacks hackathon/output/playwright/live-recovery-planner.png',fullPage:true});
  await page.reload();
  await page.getByRole('button',{name:'Restore saved comparison',exact:true}).click();
  await page.getByRole('dialog',{name:'Storm comparison'}).waitFor();
  return {restored:true,text};
}
