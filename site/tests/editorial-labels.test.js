import test from 'node:test';
import assert from 'node:assert/strict';
import {cp,mkdtemp,readFile,rm} from 'node:fs/promises';
import {dirname,join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {parseHTML} from 'linkedom';

const site=dirname(dirname(fileURLToPath(import.meta.url)));
test('editorial metadata keeps its wording without decorative numbering and preserves meaningful IDs',async()=>{
 const root=await mkdtemp(join(tmpdir(),'optimax-labels-'));
 try{
  for(const name of ['build.js','src','content','public','package.json'])await cp(join(site,name),join(root,name),{recursive:true});
  execFileSync(process.execPath,['build.js'],{cwd:root,env:{...process.env,SITE_URL:'https://optimax.alolabs.dev/'},stdio:'pipe'});
  const home=parseHTML(await readFile(join(root,'dist/index.html'),'utf8')).document;
  const help=parseHTML(await readFile(join(root,'dist/help/index.html'),'utf8')).document;
  assert.deepEqual([...home.querySelectorAll('#mechanism .step-pin')].map(e=>e.textContent),['01','02','03'],'process order remains meaningful');
  assert.equal(home.querySelectorAll('.parallel-tasks li > .junction').length,3,'each independent assignment retains a distinct connection');
  const labels=[
   ['how-it-works','WHY THE PLAN MATTERS'],
   ['mechanism','HOW OPTIMAX WORKS'],
   ['proof','EVIDENCE YOU CAN INSPECT'],
   ['benefits','WHAT THE POLICY HELPS YOU DO'],
   ['questions','BEFORE YOU INSTALL'],
   ['install','FREE PLUGIN / MIT LICENSE']
  ];
  for(const [id,expected] of labels)assert.equal(home.querySelector('#'+id+' .metadata').textContent,expected,id+' caption must retain wording without a decorative number');
  const topics=[...help.querySelectorAll('.help-group .eyebrow')].map(e=>e.textContent);
  assert.equal(topics.length,7,'all help topic groups remain present');
  assert.deepEqual(topics,Array(7).fill('TOPIC'),'topic metadata must retain wording without decorative numbers');
 }finally{await rm(root,{recursive:true,force:true})}
});
