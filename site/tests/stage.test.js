import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import {parseHTML} from 'linkedom';

const read = name => { const url = new URL('../variants/' + name, import.meta.url); return existsSync(url) ? readFileSync(url, 'utf8') : ''; };
const html = read('stage.html'), css = read('stage.css');
const document = parseHTML(html || '<html><head></head><body></body></html>').document;
const authority = parseHTML(read('circuit.html')).document;
const normalize = node => { const copy = node.cloneNode(true); for (const br of copy.querySelectorAll('br')) br.replaceWith(' '); return copy.textContent.replace(/\s+/g, ' ').trim(); };

test('Stage provides a complete page and stylesheet rather than a missing preview', () => {
  assert.ok(html, 'Stage homepage must exist');
  assert.ok(css, 'Stage stylesheet must exist');
  assert.ok(document.querySelector('main#main'));
  assert.equal(document.querySelectorAll('h1').length, 1);
  assert.equal(document.querySelector('h1').textContent, 'Get AI work done faster and cheaper');
});

test('Stage retains complete approved copy, all FAQ answers, destinations and fragments', () => {
  const copy = [...document.querySelectorAll('main h1, main h2, main h3, p, main summary')].map(normalize);
  for (const node of authority.querySelectorAll('main h1, main h2, main h3, p, main summary')) assert.ok(copy.includes(normalize(node)), 'preserve wording: ' + normalize(node));
  assert.equal(document.querySelectorAll('p').length, 36, 'preserve all 36 homepage paragraphs including footer');
  assert.equal(document.querySelectorAll('#questions details').length, 5);
  for (const node of authority.querySelectorAll('a[href]')) assert.ok([...document.querySelectorAll('a[href]')].some(link => link.getAttribute('href') === node.getAttribute('href')), 'preserve destination ' + node.getAttribute('href'));
  for (const node of authority.querySelectorAll('main [id], main[id]')) assert.ok(document.getElementById(node.id), 'retain fragment #' + node.id);
  assert.equal(document.querySelector('link[rel="canonical"]').getAttribute('href'), '{{BASE}}versions/stage/');
  assert.equal(document.querySelector('meta[name="robots"]').content, 'noindex,follow');
  for (const node of document.querySelectorAll('h1,h2,h3')) assert.ok(!node.previousElementSibling?.matches('.eyebrow,.kicker,.metadata,.section-caption'), 'no eyebrow above a heading');
});

test('Stage exposes independent work tracks and a distinct waiting acceptance boundary without animation', () => {
  const diagram = document.querySelector('.parallel-plan');
  assert.ok(diagram, 'semantic parallel plan exists');
  const tasks = diagram.querySelector('ul.parallel-tasks');
  assert.ok(tasks);
  assert.deepEqual([...tasks.children].map(node => node.querySelector('strong').textContent), ['Investigate own scope', 'Implement own files', 'Verify independent work']);
  for (const task of tasks.children) assert.match(task.textContent, /READY \/ PARALLEL/);
  const boundary = diagram.querySelector('.acceptance-boundary');
  assert.ok(boundary); assert.equal(tasks.contains(boundary), false);
  assert.match(boundary.textContent, /Integrate after acceptance/);
  assert.match(boundary.textContent, /WAITING \/ DEPENDENCIES/);
  assert.equal(diagram.getAttribute('aria-describedby'), 'plan-note');
  assert.match(document.getElementById('plan-note').textContent, /only when independent, capacity is verified and resources do not conflict/);
  assert.match(css, /@media\s*\(prefers-reduced-motion:\s*reduce\)[\s\S]*animation:\s*none/);
  assert.ok((css.match(/@keyframes\s/g) || []).length <= 1);
});

