import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {parseHTML} from 'linkedom';
function setup({saved,blocked=false,ready='loading'}={}){
 const {document}=parseHTML('<html><head><meta name="theme-color" content="stale"></head><body><button id="theme-toggle" hidden aria-label="Dark theme"></button></body></html>');
 Object.defineProperty(document,'readyState',{value:ready});const listeners=new Map(),writes=[];
 const storage={getItem:()=>saved??null,setItem:(key,value)=>{if(blocked)throw new Error('blocked');writes.push([key,value])}};
 const window={getComputedStyle:()=>({getPropertyValue:()=>document.documentElement.dataset.theme==='light'?'#faf4ef':'#111324'}),addEventListener:(type,fn)=>listeners.set(type,fn)};
 Object.defineProperty(window,'localStorage',{get(){if(blocked)throw new Error('blocked');return storage}});
 runInNewContext(readFileSync(new URL('../src/homepage-theme.js',import.meta.url),'utf8'),{document,window});
 return{document,storage,writes,button:document.getElementById('theme-toggle'),ready:()=>document.dispatchEvent(new document.defaultView.Event('DOMContentLoaded')),event:event=>listeners.get('storage')?.(event)};
}
for(const saved of [undefined,'light','invalid'])test('homepage theme uses '+(saved==='light'?'saved light':'default dark')+' before stylesheet readiness',()=>{
 const env=setup({saved});assert.equal(env.document.documentElement.dataset.theme,saved==='light'?'light':'dark');env.ready();assert.equal(env.button.hidden,false);assert.equal(env.button.getAttribute('aria-label'),'Dark theme');assert.equal(env.document.querySelector('meta').content,saved==='light'?'#faf4ef':'#111324');
});
test('homepage theme toggles despite blocked storage and reflects CSS palette',()=>{
 const env=setup({blocked:true});env.ready();env.button.click();assert.equal(env.document.documentElement.dataset.theme,'light');assert.equal(env.button.getAttribute('aria-pressed'),'false');assert.equal(env.document.querySelector('meta').content,'#faf4ef');env.button.click();assert.equal(env.document.documentElement.dataset.theme,'dark');
});
test('homepage theme follows valid same-storage cross-tab choices and resets to dark on clear',()=>{
 const env=setup({saved:'light',ready:'complete'});env.event({key:'optimax-theme',newValue:'dark',storageArea:{}});assert.equal(env.document.documentElement.dataset.theme,'light');env.event({key:'optimax-theme',newValue:'invalid',storageArea:env.storage});assert.equal(env.document.documentElement.dataset.theme,'light');env.event({key:'optimax-theme',newValue:'dark',storageArea:env.storage});assert.equal(env.document.documentElement.dataset.theme,'dark');env.event({key:'optimax-theme',newValue:'light',storageArea:env.storage});assert.equal(env.document.documentElement.dataset.theme,'light');env.event({key:null,newValue:null,storageArea:env.storage});assert.equal(env.document.documentElement.dataset.theme,'dark');assert.deepEqual(env.writes,[]);
});
