import test from 'node:test';
import assert from 'node:assert/strict';
import {parseHTML} from 'linkedom';

const index=[{page:'Guide',url:'/help/guide/',anchor:'start',title:'Install guide',text:'install'}];
let run=0;
async function setup(t){
 const {document,Event}=parseHTML('<meta name="site-base" content="/"><input id="help-search" disabled><button id="search-clear" disabled>Clear</button><p id="search-status"></p><ul id="search-results"></ul>');
 const previous={document:globalThis.document,fetch:globalThis.fetch};
 let resolveFetch,rejectFetch;
 const pending=new Promise((resolve,reject)=>{resolveFetch=resolve;rejectFetch=reject});
 globalThis.document=document;globalThis.fetch=()=>pending;
 t.after(()=>{for(const [key,value] of Object.entries(previous)){if(value===undefined)delete globalThis[key];else globalThis[key]=value}});
 await import(`../src/client.js?loading-test=${++run}`);
 const input=document.querySelector('#help-search'),clear=document.querySelector('#search-clear'),status=document.querySelector('#search-status'),results=document.querySelector('#search-results');
 return {input,clear,status,results,Event,resolveFetch,rejectFetch};
}
const settled=()=>new Promise(resolve=>setImmediate(resolve));
test('search renders a query entered while the index is loading',async t=>{
 const s=await setup(t);
 assert.equal(s.input.disabled,false);assert.equal(s.clear.disabled,false);assert.match(s.status.textContent,/loading search/i);
 s.input.value='install';s.input.dispatchEvent(new s.Event('input'));
 s.resolveFetch({ok:true,json:async()=>index});await settled();
 assert.equal(s.results.querySelector('a')?.textContent,'Install guide');
 assert.equal(s.status.textContent,'1 result');
 let renders=0;const replace=s.results.replaceChildren.bind(s.results);s.results.replaceChildren=(...args)=>{renders++;return replace(...args)};
 s.input.value='guide';s.input.dispatchEvent(new s.Event('input'));
 assert.equal(renders,1,'one input event should cause one render');
});
test('clear works while loading and the resolved index does not restore the query',async t=>{
 const s=await setup(t);
 s.input.value='install';s.input.dispatchEvent(new s.Event('input'));s.clear.dispatchEvent(new s.Event('click'));
 assert.equal(s.input.value,'');
 s.resolveFetch({ok:true,json:async()=>index});await settled();
 assert.equal(s.input.value,'');assert.equal(s.results.children.length,0);assert.equal(s.status.textContent,'');
});
test('clear remains operable after index loading fails and keeps the unavailable status',async t=>{
 const s=await setup(t);
 s.rejectFetch(new Error('network unavailable'));await settled();
 assert.equal(s.status.textContent,'Search is unavailable. Browse the articles below.');
 s.input.value='install';s.clear.dispatchEvent(new s.Event('click'));
 assert.equal(s.input.value,'');assert.equal(s.status.textContent,'Search is unavailable. Browse the articles below.');
});

for(const [name,data] of [['object',{}],['null row',[null]],['missing text',[{page:'Guide',url:'/help/guide/',anchor:'start',title:'Install'}]],['non-string title',[{...index[0],title:4}]]])test('invalid index '+name+' leaves search unavailable without crashing',async t=>{
 const s=await setup(t);s.resolveFetch({ok:true,json:async()=>data});await settled();
 assert.equal(s.status.textContent,'Search is unavailable. Browse the articles below.');
 assert.equal(s.input.disabled,true);assert.equal(s.clear.disabled,false);
 s.input.value='install';s.clear.dispatchEvent(new s.Event('click'));assert.equal(s.input.value,'');
});
