import {chromium} from '@playwright/test';
import {mkdir} from 'node:fs/promises';
import {join} from 'node:path';
import {createPreviewServer,builtBasePath} from '../scripts/preview.mjs';
const directory=process.env.OPTIMAX_CAPTURE_DIR||'.impeccable/review';
const prefix=process.env.OPTIMAX_CAPTURE_PREFIX||'final';
const screens=[['home','',1440,1000],['home','',390,844],['help','help/',1440,1000],['article','help/install-optimax/',390,844]];
let count=0;
await mkdir(directory,{recursive:true});
const server=createPreviewServer();
const browser=await chromium.launch({channel:'chromium',headless:true});
try{
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve)});
 const baseURL=`http://127.0.0.1:${server.address().port}${builtBasePath()}`;
 for(const [name,path,width,height] of screens){
  for(const theme of ['dark','light']){
   const context=await browser.newContext({viewport:{width,height},colorScheme:theme,reducedMotion:'reduce'});
   await context.addInitScript(value=>localStorage.setItem('optimax-theme',value),theme);
   const page=await context.newPage();const response=await page.goto(new URL(path,baseURL).href);if(!response.ok())throw new Error(`Capture route failed: ${path}`);await page.evaluate(()=>document.fonts.ready);
   const filename=prefix==='final'&&name==='home'?`${width===1440?'desktop':'mobile'}${theme==='light'?'-light':''}.png`:`${prefix}-${name}-${width}-${theme}.png`;
   const file=join(directory,filename);
   await page.screenshot({path:file,fullPage:true});count++;
   await context.close();
  }
 }
 if(prefix==='final'){
  const context=await browser.newContext({viewport:{width:1536,height:1024},colorScheme:'dark',reducedMotion:'reduce'});
  await context.addInitScript(()=>localStorage.setItem('optimax-theme','dark'));
  const page=await context.newPage();const response=await page.goto(baseURL);if(!response.ok())throw new Error('Hero capture route failed');await page.evaluate(()=>document.fonts.ready);
  await page.screenshot({path:join(directory,'hero-repro.png'),fullPage:false});count++;await context.close();
  const focusContext=await browser.newContext({viewport:{width:1440,height:1000},colorScheme:'dark',reducedMotion:'reduce'});
  await focusContext.addInitScript(()=>localStorage.setItem('optimax-theme','dark'));
  const focusPage=await focusContext.newPage();await focusPage.goto(baseURL);await focusPage.evaluate(()=>document.fonts.ready);
  const nav=focusPage.getByRole('banner').getByRole('link',{name:'Get started',exact:true});
  for(let i=0;i<12&&!(await nav.evaluate(element=>element===document.activeElement));i++)await focusPage.keyboard.press('Tab');
  if(!(await nav.evaluate(element=>element===document.activeElement)))throw new Error('Keyboard navigation never reached Get started');
  await focusPage.evaluate(()=>scrollTo(0,0));await focusPage.screenshot({path:join(directory,'focus-nav.png'),fullPage:false});count++;await focusContext.close();
  const searchContext=await browser.newContext({viewport:{width:1440,height:1000},colorScheme:'light',reducedMotion:'reduce'});
  await searchContext.addInitScript(()=>localStorage.setItem('optimax-theme','light'));
  const searchPage=await searchContext.newPage();const indexLoaded=searchPage.waitForResponse(response=>response.url().endsWith('/search-index.json'));
  await searchPage.goto(new URL('help/',baseURL).href);await indexLoaded;await searchPage.evaluate(()=>document.fonts.ready);
  const input=searchPage.locator('#help-search');await input.fill('install');await searchPage.locator('#search-results a').first().waitFor();await input.press('ArrowDown');
  if(!(await input.getAttribute('aria-activedescendant')))throw new Error('Search keyboard result is inactive');
  await searchPage.screenshot({path:join(directory,'search-active.png'),fullPage:false});count++;await searchContext.close();
 }
}finally{await browser.close();await new Promise(resolve=>server.close(resolve))}
console.log(`Saved ${count} captures in ${directory}`);
