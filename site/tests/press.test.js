import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync,readFileSync} from 'node:fs';
import {parseHTML} from 'linkedom';

const optionalFile=name=>{const path=new URL('../variants/'+name,import.meta.url);return existsSync(path)?readFileSync(path,'utf8'):'';};
const html=optionalFile('press.html'),css=optionalFile('press.css');
const document=parseHTML(html||'<html><head></head><body></body></html>').document;
const source=parseHTML(optionalFile('circuit.html')).document;
const text=node=>{const copy=node.cloneNode(true);for(const br of copy.querySelectorAll('br'))br.replaceWith(' ');return copy.textContent.replace(/\s+/g,' ').trim();};
const content=(doc,selector)=>[...doc.querySelectorAll(selector)].map(text).sort();

// Missing preview files produce behavioral assertions, never an import/ENOENT failure.
test('Press is a complete homepage preserving every approved paragraph, heading and FAQ',()=>{
 assert.ok(document.querySelector('main#main'),'Press must provide a complete homepage');
 assert.equal(document.querySelectorAll('h1').length,1);
 assert.equal(document.querySelector('h1').textContent,'Get AI work done faster and cheaper');
 assert.ok(content(document,'p').includes('Maximize parallelization, minimize cost'));
 assert.equal(source.querySelectorAll('p').length,36,'pin the approved source paragraph denominator');
 assert.deepEqual(content(document,'p'),content(source,'p'),'preserve all 36 paragraphs verbatim');
 assert.deepEqual(content(document,'main h1,main h2,main h3'),content(source,'main h1,main h2,main h3'));
 assert.deepEqual(content(document,'#questions summary'),content(source,'#questions summary'));
 assert.equal(document.querySelectorAll('#questions details').length,5);
});

test('Press preserves public destinations, fragment navigation and proof qualifiers',()=>{
 const links=[...document.querySelectorAll('a[href]')];
 for(const link of source.querySelectorAll('a[href]'))assert.ok(links.some(node=>node.getAttribute('href')===link.getAttribute('href')&&text(node)===text(link)),'retain link '+text(link)+' → '+link.getAttribute('href'));
 for(const node of source.querySelectorAll('main [id]'))assert.ok(document.getElementById(node.id),'retain #'+node.id);
 for(const link of links.filter(node=>node.getAttribute('href').startsWith('#')))assert.ok(document.getElementById(link.getAttribute('href').slice(1)),'resolve fragment '+link.getAttribute('href'));
 assert.ok(document.querySelector('a[href="{{BASE}}versions/circuit/"]'),'make the shortlisted alternative reachable');
 assert.match(document.getElementById('proof')?.textContent||'',/live acceptance is pending/);
 assert.match(document.getElementById('proof')?.textContent||'',/Neither establishes universal native-helper control or measured performance savings/);
});

test('Press shows semantic independent lanes and a distinct review boundary without live telemetry',()=>{
 const plan=document.querySelector('.parallel-plan'),tasks=plan?.querySelector('ul.parallel-tasks');
 assert.ok(tasks,'parallel assignments form an unordered semantic group');
 assert.deepEqual([...tasks.children].map(node=>text(node.querySelector('strong'))),['Investigate own scope','Implement own files','Verify independent work']);
 assert.equal(tasks.children.length,3);
 const diagram=plan.querySelector('.routing-visual'),boundary=diagram?.querySelector('.acceptance-boundary');
 assert.ok(boundary,'show acceptance before integration');
 assert.equal(tasks.contains(boundary),false);
 assert.match(boundary.textContent,/Integrate after acceptance/);
 assert.match(boundary.textContent,/WAITING \/ DEPENDENCIES/);
 assert.equal(diagram.getAttribute('aria-describedby'),'plan-note');
 assert.match(document.getElementById('plan-note').textContent,/only when independent, capacity is verified and resources do not conflict/);
 assert.ok(plan.compareDocumentPosition(document.getElementById('proof'))&4,'illustrate the mechanism before its evidence');
 assert.doesNotMatch(plan.textContent,/\d+\s*(?:ms|seconds|tokens|%)/i);
});

