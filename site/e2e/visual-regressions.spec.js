import {test,expect} from '@playwright/test';

async function ready(page,width=1536){
 await page.setViewportSize({width,height:1024});await page.goto('./');
 await page.evaluate(()=>document.fonts.ready);
}
function contrast(a,b){
 const luminance=color=>color.match(/[\d.]+/g).slice(0,3).map(Number).map(value=>{const channel=value/255;return channel<=.04045?channel/12.92:((channel+.055)/1.055)**2.4}).reduce((sum,value,i)=>sum+value*[.2126,.7152,.0722][i],0);
 const x=luminance(a),y=luminance(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);
}
test('Circuit actions retain contrasting keyboard outlines outside their rounded bounds',async({page})=>{
 await ready(page);await page.keyboard.press('Tab');
 for(const selector of ['.nav-cta','.hero-actions a:first-child','.hero-actions a:last-child','.closing .button']){
  const target=page.locator(selector);await target.focus();await expect(target).toBeFocused();
  const state=await target.evaluate(element=>{
   const style=getComputedStyle(element),bounds=element.getBoundingClientRect(),width=parseFloat(style.outlineWidth),offset=parseFloat(style.outlineOffset),point={x:bounds.left+bounds.width/2,y:bounds.top-offset-width/2};let surface=document.elementFromPoint(point.x,point.y)||element.parentElement,background=getComputedStyle(surface).backgroundColor;
   while(surface&&/rgba\([^)]*,\s*0\)$/.test(background)){surface=surface.parentElement;if(surface)background=getComputedStyle(surface).backgroundColor;}
   return {visible:element.matches(':focus-visible'),width,offset,color:style.outlineColor,background,point,bounds:bounds.toJSON()};
  });
  expect(state.visible,selector+' must have keyboard focus').toBe(true);
  expect(state.width).toBeGreaterThanOrEqual(3);
  expect(state.offset,selector+' outline must remain outside its rounded edge').toBeGreaterThanOrEqual(state.width);
  expect(contrast(state.color,state.background),selector+' focus ring contrast').toBeGreaterThanOrEqual(3);
 }
});
test('Circuit controls and circular junctions retain their selected geometry',async({page})=>{
 await ready(page);
 for(const [selector,radius]of [['.hero-actions .button','6px'],['.theme-toggle','8px'],['.terminal','12px'],['.routing-visual .junction','50%']])expect(await page.locator(selector).first().evaluate(element=>getComputedStyle(element).borderTopLeftRadius)).toBe(radius);
 const junctions=await page.locator('.routing-visual .junction').evaluateAll(elements=>elements.map(element=>{const style=getComputedStyle(element),box=element.getBoundingClientRect();return{width:box.width,height:box.height,border:parseFloat(style.borderWidth),background:style.backgroundColor}}));
 expect(junctions).toHaveLength(4);for(const junction of junctions){expect(junction.width).toBe(12);expect(junction.height).toBe(12);expect(junction.border).toBeGreaterThanOrEqual(1);expect(junction.background).toBe('rgb(8, 21, 37)');}
});
test('light-theme copy hover retains readable contrast and the command-accent border',async({page})=>{
 await ready(page);await page.locator('#theme-toggle').click();await page.locator('#copy-install').hover();
 const state=await page.locator('#copy-install').evaluate(element=>{const style=getComputedStyle(element);return {foreground:style.color,background:style.backgroundColor,border:style.borderTopColor}});
 expect(contrast(state.foreground,state.background)).toBeGreaterThanOrEqual(4.5);
 expect(state.border).toBe('rgb(129, 170, 255)');
});
for(const width of [1280,1440,1536,1600])test('wide Circuit keeps its subtitle and independent assignment titles on one line at '+width,async({page})=>{
 await ready(page,width);
 const boxes=await page.evaluate(()=>{function lines(element){const range=document.createRange();range.selectNodeContents(element);return new Set([...range.getClientRects()].map(rect=>Math.round(rect.top))).size}const rect=selector=>document.querySelector(selector).getBoundingClientRect().toJSON();return{subtitleLines:lines(document.querySelector('.hero-deck')),taskLines:[...document.querySelectorAll('.parallel-tasks strong')].map(lines),header:rect('.header'),hero:rect('.hero-field'),parallel:rect('.parallel-plan'),register:rect('.routing-visual'),next:rect('#how-it-works h2'),note:rect('#plan-note')};});
 expect(boxes.subtitleLines).toBe(1);expect(boxes.taskLines).toEqual([1,1,1]);expect(boxes.hero.top-boxes.header.bottom).toBeGreaterThanOrEqual(60);expect(boxes.parallel.top-boxes.hero.bottom).toBeGreaterThanOrEqual(80);expect(boxes.register.top).toBeGreaterThan(boxes.parallel.top);expect(boxes.next.top).toBeGreaterThan(boxes.register.bottom);expect(boxes.note.top).toBeGreaterThan(boxes.next.bottom);
});
