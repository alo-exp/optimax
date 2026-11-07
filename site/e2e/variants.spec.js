import {test,expect} from '@playwright/test';

const variants={circuit:'Sora',prism:'Bricolage Grotesque',stage:'DM Sans',press:'Archivo Narrow',continuum:'Figtree'};
for(const version of Object.keys(variants))for(const theme of ['dark','light'])for(const width of (version==='continuum'?[320,390,768,1440]:[320,390,1440])){
 test(`${version} preview works at ${width}px in ${theme}`,async({page,context})=>{
  await page.setViewportSize({width,height:['stage','press','continuum'].includes(version)?844:1000});await page.emulateMedia({colorScheme:theme==='dark'?'light':'dark',reducedMotion:'reduce'});
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
  if(version==='continuum'){
   expect(await page.locator('h1').evaluate(element=>getComputedStyle(element).fontFamily)).toContain(family);
   if(width<=390){
    const signature=page.locator('.hero .hero-signature');await expect(signature).toHaveCount(1);await expect(signature).toBeVisible();await expect(signature.locator('.brand-mark')).toHaveCount(0);
    const gesture=await signature.boundingBox(),brand=await page.locator('.header .brand-mark').boundingBox();expect(gesture.width).toBeGreaterThanOrEqual(width*.5);expect(gesture.height).toBeGreaterThanOrEqual(48);expect(gesture.width*gesture.height).toBeGreaterThanOrEqual(brand.width*brand.height*6);expect(gesture.x).toBeGreaterThanOrEqual(0);expect(gesture.y).toBeGreaterThanOrEqual(0);expect(gesture.x+gesture.width).toBeLessThanOrEqual(width+1);expect(gesture.y+gesture.height).toBeLessThanOrEqual(844);
   }
   const tooSmall=await page.locator('body *').evaluateAll(elements=>elements.filter(element=>[...element.childNodes].some(node=>node.nodeType===3&&node.textContent.trim())&&!['SCRIPT','STYLE','SVG'].includes(element.tagName)&&element.getBoundingClientRect().width>0).map(element=>({text:element.textContent.replace(/\s+/g,' ').trim(),size:parseFloat(getComputedStyle(element).fontSize)})).filter(element=>element.size<12));expect(tooSmall,'functional text must remain at least 12px').toEqual([]);
   const actions=await page.locator('a[href="#install"]').evaluateAll(elements=>new Promise(resolve=>{const seen=new Map(),observer=new IntersectionObserver(entries=>{for(const entry of entries)seen.set(entry.target,{width:entry.boundingClientRect.width,height:entry.boundingClientRect.height,visibleWidth:entry.intersectionRect.width,visibleHeight:entry.intersectionRect.height});if(seen.size===elements.length){observer.disconnect();resolve([...seen.values()])}});if(elements.length)elements.forEach(element=>observer.observe(element));else resolve([])}));expect(actions.some(action=>action.width>0&&action.height>=44&&action.visibleWidth>=action.width-.5&&action.visibleHeight>=action.height-.5),'first viewport needs a fully usable installation action').toBe(true);
   const geometry=await page.locator('.routing-visual').evaluate(element=>{const rect=node=>{const box=node.getBoundingClientRect();return{left:box.left,right:box.right,top:box.top,bottom:box.bottom}},rows=[...element.querySelectorAll('.parallel-tasks>li,.acceptance-boundary')];const labels=rows.flatMap(row=>[...row.querySelectorAll('strong,small')].map(node=>{const range=document.createRange();range.selectNodeContents(node);return{text:node.textContent,row:rect(row),lines:[...range.getClientRects()].map(box=>({left:box.left,right:box.right,top:box.top,bottom:box.bottom}))}}));return{labels,junctions:[...element.querySelectorAll('.junction')].map(rect)}});
   expect(geometry.labels).toHaveLength(8);expect(geometry.junctions.length).toBeGreaterThanOrEqual(3);const intersects=(a,b)=>Math.min(a.right,b.right)-Math.max(a.left,b.left)>.5&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>.5;
   for(let a=0;a<geometry.labels.length;a++){const label=geometry.labels[a];for(const line of label.lines){expect(line.left).toBeGreaterThanOrEqual(Math.max(0,label.row.left)-1);expect(line.right).toBeLessThanOrEqual(Math.min(width,label.row.right)+1);for(const junction of geometry.junctions)expect(intersects(line,junction),'task text must clear junction artwork').toBe(false);}for(let b=a+1;b<geometry.labels.length;b++)expect(label.lines.some(line=>geometry.labels[b].lines.some(other=>intersects(line,other))),'task labels must not overlap').toBe(false);}
  }
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
  if(version==='continuum'){
   const questions=page.locator('#questions details');await expect(questions).toHaveCount(7);for(let i=0;i<7;i++){await questions.nth(i).locator('summary').click();const answer=questions.nth(i).locator('p');await expect(answer).toBeVisible();expect(await answer.evaluate(element=>parseFloat(getComputedStyle(element).fontSize))).toBeGreaterThanOrEqual(12);if(i<6){const box=await answer.boundingBox(),next=await questions.nth(i+1).boundingBox();expect(box.y+box.height).toBeLessThanOrEqual(next.y+1);}}
   await page.keyboard.press('Tab');
   const luminance=color=>color.match(/[\d.]+/g).slice(0,3).map(Number).map(value=>{const channel=value/255;return channel<=.04045?channel/12.92:((channel+.055)/1.055)**2.4}).reduce((sum,value,i)=>sum+value*[.2126,.7152,.0722][i],0);
   for(const selector of ['.nav-cta','.hero-actions a:first-child','#theme-toggle']){const target=page.locator(selector);await target.focus();await expect(target).toBeFocused();const focus=await target.evaluate(element=>{const style=getComputedStyle(element),bounds=element.getBoundingClientRect(),width=parseFloat(style.outlineWidth),offset=parseFloat(style.outlineOffset),point={x:bounds.left+bounds.width/2,y:bounds.top-offset-width/2};let surface=document.elementFromPoint(point.x,point.y)||element.parentElement,background=getComputedStyle(surface).backgroundColor;while(surface&&/rgba\([^)]*,\s*0\)$/.test(background)){surface=surface.parentElement;if(surface)background=getComputedStyle(surface).backgroundColor;}return{visible:element.matches(':focus-visible'),width,color:style.outlineColor,background,offset,point,bounds:bounds.toJSON()}});expect(focus.visible).toBe(true);expect(focus.width).toBeGreaterThanOrEqual(3);const a=luminance(focus.color),b=luminance(focus.background);expect((Math.max(a,b)+.05)/(Math.min(a,b)+.05),selector+' focus contrast').toBeGreaterThanOrEqual(3);}
  }
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

for(const theme of ['dark','light'])test(`Continuum desktop composition is complete in ${theme}`,async({page})=>{
 await page.setViewportSize({width:1440,height:1000});await page.emulateMedia({reducedMotion:'reduce',colorScheme:theme==='dark'?'light':'dark'});await page.addInitScript(value=>{if(!localStorage.getItem('optimax-theme'))localStorage.setItem('optimax-theme',value)},theme);await page.goto('versions/continuum/');await page.evaluate(()=>document.fonts.ready);
 await expect(page.locator('.parallel-tasks>li')).toHaveCount(3);await expect(page.locator('.acceptance-boundary')).toHaveCount(1);
 const composition=await page.evaluate(()=>{const bounds=box=>({left:box.left,right:box.right,top:box.top,bottom:box.bottom,width:box.width,height:box.height});const groups=['.parallel-plan','.acceptance-boundary'].map(selector=>({selector,...bounds(document.querySelector(selector).getBoundingClientRect())}));const labels=[...document.querySelectorAll('.parallel-tasks>li strong,.parallel-tasks>li small')].map(element=>{const range=document.createRange();range.selectNodeContents(element);return{text:element.textContent,lines:[...range.getClientRects()].map(bounds)}});return{groups,labels}});
 expect(composition.labels).toHaveLength(6);for(const item of composition.groups){expect(item.width,item.selector).toBeGreaterThan(0);expect(item.height,item.selector).toBeGreaterThan(0);expect(item.left,item.selector).toBeGreaterThanOrEqual(0);expect(item.right,item.selector).toBeLessThanOrEqual(1441);expect(item.top,item.selector).toBeGreaterThanOrEqual(0);expect(item.bottom,item.selector+' must fit the opening viewport').toBeLessThanOrEqual(1000);}
 for(const label of composition.labels){expect(label.lines.length,label.text).toBeGreaterThan(0);for(const line of label.lines){expect(line.width,label.text).toBeGreaterThan(0);expect(line.height,label.text).toBeGreaterThan(0);expect(line.left,label.text).toBeGreaterThanOrEqual(0);expect(line.right,label.text).toBeLessThanOrEqual(1441);expect(line.top,label.text).toBeGreaterThanOrEqual(0);expect(line.bottom,label.text+' must be fully visible').toBeLessThanOrEqual(1000);}}
});
