import test from 'node:test'; import assert from 'node:assert/strict'; import {installControls} from '../src/controls.js';
class E {constructor(){this.listeners={};this.attrs={};this.hidden=false;this.textContent=''} addEventListener(k,f){this.listeners[k]=f} setAttribute(k,v){this.attrs[k]=v} click(){return this.listeners.click()}}
test('tabs select the matching panel and copy reports success or failure',async()=>{
 const tabs=[new E(),new E()],panels=[new E(),new E()],button=new E(),status=new E(); panels[1].textContent='command';
 installControls({tabs,panels,button,status,clipboard:{writeText:async x=>assert.equal(x,'command')}});
 tabs[1].click(); assert.equal(panels[0].hidden,true); assert.equal(panels[1].hidden,false); assert.equal(tabs[1].attrs['aria-pressed'],'true');
 await button.click(); assert.match(status.textContent,/copied/i);
 installControls({tabs,panels,button,status,clipboard:{writeText:async()=>{throw Error('denied')}}}); await button.click(); assert.match(status.textContent,/copy manually/i);
});

test('platform changes clear feedback and invalidate pending copies even after switching back', async()=>{
 const tabs=[new E(),new E()],panels=[new E(),new E()],button=new E(),status=new E();
 let resolveCopy; const pending=new Promise(resolve=>{resolveCopy=resolve});
 installControls({tabs,panels,button,status,clipboard:{writeText:()=>pending}});
 status.textContent='Copied to clipboard.'; tabs[1].click(); assert.equal(status.textContent,'');
 const copy=button.click(); tabs[0].click(); tabs[1].click(); resolveCopy(); await copy;
 assert.equal(status.textContent,'');
});

test('pending copy blocks reentry across platform changes until settled', async()=>{
 const tabs=[new E(),new E()],panels=[new E(),new E()],button=new E(),status=new E();
 panels[0].textContent='codex';panels[1].textContent='claude';
 const attempts=[];let committed='';const clipboard={writeText:text=>new Promise((resolve,reject)=>attempts.push({text,resolve:()=>{committed=text;resolve()},reject}))};
 installControls({tabs,panels,button,status,clipboard});
 const first=button.click();assert.equal(button.disabled,true);assert.equal(attempts.length,1);
 tabs[1].click();await button.click();assert.equal(attempts.length,1,'reentry must not start another write');
 assert.equal(tabs[1].attrs['aria-pressed'],'true');assert.equal(status.textContent,'');
 attempts[0].resolve();await first;assert.equal(committed,'codex');assert.equal(status.textContent,'');assert.equal(button.disabled,false);
 const second=button.click();assert.equal(button.disabled,true);assert.equal(attempts[1].text,'claude');
 attempts[1].resolve();await second;assert.equal(committed,'claude');assert.equal(status.textContent,'Copied to clipboard.');assert.equal(button.disabled,false);
});

test('rejected pending write after a platform change cannot report stale failure',async()=>{
 const tabs=[new E(),new E()],panels=[new E(),new E()],button=new E(),status=new E();let reject;
 installControls({tabs,panels,button,status,clipboard:{writeText:()=>new Promise((_,fail)=>{reject=fail})}});
 const first=button.click();tabs[1].click();reject(Error('denied'));await first;
 assert.equal(status.textContent,'');assert.equal(button.disabled,false);
});

test('copy becomes available after rejection, synchronous throw, or missing clipboard',async()=>{
 for(const clipboard of [{writeText:()=>Promise.reject(Error('denied'))},{writeText:()=>{throw Error('denied')}},undefined]){
  const tabs=[new E(),new E()],panels=[new E(),new E()],button=new E(),status=new E();
  installControls({tabs,panels,button,status,clipboard});await button.click();
  assert.equal(button.disabled,false);assert.match(status.textContent,/copy manually/i);
 }
});


test('generated install panel switches and copies exact marketplace commands', async t=>{
 const {mkdtemp,symlink,readFile,rm}=await import('node:fs/promises');
 const {tmpdir}=await import('node:os'); const {join,resolve}=await import('node:path');
 const {execFileSync}=await import('node:child_process'); const {parseHTML}=await import('linkedom');
 const dir=await mkdtemp(join(tmpdir(),'optimax-site-test-')); t.after(()=>rm(dir,{recursive:true,force:true}));
 for(const name of ['src','content','public']) await symlink(resolve(name),join(dir,name),'dir');
 execFileSync(process.execPath,[resolve('build.js')],{cwd:dir});
 const {document,Event}=parseHTML(await readFile(join(dir,'dist/index.html'),'utf8'));
 const group=document.querySelector('[aria-label="Installation platform"]');
 assert.equal(group.getAttribute('role'),'group');
 const tabs=[...group.querySelectorAll('button')],panels=[...document.querySelectorAll('[data-install-panel]')];
 const expected=['codex plugin marketplace add alo-labs/agent-plugins\ncodex plugin add optimax@alo-labs-codex','/plugin marketplace add alo-labs/agent-plugins\n/plugin install optimax@alo-labs'];
 assert.deepEqual(panels.map(p=>p.textContent),expected);
 assert.match(document.querySelector('#install').textContent,/Codex: run in your terminal/i);
 assert.match(document.querySelector('#install').textContent,/Claude: run inside Claude Code/i);
 assert.equal(document.querySelector('#install a').getAttribute('href'),document.querySelector('meta[name="site-base"]').getAttribute('content')+'help/');
 let copied; const button=document.querySelector('#copy-install');
 tabs.forEach(tab=>tab.disabled=true); button.disabled=true;
 const labels=panels.map(panel=>panel.previousElementSibling);
 assert.deepEqual(labels.map(label=>[label?.hasAttribute('data-install-label'),label?.hasAttribute('hidden')]),[[true,false],[true,false]],'uninitialized commands remain visibly labeled when the client module fails');
 installControls({tabs,panels,button,status:document.querySelector('#copy-status'),clipboard:{writeText:async text=>{copied=text}}});
 assert.ok(tabs.every(tab=>!tab.disabled)); assert.equal(button.disabled,false);
 assert.ok(labels.every(label=>label.hidden),'successful enhancement hides fallback labels');
 assert.deepEqual(panels.map(panel=>panel.hidden),[false,true]);
 assert.deepEqual(panels.map(panel=>panel.parentElement.hidden),[false,true],'inactive command group must be hidden from the accessibility tree');
 assert.deepEqual(tabs.map(tab=>tab.getAttribute('aria-pressed')),['true','false']);
 button.dispatchEvent(new Event('click')); await new Promise(resolve=>setImmediate(resolve)); assert.equal(copied,expected[0]);
 tabs[1].dispatchEvent(new Event('click'));
 assert.deepEqual(tabs.map(tab=>tab.getAttribute('aria-pressed')),['false','true']);
 assert.equal(panels[0].hidden,true); assert.equal(panels[1].hidden,false);
 assert.deepEqual(panels.map(panel=>panel.parentElement.hidden),[true,false],'switching must expose only the selected command group');
 button.dispatchEvent(new Event('click')); await new Promise(resolve=>setImmediate(resolve)); assert.equal(copied,expected[1]);
});