test('Press keeps dark-default progressive theme control and shared runtime hooks',()=>{
 assert.equal(document.documentElement.getAttribute('data-theme'),'dark');
 assert.equal(document.querySelector('meta[name="site-base"]')?.content,'{{BASE}}');
 assert.equal(document.querySelector('meta[name="theme-color"]')?.content,'#161616');
 assert.equal(document.querySelector('link[rel="canonical"]')?.getAttribute('href'),'{{BASE}}versions/press/');
 assert.equal(document.querySelector('meta[name="robots"]')?.content,'noindex,follow');
 assert.equal(document.querySelector('link[rel="icon"]')?.getAttribute('href'),'{{BASE}}favicon.svg');
 assert.equal(document.querySelector('link[rel="stylesheet"]')?.getAttribute('href'),'./style.css');
 const toggle=document.querySelector('#theme-toggle');assert.ok(toggle);
 assert.equal(toggle.tagName,'BUTTON');assert.equal(toggle.type,'button');
 assert.equal(toggle.getAttribute('aria-label'),'Dark theme');assert.equal(toggle.getAttribute('aria-pressed'),'true');assert.ok(toggle.hidden);
 assert.equal(toggle.parentElement.lastElementChild,toggle,'theme is the rightmost header action');
 const early=document.querySelector('head script[src="{{BASE}}versions/theme.js"]');assert.ok(early);
 assert.ok(html.indexOf(early.outerHTML)<html.indexOf('<link rel="stylesheet"'));
 for(const attribute of ['type','defer','async'])assert.equal(early.hasAttribute(attribute),false,'theme runs synchronously before CSS');
 assert.ok(document.querySelector('script[type="module"][src="{{BASE}}versions/client.js"]'));
 assert.equal(document.querySelectorAll('script').length,2,'reuse the shared runtime');
});

test('Press retains functional installation controls and exact platform/session commands',()=>{
 const panels=[...document.querySelectorAll('[data-install-panel]')];
 assert.deepEqual(panels.map(node=>node.textContent),[...source.querySelectorAll('[data-install-panel]')].map(node=>node.textContent));
 assert.deepEqual(panels.map(node=>node.hidden),[false,true]);
 const tabs=[...document.querySelectorAll('[data-install-tab]')];
 assert.deepEqual(tabs.map(node=>node.textContent),['Codex','Claude']);
 assert.deepEqual(tabs.map(node=>node.getAttribute('aria-pressed')),['true','false']);
 for(const tab of tabs)assert.equal(tab.getAttribute('type'),'button');
 assert.equal(document.querySelector('#copy-install')?.tagName,'BUTTON');
 assert.equal(document.querySelector('#copy-install')?.getAttribute('type'),'button');
 assert.equal(document.querySelector('#copy-status')?.getAttribute('role'),'status');
 assert.deepEqual(content(document,'code'),content(source,'code'));
 assert.ok(document.querySelector('.hero a[href="#install"]'),'the offer leads to a real installation action');
});

