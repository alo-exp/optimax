import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,cp,readFile,rm} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {parseHTML} from 'linkedom';
const site=dirname(dirname(fileURLToPath(import.meta.url)));

for(const deployed of ['https://optimax.alolabs.dev/','https://alo-exp.github.io/optimax/'])test('production homepage adopts Circuit without changing Help at '+deployed,async()=>{
 const root=await mkdtemp(join(tmpdir(),'optimax-production-home-'));
 try{
  for(const name of ['build.js','src','content','public','package.json'])await cp(join(site,name),join(root,name),{recursive:true});
  execFileSync(process.execPath,['build.js'],{cwd:root,env:{...process.env,SITE_URL:deployed},stdio:'pipe'});
  const base=new URL(deployed).pathname,output=join(root,'dist');
  const html=await readFile(join(output,'index.html'),'utf8'),document=parseHTML(html).document;
  assert.ok(document.querySelector(`link[rel="stylesheet"][href="${base}assets/homepage.css"]`),'selected Circuit homepage must publish its own stylesheet');
  const css=await readFile(join(output,'assets/homepage.css'),'utf8');
  assert.match(css,/font-family:\s*['"]Sora['"]/);assert.match(css,/--bg:\s*#081525/i);assert.match(css,/--accent:\s*#4D87FF/i);
  assert.equal(document.querySelector('link[rel="canonical"]').getAttribute('href'),deployed);
  assert.doesNotMatch(document.querySelector('meta[name="robots"]')?.content||'',/noindex/i);
  assert.equal(document.querySelector('meta[name="site-base"]').content,base);
  assert.equal(document.querySelectorAll('h1').length,1);assert.equal(document.querySelector('h1').textContent,'Optimize Cost, Maximize Parallel Work');
  assert.equal(document.querySelector('.hero-deck').textContent,'Maximize parallelization, minimize cost');
  assert.equal(document.querySelectorAll('.parallel-tasks > li').length,3);assert.equal(document.querySelectorAll('.acceptance-boundary').length,1);
  assert.equal(document.querySelectorAll('[data-install-tab]').length,2);assert.equal(document.querySelectorAll('[data-install-panel]').length,2);assert.ok(document.querySelector('#copy-status[role="status"]'));
  assert.ok(document.querySelector('a[href="'+base+'help/session-controls/"]'));assert.match(document.querySelector('#questions').textContent,/\$optimax off/);
  assert.equal(document.querySelectorAll('a[href*="/versions/"]').length,0,'production funnel must not contain preview comparison navigation');
  assert.doesNotMatch(html,/\{\{[^}]+\}\}|CMF|\.impeccable|\/Users\//);
  for(const tag of ['meta[name="description"]','meta[property="og:description"]','meta[property="og:title"]','meta[property="og:url"]'])assert.ok(document.querySelector(tag)?.content,tag+' must describe production');
  assert.equal(document.querySelector('meta[property="og:url"]').content,deployed);
  const copy=JSON.parse(await readFile(join(site,'tests/fixtures/homepage-copy.json'),'utf8')),text=element=>element.textContent.replace(/\s+/g,' ').trim(),texts=selector=>[...document.querySelectorAll(selector)].map(text);
  assert.equal(document.title,copy.title,'production title must use the accepted copy');assert.equal(document.querySelector('meta[name="description"]').content,copy.description);assert.equal(document.querySelector('meta[property="og:description"]').content,copy.description);assert.equal(document.querySelector('meta[property="og:title"]').content,copy.title);
  for(const [selector,expected]of Object.entries(copy.headings))assert.equal(text(document.querySelector(selector)),expected,selector);
  for(const [selector,expected]of Object.entries(copy.paragraphs))assert.deepEqual(texts(selector),expected,selector);
  for(const [selector,expected]of Object.entries(copy.metadata))assert.equal(text(document.querySelector(selector+' .metadata')),expected,selector+' caption');
  assert.deepEqual(texts('#questions summary'),copy.questions);assert.deepEqual(texts('#questions details p'),copy.answers);assert.equal(document.querySelectorAll('#questions details').length,7);
  assert.deepEqual(texts('.parallel-tasks strong'),copy.tasks);assert.deepEqual(texts('.parallel-tasks small'),copy.states);assert.equal(text(document.querySelector('.acceptance-boundary strong')),'Integrate accepted results');assert.equal(text(document.querySelector('.acceptance-boundary small')),'WAITING / REVIEW & DEPENDENCIES');
  assert.deepEqual(texts('#mechanism article h3'),copy.mechanism);assert.deepEqual(texts('#benefits article h3'),copy.benefits);assert.deepEqual(texts('a[href="#install"]'),['Install Optimax','Install Optimax']);
  assert.equal(document.querySelector('.hero-deck').nextElementSibling,document.querySelector('.hero-audience'),'audience follows the approved subtitle');
  assert.ok(document.querySelector('.questions-list details:last-of-type + .differentiation'));assert.equal(text(document.querySelector('.differentiation h3')),'Look at the whole job');
  for(const command of ['$optimax on','$optimax off','$optimax status','/optimax:optimax on','/optimax:optimax off','/optimax:optimax status'])assert.ok(texts('code').includes(command),'session command must remain exact: '+command);
  const early=document.querySelector('script[src="'+base+'assets/homepage-theme.js"]');assert.ok(early);assert.equal(early.hasAttribute('type'),false);assert.ok(html.indexOf(early.outerHTML)<html.indexOf('<link rel="stylesheet"'));
  assert.ok(document.querySelector('script[type="module"][src="'+base+'assets/client.js"]'));
  assert.equal(await readFile(join(output,'assets/homepage-theme.js'),'utf8'),await readFile(join(site,'src/homepage-theme.js'),'utf8'));
  for(const element of document.querySelectorAll('[href],[src]')){
   const raw=element.getAttribute('href')??element.getAttribute('src'),target=new URL(raw,deployed);if(target.origin!==new URL(deployed).origin)continue;
   assert.ok(target.pathname.startsWith(base),'homepage URL escapes base: '+raw);const path=target.pathname.slice(base.length),destination=join(output,path.endsWith('/')?path+'index.html':path||'index.html');assert.ok(existsSync(destination),'homepage asset missing: '+raw);
   if(target.hash)assert.ok(parseHTML(await readFile(destination,'utf8')).document.getElementById(decodeURIComponent(target.hash.slice(1))),'homepage fragment missing: '+raw);
  }
  for(const [,raw]of css.matchAll(/url\(\s*['"]?([^)'"\s]+)['"]?\s*\)/g)){const target=new URL(raw,deployed+'assets/homepage.css');assert.equal(target.origin,new URL(deployed).origin);assert.ok(target.pathname.startsWith(base));assert.ok(existsSync(join(output,target.pathname.slice(base.length))),'homepage font missing: '+raw);}
  const help=parseHTML(await readFile(join(output,'help/index.html'),'utf8')).document;
  assert.ok(help.querySelector('link[href="'+base+'assets/style.css"]'));assert.ok(help.querySelector('script[src="'+base+'assets/theme.js"]'));
  assert.equal(await readFile(join(output,'assets/style.css'),'utf8'),await readFile(join(site,'src/style.css'),'utf8'));
  assert.equal(await readFile(join(output,'assets/theme.js'),'utf8'),await readFile(join(site,'src/theme.js'),'utf8'));
 }finally{await rm(root,{recursive:true,force:true});}
});
