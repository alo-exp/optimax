import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,cp,readFile,rm} from 'node:fs/promises';
import {readFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {parseHTML} from 'linkedom';
const site=dirname(dirname(fileURLToPath(import.meta.url)));
const documentFor=html=>parseHTML(html.replace(/<br\s*\/?>/gi,' ')).document;
const text=element=>element.textContent.replace(/\s+/g,' ').trim();
function snapshot(document,base){
 return{
  copy:[...document.body.querySelectorAll('h1,h2,h3,p,summary')].map(element=>[element.tagName,text(element)]),
  states:[...document.body.querySelectorAll('strong,small')].map(text),
  links:[...document.querySelectorAll('a[href]')].filter(element=>!element.getAttribute('href').startsWith(base+'versions/')&&!(element.matches('nav .preview-return')&&element.getAttribute('href')===base&&text(element)==='Circuit')).map(element=>[element.getAttribute('href'),text(element)]),
  questions:[...document.querySelectorAll('#questions details')].map(element=>({question:text(element.querySelector('summary')),answer:text(element.querySelector('p'))})),
  commands:[...document.querySelectorAll('[data-install-panel]')].map(element=>element.textContent),
  sections:[...document.querySelectorAll('main > section[id]')].map(element=>element.id)
 };
}
for(const deployed of ['https://optimax.alolabs.dev/','https://alo-exp.github.io/optimax/'])test('Continuum publishes current production copy, controls and preview metadata at '+deployed,async()=>{
 const root=await mkdtemp(join(tmpdir(),'optimax-continuum-'));
 try{
  for(const name of ['build.js','src','content','public','variants','package.json'])await cp(join(site,name),join(root,name),{recursive:true});
  execFileSync(process.execPath,['build.js'],{cwd:root,env:{...process.env,SITE_URL:deployed},stdio:'pipe'});
  const base=new URL(deployed).pathname,pageURL=new URL('versions/continuum/',deployed);
  const html=await readFile(join(root,'dist/versions/continuum/index.html'),'utf8'),document=documentFor(html);
  const production=documentFor((await readFile(join(site,'src/homepage.html'),'utf8')).replaceAll('{{BASE}}',base).replaceAll('{{ROOT_URL}}',deployed));
  assert.deepEqual(snapshot(document,base),snapshot(production,base),'all current product copy, ordering, links, states, seven FAQs and command bytes must match production');
  assert.equal(document.querySelectorAll('#questions details').length,7);assert.equal(document.querySelectorAll('h1').length,1);
  assert.equal(document.title,production.title);for(const selector of ['meta[name="description"]','meta[property="og:title"]','meta[property="og:description"]'])assert.equal(document.querySelector(selector)?.content,production.querySelector(selector)?.content,selector+' copy');
  assert.match(document.querySelector('meta[name="robots"]').content,/noindex/);assert.equal(new URL(document.querySelector('link[rel="canonical"]').getAttribute('href'),pageURL).href,pageURL.href);
  assert.equal(new URL(document.querySelector('meta[property="og:url"]').content,pageURL).href,pageURL.href);
  assert.equal(document.querySelector('link[rel="stylesheet"]').getAttribute('href'),'./style.css');
  const early=document.querySelector('script[src="'+base+'versions/theme.js"]');assert.ok(early);assert.equal(early.hasAttribute('type'),false);assert.ok(html.indexOf(early.outerHTML)<html.indexOf('<link rel="stylesheet"'));
  assert.ok(document.querySelector('script[type="module"][src="'+base+'versions/client.js"]'));assert.equal(document.querySelectorAll('#theme-toggle').length,1);assert.equal(document.querySelectorAll('[data-install-tab]').length,2);
  assert.equal(document.querySelectorAll('a.preview-return').length,1,'exactly one preview-return exception is allowed');const back=document.querySelector('nav .preview-return[href="'+base+'"]');assert.ok(back,'comparison must reach the live selected Circuit homepage');assert.equal(text(back),'Circuit');
  assert.doesNotMatch(html,/\{\{[^}]+\}\}|CMF|\.impeccable|\/Users\//);
  assert.equal(html.includes('[lean-ctx'),false,'tool read notices must not appear in the public preview');
  assert.equal(/<\/html>\s*$/i.test(html),true,'preview HTML must end at its closing html tag');
  const css=await readFile(join(root,'dist/versions/continuum/style.css'),'utf8');assert.equal(css.includes('[lean-ctx'),false,'tool read notices must not appear in public CSS');
 }finally{await rm(root,{recursive:true,force:true});}
});
test('Figtree supply is pinned, licensed and byte-identical to Fontsource',()=>{
 const pkg=JSON.parse(readFileSync(join(site,'package.json'),'utf8')),locked=JSON.parse(readFileSync(join(site,'package-lock.json'),'utf8')).packages['node_modules/@fontsource/figtree'];
 assert.equal(pkg.devDependencies['@fontsource/figtree'],'5.3.0');assert.equal(locked.version,'5.3.0');assert.equal(locked.license,'OFL-1.1');
 for(const weight of [400,700]){const name=`figtree-latin-${weight}-normal.woff2`;assert.deepEqual(readFileSync(join(site,'public/fonts',name)),readFileSync(join(site,'node_modules/@fontsource/figtree/files',name)));}
 assert.equal(readFileSync(join(site,'public/fonts/figtree-OFL.txt'),'utf8'),readFileSync(join(site,'node_modules/@fontsource/figtree/LICENSE'),'utf8'));
});
