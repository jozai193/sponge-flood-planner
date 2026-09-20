import {chromium} from '@playwright/test';

const baseUrl=process.env.SPONGE_BASE_URL??'http://127.0.0.1:18080';
const browser=await chromium.launch();
try{
 const page=await browser.newPage({viewport:{width:1440,height:960}});
 const errors=[];
 page.on('console',message=>{if(message.type()==='error')errors.push('console: '+message.text());});
 page.on('pageerror',error=>errors.push('page: '+error.message));
 const response=await page.goto(baseUrl+'/?tour=1',{waitUntil:'domcontentloaded'});
 if(!response?.ok())throw new Error(`Production page returned ${response?.status()??'no response'}`);
 const csp=response.headers()['content-security-policy']??'';
 if(!csp.includes("script-src 'self'")||csp.includes("'unsafe-eval'"))throw new Error('Production CSP is missing or permits unsafe-eval');
 await page.getByRole('heading',{name:'Turn a flood map into a testable neighbourhood decision.'}).waitFor();
 await page.getByRole('heading',{name:'Spring Garden, Philadelphia'}).waitFor({timeout:30000});
 await page.waitForFunction(()=>{
  const button=[...document.querySelectorAll('button')].find(node=>node.textContent?.trim()==='Run storm');
  return button instanceof HTMLButtonElement&&!button.disabled;
 },undefined,{timeout:30000});
 await page.getByRole('button',{name:'Close judge tour'}).click();
 await page.getByLabel('Assume this site is eligible',{exact:false}).check();
 await page.getByRole('button',{name:'Apply to area'}).click();
 await page.getByRole('button',{name:'Plan with physics'}).click();
 const stop=page.getByRole('button',{name:'Stop simulation'});
 await stop.waitFor({timeout:10000});
 await stop.click();
 if(errors.length)throw new Error('Production browser errors:\n'+errors.join('\n'));
 console.log(JSON.stringify({status:'passed',baseUrl,csp,judgeTour:true,preparedDemo:true,scenarioDispatch:true,consoleErrors:0}));
}finally{
 await browser.close();
}
