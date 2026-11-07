import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,cp,readFile,readdir,writeFile,mkdir,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,dirname} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import {parseHTML} from 'linkedom';
import {buildContent} from '../src/content.js';
import {attachSearch,searchIndex} from '../src/search.js';

const site=dirname(dirname(fileURLToPath(import.meta.url)));
async function fixture(){
 const root=await mkdtemp(join(tmpdir(),'optimax-pages-'));
 for(const name of ['build.js','src','content','public','package.json'])await cp(join(site,name),join(root,name),{recursive:true});
 return root;
}
function build(root,url){
 const env={...process.env};delete env.SITE_URL;
 if(url!==undefined)env.SITE_URL=url;
 return execFileSync(process.execPath,['build.js'],{cwd:root,env,encoding:'utf8',stdio:'pipe'});
}
async function files(root){
 const entries=await readdir(root,{withFileTypes:true});
 return (await Promise.all(entries.map(async entry=>entry.isDirectory()?files(join(root,entry.name)):[join(root,entry.name)]))).flat();
}
for(const url of [undefined,'https://optimax.alolabs.dev/','https://alo-exp.github.io/optimax']){
 test('complete generated graph resolves under '+(url||'default Pages URL'),async()=>{
  const root=await fixture();const deployed=(url||'https://alo-exp.github.io/optimax/').replace(/\/?$/,'/');const base=new URL(deployed).pathname;
  try{
   build(root,url);
   const output=join(root,'dist'),generated=await files(output),htmlFiles=generated.filter(p=>p.endsWith('.html'));
   assert.ok(!generated.some(p=>p.includes('/dist/optimax/')),'prefix must not become an output directory');
   const source=JSON.parse(await readFile(join(root,'content/articles.json'),'utf8'));
   assert.equal(htmlFiles.length,source.articles.length+3);
   for(const file of htmlFiles){
    const relative=file.slice(output.length+1),logical=relative==='index.html'?'':relative.replace(/index\.html$/,'');
    const pageUrl=new URL(logical,deployed);const {document}=parseHTML(await readFile(file,'utf8'));
    assert.equal(document.querySelector('link[rel=canonical]').getAttribute('href'),pageUrl.href);
    assert.equal(document.querySelector('meta[property="og:url"]').getAttribute('content'),pageUrl.href);
    assert.equal(document.querySelector('meta[name="site-base"]').getAttribute('content'),base);
    for(const element of document.querySelectorAll('[href],[src]')){
     const attr=element.hasAttribute('href')?'href':'src',href=element.getAttribute(attr);
     if(/^https:\/\//.test(href))continue;
     assert.ok(href.startsWith(base)||href.startsWith('#'),relative+' contains unprefixed '+href);
     const target=new URL(href,pageUrl);assert.ok(target.pathname.startsWith(base));
     const path=target.pathname.slice(base.length),destination=join(output,path.endsWith('/')?path+'index.html':path||'index.html');
     const data=await readFile(destination,'utf8');
     if(target.hash){const targetDoc=parseHTML(data).document;assert.ok(targetDoc.getElementById(target.hash.slice(1)),relative+' missing anchor '+href)}
    }
   }
   const index=JSON.parse(await readFile(join(output,'search-index.json'),'utf8'));
   for(const row of index){
    assert.match(row.url,/^\/help\/[a-z0-9-]+\/$/);
    const document=parseHTML(await readFile(join(output,row.url.slice(1),'index.html'),'utf8')).document;
    assert.ok(document.getElementById(row.anchor));
   }
   const robots=await readFile(join(output,'robots.txt'),'utf8');
   assert.ok(robots.split('\n').includes('Allow: '+base));
   assert.match(robots,new RegExp('Sitemap: '+deployed.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'sitemap\\.xml'));
   const sitemap=await readFile(join(output,'sitemap.xml'),'utf8');
   const locations=[...sitemap.matchAll(/<loc>(.*?)<\/loc>/g)].map(m=>m[1]);
   assert.deepEqual(locations,[deployed,deployed+'help/',...source.articles.map(a=>deployed+'help/'+a.slug+'/')]);
   const errorDoc=parseHTML(await readFile(join(output,'404.html'),'utf8')).document;
   const deep=new URL('help/missing/nested/',deployed);
   for(const element of errorDoc.querySelectorAll('[src],link[rel=stylesheet],a.brand,.error-page a')){
    const href=element.getAttribute('src')||element.getAttribute('href');
    assert.ok(new URL(href,deep).pathname.startsWith(base));
   }
   assert.equal(errorDoc.querySelector('.error-page a').getAttribute('href'),base);
  }finally{await rm(root,{recursive:true,force:true})}
 });
}
test('invalid deployment URLs fail before deleting an existing build',async()=>{
 const root=await fixture();
 try{
  await mkdir(join(root,'dist'));await writeFile(join(root,'dist','keep.txt'),'previous build');
  for(const url of ['','http://example.com/','https://user:pass@example.com/','https://example.com/?q=x','https://example.com/#x','https://example.com/../escape/','https://example.com/%2e%2e/','https://example.com/a//b/','https://example.com/a\\b/','javascript:alert(1)','//example.com/']){
   assert.throws(()=>build(root,url),/SITE_URL/,'must reject '+JSON.stringify(url));
   assert.equal(await readFile(join(root,'dist','keep.txt'),'utf8'),'previous build');
  }
 }finally{await rm(root,{recursive:true,force:true})}
});
test('article links respect the deployment boundary and leave external URLs and code literal',()=>{
 const code='fetch("/help/guide/")',external='https://example.com/help/?x=1#start';
 const data={articles:[{slug:'guide',title:'Guide',description:'Guide',sections:[{heading:'Start',code:{text:code},links:[{label:'Internal',href:'/help/guide/#start'},{label:'External',href:external}]}]}]};
 const {pages,index}=buildContent(data,{basePath:'/optimax/'});
 const document=parseHTML(pages[0].html).document;
 assert.deepEqual([...document.querySelectorAll('a')].map(a=>a.getAttribute('href')),['/optimax/help/guide/#start',external]);
 assert.equal(document.querySelector('code').textContent,code);assert.equal(index[0].url,'/help/guide/');
 for(const href of ['//evil.example/','/\\evil.example/','/help/../escape/','/%2f%2fevil.example/']){
  const bad=structuredClone(data);bad.articles[0].sections[0].links=[{label:'Bad',href}];
  assert.throws(()=>buildContent(bad,{basePath:'/optimax/'}),/Invalid link/);
 }
});
test('search keeps logical URLs strict while mouse and Enter links use the trusted base',()=>{
 const {document,Event}=parseHTML('<input><button></button><p></p><ul></ul>');
 const input=document.querySelector('input'),results=document.querySelector('ul'),status=document.querySelector('p'),clear=document.querySelector('button');
 const row={page:'Guide',title:'Install',text:'install',url:'/help/guide/',anchor:'start'};
 const unsafe=['/optimax/help/guide/','//evil.example/help/guide/','/help/../guide/','https://evil.example/help/guide/','/help/guide/?x=1'];
 assert.equal(searchIndex([row,...unsafe.map(url=>({...row,url}))],'install').length,1);
 attachSearch({input,results,status,clear,document,index:[row],basePath:'/optimax/'});
 input.value='install';input.dispatchEvent(new Event('input'));
 assert.equal(results.querySelector('a').getAttribute('href'),'/optimax/help/guide/#start');
 for(const key of ['ArrowDown','Enter']){const event=new Event('keydown');Object.defineProperty(event,'key',{value:key});input.dispatchEvent(event)}
 assert.equal(document.location,'/optimax/help/guide/#start');
 for(const basePath of ['//evil.example/','/../','/optimax//','/optimax/%2f/']){
  assert.throws(()=>attachSearch({input,results,status,clear,document,index:[row],basePath}),/base path/i);
 }
});
test('actual client fetches index from configured root and renders prefixed navigation',async()=>{
 const old={document:globalThis.document,navigator:globalThis.navigator,fetch:globalThis.fetch};
 const root=await fixture();
 try{
  for(const base of ['/optimax/','/']){
   build(root,base==='/'?'https://optimax.alolabs.dev/':undefined);
   const html=await readFile(join(root,'dist/help/index.html'),'utf8');
   const {document,Event}=parseHTML(html);
   globalThis.document=document;
   Object.defineProperty(globalThis,'navigator',{value:{},configurable:true,writable:true});
   const requested=[];globalThis.fetch=async url=>{requested.push(url);return {ok:true,json:async()=>[{page:'Guide',title:'Install',text:'install',url:'/help/guide/',anchor:'start'}]}};
   await import(pathToFileURL(join(root,'dist/assets/client.js')).href+'?pages-test='+encodeURIComponent(base));
   await new Promise(resolve=>setImmediate(resolve));
   assert.deepEqual(requested,[base+'search-index.json']);
   const input=document.querySelector('input');input.value='install';input.dispatchEvent(new Event('input'));
   assert.equal(document.querySelector('#search-results a').getAttribute('href'),base+'help/guide/#start');
   for(const key of ['ArrowDown','Enter']){const event=new Event('keydown');Object.defineProperty(event,'key',{value:key});input.dispatchEvent(event)}
   assert.equal(document.location,base+'help/guide/#start');
   globalThis.document=parseHTML(html).document;
   globalThis.fetch=async()=>({ok:false});
   await import(pathToFileURL(join(root,'dist/assets/client.js')).href+'?unavailable='+encodeURIComponent(base));
   await new Promise(resolve=>setImmediate(resolve));
   assert.match(globalThis.document.querySelector('#search-status').textContent,/Search is unavailable/);
  }
 }finally{
  globalThis.document=old.document;globalThis.fetch=old.fetch;
  Object.defineProperty(globalThis,'navigator',{value:old.navigator,configurable:true,writable:true});
  await rm(root,{recursive:true,force:true});
 }
});
