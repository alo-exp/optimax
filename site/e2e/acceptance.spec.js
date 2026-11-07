import {test,expect} from '@playwright/test';

test('dark starts under light OS preference; a deliberate light choice survives navigation and reload',async({page})=>{
 await page.emulateMedia({colorScheme:'light'});await page.goto('./');
 await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
 await page.locator('#theme-toggle').click();await expect(page.locator('html')).toHaveAttribute('data-theme','light');
 await page.goto('help/');await expect(page.locator('html')).toHaveAttribute('data-theme','light');
 await page.reload();await expect(page.locator('html')).toHaveAttribute('data-theme','light');
 await page.locator('#theme-toggle').click();await expect(page.locator('html')).toHaveAttribute('data-theme','dark');
});


test('a saved light choice wins over a dark OS preference on fresh navigation',async({page})=>{
 await page.emulateMedia({colorScheme:'dark'});
 await page.addInitScript(()=>localStorage.setItem('optimax-theme','light'));
 await page.goto('./');
 await expect(page.locator('html')).toHaveAttribute('data-theme','light');
 await expect(page.locator('#theme-toggle')).toHaveAttribute('aria-pressed','false');
 expect(await page.evaluate(()=>localStorage.getItem('optimax-theme'))).toBe('light');
});

test('keyboard users can reveal the skip link and reach main content',async({page})=>{
 await page.goto('./');await page.keyboard.press('Tab');
 const skip=page.getByRole('link',{name:'Skip to content'});await expect(skip).toBeFocused();await expect(skip).toBeInViewport();
 const focus=await skip.evaluate(element=>{const style=getComputedStyle(element);return {outline:style.outlineStyle,width:parseFloat(style.outlineWidth),shadow:style.boxShadow}});
 expect((focus.outline!=='none'&&focus.width>0)||focus.shadow!=='none','keyboard focus must have a visible indicator').toBe(true);
 await page.keyboard.press('Enter');await expect(page).toHaveURL(/#main$/);await expect(page.locator('main')).toBeInViewport();
});

test('the selected Mona Sans heading family and both supplied weights load real self-hosted glyphs',async({page})=>{
 await page.goto('./');
 const fonts=await page.evaluate(async()=>{
  const requested=[];
  for(const weight of [400,700]){
   const faces=await document.fonts.load(`${weight} 24px "Mona Sans"`,'Optimax');
   requested.push({weight,count:faces.length,loaded:faces.every(face=>face.status==='loaded')});
  }
  await document.fonts.ready;
  return {requested,heading:getComputedStyle(document.querySelector('h1')).fontFamily,resources:performance.getEntriesByType('resource').filter(entry=>entry.name.endsWith('.woff2')).map(entry=>new URL(entry.name).origin)};
 });
 for(const item of fonts.requested){expect(item.count,`Mona Sans ${item.weight} face must exist`).toBeGreaterThan(0);expect(item.loaded).toBe(true);}
 expect(fonts.heading).toMatch(/Mona Sans/i);expect(fonts.resources.length).toBeGreaterThanOrEqual(2);
 expect(fonts.resources.every(origin=>origin===new URL(page.url()).origin)).toBe(true);
});

test('both install platform tabs copy the actual selected commands using the clipboard',async({page,context})=>{
 await context.grantPermissions(['clipboard-read','clipboard-write']);await page.goto('./#install');
 const tabs=page.locator('[data-install-tab]');
 for(let i=0;i<await tabs.count();i++){
  await tabs.nth(i).click();await expect(tabs.nth(i)).toHaveAttribute('aria-pressed','true');
  const commands=await page.locator('[data-install-panel]:visible').textContent();expect(commands.trim().length).toBeGreaterThan(10);
  await page.locator('#copy-install').click();await expect(page.locator('#copy-status')).toHaveText('Copied to clipboard.');
  expect(await page.evaluate(()=>navigator.clipboard.readText())).toBe(commands);
 }
});

test('search supports typing, clear, escape and keyboard navigation to a real fragment',async({page})=>{
 const loaded=page.waitForResponse(response=>response.url().endsWith('/search-index.json'));await page.goto('help/');await loaded;
 const input=page.locator('#help-search');await input.fill('install');
 await expect(page.locator('#search-results a').first()).toBeVisible();
 await page.locator('#search-clear').click();await expect(input).toHaveValue('');await expect(input).toBeFocused();
 await input.fill('install');await expect(page.locator('#search-results a').first()).toBeVisible();await input.press('Escape');await expect(input).toHaveAttribute('aria-expanded','false');await expect(input).toBeFocused();
 await input.fill('installation');await expect(page.locator('#search-results a').first()).toBeVisible();
 const target=await page.locator('#search-results a').first().getAttribute('href');
 await input.press('ArrowDown');await input.press('Enter');await expect(page).toHaveURL(new URL(target,page.url()).href);
 const anchor=new URL(page.url()).hash;expect(anchor.length).toBeGreaterThan(1);await expect(page.locator(anchor)).toBeVisible();
 expect(await page.locator(anchor).evaluate(element=>element.getBoundingClientRect().top)).toBeGreaterThanOrEqual(0);
});

test('unavailable search index presents a useful browse fallback',async({page})=>{
 await page.route('**/search-index.json',route=>route.fulfill({status:503,body:'Unavailable'}));await page.goto('help/');
 await expect(page.locator('#search-status')).toHaveText('Search is unavailable. Browse the articles below.');
 await expect(page.locator('a[href$="/help/install-optimax/"]')).toBeVisible();
});


test('FAQ answers expand without overlapping the following question at mobile and desktop widths',async({page})=>{
 for(const width of [390,1440]){
  await page.setViewportSize({width,height:1000});await page.goto('./');
  const questions=page.locator('details');expect(await questions.count()).toBeGreaterThan(1);
  await questions.first().locator('summary').click();await expect(questions.first()).toHaveAttribute('open','');
  const answer=questions.first().locator('p');await expect(answer).toBeVisible();
  const answerBox=await answer.boundingBox(),next=await questions.nth(1).boundingBox();
  expect(next.y,`following question overlaps the expanded answer at ${width}px`).toBeGreaterThanOrEqual(answerBox.y+answerBox.height);
  await questions.first().locator('summary').click();await expect(answer).not.toBeVisible();
 }
});

for(const width of [320,390,768,1440])for(const theme of ['dark','light']){
 test(`public pages reflow without viewport overflow at ${width}px in ${theme}`,async({page})=>{
  await page.setViewportSize({width,height:900});await page.addInitScript(value=>localStorage.setItem('optimax-theme',value),theme);
  const failures=[];page.on('pageerror',error=>failures.push(error.message));page.on('response',response=>{if(response.status()>=400)failures.push(`${response.status()} ${response.url()}`)});
  page.on('console',message=>{if(message.type()==='error')failures.push(`console: ${message.text()}`)});
  page.on('requestfailed',request=>failures.push(`request failed: ${request.url()} ${request.failure()?.errorText}`));
  for(const route of ['./','help/','help/install-optimax/']){
   await page.goto(route);await page.evaluate(()=>document.fonts.ready);
   await expect(page.locator('main')).toBeVisible();await expect(page.locator('h1')).toBeVisible();
   const dimensions=await page.evaluate(()=>({viewport:document.documentElement.clientWidth,width:document.documentElement.scrollWidth}));
   expect(dimensions.width,`${route} overflows at ${width}px`).toBeLessThanOrEqual(dimensions.viewport+1);
   const brokenImages=await page.locator('img').evaluateAll(images=>images.filter(image=>!image.complete||!image.naturalWidth).map(image=>image.src));expect(brokenImages).toEqual([]);
   if(route==='./')expect(await page.locator('a[href]').evaluateAll(links=>links.filter(link=>link.origin===location.origin&&link.pathname===location.pathname&&link.hash).map(link=>link.hash).filter(hash=>!document.getElementById(decodeURIComponent(hash.slice(1)))))).toEqual([]);
  }
  expect(failures).toEqual([]);
 });
}
