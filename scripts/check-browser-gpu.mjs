import {chromium} from '@playwright/test';
for(const config of [{name:'bundled-default',options:{}},{name:'chrome-new-headless',options:{channel:'chrome'}}]){
 let browser;
 try{
  browser=await chromium.launch(config.options);
  const page=await browser.newPage();
  const gpu=await page.evaluate(()=>{const c=document.createElement('canvas');const g=c.getContext('webgl2');const e=g?.getExtension('WEBGL_debug_renderer_info');return e?g.getParameter(e.UNMASKED_RENDERER_WEBGL):'unavailable';});
  console.log(config.name,gpu);
 }catch(error){console.log(config.name,error.message.split('\n')[0]);}finally{await browser?.close();}
}
