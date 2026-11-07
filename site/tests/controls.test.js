import test from 'node:test'; import assert from 'node:assert/strict'; import {installControls} from '../src/controls.js';
class E {constructor(){this.listeners={};this.attrs={};this.hidden=false;this.textContent=''} addEventListener(k,f){this.listeners[k]=f} setAttribute(k,v){this.attrs[k]=v} click(){return this.listeners.click()}}
test('tabs select the matching panel and copy reports success or failure',async()=>{
 const tabs=[new E(),new E()],panels=[new E(),new E()],button=new E(),status=new E(); panels[1].textContent='command';
 installControls({tabs,panels,button,status,clipboard:{writeText:async x=>assert.equal(x,'command')}});
 tabs[1].click(); assert.equal(panels[0].hidden,true); assert.equal(panels[1].hidden,false); assert.equal(tabs[1].attrs['aria-pressed'],'true');
 await button.click(); assert.match(status.textContent,/copied/i);
 installControls({tabs,panels,button,status,clipboard:{writeText:async()=>{throw Error('denied')}}}); await button.click(); assert.match(status.textContent,/copy manually/i);
});


test('generated install panel switches and copies exact marketplace commands', async t=>{
 const {mkdtemp,symlink,readFile,rm}=await import('node:fs/promises');
 const {tmpdir}=await import('node:os'); const {join,resolve}=await import('node:path');
 const {execFileSync}=await import('node:child_process'); const {parseHTML}=await import('linkedom');
 const dir=await mkdtemp(join(tmpdir(),'optimax-site-test-')); t.after(()=>rm(dir,{recursive:true,force:true}));
 for(const name of ['src','content']) await symlink(resolve(name),join(dir,name),'dir');
 execFileSync(process.execPath,[resolve('build.js')],{cwd:dir});
 const {document,Event}=parseHTML(await readFile(join(dir,'dist/index.html'),'utf8'));
 const group=document.querySelector('[aria-label="Installation platform"]');
 assert.equal(group.getAttribute('role'),'group');
 const tabs=[...group.querySelectorAll('button')],panels=[...document.querySelectorAll('[data-install-panel]')];
 const expected=['codex plugin marketplace add alo-labs/agent-plugins\ncodex plugin add optimax@alo-labs-codex','/plugin marketplace add alo-labs/agent-plugins\n/plugin install optimax@alo-labs'];
 assert.deepEqual(panels.map(p=>p.textContent),expected);
 assert.match(document.querySelector('#install').textContent,/terminal commands/i);
 assert.match(document.querySelector('#install').textContent,/commands in Claude Code/i);
 assert.ok(document.querySelector('#install a[href^="/help/"]'));
 let copied; const button=document.querySelector('#copy-install');
 installControls({tabs,panels,button,status:document.querySelector('#copy-status'),clipboard:{writeText:async text=>{copied=text}}});
 assert.deepEqual(tabs.map(tab=>tab.getAttribute('aria-pressed')),['true','false']);
 button.dispatchEvent(new Event('click')); await new Promise(resolve=>setImmediate(resolve)); assert.equal(copied,expected[0]);
 tabs[1].dispatchEvent(new Event('click'));
 assert.deepEqual(tabs.map(tab=>tab.getAttribute('aria-pressed')),['false','true']);
 assert.equal(panels[0].hidden,true); assert.equal(panels[1].hidden,false);
 button.dispatchEvent(new Event('click')); await new Promise(resolve=>setImmediate(resolve)); assert.equal(copied,expected[1]);
});
