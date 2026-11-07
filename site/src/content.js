export const escapeHtml = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const slugify = value => value.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
export function buildContent(data) {
  const pages=[], index=[], slugs=new Set();
  if(!Array.isArray(data.articles)) throw new Error('Articles must be an array');
  for(const article of data.articles) {
    if(!/^[a-z0-9-]+$/.test(article.slug)||slugs.has(article.slug)) throw new Error('Invalid or duplicate slug');
    slugs.add(article.slug);
    const anchors=new Set(), url='/help/'+article.slug+'/';
    const sections=article.sections.map(section=>{
      const anchor=slugify(section.heading);
      if(!anchor||anchors.has(anchor)) throw new Error('Invalid or duplicate anchor');
      anchors.add(anchor);
      const paragraphs=section.paragraphs||[], bullets=section.bullets||[], links=section.links||[];
      for(const link of links) if(!/^(https:\/\/|\/(?!\/))/.test(link.href)) throw new Error('Invalid link');
      index.push({page:article.title,url,anchor,title:section.heading,text:[article.description,...(article.keywords||[]),...paragraphs,...bullets,section.code?.text||'',...links.map(l=>l.label)].filter(Boolean).join(' ')});
      return `<section id="${anchor}" class="article-section"><h2>${escapeHtml(section.heading)}</h2>${paragraphs.map(p=>`<p>${escapeHtml(p)}</p>`).join('')}${bullets.length?'<ul>'+bullets.map(b=>`<li>${escapeHtml(b)}</li>`).join('')+'</ul>':''}${section.code?`<pre><code>${escapeHtml(section.code.text)}</code></pre>`:''}${links.length?'<p>'+links.map(l=>`<a href="${escapeHtml(l.href)}">${escapeHtml(l.label)} →</a>`).join(' · ')+'</p>':''}</section>`;
    }).join('');
    pages.push({url,article,html:sections});
  }
  return {pages,index};
}