function palette(selector){const escaped=selector.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');const block=css.match(new RegExp(escaped+'\\s*\\{([^}]+)'))?.[1]||'';return Object.fromEntries([...block.matchAll(/(--[\w-]+)\s*:\s*(#[\da-f]{6})/gi)].map(([,name,value])=>[name,value]));}
function luminance(color){assert.match(color||'',/^#[\da-f]{6}$/i,'complete authored palette');return color.slice(1).match(/../g).map(value=>parseInt(value,16)/255).map(value=>value<=.04045?value/12.92:((value+.055)/1.055)**2.4).reduce((sum,value,index)=>sum+value*[.2126,.7152,.0722][index],0);}
function contrast(a,b){const x=luminance(a),y=luminance(b);return(Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
for(const theme of ['dark','light'])test('Press '+theme+' edition has readable text, controls, commands and focus',()=>{
 const dark=palette(':root'),tokens=theme==='light'?{...dark,...palette(':root[data-theme="light"]')}:dark;
 assert.equal(tokens['--bg'],theme==='dark'?'#161616':'#f4f0e8');
 for(const [fg,bg,min] of [['--ink','--bg',4.5],['--muted','--bg',4.5],['--accent','--bg',4.5],['--on-accent','--accent',4.5],['--rail-ink','--rail-bg',4.5],['--rail-muted','--rail-bg',4.5],['--command-ink','--command-bg',4.5],['--command-muted','--command-bg',4.5],['--focus','--bg',3],['--rail-focus','--rail-bg',3]])assert.ok(contrast(tokens[fg],tokens[bg])>=min,fg+' on '+bg+' must meet '+min+':1');
});

test('Press uses self-hosted Archivo Narrow, accessible reading measures and authored responsive states',()=>{
 for(const weight of [400,700])assert.ok(css.includes('{{BASE}}assets/fonts/archivo-narrow-latin-'+weight+'-normal.woff2'));
 assert.match(css,/font-family:\s*['"]Archivo Narrow['"]/);
 assert.equal((css.match(/font-display:\s*swap/g)||[]).length,2);
 assert.match(css,/body\s*\{[^}]*font-size:\s*1\.25rem/);
 assert.match(css,/line-height:\s*1\.5/);
 assert.match(css,/max-width:\s*5[0-9]ch/);
 assert.match(css,/focus-visible[^{]*\{[^}]*outline:\s*3px solid var\(--focus\)/);
 assert.match(css,/min-height:\s*44px/);
 assert.match(css,/overflow-wrap:\s*anywhere/);
 assert.match(css,/@media\s*\(max-width:\s*700px\)/);
 assert.match(css,/@media\s*\(prefers-reduced-motion:\s*reduce\)[\s\S]*animation:\s*none/);
 assert.match(css,/\[hidden\]\s*\{[^}]*display:\s*none/);
 assert.match(css,/::selection/);assert.match(css,/scrollbar-color/);assert.match(css,/caret-color/);
 assert.doesNotMatch(css,/@import|clip-path|linear-gradient|repeating-linear-gradient|https?:/);
 assert.doesNotMatch(html,/\bstyle=/i);
 for(const heading of document.querySelectorAll('h1,h2,h3'))assert.ok(!heading.previousElementSibling?.classList.contains('eyebrow'),'no eyebrow above headings');
 assert.equal(document.querySelectorAll('.step-pin,.eyebrow').length,0,'no decorative counters or eyebrows');
});


function declarations(selector,source=css){const escaped=selector.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');const block=source.match(new RegExp(escaped+'\\s*\\{([^}]+)'))?.[1]||'';return Object.fromEntries(block.split(';').filter(value=>value.includes(':')).map(value=>{const index=value.indexOf(':');return[value.slice(0,index).trim(),value.slice(index+1).trim()];}));}

test('Press keeps a full install entry in the mobile header with a separate top-right theme control',()=>{
 const mobile=css.slice(css.indexOf('@media (max-width: 700px)'),css.indexOf('@media (prefers-reduced-motion: reduce)'));
 const cta=document.querySelector('.header .nav-cta');assert.equal(cta?.getAttribute('href'),'#install');assert.equal(text(cta),'Get started');
 const entry=declarations('.header .nav-cta',mobile);
 assert.ok(['flex','inline-flex','block','grid'].includes(entry.display),'mobile header install action must be explicitly visible after the tablet hide rule');
 assert.ok(Number.parseFloat(entry['min-height'])>=44,'mobile install entry retains a full 44px target');
 assert.equal(entry['grid-column'],'1 / -1','full install entry gets its own header row');
 const actions=declarations('.header-actions',mobile),theme=declarations('.theme-toggle',mobile),navigation=declarations('.header nav',mobile);
 assert.equal(actions.display,'contents','header actions participate in the shared grid without squeezing the wordmark');
 assert.equal(theme['grid-column'],'2');assert.equal(theme['grid-row'],'1','theme remains at the top right');
 assert.notEqual(entry['grid-row'],navigation['grid-row'],'install entry and navigation occupy separate rows');
 assert.notEqual(entry['grid-row'],theme['grid-row'],'install entry and theme occupy separate rows');
});

test('Press wordmark tracking stays within the legible minus .04em craft floor',()=>{
 const tracking=declarations('.brand')['letter-spacing'];
 assert.match(tracking||'',/^-?\.?\d+em$/);
 assert.ok(Number.parseFloat(tracking)>=-.04,'wordmark tracking must be at least -.04em; received '+tracking);
});
