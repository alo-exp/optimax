import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {parseHTML} from 'linkedom';

const optionalFile=name=>{const url=new URL('../variants/'+name,import.meta.url);return existsSync(url)?readFileSync(url,'utf8'):'';};
const html=optionalFile('circuit.html'),css=optionalFile('circuit.css');
const document=parseHTML(html||'<html><head></head><body></body></html>').document;
// Historical preview copy remains tied to the homepage at project commit 36f5533.
const source=readFileSync(new URL('./fixtures/homepage-before-circuit.html',import.meta.url),'utf8');
const original=parseHTML('<html><body><main>'+source+'</main></body></html>').document;
const text=value=>value.replace(/\s+/g,' ').trim();

test('Circuit is a complete independent homepage with the preserved offer and production fragments',()=>{
 assert.ok(document.querySelector('main#main'),'Circuit must provide the complete homepage, not a missing preview');
 assert.equal(document.querySelectorAll('h1').length,1);
 assert.equal(document.querySelector('h1').textContent,'Optimize Cost, Maximize Parallel Work');
 for(const id of ['how-it-works','mechanism','proof','benefits','questions','install','next-step'])assert.ok(document.getElementById(id),'retain production fragment #'+id);
 const copy=[...document.querySelectorAll('main h1,main h2,main h3,main p,main summary')].map(node=>text(node.textContent));
 // The user-approved hero supersedes the historical H1; all other preview copy stays frozen.
 for(const node of original.querySelectorAll('main h2,main h3,main p,main summary'))assert.ok(copy.includes(text(node.textContent)),'preserve source wording: '+text(node.textContent));
 for(const link of original.querySelectorAll('a[href]')){
  const href=link.getAttribute('href'),expected=href.startsWith('/')?'{{BASE}}'+href.slice(1):href;
  assert.ok([...document.querySelectorAll('a[href]')].some(node=>node.getAttribute('href')===expected),'retain destination '+expected);
 }
 assert.equal(document.querySelectorAll('a[href*="{{BASE}}versions/"]').length,0,'Circuit must not link to removed comparison routes');
 assert.equal(document.querySelectorAll('#questions details').length,5);
});

test('Circuit makes three independent paths and their shared acceptance boundary understandable without motion',()=>{
 const paths=document.querySelector('ul.parallel-tasks');
 assert.ok(paths,'parallel tasks must be a semantic unordered group');
 assert.deepEqual([...paths.children].map(node=>node.querySelector('strong').textContent),['Investigate own scope','Implement own files','Verify independent work']);
 const diagram=document.querySelector('.routing-visual'),acceptance=diagram?.querySelector('.acceptance-boundary');
 assert.ok(acceptance);assert.equal(paths.contains(acceptance),false);
 assert.match(acceptance.textContent,/Integrate after acceptance/);
 assert.match(acceptance.textContent,/WAITING \/ DEPENDENCIES/);
 assert.equal(diagram.getAttribute('aria-describedby'),'plan-note');
 assert.match(document.getElementById('plan-note').textContent,/only when independent, capacity is verified and resources do not conflict/);
 assert.ok((css.match(/@keyframes\s/g)||[]).length<=1,'one authored motion moment maximum');
 assert.match(css,/@media\s*\(prefers-reduced-motion:\s*reduce\)[\s\S]*animation:\s*none/);
});

