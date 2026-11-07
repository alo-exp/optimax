import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync,readFileSync} from 'node:fs';
import {parseHTML} from 'linkedom';

const readOptional=name=>{const url=new URL('../variants/'+name,import.meta.url);return existsSync(url)?readFileSync(url,'utf8'):'';};
const html=readOptional('continuum.html'),css=readOptional('continuum.css');
const document=parseHTML(html||'<html><head></head><body></body></html>').document;
const original=parseHTML(readFileSync(new URL('../src/homepage.html',import.meta.url),'utf8')).document;
const text=node=>node.textContent.replace(/\s+/g,' ').trim();
const texts=(doc,selector)=>[...doc.querySelectorAll(selector)].map(text);
const sections=['how-it-works','mechanism','proof','benefits','questions','install','next-step'];

test('Continuum publishes a clean HTML document with no trailing gateway notices',()=>{
 assert.ok(/<\/html>\s*$/.test(html),'the public source must end at its closing HTML tag');
 assert.equal(/\[lean.ctx(?: nudge)?\]|ACTIVE SESSION|postimage: bytes=|behavior_nudges=/i.test(html),false,'tool response notices are never public content');
});

test('Continuum is a complete new homepage preserving every approved CMF word and its reading order',()=>{
 assert.ok(document.querySelector('main#main'),'the new complete Continuum homepage must exist');
 assert.equal(document.querySelectorAll('h1').length,1);
 assert.equal(text(document.querySelector('h1')),text(original.querySelector('h1')));
 assert.equal(text(document.querySelector('.hero-deck')),'Maximize parallelization, minimize cost');
 assert.equal(document.querySelector('.hero-deck').nextElementSibling,document.querySelector('.hero-audience'));
 assert.deepEqual([...document.querySelectorAll('main > section[id]')].map(node=>node.id),sections);
 for(const selector of ['main h1','main h2','main h3','main p','main summary','main code','.parallel-tasks strong','.parallel-tasks small','.acceptance-boundary strong','.acceptance-boundary small','.plan-meta span','.ticker span','footer'])assert.deepEqual(texts(document,selector),texts(original,selector),'preserve exact approved content for '+selector);
 assert.equal(document.querySelectorAll('#questions details').length,7);
 for(const link of original.querySelectorAll('a[href]'))assert.ok([...document.querySelectorAll('a[href]')].some(candidate=>candidate.getAttribute('href')===link.getAttribute('href')&&text(candidate)===text(link)),'preserve real link '+link.getAttribute('href'));
 assert.ok(document.querySelector('#questions .differentiation'));
});

test('Continuum communicates independent assignments and a distinct waiting acceptance boundary without animation',()=>{
 const diagram=document.querySelector('.routing-visual'),tasks=diagram?.querySelector('ul.parallel-tasks');
 assert.ok(tasks,'task labels must remain a semantic unordered list');
 assert.equal(tasks.children.length,3);
 assert.deepEqual(texts(document,'.parallel-tasks strong'),texts(original,'.parallel-tasks strong'));
 assert.deepEqual(texts(document,'.parallel-tasks small'),texts(original,'.parallel-tasks small'));
 const acceptance=diagram.querySelector('.acceptance-boundary');assert.ok(acceptance);assert.equal(tasks.contains(acceptance),false);
 assert.equal(text(acceptance.querySelector('strong')),'Integrate accepted results');assert.equal(text(acceptance.querySelector('small')),'WAITING / REVIEW & DEPENDENCIES');
 assert.equal(diagram.getAttribute('aria-describedby'),'plan-note');assert.ok(document.getElementById('plan-note'));
 assert.ok(diagram.querySelector('svg[aria-hidden="true"]'),'countable native geometry must supplement, not replace, readable semantic labels');
 assert.match(css,/@media\s*\(prefers-reduced-motion:\s*reduce\)[\s\S]*animation:\s*none/);
 assert.ok((css.match(/@keyframes\s/g)||[]).length<=1,'motion has one authored moment');
});

