import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync,readFileSync} from 'node:fs';
import {parseHTML} from 'linkedom';

const pageUrl=new URL('../variants/prism.html',import.meta.url);
const cssUrl=new URL('../variants/prism.css',import.meta.url);
function source(){assert.ok(existsSync(pageUrl),'Prism homepage must exist and render the approved homepage content');return readFileSync(pageUrl,'utf8');}
function styles(){assert.ok(existsSync(cssUrl),'Prism stylesheet must exist with authored themes');return readFileSync(cssUrl,'utf8');}
function documentFor(html){return parseHTML(html.replaceAll('<br>',' ')).document;}
const normalize=text=>text.replace(/\s+/g,' ').trim();
function cssBlock(css,selector){const start=css.indexOf(selector+' {');assert.notEqual(start,-1,'missing CSS contract '+selector);const open=css.indexOf('{',start);return css.slice(open+1,css.indexOf('}',open));}
function tokens(css,selector){return Object.fromEntries([...cssBlock(css,selector).matchAll(/(--[\w-]+)\s*:\s*(#[\da-f]{6})/gi)].map(([,k,v])=>[k,v]));}
function luminance(hex){return hex.slice(1).match(/../g).map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);}
function contrast(a,b){const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);}

test('Prism preserves approved homepage copy, claims, commands, links and fragments',()=>{
 const html=source(),doc=documentFor(html);
 const build=readFileSync(new URL('../build.js',import.meta.url),'utf8');
 const home=build.match(/const home=`([\s\S]*?)`;\nawait write\('index.html'/)?.[1];
 assert.ok(home,'canonical homepage content is identifiable');
 const canonical=documentFor('<html><body>'+home.replace(/\$\{icon\('[^']+'\)\}/g,'')+'</body></html>');
 const actual=normalize(doc.body.textContent);
 for(const el of canonical.querySelectorAll('h1,h2,h3,p,summary')){
  if(el.classList.contains('eyebrow'))continue;
  const text=normalize(el.textContent);assert.ok(actual.includes(text),'missing approved copy: '+text);
 }
 assert.equal(normalize(doc.querySelector('h1').textContent),'Get AI work done faster and cheaper');
 assert.equal(doc.querySelectorAll('h1').length,1);
 for(const id of ['main','how-it-works','mechanism','proof','benefits','questions','install','next-step'])assert.ok(doc.getElementById(id),'missing fragment #'+id);
 for(const a of canonical.querySelectorAll('a[href]')){const href=a.getAttribute('href').replace(/^\/(?!\/)/,'{{BASE}}');assert.ok([...doc.querySelectorAll('a[href]')].some(a=>a.getAttribute('href')===href),'missing link '+href);}
 for(const command of ['codex plugin marketplace add alo-labs/agent-plugins','codex plugin add optimax@alo-labs-codex','/plugin marketplace add alo-labs/agent-plugins','/plugin install optimax@alo-labs','$optimax on','/optimax:optimax on','$optimax off','/optimax:optimax off'])assert.ok(actual.includes(command),'missing real command '+command);
 for(const href of ['{{BASE}}','{{BASE}}help/','https://alolabs.dev','https://github.com/alo-exp/optimax'])assert.ok([...doc.querySelectorAll('footer a')].some(a=>a.getAttribute('href')===href));
 assert.equal(doc.querySelectorAll('#questions details').length,5);
});

test('Prism ships independent task tracks followed by one acceptance boundary',()=>{
 const doc=documentFor(source());
 const tracks=doc.querySelectorAll('.work-track');assert.equal(tracks.length,3);
 assert.deepEqual([...tracks].map(el=>normalize(el.querySelector('strong').textContent)),['Investigate own scope','Implement own files','Verify independent work']);
 assert.equal(doc.querySelectorAll('.flow-acceptance').length,1);
 assert.match(doc.querySelector('.flow-acceptance').textContent,/Integrate after acceptance/);
 assert.match(doc.querySelector('.flow-diagram').getAttribute('aria-label'),/three independent tasks/i);
 assert.equal(doc.querySelectorAll('.mechanism-stage').length,3);
 assert.equal(doc.querySelectorAll('.benefit-band').length,3);
 assert.doesNotMatch(source(),/PARTS REGISTER|seed:|direction contract|data-seed|live telemetry dashboard/i);
});

test('Prism controls match shared runtime contracts and retain visible keyboard access',()=>{
 const html=source(),doc=documentFor(html),css=styles();
 assert.equal(doc.documentElement.dataset.theme,'dark');
 assert.equal(doc.querySelector('meta[name="site-base"]').content,'{{BASE}}');
 assert.equal(doc.querySelector('meta[name="theme-color"]').content,'#150D2C');
 const toggle=doc.querySelector('#theme-toggle');assert.ok(toggle.hasAttribute('hidden'));assert.equal(toggle.getAttribute('aria-label'),'Dark theme');assert.equal(toggle.getAttribute('aria-pressed'),'true');
 assert.equal(doc.querySelector('.header-actions').lastElementChild,toggle);
 assert.ok(html.indexOf('versions/theme.js')<html.indexOf('./style.css'));
 assert.ok(doc.querySelector('script[type="module"][src="{{BASE}}versions/client.js"]'));
 assert.equal(doc.querySelectorAll('[data-install-tab]').length,2);assert.equal(doc.querySelectorAll('[data-install-panel]').length,2);
 assert.ok(doc.querySelector('#copy-install'));assert.equal(doc.querySelector('#copy-status').getAttribute('role'),'status');
 assert.match(css,/focus-visible[^{}]*\{[^}]*outline:\s*3px solid var\(--focus\)/);
 assert.match(cssBlock(css,'.theme-toggle'),/min-height:\s*44px/);assert.match(cssBlock(css,'.theme-toggle'),/min-width:\s*44px/);
 assert.match(cssBlock(css,'.theme-toggle[hidden]'),/display:\s*none/);
 assert.match(cssBlock(css,'pre'),/white-space:\s*pre-wrap/);assert.match(cssBlock(css,'pre'),/overflow-wrap:\s*anywhere/);
});

for(const selector of [':root',':root[data-theme="light"]'])test('Prism '+selector+' surfaces meet contrast for real content',()=>{
 const css=styles(),t={...tokens(css,':root'),...tokens(css,selector)};
 for(const [fg,bg] of [['--ink','--bg'],['--muted','--bg'],['--accent','--bg'],['--on-action','--action'],['--on-install','--install'],['--install-muted','--install'],['--code-ink','--code-bg'],['--code-muted','--code-bg']]){
  assert.ok(t[fg]&&t[bg],'explicit palette tokens '+fg+' '+bg);const ratio=contrast(t[fg],t[bg]);assert.ok(ratio>=4.5,fg+' on '+bg+' contrast '+ratio.toFixed(2));
 }
 assert.ok(contrast(t['--focus'],t['--bg'])>=3);
});

test('Prism uses its own display face, responsive geometry and optional nonlooping motion',()=>{
 const css=styles();
 assert.match(css,/@font-face[\s\S]*font-family:\s*['"]Bricolage Grotesque['"]/);
 for(const weight of ['400','700'])assert.ok(css.includes('bricolage-grotesque-latin-'+weight+'-normal.woff2'));
 assert.doesNotMatch(css,/gradient\(|box-shadow:|Space Grotesk|Mona Sans|prefers-color-scheme/i);
 assert.match(css,/@media\s*\(max-width:\s*700px\)/);
 assert.match(css,/@media\s*\(max-width:\s*420px\)/);
 assert.match(css,/@media\s*\(prefers-reduced-motion:\s*reduce\)[\s\S]*animation:\s*none/);
 assert.equal((css.match(/@keyframes\s/g)||[]).length,1);
 assert.doesNotMatch(css,/animation[^;{}]*infinite|opacity:\s*0\b|visibility:\s*hidden/);
 assert.match(css,/::selection/);assert.match(css,/caret-color:/);assert.match(css,/scrollbar-color:/);
});
