import {installControls} from '../assets/controls.js';

const tabs=[...document.querySelectorAll('[data-install-tab]')];
if(tabs.length)installControls({
 tabs,panels:[...document.querySelectorAll('[data-install-panel]')],
 button:document.querySelector('#copy-install'),status:document.querySelector('#copy-status'),clipboard:navigator.clipboard
});
