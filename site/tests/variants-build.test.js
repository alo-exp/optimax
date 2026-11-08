import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,cp,mkdir,writeFile,readFile,readdir,rm} from 'node:fs/promises';
import {readFileSync,existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {runInNewContext} from 'node:vm';
import {parseHTML} from 'linkedom';
import {installControls} from '../src/controls.js';
const site=dirname(dirname(fileURLToPath(import.meta.url)));

for(const url of ['https://optimax.alolabs.dev/','https://alo-exp.github.io/optimax/']){
 test('preview templates publish isolated routes and shared runtime at '+url,async()=>{
  const root=await mkdtemp(join(tmpdir(),'optimax-variants-'));
  try{
   for(const name of ['build.js','src','content','public','package.json'])await cp(join(site,name),join(root,name),{recursive:true});
   await mkdir(join(root,'variants'));
   for(const name of ['circuit']){
    await writeFile(join(root,'variants',name+'.html'),`<!doctype html><html><head><link rel="icon" type="image/svg+xml" href="{{BASE}}favicon.svg"><script src="{{BASE}}versions/theme.js"></script><link rel="stylesheet" href="./style.css"></head><body><h1>${name} preview</h1><a href="{{BASE}}help/">Help</a><script type="module" src="{{BASE}}versions/client.js"></script></body></html>`);
    await writeFile(join(root,'variants',name+'.css'),`:root{--bg:${name==='circuit'?'#001122':'#332211'}}`);
   }
   for(const name of ['theme.js','client.js'])await writeFile(join(root,'variants',name),'// shared '+name);
   execFileSync(process.execPath,['build.js'],{cwd:root,env:{...process.env,SITE_URL:url},stdio:'pipe'});
   const base=new URL(url).pathname;
   for(const name of ['circuit']){
    const path=join(root,'dist/versions',name,'index.html');
    assert.ok(existsSync(path),'build must publish '+name+' preview route');
    const html=await readFile(path,'utf8');assert.match(html,new RegExp(name+' preview'));assert.doesNotMatch(html,/\{\{BASE\}\}/);
    assert.ok(html.includes(`href="${base}help/"`));assert.ok(html.includes(`src="${base}versions/theme.js"`));
    assert.equal(await readFile(join(root,'dist/versions',name,'style.css'),'utf8'),await readFile(join(root,'variants',name+'.css'),'utf8'));
   }
   for(const name of ['theme.js','client.js'])assert.equal(await readFile(join(root,'dist/versions',name),'utf8'),'// shared '+name);
   assert.doesNotMatch(await readFile(join(root,'dist/index.html'),'utf8'),/circuit preview/);
  }finally{await rm(root,{recursive:true,force:true});}
 });
}

for(const deployed of ['https://optimax.alolabs.dev/','https://alo-exp.github.io/optimax/'])test('actual preview assets and self canonicals stay beneath '+deployed,async()=>{
 const root=await mkdtemp(join(tmpdir(),'optimax-actual-variants-'));
 try{
  for(const name of ['build.js','src','content','public','variants','package.json'])await cp(join(site,name),join(root,name),{recursive:true});
  execFileSync(process.execPath,['build.js'],{cwd:root,env:{...process.env,SITE_URL:deployed},stdio:'pipe'});
  const output=join(root,'dist'),base=new URL(deployed).pathname;
  assert.deepEqual((await readdir(join(output,'versions'),{withFileTypes:true})).filter(e=>e.isDirectory()).map(e=>e.name).sort(),['circuit']);
  for(const name of ['circuit']){
   const pageURL=new URL('versions/'+name+'/',deployed),html=await readFile(join(output,'versions',name,'index.html'),'utf8'),document=parseHTML(html).document;
   assert.match(document.querySelector('meta[name="robots"]').content,/noindex/);assert.equal(new URL(document.querySelector('link[rel="canonical"]').getAttribute('href'),pageURL).href,pageURL.href);
   assert.doesNotMatch(html,/\{\{BASE\}\}/);assert.equal(document.querySelectorAll('#theme-toggle').length,1);
   const early=document.querySelector('script[src="'+base+'versions/theme.js"]');assert.ok(early);assert.equal(early.hasAttribute('type'),false);assert.ok(html.indexOf(early.outerHTML)<html.indexOf('<link rel="stylesheet"'));
   assert.ok(document.querySelector('script[type="module"][src="'+base+'versions/client.js"]'));
   for(const element of document.querySelectorAll('[href],[src]')){
    const href=element.getAttribute('href')??element.getAttribute('src'),target=new URL(href,pageURL);if(target.origin!==pageURL.origin)continue;
    assert.ok(target.pathname.startsWith(base),name+' leaves deployment base: '+href);const path=target.pathname.slice(base.length),destination=join(output,path.endsWith('/')?path+'index.html':path);assert.ok(existsSync(destination),name+' missing asset: '+href);
    if(target.hash)assert.ok(parseHTML(await readFile(destination,'utf8')).document.getElementById(decodeURIComponent(target.hash.slice(1))),name+' missing fragment: '+href);
   }
   const css=await readFile(join(output,'versions',name,'style.css'),'utf8');assert.doesNotMatch(css,/\{\{BASE\}\}|https?:\/\/fonts\./);
   for(const [,raw]of css.matchAll(/url\(\s*['"]?([^)'"\s]+)['"]?\s*\)/g)){if(raw.startsWith('data:'))continue;const target=new URL(raw,new URL('style.css',pageURL));assert.equal(target.origin,pageURL.origin);assert.ok(target.pathname.startsWith(base));assert.ok(existsSync(join(output,target.pathname.slice(base.length))),name+' missing CSS asset '+raw);}
  }
 }finally{await rm(root,{recursive:true,force:true});}
});

test('preview font supply contains pinned Latin weights and each open font license',()=>{
 for(const family of ['sora']){
  for(const weight of [400,700]){const path=join(site,'public/fonts',`${family}-latin-${weight}-normal.woff2`);assert.ok(existsSync(path),'preview font must ship: '+path);const bytes=readFileSync(path);assert.equal(bytes.subarray(0,4).toString(),'wOF2');assert.ok(bytes.length>1000);}
  assert.match(readFileSync(join(site,'public/fonts',family+'-OFL.txt'),'utf8'),/SIL OPEN FONT LICENSE/i);
 }
});


test('preview client binds real install controls and reports clipboard rejection',async()=>{
 const {document,Event}=parseHTML('<html><body><button data-install-tab>Codex</button><button data-install-tab>Claude</button><code data-install-panel>codex command</code><code data-install-panel hidden>claude command</code><button id="copy-install">Copy</button><span id="copy-status"></span></body></html>');
 const copied=[],clipboard={writeText:async value=>copied.push(value)},source=readFileSync(join(site,'variants/client.js'),'utf8');assert.match(source,/from ['"]\.\.\/assets\/controls\.js['"]/);
 runInNewContext(source.replace(/^import[^\n]+\n/,''),{document,navigator:{clipboard},installControls});
 const tabs=[...document.querySelectorAll('[data-install-tab]')],panels=[...document.querySelectorAll('[data-install-panel]')],button=document.getElementById('copy-install'),status=document.getElementById('copy-status');
 for(let i=0;i<2;i++){tabs[i].dispatchEvent(new Event('click'));assert.equal(tabs[i].getAttribute('aria-pressed'),'true');assert.equal(panels[i].hidden,false);assert.equal(panels[1-i].hidden,true);button.dispatchEvent(new Event('click'));await new Promise(resolve=>setImmediate(resolve));assert.equal(copied[i],i?'claude command':'codex command');assert.equal(status.textContent,'Copied to clipboard.');}
 clipboard.writeText=async()=>{throw new Error('denied')};button.dispatchEvent(new Event('click'));await new Promise(resolve=>setImmediate(resolve));assert.equal(status.textContent,'Copy unavailable. Select the command and copy manually.');
});

function setup({saved,blocked=false,ready='loading'}={}){
 const {document}=parseHTML('<html><head><meta name="theme-color" content="stale"></head><body><button id="theme-toggle" hidden aria-label="Dark theme"></button></body></html>');
 Object.defineProperty(document,'readyState',{value:ready});const listeners=new Map(),writes=[];
 const storage={getItem:()=>saved??null,setItem:(key,value)=>{if(blocked)throw new Error('blocked');writes.push([key,value])}};
 const window={getComputedStyle:()=>({getPropertyValue:()=>document.documentElement.dataset.theme==='light'?'#faf4ef':'#111324'}),addEventListener:(type,fn)=>listeners.set(type,fn)};
 Object.defineProperty(window,'localStorage',{get(){if(blocked)throw new Error('blocked');return storage}});
 const path=join(site,'variants/theme.js');runInNewContext(existsSync(path)?readFileSync(path,'utf8'):'',{document,window});
 return{document,storage,writes,button:document.getElementById('theme-toggle'),ready:()=>document.dispatchEvent(new document.defaultView.Event('DOMContentLoaded')),event:event=>listeners.get('storage')?.(event)};
}
for(const saved of [undefined,'light','invalid'])test('preview theme uses '+(saved==='light'?'saved light':'default dark')+' before stylesheet readiness',()=>{
 const env=setup({saved});assert.equal(env.document.documentElement.dataset.theme,saved==='light'?'light':'dark');env.ready();assert.equal(env.button.hidden,false);assert.equal(env.button.getAttribute('aria-label'),'Dark theme');assert.equal(env.document.querySelector('meta').content,saved==='light'?'#faf4ef':'#111324');
});
test('preview theme toggles despite blocked storage and reflects CSS palette',()=>{
 const env=setup({blocked:true});env.ready();env.button.click();assert.equal(env.document.documentElement.dataset.theme,'light');assert.equal(env.button.getAttribute('aria-pressed'),'false');assert.equal(env.document.querySelector('meta').content,'#faf4ef');env.button.click();assert.equal(env.document.documentElement.dataset.theme,'dark');
});
test('preview theme follows valid same-storage cross-tab choices and resets to dark on clear',()=>{
 const env=setup({saved:'light',ready:'complete'});env.event({key:'optimax-theme',newValue:'dark',storageArea:{}});assert.equal(env.document.documentElement.dataset.theme,'light');env.event({key:'optimax-theme',newValue:'invalid',storageArea:env.storage});assert.equal(env.document.documentElement.dataset.theme,'light');env.event({key:'optimax-theme',newValue:'dark',storageArea:env.storage});assert.equal(env.document.documentElement.dataset.theme,'dark');env.event({key:'optimax-theme',newValue:'light',storageArea:env.storage});assert.equal(env.document.documentElement.dataset.theme,'light');env.event({key:null,newValue:null,storageArea:env.storage});assert.equal(env.document.documentElement.dataset.theme,'dark');assert.deepEqual(env.writes,[]);
});
