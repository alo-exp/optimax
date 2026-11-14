import {attachSearch} from './search.js';
import {installControls} from './controls.js';
import {sitePath,validateBasePath} from './deployment.js';
const input=document.querySelector('#help-search');
if(input){
 const basePath=validateBasePath(document.querySelector('meta[name="site-base"]').content);
 const clear=document.querySelector('#search-clear'),status=document.querySelector('#search-status');
 const clearPending=()=>{input.value='';input.focus()};
 clear.addEventListener('click',clearPending);
 status.textContent='Loading search. Browse the articles below.';input.disabled=false;clear.disabled=false;
 fetch(sitePath('/search-index.json',basePath)).then(r=>{if(!r.ok)throw new Error('index unavailable');return r.json()}).then(index=>{
  if(!Array.isArray(index)||!index.every(row=>row && ['page','url','anchor','title','text'].every(key=>typeof row[key]==='string')))throw new Error('invalid index');
  clear.removeEventListener('click',clearPending);status.textContent='';
  attachSearch({input,results:document.querySelector('#search-results'),status,clear,document,index,basePath});
 }).catch(()=>{input.disabled=true;status.textContent='Search is unavailable. Browse the articles below.'});
}
const tabs=[...document.querySelectorAll('[data-install-tab]')];
if(tabs.length) installControls({tabs,panels:[...document.querySelectorAll('[data-install-panel]')],button:document.querySelector('#copy-install'),status:document.querySelector('#copy-status'),clipboard:navigator.clipboard});
