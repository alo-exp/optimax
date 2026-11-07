import {test,expect} from '@playwright/test';

const variants={circuit:'Sora',prism:'Bricolage Grotesque',stage:'DM Sans',press:'Archivo Narrow'};
for(const version of Object.keys(variants))for(const theme of ['dark','light'])for(const width of [320,390,1440]){
 test(`${version} preview works at ${width}px in ${theme}`,async({page,context})=>{
  await page.setViewportSize({width,height:['stage','press'].includes(version)?844:1000});await page.emulateMedia({colorScheme:theme==='dark'?'light':'dark',reducedMotion:'reduce'});
  await page.addInitScript(value=>{if(!localStorage.getItem('optimax-theme'))localStorage.setItem('optimax-theme',value)},theme);
  const failures=[];page.on('pageerror',error=>failures.push(error.message));page.on('console',message=>{if(message.type()==='error')failures.push(`console: ${message.text()} ${message.location().url}`)});
  page.on('request',request=>{if(/fonts\.(?:googleapis|gstatic)\.com/.test(request.url()))failures.push('remote font: '+request.url())});
  page.on('response',response=>{if(response.status()>=400)failures.push(`${response.status()} ${response.url()}`)});page.on('requestfailed',request=>failures.push(`${request.url()} ${request.failure()?.errorText}`));
  const response=await page.goto(`versions/${version}/`);expect(response.status()).toBe(200);await page.evaluate(()=>document.fonts.ready);
  await expect(page.locator('h1')).toBeVisible();await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
  const family=variants[version];
  const fonts=await page.evaluate(async family=>{for(const weight of [400,700])await document.fonts.load(`${weight} 20px "${family}"`);return [...document.fonts].filter(face=>face.family.replace(/["']/g,'')===family).map(face=>({weight:face.weight,status:face.status}))},family);
  expect(fonts).toEqual(expect.arrayContaining([{weight:'400',status:'loaded'},{weight:'700',status:'loaded'}]));
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute('content',/noindex/);
  const dimensions=await page.evaluate(()=>({viewport:document.documentElement.clientWidth,width:document.documentElement.scrollWidth}));expect(dimensions.width).toBeLessThanOrEqual(dimensions.viewport+1);
  expect(await page.locator('a[href]').evaluateAll(links=>links.filter(a=>a.origin===location.origin&&a.pathname===location.pathname&&a.hash).map(a=>a.hash).filter(hash=>!document.getElementById(decodeURIComponent(hash.slice(1)))))).toEqual([]);
  if(version==='stage'){
   const tooSmall=await page.locator('small,.section-caption,.plan-meta,.plan-meta *,.ticker,.ticker *,.command-heading,.command-heading *,.footer-links>span,.footer-bottom,.footer-bottom *').evaluateAll(elements=>elements.filter(element=>[...element.childNodes].some(node=>node.nodeType===3&&node.textContent.trim())).map(element=>({text:element.textContent.replace(/\s+/g,' ').trim(),size:parseFloat(getComputedStyle(element).fontSize)})).filter(element=>element.size<12));
   expect.soft(tooSmall,'Stage functional labels must remain at least 12px').toEqual([]);
  }
  if(version==='press'){
   const actions=await page.locator('a[href="#install"]').evaluateAll(elements=>new Promise(resolve=>{
    const seen=new Map(),observer=new IntersectionObserver(entries=>{for(const entry of entries)seen.set(entry.target,{width:entry.boundingClientRect.width,height:entry.boundingClientRect.height,visibleWidth:entry.intersectionRect.width,visibleHeight:entry.intersectionRect.height,intersecting:entry.isIntersecting});if(seen.size===elements.length){observer.disconnect();resolve([...seen.values()])}});
    if(elements.length)elements.forEach(element=>observer.observe(element));else resolve([]);
   }));
   expect.soft(actions.filter(action=>action.intersecting&&action.width>0&&action.height>=44&&action.visibleWidth>=action.width-.5&&action.visibleHeight>=action.height-.5),'Press needs a fully visible first-viewport install action').not.toHaveLength(0);
   const brands=await page.locator('.brand').evaluateAll(elements=>elements.map(element=>{const style=getComputedStyle(element);return{label:element.textContent.trim(),ratio:(parseFloat(style.letterSpacing)||0)/parseFloat(style.fontSize)}}));
   expect(brands.length).toBeGreaterThan(0);for(const brand of brands)expect.soft(brand.ratio,'Press brand tracking must be at least -0.04em').toBeGreaterThanOrEqual(-.04);
  }
  if(['stage','press'].includes(version)&&width<=390){
   const clearance=await page.locator('.parallel-tasks > li,.acceptance-boundary').evaluateAll(rows=>{
    const bounds=rect=>({left:rect.left,right:rect.right,top:rect.top,bottom:rect.bottom});
    const groups=rows.map(row=>[...row.querySelectorAll('strong,small')].map(node=>{const range=document.createRange();range.selectNodeContents(node);return{text:node.textContent,lines:[...range.getClientRects()].map(bounds),row:bounds(row.getBoundingClientRect())}}));
    const labels=groups.flat();
    const overlaps=[];
    for(let a=0;a<labels.length;a++)for(let b=a+1;b<labels.length;b++)if(labels[a].lines.some(x=>labels[b].lines.some(y=>Math.min(x.right,y.right)-Math.max(x.left,y.left)>.5&&Math.min(x.bottom,y.bottom)-Math.max(x.top,y.top)>.5)))overlaps.push([labels[a].text,labels[b].text]);
    return{rows:rows.map(row=>bounds(row.getBoundingClientRect())),labels,overlaps,textGaps:groups.slice(1).map((labels,i)=>Math.min(...labels.flatMap(label=>label.lines.map(line=>line.top)))-Math.max(...groups[i].flatMap(label=>label.lines.map(line=>line.bottom))))};
   });
   expect(clearance.rows).toHaveLength(4);expect(clearance.labels).toHaveLength(8);expect(clearance.overlaps).toEqual([]);
   for(const {row,lines}of clearance.labels)for(const line of lines){expect(line.left).toBeGreaterThanOrEqual(Math.max(0,row.left)-1);expect(line.right).toBeLessThanOrEqual(Math.min(width,row.right)+1);expect(line.top).toBeGreaterThanOrEqual(row.top-1);expect(line.bottom).toBeLessThanOrEqual(row.bottom+1);}
   for(let i=1;i<clearance.rows.length;i++)expect(clearance.rows[i].top-clearance.rows[i-1].bottom).toBeGreaterThanOrEqual(0);
   for(const gap of clearance.textGaps)expect(gap).toBeGreaterThanOrEqual(8);
  }
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
for(const version of Object.keys(variants))test(`${version} theme remains operable with blocked storage`,async({page})=>{
 await page.addInitScript(()=>Object.defineProperty(window,'localStorage',{get(){throw new Error('Storage blocked')}}));await page.goto(`versions/${version}/`);await expect(page.locator('html')).toHaveAttribute('data-theme','dark');await page.locator('#theme-toggle').click();await expect(page.locator('html')).toHaveAttribute('data-theme','light');
});
