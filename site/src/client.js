import {attachSearch} from './search.js';
import {installControls} from './controls.js';
import {sitePath,validateBasePath} from './deployment.js';
const input=document.querySelector('#help-search');
if(input){
 const basePath=validateBasePath(document.querySelector('meta[name="site-base"]').content);
 fetch(sitePath('/search-index.json',basePath)).then(r=>{if(!r.ok)throw new Error('index unavailable');return r.json()}).then(index=>attachSearch({input,results:document.querySelector('#search-results'),status:document.querySelector('#search-status'),clear:document.querySelector('#search-clear'),document,index,basePath})).catch(()=>{document.querySelector('#search-status').textContent='Search is unavailable. Browse the articles below.'});
}
const tabs=[...document.querySelectorAll('[data-install-tab]')];
if(tabs.length) installControls({tabs,panels:[...document.querySelectorAll('[data-install-panel]')],button:document.querySelector('#copy-install'),status:document.querySelector('#copy-status'),clipboard:navigator.clipboard});
