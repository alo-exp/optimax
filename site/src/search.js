import {sitePath,validateBasePath} from './deployment.js';
const safePath = row => /^\/help\/[a-z0-9-]+\/$/.test(row.url) && /^[a-z0-9-]+$/.test(row.anchor);
export function searchIndex(index, query) {
  const q = query.trim().toLowerCase();
  if (q.length < 2) return [];
  const terms = q.split(/\s+/);
  return index.filter(row => safePath(row)).map(row => {
    const title = row.title.toLowerCase(), page = row.page.toLowerCase(), text = row.text.toLowerCase();
    if (!terms.every(term => (title + ' ' + page + ' ' + text).includes(term))) return null;
    return {row, score:terms.reduce((score,term)=>score + (title.includes(term)?4:0) + (page.includes(term)?2:0) + (text.includes(term)?1:0),0)};
  }).filter(Boolean).sort((a,b)=>b.score-a.score).slice(0,8).map(x=>x.row);
}
export function attachSearch({input,results,status,clear,document,index,basePath='/'}) {
  validateBasePath(basePath);
  let matches=[], selected=-1;
  const reset=()=>{matches=[];selected=-1;results.replaceChildren();status.textContent='';input.setAttribute('aria-expanded','false');input.setAttribute('aria-activedescendant','')};
  const render=()=>{
    matches=searchIndex(index,input.value); selected=-1; results.replaceChildren(); input.setAttribute('aria-activedescendant','');
    if(input.value.trim().length<2){reset();return}
    status.textContent=matches.length ? `${matches.length} result${matches.length===1?'':'s'}` : 'No results found.';
    input.setAttribute('aria-expanded',String(matches.length>0));
    matches.forEach((row,i)=>{
      const item=document.createElement('li'), link=document.createElement('a'), label=document.createElement('span');
      item.setAttribute('role','option');item.setAttribute('id',`search-result-${i}`);
      link.setAttribute('href',sitePath(row.url,basePath)+'#'+row.anchor);link.textContent=row.title;
      label.textContent=row.page;item.append(link,label);results.append(item);
    });
  };
  input.addEventListener('input',render);
  input.addEventListener('keydown',event=>{
    if(event.key==='Escape'){reset();return}
    if(!matches.length)return;
    if(event.key==='ArrowDown'||event.key==='ArrowUp'){
      event.preventDefault(); selected=selected<0 ? (event.key==='ArrowDown'?0:matches.length-1) : (selected+(event.key==='ArrowDown'?1:-1)+matches.length)%matches.length;
      input.setAttribute('aria-activedescendant',`search-result-${selected}`);
      Array.from(results.children).forEach((item,i)=>item.setAttribute('aria-selected',String(i===selected)));
    } else if(event.key==='Enter' && selected>=0){
      event.preventDefault(); const row=matches[selected]; document.location=sitePath(row.url,basePath)+'#'+row.anchor;
    }
  });
  clear.addEventListener('click',()=>{input.value='';reset();input.focus()});
}
