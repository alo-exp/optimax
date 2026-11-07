import {test,expect} from '@playwright/test';

test('full-page light article captures include the actual offscreen footer glyphs',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.emulateMedia({colorScheme:'light',reducedMotion:'reduce'});
 await page.addInitScript(()=>localStorage.setItem('optimax-theme','light'));
 await page.goto('help/install-optimax/');await page.evaluate(()=>document.fonts.ready);
 const brand=page.locator('footer').getByRole('link',{name:'Optimax',exact:true});
 const box=await brand.evaluate(element=>{const r=element.getBoundingClientRect();return{x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height}});
 const png=(await page.screenshot({fullPage:true})).toString('base64');
 const lightPixels=await page.evaluate(async({png,box})=>{
  const bytes=Uint8Array.from(atob(png),character=>character.charCodeAt(0));
  const image=await createImageBitmap(new Blob([bytes],{type:'image/png'}));
  const canvas=document.createElement('canvas');canvas.width=Math.ceil(box.width);canvas.height=Math.ceil(box.height);
  const context=canvas.getContext('2d');context.drawImage(image,-box.x,-box.y);image.close();
  const {data}=context.getImageData(0,0,canvas.width,canvas.height);let count=0;
  for(let i=0;i<data.length;i+=4)if(data[i]>180&&data[i+1]>180&&data[i+2]>180)count++;
  return count;
 },{png,box});
 expect(lightPixels,'light footer brand glyphs must be painted in the actual PNG').toBeGreaterThan(100);
});
