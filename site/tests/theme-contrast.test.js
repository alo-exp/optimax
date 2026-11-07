import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const css=readFileSync(new URL('../src/style.css',import.meta.url),'utf8');
function block(selector){
 const start=css.indexOf(selector);
 assert.notEqual(start,-1,'missing CSS contract: '+selector);
 const open=css.indexOf('{',start),close=css.indexOf('}',open);
 return css.slice(open+1,close);
}
function declarations(source){
 return Object.fromEntries([...source.matchAll(/(--[\w-]+)\s*:\s*([^;{}]+)/g)].map(([,name,value])=>[name,value.trim()]));
}
const light=()=>declarations(block(':root'));
const dark=()=>({...light(),...declarations(block(':root[data-theme="dark"]'))});
function rgb(value){assert.match(value||'',/^#[\da-f]{6}$/i,'contrast token must have an explicit sRGB value');return value.slice(1).match(/../g).map(x=>parseInt(x,16)/255);}
function luminance(color){return color.map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4).reduce((sum,c,i)=>sum+c*[.2126,.7152,.0722][i],0);}
function ratio(a,b){const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);}
function readable(tokens,foreground,background,min=4.5){const actual=ratio(rgb(tokens[foreground]),rgb(tokens[background]));assert.ok(actual>=min,foreground+' on '+background+' has contrast '+actual.toFixed(2)+'; needs '+min);}
for(const [theme,tokens] of [['light',light],['dark',dark]]){
 test(theme+' text, search and technical surfaces retain readable contrast',()=>{
  const t=tokens();
  for(const background of ['--bg','--elevated','--selected'])for(const foreground of ['--ink','--muted','--accent'])readable(t,foreground,background);
  for(const foreground of ['--on-panel','--panel-muted','--panel-accent'])readable(t,foreground,'--panel');
  readable(t,'--focus','--bg',3);
  readable(t,'--panel-accent','--panel',3);
 });
 test(theme+' gradient text and white CTA text stay readable across the gradient',()=>{
  const t=tokens();
  for(const [start,end,foreground,background] of [
   ['--gradient-start','--gradient-end','--on-gradient',null],
   ['--display-start','--display-end',null,'--bg']
  ]){
   const a=rgb(t[start]),b=rgb(t[end]);
   for(let step=0;step<=100;step++){
    const color=a.map((channel,i)=>channel+(b[i]-channel)*step/100);
    const contrast=foreground?ratio(rgb(t[foreground]),color):ratio(color,rgb(t[background]));
    assert.ok(contrast>=4.5,theme+' gradient at '+step+'% has contrast '+contrast.toFixed(2));
   }
  }
 });
}
test('no-JavaScript dark preference matches the complete explicit dark palette',()=>{
 const explicit=declarations(block(':root[data-theme="dark"]'));
 assert.ok(Object.keys(explicit).length>=12,'dark theme must define its semantic palette');
 const fallback=declarations(block(':root:not([data-theme])'));
 assert.deepEqual(fallback,explicit);
 assert.match(css,/@media\s*\(prefers-color-scheme:\s*dark\)/);
 assert.match(block(':root'),/color-scheme:\s*light/);
 assert.match(block(':root[data-theme="dark"]'),/color-scheme:\s*dark/);
});
test('theme control remains visible, operable and rightmost at compact widths',()=>{
 assert.match(block('.header-actions'),/margin-left:\s*auto/);
 assert.match(block('.header-actions'),/display:\s*flex/);
 const toggle=block('.theme-toggle');
 assert.match(toggle,/min-height:\s*44px/);
 assert.match(toggle,/min-width:\s*44px/);
 assert.match(toggle,/flex-shrink:\s*0/);
 assert.match(block('.theme-toggle[hidden]'),/display:\s*none/);
 assert.match(css,/focus-visible[^{}]*\{[^}]*outline:\s*3px solid var\(--focus\)/);
 assert.doesNotMatch(css,/\.header-actions[^{}]*last-child[^{}]*\{[^}]*display:\s*none/);
});
test('text color fallbacks and reduced motion survive visual enhancement',()=>{
 assert.match(block('h1 em,h2 em'),/color:\s*var\(--accent\)/);
 assert.match(css,/@supports\s*\([^)]*background-clip:\s*text/);
 assert.match(css,/@media\s*\(prefers-reduced-motion:\s*reduce\)/);
 assert.match(block('.search input'),/color:\s*var\(--ink\)/);
 assert.match(block('.search li[aria-selected="true"]'),/background:\s*var\(--selected\)/);
});
test('all explicit CSS colors belong to the neutral and purple palette',()=>{
 const colors=[...new Set(css.match(/#[\da-f]{6}\b/gi)||[])];
 assert.ok(colors.length>10,'theme palette should expose auditable color values');
 for(const color of colors){const [r,g,b]=rgb(color);assert.ok(!(g>r&&g>b),'legacy green color remains: '+color);}
});

test('hovered links stay readable within technical and gradient sections',()=>{
 assert.match(block('.header nav a:hover,.text-link:hover'),/color:\s*var\(--accent\)/);
 for(const tokens of [light(),dark()]){
  for(const [selector,background] of [['.routing-visual,.dark-section','--panel'],['.closing','--gradient-end']]){
   const scoped={...tokens,...declarations(block(selector))};
   function resolve(name){const value=scoped[name];const alias=value?.match(/^var\((--[\w-]+)\)$/);return alias?resolve(alias[1]):value;}
   const contrast=ratio(rgb(resolve('--accent')),rgb(resolve(background)));
   assert.ok(contrast>=4.5,'hover accent within '+selector+' has contrast '+contrast.toFixed(2));
  }
 }
});