test('Stage preserves progressive theme and installation behavior hooks', () => {
  assert.equal(document.documentElement.getAttribute('data-theme'), 'dark');
  assert.equal(document.querySelector('meta[name="site-base"]').content, '{{BASE}}');
  const early = document.querySelector('head script[src="{{BASE}}versions/theme.js"]');
  assert.ok(early); assert.ok(html.indexOf(early.outerHTML) < html.indexOf('<link rel="stylesheet"'));
  assert.equal(early.hasAttribute('type'), false); assert.equal(early.hasAttribute('defer'), false);
  assert.ok(document.querySelector('script[type="module"][src="{{BASE}}versions/client.js"]'));
  const toggle = document.querySelector('#theme-toggle');
  assert.ok(toggle); assert.equal(toggle.type, 'button'); assert.ok(toggle.hidden);
  assert.equal(toggle.getAttribute('aria-label'), 'Dark theme'); assert.equal(toggle.getAttribute('aria-pressed'), 'true');
  assert.equal(toggle.parentElement.lastElementChild, toggle);
  assert.deepEqual([...document.querySelectorAll('[data-install-tab]')].map(node => node.getAttribute('aria-pressed')), ['true', 'false']);
  const panels = [...document.querySelectorAll('[data-install-panel]')];
  assert.deepEqual(panels.map(node => node.textContent), [...authority.querySelectorAll('[data-install-panel]')].map(node => node.textContent));
  assert.deepEqual(panels.map(node => node.hidden), [false, true]);
  assert.ok(document.querySelector('button#copy-install[type="button"]'));
  assert.equal(document.querySelector('#copy-status').getAttribute('role'), 'status');
  for (const command of ['$optimax off', '/optimax:optimax off', '$optimax on', '/optimax:optimax on']) assert.ok(document.body.textContent.includes(command));
});

const palette = selector => { const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); const block = css.match(new RegExp(escaped + '\\s*\\{([^}]+)'))?.[1] || ''; return Object.fromEntries([...block.matchAll(/(--[\w-]+)\s*:\s*(#[\da-f]{6})/gi)].map(([,name,value]) => [name,value])); };
const luminance = color => { assert.match(color || '', /^#[\da-f]{6}$/i); return color.slice(1).match(/../g).map(value => parseInt(value, 16) / 255).map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4).reduce((sum, value, index) => sum + value * [.2126,.7152,.0722][index], 0); };
const contrast = (a,b) => { const x = luminance(a), y = luminance(b); return (Math.max(x,y) + .05) / (Math.min(x,y) + .05); };
for (const theme of ['dark','light']) test('Stage ' + theme + ' has readable authored text grounds and controls', () => {
  const tokens = theme === 'light' ? {...palette(':root'), ...palette(':root[data-theme="light"]')} : palette(':root');
  assert.equal(tokens['--bg'], theme === 'dark' ? '#170F26' : '#F2ECFA');
  for (const [fg,bg,min] of [['--ink','--bg',4.5],['--muted','--bg',4.5],['--accent','--bg',4.5],['--on-accent','--accent',4.5],['--field-ink','--field',4.5],['--field-muted','--field',4.5],['--command-ink','--command-bg',4.5],['--command-muted','--command-bg',4.5],['--focus','--bg',3]]) assert.ok(contrast(tokens[fg],tokens[bg]) >= min, fg + ' on ' + bg + ' needs ' + min + ':1');
});

test('Stage authors local DM Sans, mobile reflow and keyboard surfaces', () => {
  for (const weight of [400,700]) assert.ok(css.includes('{{BASE}}assets/fonts/dm-sans-latin-' + weight + '-normal.woff2'));
  assert.match(css, /font-family:\s*["']DM Sans["']/); assert.match(css, /font-display:\s*swap/);
  assert.match(css, /focus-visible[^{]*\{[^}]*outline:\s*3px solid var\(--focus\)/);
  assert.match(css, /min-height:\s*44px/); assert.match(css, /min-width:\s*44px/);
  assert.match(css, /overflow-wrap:\s*anywhere/); assert.match(css, /@media\s*\(max-width:\s*700px\)/);
  assert.match(css, /::selection/); assert.match(css, /scrollbar-color/); assert.match(css, /caret-color/);
  assert.doesNotMatch(css, /@import|https?:\/\/|clip-path|repeating-linear-gradient|background-clip:\s*text/);
});


test('Stage functional labels remain at least 12px in base and responsive CSS rules', () => {
  const selectors = ['.parallel-tasks small', '.acceptance-boundary small', '.section-caption', '.plan-meta', '.ticker', '.command-heading', '.footer-links>span', '.footer-bottom', '#copy-status'];
  const rules = [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].map(([,selector,body]) => ({selectors: selector.trim().split(',').map(value => value.trim()), size: body.match(/(?:^|;)\s*font-size\s*:\s*([\d.]+)px\s*(?:;|$)/)?.[1]}));
  for (const selector of selectors) {
    assert.ok(document.querySelector(selector), 'qualify visible functional content for ' + selector);
    const declarations = rules.filter(rule => rule.selectors.includes(selector) && rule.size !== undefined);
    assert.ok(declarations.length, 'explicit readable base size for ' + selector);
    for (const rule of declarations) assert.ok(Number(rule.size) >= 12, selector + ' must not shrink below 12px; found ' + rule.size + 'px');
  }
});
