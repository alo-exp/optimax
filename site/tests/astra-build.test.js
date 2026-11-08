import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,cp,readFile,rm,writeFile,access,mkdir} from 'node:fs/promises';
import {readFileSync,existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {parseHTML} from 'linkedom';
const site=dirname(dirname(fileURLToPath(import.meta.url)));

for(const deployed of ['https://optimax.alolabs.dev/','https://alo-exp.github.io/optimax/'])test('Astra publishes an isolated prefixed route at '+deployed,async()=>{
 const root=await mkdtemp(join(tmpdir(),'optimax-astra-route-'));
 try{
  for(const name of ['build.js','src','content','public','variants','package.json'])await cp(join(site,name),join(root,name),{recursive:true});
  await writeFile(join(root,'variants/astra.html'),'<!doctype html><html><head><link rel="stylesheet" href="./style.css"></head><body><h1>Astra fixture</h1><a href="{{BASE}}help/">Help</a><script src="{{BASE}}versions/theme.js"></script><script type="module" src="{{BASE}}versions/client.js"></script></body></html>');
  await writeFile(join(root,'variants/astra.css'),'.fixture{background-image:url("{{BASE}}assets/fonts/figtree-latin-400-normal.woff2")}');
  execFileSync(process.execPath,['build.js'],{cwd:root,env:{...process.env,SITE_URL:deployed},stdio:'pipe'});
  const base=new URL(deployed).pathname;
  let exists=true;try{await access(join(root,'dist/versions/astra/index.html'))}catch{exists=false}
  assert.equal(exists,true,'build must publish the new Astra route');
  const html=await readFile(join(root,'dist/versions/astra/index.html'),'utf8'),document=parseHTML(html).document;
  assert.equal(document.querySelector('h1').textContent,'Astra fixture');
  assert.equal(document.querySelector('a').getAttribute('href'),base+'help/');
  for(const name of ['theme.js','client.js'])assert.ok(document.querySelector('script[src="'+base+'versions/'+name+'"]'));
  assert.equal(await readFile(join(root,'dist/versions/astra/style.css'),'utf8'),'.fixture{background-image:url("'+base+'assets/fonts/figtree-latin-400-normal.woff2")}');
  assert.equal(await readFile(join(root,'dist/index.html'),'utf8'),(await readFile(join(site,'src/homepage.html'),'utf8')).replaceAll('{{BASE}}',base).replaceAll('{{ROOT_URL}}',deployed),'production homepage is byte-preserved');
 }finally{await rm(root,{recursive:true,force:true});}
});

const documentFor=html=>parseHTML(html.replace(/<br\s*\/?>/gi,' ')).document;
const text=element=>element.textContent.replace(/\s+/g,' ').trim();
function snapshot(document){
 return{
  copy:[...document.body.querySelectorAll('h1,h2,h3,p,summary')].map(element=>[element.tagName,text(element)]),
  states:[...document.body.querySelectorAll('strong,small')].map(text),
  links:[...document.querySelectorAll('a[href]')].filter(element=>!element.matches('nav .preview-return')).map(element=>[element.getAttribute('href'),text(element)]),
  commands:[...document.querySelectorAll('code')].map(element=>element.textContent),
  sections:[...document.querySelectorAll('main > section[id]')].map(element=>element.id)
 };
}
for(const deployed of ['https://optimax.alolabs.dev/','https://alo-exp.github.io/optimax/'])test('Astra preserves current production copy, metadata and controls at '+deployed,async()=>{
 const root=await mkdtemp(join(tmpdir(),'optimax-astra-content-'));
 try{
  for(const name of ['build.js','src','content','public','variants','package.json'])await cp(join(site,name),join(root,name),{recursive:true});
  execFileSync(process.execPath,['build.js'],{cwd:root,env:{...process.env,SITE_URL:deployed},stdio:'pipe'});
  const base=new URL(deployed).pathname,pageURL=new URL('versions/astra/',deployed),path=join(root,'dist/versions/astra/index.html');
  let exists=true;try{await access(path)}catch{exists=false}assert.equal(exists,true,'Astra content contract requires the published preview route');
  const html=await readFile(path,'utf8'),document=documentFor(html),production=documentFor((await readFile(join(site,'src/homepage.html'),'utf8')).replaceAll('{{BASE}}',base).replaceAll('{{ROOT_URL}}',deployed));
  assert.equal(document.querySelectorAll('a.preview-return').length,1,'only one Circuit return link may be added');
  const back=document.querySelector('nav .preview-return');assert.ok(back);assert.equal(back.getAttribute('href'),base);assert.equal(text(back),'Circuit');
  assert.deepEqual(snapshot(document),snapshot(production),'preserve every heading, paragraph, FAQ, strong/small state, code byte, link label/destination and section order');
  assert.equal(document.querySelectorAll('p').length,44);assert.equal(document.querySelectorAll('code').length,8);assert.equal(document.querySelectorAll('#questions details').length,7);assert.equal(document.querySelectorAll('h1').length,1);
  assert.equal(document.title,production.title);for(const selector of ['meta[name="description"]','meta[property="og:title"]','meta[property="og:description"]'])assert.equal(document.querySelector(selector)?.content,production.querySelector(selector)?.content,selector+' copy');
  assert.match(document.querySelector('meta[name="robots"]').content,/noindex/);assert.equal(new URL(document.querySelector('link[rel="canonical"]').getAttribute('href'),pageURL).href,pageURL.href);assert.equal(new URL(document.querySelector('meta[property="og:url"]').content,pageURL).href,pageURL.href);
  assert.equal(document.querySelector('link[rel="stylesheet"]').getAttribute('href'),'./style.css');
  const early=document.querySelector('script[src="'+base+'versions/theme.js"]');assert.ok(early);assert.equal(early.hasAttribute('type'),false);assert.ok(html.indexOf(early.outerHTML)<html.indexOf('<link rel="stylesheet"'));
  assert.ok(document.querySelector('script[type="module"][src="'+base+'versions/client.js"]'));
  for(const selector of ['#theme-toggle','#copy-install','#copy-status','[data-install-tab]','[data-install-panel]']){
   const controls=[...document.querySelectorAll(selector)],expected=[...production.querySelectorAll(selector)];assert.equal(controls.length,expected.length,selector+' count');
   for(let i=0;i<controls.length;i++)for(const attr of ['type','aria-label','aria-pressed','aria-controls','aria-live','hidden','data-install-tab','data-install-panel'])assert.equal(controls[i].getAttribute(attr),expected[i].getAttribute(attr),selector+' '+attr);
  }
  assert.doesNotMatch(html,/\{\{[^}]+\}\}|CMF|\.impeccable|\/Users\/|\[lean-ctx/);assert.match(html,/<\/html>\s*$/i);
  const css=await readFile(join(root,'dist/versions/astra/style.css'),'utf8');assert.doesNotMatch(css,/\{\{[^}]+\}\}|\.impeccable|\/Users\/|\[lean-ctx|https?:\/\/fonts\./);
 }finally{await rm(root,{recursive:true,force:true});}
});

test('Astra Fahkwang display font is pinned, licensed and identical to Fontsource',()=>{
 const pkg=JSON.parse(readFileSync(join(site,'package.json'),'utf8'));
 assert.equal(pkg.devDependencies['@fontsource/fahkwang'],'5.3.0','Astra display font dependency must be pinned to 5.3.0');
 const locked=JSON.parse(readFileSync(join(site,'package-lock.json'),'utf8')).packages['node_modules/@fontsource/fahkwang'];
 assert.equal(locked.version,'5.3.0');assert.equal(locked.license,'OFL-1.1');
 const name='fahkwang-latin-600-normal.woff2',local=readFileSync(join(site,'public/fonts',name));
 assert.equal(local.subarray(0,4).toString(),'wOF2');assert.ok(local.length>1000);assert.deepEqual(local,readFileSync(join(site,'node_modules/@fontsource/fahkwang/files',name)));
 assert.equal(readFileSync(join(site,'public/fonts/fahkwang-OFL.txt'),'utf8'),readFileSync(join(site,'node_modules/@fontsource/fahkwang/LICENSE'),'utf8'));assert.match(readFileSync(join(site,'public/fonts/fahkwang-OFL.txt'),'utf8'),/SIL OPEN FONT LICENSE/i);
});
for(const deployed of ['https://optimax.alolabs.dev/','https://alo-exp.github.io/optimax/'])test('Astra publishes only its contracted local photograph at '+deployed,async()=>{
 const root=await mkdtemp(join(tmpdir(),'optimax-astra-image-'));
 try{
  for(const name of ['build.js','src','content','public','variants','package.json'])await cp(join(site,name),join(root,name),{recursive:true});
  await mkdir(join(root,'public/images'),{recursive:true});const expected=Buffer.from('RIFF-ASTRA-ISOLATED-ASSET-FIXTURE');await writeFile(join(root,'public/images/astra-exposure.webp'),expected);await writeFile(join(root,'public/images/development-provenance.txt'),'private fixture metadata');
  execFileSync(process.execPath,['build.js'],{cwd:root,env:{...process.env,SITE_URL:deployed},stdio:'pipe'});
  const asset=join(root,'dist/assets/images/astra-exposure.webp');assert.equal(existsSync(asset),true,'build must publish the contracted local Astra image');assert.deepEqual(await readFile(asset),expected,'photograph bytes must be copied intact');assert.equal(existsSync(join(root,'dist/assets/images/development-provenance.txt')),false,'only the contracted asset is public');
 }finally{await rm(root,{recursive:true,force:true});}
});
