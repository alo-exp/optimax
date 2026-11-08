import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,rm,readFile} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {prepareBuildFixture} from '../e2e/fixture.mjs';

test('isolated real-build fixtures retain the public font supply and license',async()=>{
 const site=fileURLToPath(new URL('../',import.meta.url)),workspace=await mkdtemp(join(tmpdir(),'optimax-fixture-test-'));
 try{
  await prepareBuildFixture(site,workspace);
  for(const family of ['mona-sans','sora'])for(const name of [`${family}-latin-400-normal.woff2`,`${family}-latin-700-normal.woff2`,family==='mona-sans'?'OFL.txt':`${family}-OFL.txt`]){
   const relative=join('public','fonts',name),asset=join(workspace,relative);
   assert.ok(existsSync(asset),`isolated build must retain public asset ${relative}`);
   assert.deepEqual(await readFile(asset),await readFile(join(site,relative)));
  }
 }finally{await rm(workspace,{recursive:true,force:true});}
});
