import test from 'node:test';
import assert from 'node:assert/strict';
import {cp,mkdtemp,readFile,readdir,rm} from 'node:fs/promises';
import {dirname,join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {parseHTML} from 'linkedom';

const site=dirname(dirname(fileURLToPath(import.meta.url)));
async function withBuild(url,check){
 const root=await mkdtemp(join(tmpdir(),'optimax-contract-'));
 try{
  for(const name of ['build.js','src','content','package.json'])await cp(join(site,name),join(root,name),{recursive:true});
  execFileSync(process.execPath,['build.js'],{cwd:root,env:{...process.env,SITE_URL:url},stdio:'pipe'});
  await check(join(root,'dist'));
 }finally{await rm(root,{recursive:true,force:true})}
}
async function htmlFiles(root){
 const entries=await readdir(root,{withFileTypes:true});
 return (await Promise.all(entries.map(entry=>entry.isDirectory()?htmlFiles(join(root,entry.name)):entry.name.endsWith('.html')?[join(root,entry.name)]:[]))).flat();
}
for(const url of ['https://optimax.alolabs.dev/','https://alo-exp.github.io/optimax/']){
 test('every generated page has a progressive theme control and prefixed early script at '+url,async()=>{
  await withBuild(url,async output=>{
   const base=new URL(url).pathname;
   assert.ok((await htmlFiles(output)).length>3);
   for(const file of await htmlFiles(output)){
    const html=await readFile(file,'utf8'),document=parseHTML(html).document;
    assert.doesNotMatch(document.body.textContent,/Created by Shafqat Ullah/i,file);
    const actions=document.querySelector('.header-actions'),button=actions?.querySelector('#theme-toggle');
    assert.ok(button,file+' needs a theme toggle');
    assert.equal(actions.lastElementChild,button,'theme control must be rightmost');
    assert.ok(actions.querySelector('.nav-cta'));
    assert.equal(button.tagName,'BUTTON');assert.equal(button.type,'button');
    assert.equal(button.getAttribute('aria-label'),'Dark theme');assert.equal(button.getAttribute('aria-pressed'),'false');
    assert.ok(button.hasAttribute('hidden'),'hide the control until the theme behavior is bound');
    assert.match(button.textContent,/Theme/);assert.ok(button.querySelector('[aria-hidden="true"]'));
    const theme=document.querySelector('head script[src="'+base+'assets/theme.js"]');
    assert.ok(theme);for(const attribute of ['type','defer','async'])assert.equal(theme.hasAttribute(attribute),false);
    assert.ok(html.indexOf(theme.outerHTML)<html.indexOf('<link rel="stylesheet"'),'theme must be chosen before CSS');
    assert.ok(document.querySelector('script[type="module"][src="'+base+'assets/client.js"]'));
   }
   assert.equal(await readFile(join(output,'assets/theme.js'),'utf8'),await readFile(join(site,'src/theme.js'),'utf8'));
  });
 });
}
test('homepage explains useful parallel work, inspectable proof, objections and the first session in order',async()=>{
 await withBuild('https://optimax.alolabs.dev/',async output=>{
  const document=parseHTML(await readFile(join(output,'index.html'),'utf8')).document;
  assert.equal(document.querySelector('h1').textContent,'Put the right models to work, together.');
  assert.match(document.querySelector('.hero-deck').textContent,/quality-based model routing with safe parallel work/);
  const visual=document.querySelector('.routing-visual');
  assert.match(visual.textContent,/independent|Independent/);assert.match(visual.textContent,/waiting/i);
  assert.match(visual.textContent,/illustrative/i);assert.ok(visual.querySelectorAll('.route-row').length>=3);
  const ordered=['how-it-works','mechanism','proof','benefits','questions','install','next-step'];
  const actual=[...document.querySelectorAll('main [id]')].map(element=>element.id).filter(id=>ordered.includes(id));
  assert.deepEqual(actual,ordered);
  assert.match(document.querySelector('#how-it-works').textContent,/maximize useful parallelization/i);
  assert.match(document.querySelector('#mechanism').textContent,/verified capacity/i);
  for(const heading of ['Scope the work','Route and run together','Review, accept and learn'])assert.ok([...document.querySelectorAll('#mechanism h3')].some(e=>e.textContent===heading));
  const proof=document.querySelector('#proof');assert.ok(proof.querySelectorAll('a[href^="https://github.com/alo-exp/optimax/"]').length>=3);
  assert.match(proof.textContent,/Codex/);assert.match(proof.textContent,/Claude/);assert.match(proof.textContent,/static|limited/);
  const questions=document.querySelector('#questions').textContent;
  for(const expected of [/Orchestrator/,/cheapest/i,/capacity/i,/conflict/i,/opaque/i,/off/i])assert.match(questions,expected);
  assert.match(document.querySelector('#install').textContent,/MIT/);assert.match(document.querySelector('#install').textContent,/usage charges/i);
  assert.deepEqual([...document.querySelectorAll('[data-install-panel]')].map(e=>e.textContent),[
   'codex plugin marketplace add alo-labs/agent-plugins\ncodex plugin add optimax@alo-labs-codex',
   '/plugin marketplace add alo-labs/agent-plugins\n/plugin install optimax@alo-labs'
  ]);
  assert.ok(document.querySelector('#copy-install'));assert.ok(document.querySelector('#copy-status'));
  const next=document.querySelector('#next-step');
  assert.match(next.textContent,/Start your first session/);
  assert.ok(next.querySelector('a[href="/help/first-session/"]'));assert.ok(next.querySelector('a[href="/help/session-controls/"]'));
 });
});
test('parallel work guide describes bounded dispatch and makes helper evidence limits explicit',async()=>{
 await withBuild('https://optimax.alolabs.dev/',async output=>{
  assert.ok((await htmlFiles(output)).includes(join(output,'help/parallel-work/index.html')),'parallel work must have its own generated help page');
  const html=await readFile(join(output,'help/parallel-work/index.html'),'utf8'),text=parseHTML(html).document.body.textContent;
  for(const expected of [/ready/i,/dependenc/i,/verified capacity/i,/conflict/i,/greedy/i,/snapshot/i,/global.*optimum|globally optimal/i])assert.match(text,expected);
  const index=JSON.parse(await readFile(join(output,'search-index.json'),'utf8'));
  assert.ok(index.some(row=>row.url==='/help/parallel-work/'));
 });
});