test('Circuit retains progressive theme, installation and session controls',()=>{
 assert.equal(document.documentElement.getAttribute('data-theme'),'dark');
 assert.equal(document.querySelector('meta[name="site-base"]').content,'{{BASE}}');
 assert.equal(document.querySelector('meta[name="theme-color"]').content,'#081525');
 const theme=document.querySelector('#theme-toggle');
 assert.equal(theme.tagName,'BUTTON');assert.equal(theme.type,'button');
 assert.equal(theme.getAttribute('aria-label'),'Dark theme');assert.equal(theme.getAttribute('aria-pressed'),'true');assert.ok(theme.hidden);
 assert.equal(theme.parentElement.lastElementChild,theme,'theme control is the last header action');
 const early=document.querySelector('head script[src="{{BASE}}versions/theme.js"]');assert.ok(early);assert.ok(html.indexOf(early.outerHTML)<html.indexOf('<link rel="stylesheet"'));
 assert.equal(early.hasAttribute('type'),false);assert.equal(early.hasAttribute('defer'),false);
 assert.ok(document.querySelector('script[type="module"][src="{{BASE}}versions/client.js"]'));
 const panels=[...document.querySelectorAll('[data-install-panel]')];
 assert.deepEqual(panels.map(node=>node.textContent),['codex plugin marketplace add alo-labs/agent-plugins\ncodex plugin add optimax@alo-labs-codex','/plugin marketplace add alo-labs/agent-plugins\n/plugin install optimax@alo-labs']);
 assert.deepEqual(panels.map(node=>node.hidden),[false,true]);
 assert.deepEqual([...document.querySelectorAll('[data-install-tab]')].map(node=>node.getAttribute('aria-pressed')),['true','false']);
 assert.ok(document.querySelector('button#copy-install'));assert.equal(document.querySelector('#copy-status').getAttribute('role'),'status');
 for(const command of ['$optimax off','/optimax:optimax off','$optimax on','/optimax:optimax on'])assert.ok(document.body.textContent.includes(command));
});

function palette(selector){const escaped=selector.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');const content=css.match(new RegExp(escaped+'\\s*\\{([^}]+)'))?.[1]||'';return Object.fromEntries([...content.matchAll(/(--[\w-]+)\s*:\s*(#[\da-f]{6})/gi)].map(([,name,value])=>[name,value]));}
function luminance(color){assert.match(color||'',/^#[\da-f]{6}$/i);return color.slice(1).match(/../g).map(value=>parseInt(value,16)/255).map(value=>value<=.04045?value/12.92:((value+.055)/1.055)**2.4).reduce((sum,value,index)=>sum+value*[.2126,.7152,.0722][index],0);}
function contrast(a,b){const x=luminance(a),y=luminance(b);return(Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
for(const theme of ['dark','light'])test('Circuit '+theme+' reading, links and command text have readable contrast',()=>{
 const dark=palette(':root'),tokens=theme==='light'?{...dark,...palette(':root[data-theme="light"]')}:dark;
 assert.equal(tokens['--bg'],theme==='dark'?'#081525':'#F3F7FF');
 for(const [fg,bg,min] of [['--ink','--bg',4.5],['--muted','--bg',4.5],['--accent','--bg',4.5],['--on-accent','--accent',4.5],['--command-ink','--command-bg',4.5],['--command-muted','--command-bg',4.5],['--focus','--bg',3]])assert.ok(contrast(tokens[fg],tokens[bg])>=min,fg+' on '+bg+' must meet '+min+':1');
});

test('Circuit supports narrow reading and keyboard use with local Sora and no inherited production CSS',()=>{
 for(const weight of [400,700])assert.ok(css.includes("{{BASE}}assets/fonts/sora-latin-"+weight+"-normal.woff2"));
 assert.match(css,/font-family:\s*["']Sora["']/);
 assert.match(css,/font-display:\s*swap/);
 assert.match(css,/focus-visible[^{]*\{[^}]*outline:\s*3px solid var\(--focus\)/);
 assert.match(css,/min-height:\s*44px/);
 assert.match(css,/overflow-wrap:\s*anywhere/);
 assert.match(css,/@media\s*\(max-width:\s*700px\)/);
 assert.match(css,/::selection/);assert.match(css,/scrollbar-color/);assert.match(css,/caret-color/);
 assert.doesNotMatch(css,/@import|clip-path|linear-gradient|repeating-linear-gradient/);
 for(const heading of document.querySelectorAll('h1,h2,h3'))assert.ok(!heading.previousElementSibling?.classList.contains('eyebrow'),'metadata belongs below a heading');
});
