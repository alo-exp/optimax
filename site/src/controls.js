export function installControls({tabs,panels,button,status,clipboard}) {
  let selected=0, generation=0, pending=false;
  const select=i=>{if(i!==selected){generation++;status.textContent=''} selected=i; tabs.forEach((tab,n)=>tab.setAttribute('aria-pressed',String(n===i)));panels.forEach((panel,n)=>{panel.hidden=n!==i;const group=panel.parentElement;if(group?.getAttribute('role')==='group')group.hidden=n!==i})};
  tabs.forEach((tab,i)=>tab.addEventListener('click',()=>select(i)));
  button.addEventListener('click',async()=>{
    if(pending)return;
    pending=true; button.disabled=true;
    const attempt=++generation; status.textContent='';
    try { await clipboard.writeText(panels[selected].textContent); if(attempt===generation) status.textContent='Copied to clipboard.'; }
    catch { if(attempt===generation) status.textContent='Copy unavailable. Select the command and copy manually.'; }
    finally { pending=false; button.disabled=false; }
  });
  select(0);
  panels.forEach(panel=>{const label=panel.previousElementSibling;if(label?.hasAttribute('data-install-label'))label.hidden=true});
  tabs.forEach(tab=>tab.disabled=false); button.disabled=false;
}
