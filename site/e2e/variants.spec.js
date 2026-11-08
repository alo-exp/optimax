import {test,expect} from '@playwright/test';

const version='circuit',family='Sora';
for(const theme of ['dark','light'])for(const width of [320,390,1440]){
 test('Circuit preview works at '+width+'px in '+theme,async({page,context})=>{
  await page.setViewportSize({width,height:1000});await page.emulateMedia({colorScheme:theme==='dark'?'light':'dark',reducedMotion:'reduce'});
  await page.addInitScript(value=>{if(!localStorage.getItem('optimax-theme'))localStorage.setItem('optimax-theme',value)},theme);
  const failures=[];page.on('pageerror',error=>failures.push(error.message));page.on('console',message=>{if(message.type()==='error')failures.push('console: '+message.text()+' '+message.location().url)});
  page.on('request',request=>{if(/fonts\.(?:googleapis|gstatic)\.com/.test(request.url()))failures.push('remote font: '+request.url())});
  page.on('response',response=>{if(response.status()>=400)failures.push(response.status()+' '+response.url())});page.on('requestfailed',request=>failures.push(request.url()+' '+request.failure()?.errorText));
  const response=await page.goto('versions/'+version+'/');expect(response.status()).toBe(200);await page.evaluate(()=>document.fonts.ready);
  await expect(page.locator('h1')).toBeVisible();await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
  const weights=[400,700];const fonts=await page.evaluate(async({family,weights})=>{for(const weight of weights)await document.fonts.load(weight+' 20px "'+family+'"');return [...document.fonts].filter(face=>face.family.replace(/["']/g,'')===family).map(face=>({weight:face.weight,status:face.status}))},{family,weights});
  expect(fonts).toEqual(expect.arrayContaining(weights.map(weight=>({weight:String(weight),status:'loaded'}))));
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content',/noindex/);
  const dimensions=await page.evaluate(()=>({viewport:document.documentElement.clientWidth,width:document.documentElement.scrollWidth}));expect(dimensions.width).toBeLessThanOrEqual(dimensions.viewport+1);
  expect(await page.locator('a[href]').evaluateAll(links=>links.filter(a=>a.origin===location.origin&&a.pathname===location.pathname&&a.hash).map(a=>a.hash).filter(hash=>!document.getElementById(decodeURIComponent(hash.slice(1)))))).toEqual([]);
  const toggle=page.locator('#theme-toggle');await expect(toggle).toHaveAccessibleName('Dark theme');await expect(toggle).toHaveAttribute('aria-pressed',String(theme==='dark'));
  const nextTheme=theme==='dark'?'light':'dark';await toggle.click();await expect(page.locator('html')).toHaveAttribute('data-theme',nextTheme);await page.reload();await expect(page.locator('html')).toHaveAttribute('data-theme',nextTheme);
  const palette=await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue('--bg').trim());expect(await page.locator('meta[name="theme-color"]').getAttribute('content')).toBe(palette);
  await context.grantPermissions(['clipboard-read','clipboard-write']);
  const tabs=page.locator('[data-install-tab]'),panels=page.locator('[data-install-panel]');await expect(tabs).toHaveCount(2);await expect(panels).toHaveCount(2);
  const commands=['codex plugin marketplace add alo-labs/agent-plugins\ncodex plugin add optimax@alo-labs-codex','/plugin marketplace add alo-labs/agent-plugins\n/plugin install optimax@alo-labs'];
  for(let i=0;i<2;i++){await tabs.nth(i).click();await expect(tabs.nth(i)).toHaveAttribute('aria-pressed','true');await expect(panels.nth(i)).toBeVisible();await expect(panels.nth(1-i)).toBeHidden();expect(await panels.nth(i).textContent()).toBe(commands[i]);await page.locator('#copy-install').click();await expect(page.locator('#copy-status')).toHaveText('Copied to clipboard.');expect(await page.evaluate(()=>navigator.clipboard.readText())).toBe(commands[i]);}
  expect(failures).toEqual([]);
 });
}
test('Circuit theme remains operable with blocked storage',async({page})=>{
 await page.addInitScript(()=>Object.defineProperty(window,'localStorage',{get(){throw new Error('Storage blocked')}}));await page.goto('versions/circuit/');await expect(page.locator('html')).toHaveAttribute('data-theme','dark');await page.locator('#theme-toggle').click();await expect(page.locator('html')).toHaveAttribute('data-theme','light');
});
