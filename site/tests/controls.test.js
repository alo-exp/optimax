import test from 'node:test'; import assert from 'node:assert/strict'; import {installControls} from '../src/controls.js';
class E {constructor(){this.listeners={};this.attrs={};this.hidden=false;this.textContent=''} addEventListener(k,f){this.listeners[k]=f} setAttribute(k,v){this.attrs[k]=v} click(){return this.listeners.click()}}
test('tabs select the matching panel and copy reports success or failure',async()=>{
 const tabs=[new E(),new E()],panels=[new E(),new E()],button=new E(),status=new E(); panels[1].textContent='command';
 installControls({tabs,panels,button,status,clipboard:{writeText:async x=>assert.equal(x,'command')}});
 tabs[1].click(); assert.equal(panels[0].hidden,true); assert.equal(panels[1].hidden,false); assert.equal(tabs[1].attrs['aria-pressed'],'true');
 await button.click(); assert.match(status.textContent,/copied/i);
 installControls({tabs,panels,button,status,clipboard:{writeText:async()=>{throw Error('denied')}}}); await button.click(); assert.match(status.textContent,/copy manually/i);
});
