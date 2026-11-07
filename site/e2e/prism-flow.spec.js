import {test,expect} from '@playwright/test';

for(const theme of ['dark','light'])for(const width of [320,390,1440]){
 test(`Prism flow keeps every label clear of its visible curves at ${width}px in ${theme}`,async({page})=>{
  await page.setViewportSize({width,height:1000});
  await page.emulateMedia({colorScheme:theme,reducedMotion:'reduce'});
  await page.addInitScript(value=>localStorage.setItem('optimax-theme',value),theme);
  await page.goto('versions/prism/');
  await page.evaluate(()=>document.fonts.ready);
  await expect(page.locator('html')).toHaveAttribute('data-theme',theme);
  const tracks=page.locator('.work-track');
  await expect(tracks).toHaveCount(3);
  const headings=['Investigate own scope','Implement own files','Verify independent work'];
  for(let i=0;i<3;i++){
   await expect(tracks.nth(i).locator('strong')).toHaveText(headings[i]);
   await expect(tracks.nth(i).locator('strong')).toBeVisible();
   await expect(tracks.nth(i).locator('small')).toHaveText('READY / PARALLEL');
   await expect(tracks.nth(i).locator('small')).toBeVisible();
   await expect(tracks.nth(i).locator('.track-line')).toBeVisible();
  }
  await expect(page.locator('.flow-acceptance strong')).toHaveText('Integrate after acceptance');
  await expect(page.locator('.flow-acceptance small')).toHaveText('WAITING / DEPENDENCIES');
  await expect(page.locator('.flow-acceptance')).toBeVisible();
  const geometry=await page.locator('.flow-diagram').evaluate(diagram=>{
   // Use rendered text ranges, not padded label boxes, and transform actual SVG
   // path samples into the same viewport coordinate system. Include the stroke
   // radius and two pixels of clearance so a curve cannot merely graze letters.
   const labels=[...diagram.querySelectorAll('strong,small')].flatMap(element=>{
    const range=document.createRange();range.selectNodeContents(element);
    return [...range.getClientRects()].map(rect=>({text:element.textContent,left:rect.left,right:rect.right,top:rect.top,bottom:rect.bottom}));
   });
   const collisions=[],curves=[];
   for(const [index,path] of [...diagram.querySelectorAll('.track-line path')].entries()){
    const style=getComputedStyle(path),matrix=path.getScreenCTM(),length=path.getTotalLength();
    const radius=parseFloat(style.strokeWidth)/2+2;
    curves.push({width:path.getBoundingClientRect().width,length,stroke:style.stroke,opacity:style.opacity,display:style.display,visibility:style.visibility});
    for(let distance=0;distance<=length;distance+=.5){
     const point=path.getPointAtLength(distance).matrixTransform(matrix);
     const hit=labels.find(rect=>point.x>=rect.left-radius&&point.x<=rect.right+radius&&point.y>=rect.top-radius&&point.y<=rect.bottom+radius);
     if(hit){collisions.push({track:index+1,text:hit.text,x:Math.round(point.x),y:Math.round(point.y)});break;}
    }
   }
   return {collisions,curves,trackWidth:diagram.querySelector('.work-track').getBoundingClientRect().width,labelsInside:labels.every(rect=>rect.left>=0&&rect.right<=innerWidth),acceptanceBelow:diagram.querySelector('.flow-acceptance').getBoundingClientRect().top>=diagram.querySelector('.flow-tracks').getBoundingClientRect().bottom};
  });
  expect(geometry.collisions,'visible curve strokes must leave headings and status text clear').toEqual([]);
  expect(geometry.labelsInside,'all label text stays within the viewport').toBe(true);
  expect(geometry.acceptanceBelow,'acceptance remains after all three tracks').toBe(true);
  expect(geometry.curves).toHaveLength(3);
  for(const curve of geometry.curves){
   expect(curve.length).toBeGreaterThan(1100);
   expect(curve.width).toBeGreaterThan(geometry.trackWidth*.95);
   expect(curve.stroke).not.toBe('none');expect(Number(curve.opacity)).toBeGreaterThan(0);
   expect(curve.display).not.toBe('none');expect(curve.visibility).toBe('visible');
  }
 });
}
