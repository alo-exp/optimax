import {test,expect} from '@playwright/test';

for(const theme of ['dark','light']){
 test(`all 17 help articles render without browser failures at 390px in ${theme}`,async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.emulateMedia({colorScheme:theme,reducedMotion:'reduce'});
  await page.addInitScript(value=>localStorage.setItem('optimax-theme',value),theme);
  const failures=[];
  page.on('pageerror',error=>failures.push(error.message));
  page.on('console',message=>{if(message.type()==='error')failures.push(`console: ${message.text()} ${message.location().url}`)});
  page.on('response',response=>{if(response.status()>=400)failures.push(`${response.status()} ${response.url()}`)});
  page.on('requestfailed',request=>failures.push(`request failed: ${request.url()} ${request.failure()?.errorText}`));
  const indexResponse=await page.goto('help/');expect(indexResponse.status()).toBe(200);
  const icon=page.locator('link[rel="icon"]');await expect(icon).toHaveCount(1);
  const iconURL=new URL(await icon.getAttribute('href'),page.url());
  expect(iconURL.pathname).toBe(new URL('../favicon.svg',page.url()).pathname);
  expect((await page.request.get(iconURL.href)).status(),iconURL.href).toBe(200);
  const articles=await page.locator('.article-link').evaluateAll(links=>links.map(link=>link.href));
  expect(articles).toHaveLength(17);expect(new Set(articles).size).toBe(17);
  for(const article of articles){
   const response=await page.goto(article);expect(response.status(),article).toBe(200);
   await page.evaluate(()=>document.fonts.ready);
   await expect(page.locator('h1'),article).toBeVisible();
   await expect(page.locator('html'),article).toHaveAttribute('data-theme',theme);
   const state=await page.evaluate(()=>({
    viewport:document.documentElement.clientWidth,width:document.documentElement.scrollWidth,
    brokenImages:[...document.images].filter(image=>!image.complete||!image.naturalWidth).map(image=>image.src),
    brokenFragments:[...document.querySelectorAll('a[href]')].filter(link=>link.origin===location.origin&&link.pathname===location.pathname&&link.hash).map(link=>link.hash).filter(hash=>{try{return !document.getElementById(decodeURIComponent(hash.slice(1)))}catch{return true}})
   }));
   expect(state.width,`${article} overflows at 390px in ${theme}`).toBeLessThanOrEqual(state.viewport+1);
   expect(state.brokenImages,article).toEqual([]);expect(state.brokenFragments,article).toEqual([]);
  }
  expect(failures).toEqual([]);
 });
}
