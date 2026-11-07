import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,writeFile,rm,mkdir,symlink,readFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createPreviewServer} from '../scripts/preview.mjs';
import {fileURLToPath} from 'node:url';
import {prepareBuildFixture} from '../e2e/fixture.mjs';

test('preview serves only public build beneath its deployment prefix with correct MIME and 404', async()=>{
 const root=await mkdtemp(join(tmpdir(),'optimax-preview-'));
 await writeFile(join(root,'index.html'),'<h1>Public build</h1>');
 await writeFile(join(root,'404.html'),'<h1>Not found</h1>');
 await writeFile(join(root,'theme.js'),'export {};');
 await writeFile(join(root,'font.woff2'),'font');
 const server=createPreviewServer({root,prefix:'/optimax/'});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const base=`http://127.0.0.1:${server.address().port}`;
 try {
  const home=await fetch(base+'/optimax/'); assert.equal(home.status,200); assert.match(await home.text(),/Public build/);
  const js=await fetch(base+'/optimax/theme.js'); assert.match(js.headers.get('content-type'),/javascript/);
  const font=await fetch(base+'/optimax/font.woff2'); assert.equal(font.headers.get('content-type'),'font/woff2');
  for(const path of ['/','/optimax/missing/','/optimax/%2e%2e%2fpackage.json','/optimax/%ZZ']){
   const response=await fetch(base+path); assert.equal(response.status,404,path); assert.match(await response.text(),/Not found/);
  }
 } finally {await new Promise(resolve=>server.close(resolve));await rm(root,{recursive:true,force:true});}
});


test('preview rejects file, directory, index and fallback symlinks outside its public root',async()=>{
 const workspace=await mkdtemp(join(tmpdir(),'optimax-boundary-')),root=join(workspace,'dist'),outside=join(workspace,'outside');
 await mkdir(root);await mkdir(outside);await writeFile(join(outside,'index.html'),'OUTSIDE_BUILD_SENTINEL');await writeFile(join(workspace,'outside.txt'),'OUTSIDE_BUILD_SENTINEL');
 await writeFile(join(root,'index.html'),'INSIDE');await symlink(join(workspace,'outside.txt'),join(root,'linked.txt'));await symlink(outside,join(root,'directory'));
 await mkdir(join(root,'index-link'));await symlink(join(outside,'index.html'),join(root,'index-link/index.html'));await symlink(join(workspace,'outside.txt'),join(root,'404.html'));
 const server=createPreviewServer({root,prefix:'/optimax/'});await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const base=`http://127.0.0.1:${server.address().port}/optimax/`;
 try{for(const path of ['linked.txt','directory/','index-link/','missing']){const response=await fetch(base+path);assert.equal(response.status,404,path);assert.doesNotMatch(await response.text(),/OUTSIDE_BUILD_SENTINEL/,path);}assert.equal(await (await fetch(base)).text(),'INSIDE');}
 finally{await new Promise(resolve=>server.close(resolve));await rm(workspace,{recursive:true,force:true});}
});

for(const siteUrl of ['https://optimax.alolabs.dev/','https://alo-exp.github.io/optimax/'])test(`actual build and preview agree on deployed asset paths for ${siteUrl}`,async()=>{
 const workspace=await mkdtemp(join(tmpdir(),'optimax-built-prefix-'));
 try{
  await prepareBuildFixture(fileURLToPath(new URL('../',import.meta.url)),workspace);
  execFileSync(process.execPath,['build.js'],{cwd:workspace,env:{...process.env,SITE_URL:siteUrl},stdio:'pipe'});
  const root=join(workspace,'dist'),html=await readFile(join(root,'index.html'),'utf8'),prefix=new URL(siteUrl).pathname;
  const server=createPreviewServer({root});await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  try{const base=`http://127.0.0.1:${server.address().port}`;assert.equal((await fetch(base+prefix)).status,200,'actual build home must resolve at its advertised prefix');
   const assets=[...html.matchAll(/(?:src|href)="([^"]+[.](?:js|css))"/g)].map(match=>match[1]);assert.ok(assets.length>=3,'actual build exposes JS and CSS assets');
   for(const asset of assets)assert.equal((await fetch(base+asset)).status,200,asset);
  }finally{await new Promise(resolve=>server.close(resolve));}
 }finally{await rm(workspace,{recursive:true,force:true});}
});
