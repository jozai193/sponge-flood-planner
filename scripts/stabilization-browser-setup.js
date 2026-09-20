async page => {
 const root='E:/Nextstep Hacks hackathon';
 const id='2c607f51e1a064fc76ee6f5585cbc343358d0e9a39ead1a2806643e21cae37ba';
 await page.unroute('**/api/v1/bundles/**');
 await page.route('**/api/v1/bundles/**',async route=>{
  const path=route.request().url().split('?')[0],match=path.match(/arrays\/([a-z_]+)$/);
  if(match)return route.fulfill({path:`${root}/data/local/bundles/${id}/${match[1]}.bin`,contentType:'application/octet-stream'});
  if(path.endsWith('/context'))return route.fulfill({path:`${root}/artifacts/verification/landscape-fixtures/${id}.json`,contentType:'application/json'});
  if(path.endsWith(id))return route.fulfill({path:`${root}/data/local/bundles/${id}/manifest.json`,contentType:'application/json'});
  return route.fulfill({status:503,json:{detail:'Prepared UI verification: live API and imagery excluded'}});
 });
 await page.goto(`http://127.0.0.1:5173/?bundle=${id}`);
 await page.waitForFunction(()=>document.documentElement.dataset.sceneDetailReadyMs);
}
