import {cp,symlink} from 'node:fs/promises';
import {join} from 'node:path';

export async function prepareBuildFixture(site,workspace){
 for(const entry of ['build.js','src','content','public'])await cp(join(site,entry),join(workspace,entry),{recursive:true});
 await symlink(join(site,'node_modules'),join(workspace,'node_modules'),'dir');
}
