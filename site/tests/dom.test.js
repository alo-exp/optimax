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
 const link=results.querySelector('a');let focused=false;link.focus=()=>{focused=true};
 const down=new Event('keydown');Object.defineProperty(down,'key',{value:'ArrowDown'});input.dispatchEvent(down);
 assert.equal(focused,true);assert.equal(input.hasAttribute('aria-activedescendant'),false);
 assert.equal(results.firstElementChild.hasAttribute('role'),false);assert.equal(results.firstElementChild.hasAttribute('aria-selected'),false);
 clear.dispatchEvent(new Event('click'));assert.equal(results.children.length,0);assert.equal(status.textContent,'');
});

test('keyboard navigation selects and wraps actual results, including after clear',()=>{
 const {document,Event}=parseHTML('<input><button>Clear</button><p></p><ul></ul>');
 const input=document.querySelector('input'),clear=document.querySelector('button'),status=document.querySelector('p'),results=document.querySelector('ul');
 const index=['one','two','three'].map(title=>({page:'Guide',url:'/help/guide/',anchor:title,title,text:'install'}));
 attachSearch({input,clear,status,results,document,index});
 const type=value=>{input.value=value;input.dispatchEvent(new Event('input'))};
 const key=(target,value)=>{const event=new Event('keydown',{bubbles:true,cancelable:true});Object.defineProperty(event,'key',{value});target.dispatchEvent(event)};
 let focused;const links=()=>Array.from(results.querySelectorAll('a'));const track=()=>links().forEach((link,i)=>{link.focus=()=>{focused=i}});
 type('install');track();key(input,'ArrowUp');assert.equal(focused,2);key(links()[2],'ArrowUp');assert.equal(focused,1);key(links()[1],'ArrowDown');assert.equal(focused,2);key(links()[2],'ArrowDown');assert.equal(focused,0);key(links()[0],'ArrowUp');assert.equal(focused,2);
 let inputFocused=false;input.focus=()=>{inputFocused=true};key(links()[2],'Escape');assert.equal(inputFocused,true);assert.equal(input.value,'');assert.equal(results.children.length,0);
 type('install');track();key(input,'ArrowDown');assert.equal(focused,0);
 type('no matches');key(input,'ArrowUp');key(input,'ArrowDown');assert.equal(results.children.length,0);
});
