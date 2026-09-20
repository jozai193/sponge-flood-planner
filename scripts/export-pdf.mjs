import {readFile,writeFile,mkdir,rename} from 'node:fs/promises';
import {resolve,dirname,basename,join} from 'node:path';
import {createHash} from 'node:crypto';
import {chromium} from '@playwright/test';

const [manifestArgument,outputArgument]=process.argv.slice(2);
if(!manifestArgument||!outputArgument)throw new Error('Usage: pnpm export:pdf <sponge-export-manifest.json> <report.pdf>');
const manifestPath=resolve(manifestArgument),folder=dirname(manifestPath),output=resolve(outputArgument);
if(!output.toLowerCase().endsWith('.pdf'))throw new Error('Output must be a PDF path');
const manifestBytes=await readFile(manifestPath),manifest=JSON.parse(manifestBytes.toString('utf8'));
if(manifest.schema!=='sponge-export-manifest'||manifest.version!==1||!Array.isArray(manifest.artifacts)||!manifest.artifacts.length)throw new Error('Unsupported export manifest');
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const seen=new Set();let html;
for(const artifact of manifest.artifacts){
 const name=artifact.name;
 if(typeof name!=='string'||!name||/[\\/:]/.test(name)||['.','..'].includes(name)||seen.has(name))throw new Error('Invalid export filename');
 seen.add(name);const bytes=await readFile(join(folder,name));
 if(bytes.length!==artifact.bytes||hash(bytes)!==artifact.sha256)throw new Error('Export integrity check failed: '+name);
 if(name==='sponge-planning-report.html')html=bytes.toString('utf8');
}
if(!html)throw new Error('Planning HTML is missing from the verified manifest');
const browser=await chromium.launch({headless:true});
try{
 // Exported content is inert: no scripts or external network resources execute.
 const context=await browser.newContext({javaScriptEnabled:false});
 await context.route('**/*',route=>route.abort());
 const page=await context.newPage();await page.setContent(html,{waitUntil:'load'});
 await page.emulateMedia({media:'print'});
 const bytes=await page.pdf({format:'A4',printBackground:true,preferCSSPageSize:true,displayHeaderFooter:true,
  headerTemplate:'<span></span>',footerTemplate:'<div style="font-size:8px;width:100%;text-align:center;color:#526967">SPONGE | Exploratory planning | <span class="pageNumber"></span> / <span class="totalPages"></span></div>'});
 await mkdir(dirname(output),{recursive:true});
 const temporary=output+'.tmp';await writeFile(temporary,bytes);await rename(temporary,output);
 const record={schema:'sponge-pdf-derivation',version:1,pdf:{name:basename(output),bytes:bytes.length,sha256:hash(bytes)},
  sourceManifest:{name:basename(manifestPath),sha256:hash(manifestBytes)},sourceHtml:manifest.artifacts.find(a=>a.name==='sponge-planning-report.html'),
  renderer:{name:'Chromium',version:browser.version()},note:'Derived from checksum-verified HTML. PDF bytes may vary across browser versions and creation times; checksums do not certify model accuracy.'};
 await writeFile(output+'.manifest.json',JSON.stringify(record,null,2));
 console.log('Created '+output+' from verified exports.');
}finally{await browser.close();}
