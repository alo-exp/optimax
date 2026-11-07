export function installControls({tabs,panels,button,status,clipboard}) {
  let selected=0;
  const select=i=>{selected=i; tabs.forEach((tab,n)=>tab.setAttribute('aria-pressed',String(n===i)));panels.forEach((panel,n)=>panel.hidden=n!==i)};
  tabs.forEach((tab,i)=>tab.addEventListener('click',()=>select(i)));
  button.addEventListener('click',async()=>{
    try { await clipboard.writeText(panels[selected].textContent); status.textContent='Copied to clipboard.'; }
    catch { status.textContent='Copy unavailable. Select the command and copy manually.'; }
  });
  select(0);
}
