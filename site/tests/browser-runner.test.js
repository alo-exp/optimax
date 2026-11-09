import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, mkdir, cp, writeFile, readFile, rm, realpath} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

test('browser gate tests the existing candidate and stops when it fails', async()=>{
 const site=fileURLToPath(new URL('../',import.meta.url));
 const workspace=await mkdtemp(join(tmpdir(),'optimax-runner-test-'));
 try{
  for(const dir of ['e2e','scripts','src','content','public','dist','node_modules/@playwright/test'])await mkdir(join(workspace,dir),{recursive:true});
  for(const file of ['run.mjs','fixture.mjs'])await cp(join(site,'e2e',file),join(workspace,'e2e',file));
  await cp(join(site,'scripts/preview.mjs'),join(workspace,'scripts/preview.mjs'));
  await cp(join(site,'src/deployment.js'),join(workspace,'src/deployment.js'));
  await writeFile(join(workspace,'package.json'),'{"type":"module"}');
  const candidate='<meta name="site-base" content="/custom/deployment/">\nBROKEN CANDIDATE';
  await writeFile(join(workspace,'dist/index.html'),candidate);
  await writeFile(join(workspace,'build.js'),"const fs=require('fs');fs.mkdirSync('dist',{recursive:true});fs.writeFileSync('dist/index.html',process.env.SITE_URL);");
  await writeFile(join(workspace,'node_modules/@playwright/test/cli.js'),`
   const fs=require('fs'),path=require('path');
   const root=process.env.PREVIEW_ROOT;
   const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
   fs.appendFileSync(process.env.RUNNER_LOG,JSON.stringify({root,html})+'\\n');
   if(html.includes('BROKEN CANDIDATE')) process.exit(42);
  `);
  const log=join(workspace,'runs.log');
  const result=spawnSync(process.execPath,[join(workspace,'e2e/run.mjs')],{cwd:workspace,env:{...process.env,RUNNER_LOG:log},encoding:'utf8'});
  assert.equal(result.status,42,`candidate failure must block the gate: ${result.stderr}`);
  const runs=(await readFile(log,'utf8')).trim().split('\n').map(JSON.parse);
  assert.deepEqual(runs,[{root:await realpath(join(workspace,'dist')),html:candidate}]);
  assert.equal(await readFile(join(workspace,'dist/index.html'),'utf8'),candidate,'candidate must remain untouched');
  const passing='<meta name="site-base" content="/custom/deployment/">\nVALID CANDIDATE';
  await writeFile(join(workspace,'dist/index.html'),passing);
  await writeFile(log,'');
  const success=spawnSync(process.execPath,[join(workspace,'e2e/run.mjs')],{cwd:workspace,env:{...process.env,RUNNER_LOG:log},encoding:'utf8'});
  assert.equal(success.status,0,success.stderr);
  assert.match(success.stdout,/publication candidate \/custom\/deployment\//);
  const completed=(await readFile(log,'utf8')).trim().split('\n').map(JSON.parse);
  assert.deepEqual(completed[0],{root:await realpath(join(workspace,'dist')),html:passing});
  assert.deepEqual(completed.slice(1).map(run=>run.html),['https://optimax.alolabs.dev/','https://alo-exp.github.io/optimax/']);
  assert.equal(await readFile(join(workspace,'dist/index.html'),'utf8'),passing);
 }finally{await rm(workspace,{recursive:true,force:true});}
});
