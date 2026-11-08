import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,cp,mkdir,writeFile,readFile,readdir,rm} from 'node:fs/promises';
import {existsSync,readFileSync,readdirSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,dirname,relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {parseHTML} from 'linkedom';

const site=dirname(dirname(fileURLToPath(import.meta.url)));
const snapshots=JSON.parse(readFileSync(join(site,'tests/fixtures/production-public-sha256.json'),'utf8'));

async function filesIn(directory){
 const entries=await readdir(directory,{withFileTypes:true});
 return(await Promise.all(entries.map(entry=>entry.isDirectory()?filesIn(join(directory,entry.name)):[join(directory,entry.name)]))).flat();
}

test('production sources have no standalone preview ownership',()=>{
 assert.equal(existsSync(join(site,'variants')),false,'preview sources must be retired');
 assert.ok(existsSync(join(site,'src/homepage-theme.js')),'the homepage theme runtime belongs to production');
 const document=parseHTML(readFileSync(join(site,'src/homepage.html'),'utf8')).document;
 assert.equal(document.querySelectorAll('a[href*="versions/"]').length,0,'production navigation must not expose preview routes');
});

test('production keeps its licensed fonts and pinned font dependencies',()=>{
 const expected=['OFL.txt','sora-OFL.txt',...['mona-sans','sora'].flatMap(family=>[400,700].map(weight=>family+'-latin-'+weight+'-normal.woff2'))];
 assert.deepEqual(readdirSync(join(site,'public/fonts')).sort(),expected.sort(),'fonts used by the homepage and Help must ship');
 const pkg=JSON.parse(readFileSync(join(site,'package.json'),'utf8'));
 assert.deepEqual(Object.keys(pkg.devDependencies).filter(name=>name.startsWith('@fontsource/')).sort(),['@fontsource/mona-sans','@fontsource/sora']);
 assert.equal(existsSync(join(site,'public/images/astra-exposure.webp')),false);
});

for(const deployed of Object.keys(snapshots))test('production-only build clears stale previews and preserves every production byte at '+deployed,async()=>{
 const root=await mkdtemp(join(tmpdir(),'optimax-production-only-'));
 try{
  for(const name of ['build.js','src','content','public','package.json'])await cp(join(site,name),join(root,name),{recursive:true});
  // Obsolete inputs must not restore preview publication or own the production runtime.
  await mkdir(join(root,'variants'));
  for(const name of ['circuit.html','circuit.css','theme.js','client.js'])await writeFile(join(root,'variants',name),'/* obsolete preview input */');
  for(const name of ['circuit','prism']){
   await mkdir(join(root,'dist/versions',name),{recursive:true});
   await writeFile(join(root,'dist/versions',name,'stale.html'),'obsolete preview output');
  }
  await writeFile(join(root,'dist/versions/theme.js'),'obsolete shared output');
  execFileSync(process.execPath,['build.js'],{cwd:root,env:{...process.env,SITE_URL:deployed},stdio:'pipe'});
  const output=join(root,'dist'),base=new URL(deployed).pathname;
  assert.equal(existsSync(join(output,'versions')),false,'build must not publish any standalone preview directory');
  const files=(await filesIn(output)).map(file=>relative(output,file)).sort();
  assert.deepEqual(files,Object.keys(snapshots[deployed]).sort(),'fresh output must contain exactly the retained production files');
  assert.equal(existsSync(join(output,'assets/images')),false,'unused image directory must not be published');
  for(const [file,sha256]of Object.entries(snapshots[deployed])){
   assert.equal(createHash('sha256').update(await readFile(join(output,file))).digest('hex'),sha256,'retained production bytes changed: '+file);
  }

  for(const file of files.filter(file=>file.endsWith('.html'))){
   const pageURL=new URL(file==='index.html'?'':file.replace(/index\.html$/,''),deployed);
   const document=parseHTML(await readFile(join(output,file),'utf8')).document;
   for(const element of document.querySelectorAll('[href],[src]')){
    const raw=element.getAttribute('href')??element.getAttribute('src'),target=new URL(raw,pageURL);
    if(target.origin!==pageURL.origin)continue;
    assert.ok(target.pathname.startsWith(base),file+' leaves deployment base: '+raw);
    const path=target.pathname.slice(base.length),destination=join(output,path.endsWith('/')?path+'index.html':path||'index.html');
    assert.ok(existsSync(destination),file+' has missing local target: '+raw);
    if(target.hash)assert.ok(parseHTML(await readFile(destination,'utf8')).document.getElementById(decodeURIComponent(target.hash.slice(1))),file+' has missing fragment: '+raw);
   }
  }
  for(const file of files.filter(file=>file.endsWith('.css'))){
   const css=await readFile(join(output,file),'utf8'),cssURL=new URL(file,deployed);
   for(const [,raw]of css.matchAll(/url\(\s*['"]?([^)'"\s]+)['"]?\s*\)/g)){
    if(raw.startsWith('data:'))continue;
    const target=new URL(raw,cssURL);assert.equal(target.origin,cssURL.origin);assert.ok(target.pathname.startsWith(base));
    assert.ok(existsSync(join(output,target.pathname.slice(base.length))),file+' has missing CSS asset: '+raw);
   }
  }
 }finally{await rm(root,{recursive:true,force:true});}
});
