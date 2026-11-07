import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync,spawnSync} from 'node:child_process';
import {prepareBuildFixture} from './fixture.mjs';

// Each real deployment build gets the same rendered acceptance checks. Keep the
// publication candidate in dist untouched and remove isolated fixtures afterward.
const site=fileURLToPath(new URL('../',import.meta.url));
const workspace=await mkdtemp(join(tmpdir(),'optimax-browser-'));
try{
 await prepareBuildFixture(site,workspace);
 for(const SITE_URL of ['https://optimax.alolabs.dev/','https://alo-exp.github.io/optimax/']){
  console.log(`Rendered deployment acceptance: ${SITE_URL}`);
  execFileSync(process.execPath,['build.js'],{cwd:workspace,env:{...process.env,SITE_URL},stdio:'inherit'});
  const result=spawnSync(process.execPath,[join(site,'node_modules/@playwright/test/cli.js'),'test'],{cwd:site,env:{...process.env,PREVIEW_ROOT:join(workspace,'dist')},stdio:'inherit'});
  if(result.error)throw result.error;
  if(result.status!==0){process.exitCode=result.status||1;break;}
 }
}finally{await rm(workspace,{recursive:true,force:true});}
