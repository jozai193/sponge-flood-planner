async page => {
  const qa=await page.context().newPage();
  const checks=[];
  const verify=(condition,name)=>{if(!condition)throw Error(name);checks.push(name);};
  try{
    await qa.goto('http://127.0.0.1:5173/');
    await qa.getByRole('button',{name:'Search',exact:true}).waitFor();
    await qa.waitForFunction(()=>!document.querySelector('button[aria-label="Search"]').disabled);
    let release,started;
    const received=new Promise(resolve=>started=resolve);
    const held=new Promise(resolve=>release=resolve);
    await qa.route('**/api/v1/geocode',async route=>{
      const body=route.request().postDataJSON();
      if(body.query==='old query'){
        started();await held;
        await route.fulfill({json:{locations:[{label:'Stale location',latitude:1,longitude:2}]}}).catch(()=>{});
      }else if(body.query==='empty query'){
        await route.fulfill({json:{locations:[],warnings:[]}});
      }else if(body.query==='polar query'){
        await route.fulfill({json:{locations:[{label:'Polar location',latitude:89,longitude:0,terrain_supported:false,coverage_note:'Terrain outside 80°S–80°N is not supported yet.'}],warnings:[]}});
      }else{
        await route.fulfill({status:503,json:{detail:'Controlled outage'}});
      }
    });
    await qa.getByLabel('Address',{exact:true}).fill('old query');
    await qa.getByRole('button',{name:'Search',exact:true}).click();await received;
    verify(await qa.getByRole('button',{name:'Search',exact:true}).isDisabled(),'Search disabled while in flight');
    await qa.getByLabel('Address',{exact:true}).fill('empty query');release();
    await qa.getByRole('button',{name:'Search',exact:true}).click();
    await qa.getByRole('status').filter({hasText:'No matching place found'}).waitFor();
    verify(await qa.locator('.location').count()===0,'Changed query rejects stale results and explains empty results');
    await qa.getByLabel('Address',{exact:true}).fill('polar query');
    await qa.getByRole('button',{name:'Search',exact:true}).click();
    await qa.getByRole('button',{name:'Polar location',exact:true}).waitFor();
    verify(await qa.getByRole('button',{name:'Polar location',exact:true}).isDisabled(),'Unsupported polar terrain cannot start preparation');
    await qa.getByLabel('Address',{exact:true}).fill('outage query');
    await qa.getByRole('button',{name:'Search',exact:true}).click();
    await qa.getByRole('status').filter({hasText:'Search could not finish'}).waitFor();
    verify(await qa.locator('.location').count()===0,'Outage clears old locations and offers coordinate fallback');
    await qa.screenshot({path:'E:/Nextstep Hacks hackathon/output/playwright/location-search-outage.png'});
  }finally{await qa.close();}
  verify((await page.locator('h1').innerText()).includes('Ozone Evengreen Apartments'),'Live Ozone neighbourhood loaded');
  verify(await page.getByRole('button',{name:'Run storm',exact:true}).isEnabled(),'Live Ozone storm controls ready');
  verify(await page.locator('.error').count()===0,'Live Ozone has no visible error');
  await page.screenshot({path:'E:/Nextstep Hacks hackathon/output/playwright/location-search-loaded.png'});
  return {checks,live_url:page.url(),buildings:await page.locator('.facts').innerText()};
}
