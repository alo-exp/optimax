import {test,expect} from '@playwright/test';
import {mkdtemp,rm,readdir} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {prepareBuildFixture} from './fixture.mjs';

const site=dirname(dirname(fileURLToPath(import.meta.url))),run=promisify(execFile);
test('default capture completes and records keyboard focus and search',async()=>{
 test.setTimeout(90000);
 const workspace=await mkdtemp(join(tmpdir(),'optimax-capture-test-'));
 try{
  await prepareBuildFixture(site,workspace);
  await run(process.execPath,['build.js'],{cwd:workspace});
  const directory=join(workspace,'captures');
  await run(process.execPath,[join(site,'e2e/capture.mjs')],{cwd:site,env:{...process.env,PREVIEW_ROOT:join(workspace,'dist'),OPTIMAX_CAPTURE_DIR:directory,OPTIMAX_CAPTURE_PREFIX:'final'},timeout:70000});
  const files=await readdir(directory);
  expect(files).toHaveLength(11);
  expect(files).toEqual(expect.arrayContaining(['focus-nav.png','hero-repro.png','search-active.png']));
 }finally{await rm(workspace,{recursive:true,force:true});}
});
