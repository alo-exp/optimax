import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,cp,readFile,readdir,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {parseHTML} from 'linkedom';

const site=dirname(dirname(fileURLToPath(import.meta.url)));
async function htmlFiles(directory){
 const entries=await readdir(directory,{withFileTypes:true});
 return (await Promise.all(entries.map(entry=>entry.isDirectory()?htmlFiles(join(directory,entry.name)):entry.name.endsWith('.html')?[join(directory,entry.name)]:[]))).flat();
}
for(const url of ['https://optimax.alolabs.dev/','https://alo-exp.github.io/optimax/']){
 test('every generated page declares a shipped SVG favicon at '+url,async()=>{
  const root=await mkdtemp(join(tmpdir(),'optimax-favicon-'));
  try{
   for(const name of ['build.js','src','content','public','package.json'])await cp(join(site,name),join(root,name),{recursive:true});
   execFileSync(process.execPath,['build.js'],{cwd:root,env:{...process.env,SITE_URL:url},stdio:'pipe'});
   const output=join(root,'dist'),base=new URL(url).pathname;
   for(const page of await htmlFiles(output)){
    const {document}=parseHTML(await readFile(page,'utf8')),links=document.querySelectorAll('head link[rel="icon"]');
    assert.equal(links.length,1,'every generated head must explicitly declare one favicon: '+page);
    assert.equal(links[0].getAttribute('type'),'image/svg+xml');
    assert.equal(links[0].getAttribute('href'),base+'favicon.svg');
   }
   const bytes=await readFile(join(output,'favicon.svg'));
   assert.deepEqual(bytes,await readFile(join(root,'public/favicon.svg')));
   const svg=parseHTML(bytes.toString()).document.querySelector('svg');
   assert.ok(svg,'favicon must contain an SVG root');
   assert.equal(svg.getAttribute('xmlns'),'http://www.w3.org/2000/svg');
   assert.equal(svg.getAttribute('viewBox'),'0 0 32 32');
   assert.ok(bytes.length<2048,'favicon should remain a compact vector asset');
   assert.doesNotMatch(bytes.toString(),/<(?:script|image|foreignObject)\b/i);
  }finally{await rm(root,{recursive:true,force:true})}
 });
}
