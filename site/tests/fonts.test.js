import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync,readFileSync,statSync} from 'node:fs';

test('self-hosted Mona Sans supplies licensed Latin 400 and 700 WOFF2 within the public font budget',()=>{
 const directory=new URL('../public/fonts/',import.meta.url);
 let totalBytes=0;
 for(const weight of [400,700]){
  const filename=`mona-sans-latin-${weight}-normal.woff2`,asset=new URL(filename,directory);
  assert.ok(existsSync(asset),`public font supply must include ${filename}`);
  const bytes=readFileSync(asset);assert.equal(bytes.subarray(0,4).toString(),'wOF2');
  assert.ok(bytes.length>1000,'font must contain an actual compressed glyph payload');
  const official=new URL(`../node_modules/@fontsource/mona-sans/files/${filename}`,import.meta.url);
  assert.deepEqual(bytes,readFileSync(official),'public asset must match the locked official package');totalBytes+=statSync(asset).size;
 }
 assert.ok(totalBytes<=120*1024,`two font weights exceed 120KiB: ${totalBytes}`);
 const license=readFileSync(new URL('OFL.txt',directory),'utf8');
 assert.match(license,/SIL OPEN FONT LICENSE/i);assert.match(license,/Version 1[.]1/);assert.match(license,/Copyright/i);
 assert.equal(license,readFileSync(new URL('../node_modules/@fontsource/mona-sans/LICENSE',import.meta.url),'utf8'));
 const pkg=JSON.parse(readFileSync(new URL('../package.json',import.meta.url),'utf8'));
 assert.equal(pkg.devDependencies['@fontsource/mona-sans'],'5.3.0','font provenance must use the verified exact package version');
});
