import {test,expect} from '@playwright/test';

async function ready(page,width=1536){
 await page.setViewportSize({width,height:1024});await page.goto('./');
 await page.evaluate(()=>document.fonts.ready);
}
function contrast(a,b){
 const luminance=color=>color.match(/[\d.]+/g).slice(0,3).map(Number).map(value=>{const channel=value/255;return channel<=.04045?channel/12.92:((channel+.055)/1.055)**2.4}).reduce((sum,value,i)=>sum+value*[.2126,.7152,.0722][i],0);
 const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);
}
test('clipped action controls keep contrasting keyboard outlines inside their painted bounds',async({page})=>{
 await ready(page);await page.keyboard.press('Tab');
 for(const selector of ['.nav-cta','.hero-actions a:first-child','.hero-actions a:last-child','.closing .button']){
  const target=page.locator(selector);await target.focus();await expect(target).toBeFocused();
  const state=await target.evaluate(element=>{
   const style=getComputedStyle(element);let surface=element,background=style.backgroundColor;
   while(surface&&/rgba\([^)]*,\s*0\)$/.test(background)){surface=surface.parentElement;if(surface)background=getComputedStyle(surface).backgroundColor;}
   return {visible:element.matches(':focus-visible'),width:parseFloat(style.outlineWidth),offset:parseFloat(style.outlineOffset),color:style.outlineColor,background};
  });
  expect(state.visible,selector+' must have keyboard focus').toBe(true);
  expect(state.width).toBeGreaterThanOrEqual(3);
  expect(state.offset,selector+' outline must be inside its clip').toBeLessThanOrEqual(-state.width);
  expect(contrast(state.color,state.background),selector+' focus ring contrast').toBeGreaterThanOrEqual(3);
 }
});
test('each clipped component uses its own corner size and the number badge has a dark inset',async({page})=>{
 await ready(page);
 for(const [selector,cut] of [['.nav-cta',8],['.route-row',13],['.routing-visual',20],['.acceptance-boundary',9]]){
  const clip=await page.locator(selector).first().evaluate(element=>getComputedStyle(element).clipPath);
  expect(clip,selector+' uses its own cut').toMatch(new RegExp('^polygon\\('+cut+'px '));
 }
 const badge=await page.locator('.route-number').first().evaluate(element=>{const style=getComputedStyle(element),box=element.getBoundingClientRect();return {background:style.backgroundColor,color:style.color,width:box.width,height:box.height}});
 expect(badge.background).toBe('rgb(8, 40, 32)');expect(badge.color).toBe('rgb(236, 234, 233)');
 expect(badge.width).toBeGreaterThanOrEqual(48);expect(badge.height).toBeGreaterThanOrEqual(44);
});
test('light-theme copy hover retains readable contrast on the technical surface',async({page})=>{
 await ready(page);await page.locator('#theme-toggle').click();await page.locator('#copy-install').hover();
 const state=await page.locator('#copy-install').evaluate(element=>{const style=getComputedStyle(element);return {foreground:style.color,background:style.backgroundColor,decoration:style.textDecorationLine}});
 expect(contrast(state.foreground,state.background)).toBeGreaterThanOrEqual(4.5);
 expect(state.decoration).toContain('underline');
});
for(const width of [1280,1440,1536,1600])test('wide manifest keeps its subtitle and independent assignments on one line at '+width,async({page})=>{
 await ready(page,width);
 const boxes=await page.evaluate(()=>{
  function textLines(selector){const element=document.querySelector(selector),range=document.createRange();range.selectNodeContents(element);return [...range.getClientRects()].map(rect=>Math.round(rect.top)).filter((value,index,array)=>array.indexOf(value)===index).length;}
  const subtitle=document.querySelector('.hero-deck'),style=getComputedStyle(subtitle),canvas=document.createElement('canvas'),context=canvas.getContext('2d');context.font='700 38px "Mona Sans"';
  return {subtitle38pxWidth:context.measureText(subtitle.textContent).width,subtitleAvailable:subtitle.clientWidth-parseFloat(style.paddingLeft)-parseFloat(style.paddingRight),subtitleLines:textLines('.hero-deck'),taskLines:[...document.querySelectorAll('.route-row strong')].map((_,i)=>textLines('.route-row:nth-child('+(i+1)+') strong')),hero:document.querySelector('.hero-field').getBoundingClientRect().toJSON(),parallel:document.querySelector('#parallel-title').getBoundingClientRect().toJSON(),register:document.querySelector('.routing-visual').getBoundingClientRect().toJSON(),next:document.querySelector('#how-it-works h2').getBoundingClientRect().toJSON(),note:document.querySelector('.visual-note').getBoundingClientRect().toJSON()};
 });
 expect(boxes.subtitleLines,JSON.stringify(boxes)).toBe(1);expect(boxes.taskLines).toEqual([1,1,1]);
 expect(boxes.note.top).toBeGreaterThan(boxes.next.bottom);
 if(width===1536){
  expect(Math.abs(boxes.hero.y-110)).toBeLessThanOrEqual(4);expect(Math.abs(boxes.hero.height-372)).toBeLessThanOrEqual(12);
  expect(Math.abs(boxes.parallel.y-529)).toBeLessThanOrEqual(12);expect(Math.abs(boxes.register.y-611)).toBeLessThanOrEqual(12);
  expect(Math.abs(boxes.register.height-271)).toBeLessThanOrEqual(12);expect(Math.abs(boxes.next.y-947)).toBeLessThanOrEqual(16);
 }
});
