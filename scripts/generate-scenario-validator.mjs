import Ajv from 'ajv';
import standaloneCode from 'ajv/dist/standalone/index.js';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';

const schemaPath=fileURLToPath(new URL('../packages/contracts/schema/ScenarioSpecV2.json',import.meta.url));
const outputPath=fileURLToPath(new URL('../packages/domain/generated/scenario-validator.ts',import.meta.url));
const schema=JSON.parse(await readFile(schemaPath,'utf8'));
const ajv=new Ajv({strict:false,strictNumbers:true,allErrors:true,code:{source:true,esm:true}});
const helper='const func2 = require("ajv/dist/runtime/ucs2length").default;';
const standalone=standaloneCode(ajv,ajv.compile(schema));
if(!standalone.includes(helper)||standalone.replace(helper,'').includes('require('))throw new Error('Ajv standalone helpers changed; update the CSP-safe ESM generator.');
const generated='// @ts-nocheck\n// Generated from ScenarioSpecV2.json; run pnpm generate:validators after schema changes.\nfunction func2(value){let length=0;for(const unused of value)length++;return length;}\n'+standalone.replace(helper,'')+'\n';

if(process.argv.includes('--check')){
 let current='';
 try{current=await readFile(outputPath,'utf8');}catch{}
 if(current!==generated)throw new Error('Generated scenario validator is stale. Run pnpm generate:validators.');
 console.log('Generated scenario validator is current.');
}else{
 await mkdir(fileURLToPath(new URL('../packages/domain/generated',import.meta.url)),{recursive:true});
 await writeFile(outputPath,generated);
 console.log('Generated CSP-safe scenario validator.');
}
