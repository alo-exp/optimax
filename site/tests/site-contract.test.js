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
  for(const name of ['build.js','src','content','public','package.json'])await cp(join(site,name),join(root,name),{recursive:true});
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
   for(const file of (await htmlFiles(output)).filter(file=>!file.startsWith(join(output,'versions')+'/'))){
    const html=await readFile(file,'utf8'),document=parseHTML(html).document;
    assert.doesNotMatch(document.body.textContent,/Created by Shafqat Ullah/i,file);
    const actions=document.querySelector('.header-actions'),button=actions?.querySelector('#theme-toggle');
    assert.ok(button,file+' needs a theme toggle');
    assert.equal(actions.lastElementChild,button,'theme control must be rightmost');
    assert.ok(actions.querySelector('.nav-cta'));
    assert.equal(button.tagName,'BUTTON');assert.equal(button.type,'button');
    assert.equal(document.documentElement.getAttribute('data-theme'),'dark','static HTML must start dark even without JavaScript');
    assert.equal(document.querySelector('meta[name="theme-color"]').content,file===join(output,'index.html')?'#081525':'#082820');
    assert.equal(button.getAttribute('aria-label'),'Dark theme');assert.equal(button.getAttribute('aria-pressed'),'true');
    assert.ok(button.hasAttribute('hidden'),'hide the control until the theme behavior is bound');
    assert.match(button.textContent,/Theme/);assert.ok(button.querySelector('[aria-hidden="true"]'));
    const theme=document.querySelector('head script[src="'+base+'assets/'+(file===join(output,'index.html')?'homepage-theme.js':'theme.js')+'"]');
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
  assert.equal(document.querySelector('h1').textContent,'Optimize Cost, Maximize Parallel Work');
  assert.equal(document.querySelector('.hero-deck').textContent,'The right models. Independent tasks. Reviewed results.');
  assert.ok(document.querySelector('.hero-support'),'the wide hero field needs its full supporting explanation');
  assert.equal(document.querySelector('.hero-support').textContent,'Optimax is an open-source plugin that helps your AI agent delegate well. Run independent tasks together, choose helper models by task complexity and reviewed results, and check each result before accepting it.');
  const visual=document.querySelector('.routing-visual');
  assert.match(visual.textContent,/independent/i);assert.match(visual.textContent,/waiting/i);
  assert.equal(visual.getAttribute('aria-describedby'),'plan-note');
  assert.match(document.querySelector('#plan-note').textContent,/dependencies are accepted, capacity is verified and their work does not conflict/);
  assert.match(document.querySelector('.parallel-plan').textContent,/illustrative/i);
  const assignments=visual.querySelector('ul.parallel-tasks');
  assert.ok(assignments,'independent work belongs to an unordered parallel group');
  assert.deepEqual([...assignments.children].map(task=>task.querySelector('strong').textContent),['Investigate the reported defect','Build an unrelated feature','Review a completed change']);
  assert.equal(assignments.children.length,3);
  assert.equal(visual.querySelectorAll('ol').length,0,'independent work must not imply sequential steps');
  const acceptance=visual.querySelector('.acceptance-boundary');
  assert.ok(acceptance);assert.match(acceptance.textContent,/Integrate accepted results/);
  assert.ok(!assignments.contains(acceptance),'acceptance spans the independent group');
  const ordered=['how-it-works','mechanism','proof','benefits','questions','install','next-step'];
  const actual=[...document.querySelectorAll('main [id]')].map(element=>element.id).filter(id=>ordered.includes(id));
  assert.deepEqual(actual,ordered);
  assert.match(document.querySelector('#how-it-works').textContent,/what can run together/i);
  assert.match(document.querySelector('#mechanism').textContent,/verified capacity/i);
  for(const heading of ['Define what a good result looks like','Match the helper and run ready work','Review the work, then learn from it'])assert.ok([...document.querySelectorAll('#mechanism h3')].some(e=>e.textContent===heading));
  const proof=document.querySelector('#proof');assert.ok(proof.querySelectorAll('a[href^="https://github.com/alo-exp/optimax/"]').length>=3);
  assert.match(proof.textContent,/Codex/);assert.match(proof.textContent,/Claude/);assert.match(proof.textContent,/static|limited/);
  const questions=document.querySelector('#questions').textContent;
  for(const expected of [/chosen session model/i,/cheapest/i,/capacity/i,/shared resources/i,/hidden worker/i,/off/i])assert.match(questions,expected);
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
test('production surfaces use local type assets and keep labels below headings',async()=>{
 await withBuild('https://alo-exp.github.io/optimax/',async output=>{
  const css=await readFile(join(output,'assets/style.css'),'utf8');
  for(const weight of [400,700]){
   const name='mona-sans-latin-'+weight+'-normal.woff2';
   assert.ok((await readFile(join(output,'assets/fonts',name))).length>1000,'publish the local '+weight+' font');
   assert.match(css,new RegExp('url\\(\\s*[\"\\\']?\\./fonts/'+name.replaceAll('.','\\.')+'[\"\\\']?\\s*\\)'));
  }
  assert.match(css,/font-display:\s*swap/);
  for(const file of (await htmlFiles(output)).filter(file=>!file.startsWith(join(output,'versions')+'/'))){
   const document=parseHTML(await readFile(file,'utf8')).document;
   for(const heading of document.querySelectorAll('h1,h2,h3'))assert.ok(!heading.previousElementSibling?.classList.contains('eyebrow'),file+' has a label above a heading');
  }
  const document=parseHTML(await readFile(join(output,'index.html'),'utf8')).document;
  assert.equal(document.querySelector('img,picture,canvas'),null,'the manifest is semantic flat geometry');
  assert.equal(document.querySelectorAll('.hero-field').length,1);
  assert.equal(document.querySelectorAll('.hero-field h1').length,1);
 });
});
test('navigation and document link icons use hidden SVG without changing labels',async()=>{
 await withBuild('https://optimax.alolabs.dev/',async output=>{
  let articleIcons=0;
  const data=JSON.parse(await readFile(join(site,'content/articles.json'),'utf8'));
  const expectedReferences=data.articles.flatMap(article=>article.sections).reduce((sum,section)=>sum+(section.links?.length||0),0);
  for(const file of (await htmlFiles(output)).filter(file=>!file.startsWith(join(output,'versions')+'/'))){
   const document=parseHTML(await readFile(file,'utf8')).document;
   for(const link of document.querySelectorAll('a,button'))assert.doesNotMatch(link.textContent,/[↗→↓⌕⌘✳◐]/,'decorative glyph remains in '+file);
   for(const icon of document.querySelectorAll('svg.icon'))assert.equal(icon.getAttribute('aria-hidden'),'true');
   articleIcons+=document.querySelectorAll('.article-section a svg.icon').length;
  }
  assert.ok(expectedReferences>0);assert.equal(articleIcons,expectedReferences,'every source reference link keeps a consistent drawn icon');
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
