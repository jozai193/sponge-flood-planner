import {compileFromFile} from 'json-schema-to-typescript';
import {mkdir, readdir, writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const base = new URL('../packages/contracts/', import.meta.url);
await mkdir(new URL('src/', base), {recursive:true});
for (const file of await readdir(new URL('schema/',base))) {
  if (!file.endsWith('.json')) continue;
  const source = await compileFromFile(fileURLToPath(new URL(`schema/${file}`,base)), {
    bannerComment:'/* Generated from canonical schema. Run scripts/generate-types.mjs. */',
  });
  await writeFile(new URL(`src/${file.replace('.json','.ts')}`,base),source);
}
