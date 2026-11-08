import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {parseHTML} from 'linkedom';

const html=readFileSync(new URL('../src/homepage.html',import.meta.url),'utf8');
const css=readFileSync(new URL('../src/homepage.css',import.meta.url),'utf8');
const document=parseHTML(html).document;

function palette(selector){const escaped=selector.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');const content=css.match(new RegExp(escaped+'\\s*\\{([^}]+)'))?.[1]||'';return Object.fromEntries([...content.matchAll(/(--[\w-]+)\s*:\s*(#[\da-f]{6})/gi)].map(([,name,value])=>[name,value]));}
function luminance(color){assert.match(color||'',/^#[\da-f]{6}$/i);return color.slice(1).match(/../g).map(value=>parseInt(value,16)/255).map(value=>value<=.04045?value/12.92:((value+.055)/1.055)**2.4).reduce((sum,value,index)=>sum+value*[.2126,.7152,.0722][index],0);}
function contrast(a,b){const x=luminance(a),y=luminance(b);return(Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
for(const theme of ['dark','light'])test('homepage '+theme+' reading, links and command text have readable contrast',()=>{
 const dark=palette(':root'),tokens=theme==='light'?{...dark,...palette(':root[data-theme="light"]')}:dark;
 assert.equal(tokens['--bg'],theme==='dark'?'#081525':'#F3F7FF');
 for(const [fg,bg,min] of [['--ink','--bg',4.5],['--muted','--bg',4.5],['--accent','--bg',4.5],['--on-accent','--accent',4.5],['--command-ink','--command-bg',4.5],['--command-muted','--command-bg',4.5],['--focus','--bg',3]])assert.ok(contrast(tokens[fg],tokens[bg])>=min,fg+' on '+bg+' must meet '+min+':1');
});

test('homepage supports narrow reading and keyboard use with local Sora',()=>{
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

test('homepage motion remains bounded and respects reduced motion',()=>{
 assert.ok((css.match(/@keyframes\s/g)||[]).length<=1,'one authored motion moment maximum');
 assert.match(css,/@media\s*\(prefers-reduced-motion:\s*reduce\)[\s\S]*animation:\s*none/);
});