test('Continuum preserves prefix-safe preview metadata, early theme and working install-control hooks',()=>{
 assert.equal(document.documentElement.getAttribute('data-theme'),'dark');
 assert.equal(document.querySelector('meta[name="robots"]')?.content,'noindex');
 assert.equal(document.querySelector('link[rel="canonical"]')?.getAttribute('href'),'{{BASE}}versions/continuum/');
 assert.equal(document.querySelector('meta[name="site-base"]')?.content,'{{BASE}}');
 for(const selector of ['meta[name="description"]','meta[property="og:description"]','meta[property="og:title"]'])assert.equal(document.querySelector(selector)?.content,original.querySelector(selector).content);
 assert.equal(document.title,original.title);
 const early=document.querySelector('head script[src="{{BASE}}versions/theme.js"]');assert.ok(early);assert.ok(html.indexOf(early.outerHTML)<html.indexOf('<link rel="stylesheet"'));assert.equal(early.hasAttribute('type'),false);assert.equal(early.hasAttribute('defer'),false);
 assert.ok(document.querySelector('link[rel="stylesheet"][href="./style.css"]'));
 assert.ok(document.querySelector('script[type="module"][src="{{BASE}}versions/client.js"]'));
 const theme=document.getElementById('theme-toggle');assert.equal(theme?.tagName,'BUTTON');assert.equal(theme.type,'button');assert.equal(theme.getAttribute('aria-label'),'Dark theme');assert.equal(theme.getAttribute('aria-pressed'),'true');assert.ok(theme.hidden);assert.equal(theme.parentElement.lastElementChild,theme);
 assert.deepEqual(texts(document,'[data-install-panel]'),texts(original,'[data-install-panel]'));
 assert.deepEqual([...document.querySelectorAll('[data-install-panel]')].map(node=>node.hidden),[false,true]);
 assert.deepEqual([...document.querySelectorAll('[data-install-tab]')].map(node=>node.getAttribute('aria-pressed')),['true','false']);
 assert.equal(document.querySelector('#copy-install')?.type,'button');assert.equal(document.querySelector('#copy-status')?.getAttribute('role'),'status');
 for(const id of ['main',...sections])assert.ok(document.getElementById(id));
});

function palette(selector){const escaped=selector.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');const source=css.match(new RegExp(escaped+'\\s*\\{([^}]+)'))?.[1]||'';return Object.fromEntries([...source.matchAll(/(--[\w-]+)\s*:\s*(#[\da-f]{6})/gi)].map(([,key,value])=>[key,value]));}
function luminance(color){assert.match(color||'',/^#[\da-f]{6}$/i);return color.slice(1).match(/../g).map(value=>parseInt(value,16)/255).map(value=>value<=.04045?value/12.92:((value+.055)/1.055)**2.4).reduce((sum,value,index)=>sum+value*[.2126,.7152,.0722][index],0);}
function ratio(a,b){const x=luminance(a),y=luminance(b);return(Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
for(const theme of ['dark','light'])test('Continuum '+theme+' edition retains readable body, colored fields, links, states and commands',()=>{
 const dark=palette(':root'),tokens=theme==='light'?{...dark,...palette(':root[data-theme="light"]')}:dark;
 for(const [fg,bg,min]of [['--ink','--bg',4.5],['--muted','--bg',4.5],['--accent','--bg',4.5],['--ink','--surface',4.5],['--muted','--surface',4.5],['--field-ink','--field',4.5],['--field-muted','--field',4.5],['--on-accent','--accent',4.5],['--command-ink','--command-bg',4.5],['--command-muted','--command-bg',4.5],['--plan-ink','--plan-label',4.5],['--plan-muted','--plan-label',4.5],['--ink','--plane',4.5],['--muted','--plane',4.5],['--focus','--bg',3]])assert.ok(ratio(tokens[fg],tokens[bg])>=min,fg+' on '+bg+' must meet '+min+':1');
 assert.equal(document.querySelector('meta[name="theme-color"]').content,dark['--bg']);
});

test('Continuum owns responsive typography and keyboard states with local Figtree and no inherited skin',()=>{
 for(const weight of [400,700])assert.ok(css.includes('{{BASE}}assets/fonts/figtree-latin-'+weight+'-normal.woff2'));
 assert.match(css,/font-family:\s*['"]Figtree['"]/);assert.match(css,/font-display:\s*swap/);
 assert.match(css,/focus-visible[^{}]*\{[^}]*outline:\s*3px solid var\(--focus\)/);
 assert.match(css,/min-height:\s*44px/);assert.match(css,/overflow-wrap:\s*anywhere/);
 assert.match(css,/@media\s*\(max-width:\s*700px\)/);
 assert.match(css,/::selection/);assert.match(css,/scrollbar-color/);assert.match(css,/caret-color/);
 assert.equal(document.querySelectorAll('link[rel="stylesheet"]').length,1);
 assert.doesNotMatch(css,/@import|backdrop-filter/);
 for(const [,number]of css.matchAll(/font-size\s*:\s*(\d+(?:\.\d+)?)px/g))assert.ok(Number(number)>=12,'no functional text below 12px');
 assert.match(css,/\.parallel-tasks small[^{}]*\{[^}]*font-size:\s*13px/);
 for(const heading of document.querySelectorAll('h1,h2,h3'))assert.ok(!heading.previousElementSibling?.classList.contains('eyebrow'));
});
