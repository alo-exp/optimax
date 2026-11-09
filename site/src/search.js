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
  let links=[];
  const reset=()=>{links=[];results.replaceChildren();status.textContent=''};
  const dismiss=()=>{input.value='';reset();input.focus()};
  const render=()=>{
    const matches=searchIndex(index,input.value); links=[]; results.replaceChildren();
    if(input.value.trim().length<2){reset();return}
    status.textContent=matches.length ? `${matches.length} result${matches.length===1?'':'s'}` : 'No results found.';
    matches.forEach((row,i)=>{
      const item=document.createElement('li'), link=document.createElement('a'), label=document.createElement('span');
      link.setAttribute('href',sitePath(row.url,basePath)+'#'+row.anchor);link.textContent=row.title;
      link.addEventListener('keydown',event=>{
        if(event.key==='Escape'){event.preventDefault();dismiss();return}
        if(event.key==='ArrowDown'||event.key==='ArrowUp'){
          event.preventDefault();links[(i+(event.key==='ArrowDown'?1:-1)+links.length)%links.length].focus();
        }
      });
      links.push(link);label.textContent=row.page;item.append(link,label);results.append(item);
    });
  };
  input.addEventListener('input',render);
  input.addEventListener('keydown',event=>{
    if(event.key==='Escape'){event.preventDefault();dismiss();return}
    if(links.length&&(event.key==='ArrowDown'||event.key==='ArrowUp')){
      event.preventDefault();links[event.key==='ArrowDown'?0:links.length-1].focus();
    }
  });
  clear.addEventListener('click',dismiss);
  if(input.value.trim().length>=2) render();
}
