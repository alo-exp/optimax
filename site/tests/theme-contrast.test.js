import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const css=readFileSync(new URL('../src/style.css',import.meta.url),'utf8');
function block(selector){
 const start=css.indexOf(selector+' {');
 assert.notEqual(start,-1,'missing CSS contract: '+selector);
 const open=css.indexOf('{',start),close=css.indexOf('}',open);
 return css.slice(open+1,close);
}
function declarations(source){return Object.fromEntries([...source.matchAll(/(--[\w-]+)\s*:\s*([^;{}]+)/g)].map(([,name,value])=>[name,value.trim()]));}
const dark=()=>declarations(block(':root'));
const light=()=>({...dark(),...declarations(block(':root[data-theme="light"]'))});
function rgb(value){assert.match(value||'',/^#[\da-f]{6}$/i,'contrast token must have an explicit sRGB value');return value.slice(1).match(/../g).map(x=>parseInt(x,16)/255);}
function luminance(color){return color.map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4).reduce((sum,c,i)=>sum+c*[.2126,.7152,.0722][i],0);}
function ratio(a,b){const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
function readable(tokens,foreground,background,min=4.5){const actual=ratio(rgb(tokens[foreground]),rgb(tokens[background]));assert.ok(actual>=min,foreground+' on '+background+' has contrast '+actual.toFixed(2)+'; needs '+min);}
for(const [theme,tokens] of [['light',light],['dark',dark]]){
 test(theme+' text, search, mineral, brass and technical surfaces retain readable contrast',()=>{
  const t=tokens();
  for(const background of ['--bg','--elevated','--selected'])for(const foreground of ['--ink','--muted','--accent'])readable(t,foreground,background);
  for(const foreground of ['--on-panel','--panel-muted','--panel-accent'])readable(t,foreground,'--panel');
  for(const foreground of ['--on-mineral','--mineral-muted'])readable(t,foreground,'--mineral');
  readable(t,'--on-brass','--brass');readable(t,'--focus','--bg',3);
 });
}
test('dark palette is the unconditional CSS fallback and light is an explicit alternate',()=>{
 assert.match(block(':root'),/color-scheme:\s*dark/);
 assert.equal(dark()['--bg'],'#082820');assert.equal(dark()['--mineral'],'#eceae9');assert.equal(dark()['--brass'],'#dbba68');
 assert.match(block(':root[data-theme="light"]'),/color-scheme:\s*light/);
 assert.ok(Object.keys(declarations(block(':root[data-theme="light"]'))).length>=10);
 assert.doesNotMatch(css,/prefers-color-scheme/,'OS appearance must not change the default');
});
test('theme control remains operable and rightmost at compact widths',()=>{
 assert.match(block('.header-actions'),/margin-left:\s*auto/);assert.match(block('.header-actions'),/display:\s*flex/);
 const toggle=block('.theme-toggle');
 assert.match(toggle,/min-height:\s*44px/);assert.match(toggle,/min-width:\s*44px/);assert.match(toggle,/flex-shrink:\s*0/);
 assert.match(block('.theme-toggle[hidden]'),/display:\s*none/);
 assert.match(css,/focus-visible[^{}]*\{[^}]*outline:\s*3px solid var\(--focus\)/);
 assert.doesNotMatch(css,/\.header-actions[^{}]*last-child[^{}]*\{[^}]*display:\s*none/);
});
test('parallel labels share an unordered row and acceptance spans the group',()=>{
 assert.match(block('.parallel-tasks'),/display:\s*grid/);
 assert.match(block('.parallel-tasks'),/grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/);
 assert.match(block('.acceptance-boundary'),/width:\s*100%/);
 assert.match(css,/@media\s*\(max-width:\s*900px\)/);
});
test('a single acceptance emphasis respects reduced motion without hiding content',()=>{
 assert.equal((css.match(/@keyframes\s/g)||[]).length,1);
 assert.match(block('.acceptance-boundary'),/animation:\s*acceptance-emphasis/);
 assert.match(css,/@media\s*\(prefers-reduced-motion:\s*reduce\)[\s\S]*animation:\s*none/);
 assert.doesNotMatch(block('.acceptance-boundary'),/opacity:\s*0\b|visibility:\s*hidden/);
});
test('read surfaces and search states retain visible text and a calm measure',()=>{
 assert.match(block('.article'),/max-width:\s*72ch/);
 assert.match(block('.search input'),/color:\s*var\(--ink\)/);
 assert.match(block('.search li[aria-selected="true"]'),/background:\s*var\(--selected\)/);
 assert.match(css,/caret-color:\s*var\(--accent\)/);assert.match(css,/::selection/);assert.match(css,/scrollbar-color:/);
});
test('the approved world uses flat color and self-hosted Mona Sans without legacy styling',()=>{
 assert.match(css,/@font-face[\s\S]*font-family:\s*["']Mona Sans["']/);assert.match(css,/font-family:\s*["']Mona Sans["']/);
 assert.doesNotMatch(css,/gradient\(|background-clip:\s*text|Georgia|Inter,|#6d28d9|#9333ea|box-shadow:/i);
});
