import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {readFileSync,readdirSync} from 'node:fs';
import {join,relative} from 'node:path';
const repository=fileURLToPath(new URL('../..',import.meta.url));
const sourceHash=createHash('sha256');
for(const folder of ['packages/simulation','packages/domain','packages/optimizer','packages/metrics']){
 const root=join(repository,folder),walk=(directory:string):string[]=>readdirSync(directory,{withFileTypes:true}).flatMap(entry=>entry.isDirectory()?walk(join(directory,entry.name)):/\.(ts|json|glsl)$/.test(entry.name)?[join(directory,entry.name)]:[]);
 for(const path of walk(root).sort()){sourceHash.update(relative(repository,path).replaceAll('\\','/'));sourceHash.update('\0');sourceHash.update(readFileSync(path));sourceHash.update('\0');}
}
export default defineConfig({
  root:fileURLToPath(new URL('.',import.meta.url)), plugins:[react()],
  define:{__SPONGE_MODEL_SOURCE_SHA256__:JSON.stringify(sourceHash.digest('hex'))},
  server:{port:5173,strictPort:true,proxy:{'/api':'http://127.0.0.1:8787'}},
  build:{outDir:'../../dist',emptyOutDir:true,rolldownOptions:{output:{strictExecutionOrder:true,codeSplitting:{groups:[
    {name:'react',test:/node_modules[\\/](react|react-dom)[\\/]/,priority:20},
    {name:'graphics',test:/node_modules[\\/](@deck\.gl|@luma\.gl|@loaders\.gl|@math\.gl)[\\/]/,maxSize:450_000,priority:15},
    {name:'vendor',test:/node_modules[\\/]/,minSize:100_000,maxSize:450_000,priority:5}
  ]}}}},
  worker:{format:'es'}
});
