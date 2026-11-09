import test from 'node:test';
import assert from 'node:assert/strict';
import { searchIndex, attachSearch } from '../src/search.js';
const index = [
  {page:'Install',url:'/help/install/',anchor:'start',title:'Install Optimax',text:'Set up your plugin'},
  {page:'Routing',url:'/help/routing/',anchor:'install',title:'Routing details',text:'install helpers'}
];
test('search requires two characters, ranks titles, matches terms case insensitively and limits results', () => {
  assert.deepEqual(searchIndex(index,'i'), []);
  assert.equal(searchIndex(index,'INSTALL')[0].title, 'Install Optimax');
  assert.deepEqual(searchIndex(index,'install plugin').map(x=>x.title), ['Install Optimax']);
  assert.equal(searchIndex(Array(12).fill(index[0]),'install').length,8);
});
test('search rejects unsafe paths and treats markup as literal text', () => {
  assert.deepEqual(searchIndex([{...index[0],url:'javascript:alert(1)'}],'install'),[]);
  assert.deepEqual(searchIndex(index,'<img src=x onerror=alert(1)>'),[]);
});
class Element {
  constructor(tag='div') { this.tagName=tag; this.children=[]; this.attrs={}; this.listeners={}; this.value=''; this.textContent=''; this.hidden=false; }
  setAttribute(k,v){this.attrs[k]=String(v)}
  addEventListener(k,fn){this.listeners[k]=fn}
  replaceChildren(...xs){this.children=xs}
  append(...xs){this.children.push(...xs)}
  dispatch(k,extra={}){this.listeners[k]?.({key:'',preventDefault(){},...extra})}
  focus(){this.focused=true}
}
test('typeahead renders safely, supports keyboard navigation, no results and clearing', () => {
  const input=new Element('input'), results=new Element(), status=new Element(), clear=new Element('button');
  const document={createElement:tag=>new Element(tag)};
  attachSearch({input,results,status,clear,document,index});
  input.value='install'; input.dispatch('input');
  assert.equal(results.children.length,2); assert.match(status.textContent,/2/);
  assert.equal(results.children[0].children[0].textContent,'Install Optimax');
  input.dispatch('keydown',{key:'ArrowDown'}); assert.equal(results.children[0].children[0].focused,true);
  assert.equal(input.attrs['aria-activedescendant'],undefined);
  input.value='plugin'; input.dispatch('input'); assert.equal(results.children.length,1);
  input.value='nonexistent'; input.dispatch('input'); assert.match(status.textContent,/no results/i);
  input.value='<img src=x onerror=alert(1)>'; input.dispatch('input');
  assert.equal(results.children.length,0);
  clear.dispatch('click'); assert.equal(input.value,''); assert.equal(results.children.length,0); assert.equal(status.textContent,'');
  input.value='install'; input.dispatch('input'); input.dispatch('keydown',{key:'Escape'}); assert.equal(results.children.length,0);
});
