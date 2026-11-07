import {readFile,writeFile,mkdir,rm,copyFile,cp} from 'node:fs/promises';
import {dirname,join} from 'node:path';
import {buildContent,escapeHtml as e} from './src/content.js';
import {deploymentUrl,sitePath} from './src/deployment.js';
const deployment=deploymentUrl(process.env.SITE_URL), out='dist';
const prefix=path=>sitePath(path,deployment.basePath);
const absolute=path=>deployment.url+path.slice(1);
const data=JSON.parse(await readFile('content/articles.json','utf8'));
const {pages,index}=buildContent(data);
await rm(out,{recursive:true,force:true}); await mkdir(join(out,'assets'),{recursive:true});
async function write(path,value){const file=join(out,path);await mkdir(dirname(file),{recursive:true});await writeFile(file,value)}
const icon=(name)=>`<svg class="icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="square" stroke-linejoin="miter">${({arrow:'<path d="M4 12h15M13 5l7 7-7 7"/>',sun:'<circle cx="12" cy="12" r="4"/><path d="M12 1v2m0 18v2M1 12h2m18 0h2M4.2 4.2l1.5 1.5m12.6 12.6 1.5 1.5M4.2 19.8l1.5-1.5M18.3 5.7l1.5-1.5"/>',check:'<path d="m5 12 5 5L20 6"/>',search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>'})[name]}</svg>`;
const nav=`<header class="header"><a class="brand" href="/" aria-label="Optimax home">Optimax</a><nav aria-label="Main navigation"><a href="/#how-it-works">How it works</a><a href="/help/">Help center</a><a href="https://github.com/alo-exp/optimax">GitHub ${icon('arrow')}</a></nav><div class="header-actions"><a class="nav-cta" href="/#install">Get started</a><button id="theme-toggle" class="theme-toggle" type="button" aria-label="Dark theme" aria-pressed="true" hidden>${icon('sun')}<span>Theme</span></button></div></header>`;
const footer=`<footer class="footer"><div><a class="brand" href="/">Optimax</a><p>Thoughtful routing for capable agents.</p></div><div><span class="eyebrow">EXPLORE</span><a href="/help/">Help center</a><a href="https://github.com/alo-exp/optimax">GitHub ${icon('arrow')}</a></div><div><span class="eyebrow">A PROJECT BY</span><a href="https://alolabs.dev">ĀloLabs ${icon('arrow')}</a></div><div class="footer-bottom">OPTIMAX / BUILT FOR BETTER DELEGATION <span>ĀLOLABS © 2026</span></div></footer>`;
// Prefix only HTML URL attributes; escaped article text and command examples stay literal.
function layout(title,description,path,body){return `<!doctype html><html lang="en" data-theme="dark"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="site-base" content="${deployment.basePath}"><title>${e(title)} · Optimax</title><meta name="description" content="${e(description)}"><link rel="canonical" href="${absolute(path)}"><link rel="icon" type="image/svg+xml" href="/favicon.svg"><meta property="og:title" content="${e(title)} · Optimax"><meta property="og:description" content="${e(description)}"><meta property="og:url" content="${absolute(path)}"><meta name="theme-color" content="#082820"><script src="/assets/theme.js"></script><link rel="stylesheet" href="/assets/style.css"><script type="module" src="/assets/client.js"></script></head><body><a class="skip" href="#main">Skip to content</a>${nav}<main id="main">${body}</main>${footer}</body></html>`.replace(/\b(href|src)="(\/(?!\/)[^"]*)"/g,(_,attr,url)=>`${attr}="${prefix(url)}"`)}
const homepage=(await readFile('src/homepage.html','utf8')).replaceAll('{{BASE}}',deployment.basePath).replaceAll('{{ROOT_URL}}',e(deployment.url));
await write('index.html',homepage);
await write('assets/homepage.css',(await readFile('src/homepage.css','utf8')).replaceAll('{{BASE}}',deployment.basePath));
// Reuse the palette-aware theme implementation; Help retains its original theme asset.
await copyFile('variants/theme.js',join(out,'assets/homepage-theme.js'));
const groups=[...new Set(data.articles.map(a=>a.category))];
const help=`<section class="help-hero wrap"><h1>How can we help?</h1><p class="eyebrow">OPTIMAX / HELP CENTER</p><p>Guides to installation, routing, native modes and the decisions behind Optimax.</p><div class="search"><label for="help-search">Search the help center</label><div class="search-box">${icon('search')}<input id="help-search" type="search" autocomplete="off" placeholder="Search articles..." role="combobox" aria-autocomplete="list" aria-controls="search-results" aria-expanded="false"><button id="search-clear" type="button">Clear</button></div><p id="search-status" role="status" aria-live="polite"></p><ul id="search-results" role="listbox"></ul></div></section><section class="wrap help-library"><div class="library-heading"><p class="eyebrow">THE LIBRARY</p><p>Browse by topic <span class="direction-down">${icon('arrow')}</span></p></div>${groups.map(g=>`<div class="help-group"><div><h2>${e(g)}</h2><span class="eyebrow">TOPIC</span></div><div>${data.articles.filter(a=>a.category===g).map(a=>`<a class="article-link" href="/help/${e(a.slug)}/"><span><strong>${e(a.title)}</strong><small>${e(a.description)}</small></span><span>${icon('arrow')}</span></a>`).join('')}</div></div>`).join('')}</section>`;
await write('help/index.html',layout('Help center','Explore Optimax guides and reference articles.','/help/',help));
for(const page of pages){const a=page.article;await write(page.url.slice(1)+'index.html',layout(a.title,a.description,page.url,`<article class="wrap article"><a class="back-link" href="/help/"><span class="direction-back">${icon('arrow')}</span> All articles</a><h1>${e(a.title)}</h1><p class="eyebrow">${e(a.category)} / GUIDE</p><p class="article-deck">${e(a.description)}</p><div class="article-body">${page.html}</div><div class="article-end"><span>NEED MORE CONTEXT?</span><a href="/help/">Browse all articles ${icon('arrow')}</a></div></article>`))}
await write('search-index.json',JSON.stringify(index));
await write('404.html',layout('Page not found','The requested page could not be found.','/404.html',`<section class="wrap error-page"><h1>Off the<br>beaten path.</h1><p class="eyebrow">404 / NOT FOUND</p><p>That page could not be found.</p><a class="button primary" href="/">Back to Optimax ${icon('arrow')}</a></section>`));
await write('robots.txt',`User-agent: *\nAllow: ${deployment.basePath}\nSitemap: ${absolute('/sitemap.xml')}\n`);
await write('sitemap.xml',`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${['/','/help/',...pages.map(p=>p.url)].map(path=>`<url><loc>${absolute(path)}</loc></url>`).join('')}</urlset>`);
for(const name of ['style.css','theme.js','client.js','search.js','controls.js','deployment.js']) await copyFile('src/'+name,join(out,'assets',name));
await cp('public/fonts',join(out,'assets/fonts'),{recursive:true});
await copyFile('public/favicon.svg',join(out,'favicon.svg'));
// Preview pages are separate build inputs; the production layout above stays unchanged.
for(const name of ['circuit','prism','stage','press','continuum']){
 await write(`versions/${name}/index.html`,(await readFile(`variants/${name}.html`,'utf8')).replaceAll('{{BASE}}',deployment.basePath));
 await write(`versions/${name}/style.css`,(await readFile(`variants/${name}.css`,'utf8')).replaceAll('{{BASE}}',deployment.basePath));
}
for(const name of ['theme.js','client.js'])await copyFile(join('variants',name),join(out,'versions',name));
console.log(`Built ${pages.length} articles and ${index.length} search entries in ${out}/`);
