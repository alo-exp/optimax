import test from 'node:test';
import assert from 'node:assert/strict';
import {parseHTML} from 'linkedom';
import {attachSearch} from '../src/search.js';
test('real DOM search exposes results, keyboard state and safe text',()=>{
 const {document,Event}=parseHTML('<input><button>Clear</button><p></p><ul></ul>');
 const input=document.querySelector('input'),clear=document.querySelector('button'),status=document.querySelector('p'),results=document.querySelector('ul');
 const index=[{page:'Guide',url:'/help/guide/',anchor:'start',title:'<img src=x onerror=alert(1)>',text:'install'}];
 attachSearch({input,clear,status,results,document,index});
 input.value='install';input.dispatchEvent(new Event('input'));
 assert.equal(results.querySelectorAll('img').length,0);
 assert.equal(results.querySelector('a').textContent,index[0].title);
 assert.equal(results.querySelector('a').getAttribute('href'),'/help/guide/#start');
 const down=new Event('keydown');Object.defineProperty(down,'key',{value:'ArrowDown'});input.dispatchEvent(down);
 assert.equal(input.getAttribute('aria-activedescendant'),'search-result-0');
 assert.equal(results.firstElementChild.getAttribute('aria-selected'),'true');
 clear.dispatchEvent(new Event('click'));assert.equal(results.children.length,0);assert.equal(status.textContent,'');
});

test('keyboard navigation selects and wraps actual results, including after clear',()=>{
 const {document,Event}=parseHTML('<input><button>Clear</button><p></p><ul></ul>');
 const input=document.querySelector('input'),clear=document.querySelector('button'),status=document.querySelector('p'),results=document.querySelector('ul');
 const index=['one','two','three'].map(title=>({page:'Guide',url:'/help/guide/',anchor:title,title,text:'install'}));
 attachSearch({input,clear,status,results,document,index});
 const type=value=>{input.value=value;input.dispatchEvent(new Event('input'))};
 const key=value=>{const event=new Event('keydown');Object.defineProperty(event,'key',{value});input.dispatchEvent(event)};
 const selected=i=>{assert.equal(input.getAttribute('aria-activedescendant'),`search-result-${i}`);assert.deepEqual(Array.from(results.children,el=>el.getAttribute('aria-selected')),index.map((_,j)=>String(i===j)))};
 type('install');key('ArrowUp');selected(2);key('ArrowUp');selected(1);key('ArrowDown');selected(2);key('ArrowDown');selected(0);key('ArrowUp');selected(2);
 clear.dispatchEvent(new Event('click'));assert.equal(input.getAttribute('aria-activedescendant'),'');assert.equal(results.children.length,0);
 type('install');key('ArrowDown');selected(0);
 type('no matches');key('ArrowUp');key('ArrowDown');assert.equal(results.children.length,0);assert.equal(input.getAttribute('aria-activedescendant'),'');
});
