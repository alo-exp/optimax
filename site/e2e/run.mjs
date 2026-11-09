import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync,spawnSync} from 'node:child_process';
import {prepareBuildFixture} from './fixture.mjs';
import {builtBasePath} from '../scripts/preview.mjs';

// Run the publication candidate first, then exercise distinct alternate bases
// in isolated fixtures without modifying the candidate.
const site=fileURLToPath(new URL('../',import.meta.url));
const candidate=join(site,'dist');
const candidateBase=builtBasePath(candidate);
function runBrowser(root){
 const result=spawnSync(process.execPath,[join(site,'node_modules/@playwright/test/cli.js'),'test'],{cwd:site,env:{...process.env,PREVIEW_ROOT:root},stdio:'inherit'});
 if(result.error)throw result.error;
 return result.status===0?0:result.status||1;
}
console.log(`Rendered deployment acceptance: publication candidate ${candidateBase}`);
process.exitCode=runBrowser(candidate);
if(process.exitCode===0){
 const workspace=await mkdtemp(join(tmpdir(),'optimax-browser-'));
 try{
  await prepareBuildFixture(site,workspace);
  for(const SITE_URL of ['https://optimax.alolabs.dev/','https://alo-exp.github.io/optimax/']){
   if(new URL(SITE_URL).pathname===candidateBase)continue;
   console.log(`Rendered deployment acceptance: ${SITE_URL}`);
   execFileSync(process.execPath,['build.js'],{cwd:workspace,env:{...process.env,SITE_URL},stdio:'inherit'});
   process.exitCode=runBrowser(join(workspace,'dist'));
   if(process.exitCode!==0)break;
  }
 }finally{await rm(workspace,{recursive:true,force:true});}
}
