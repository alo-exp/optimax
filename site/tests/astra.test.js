import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { parseHTML } from 'linkedom';

const readSource = name => {
  const path = new URL('../variants/' + name, import.meta.url);
  return existsSync(path) ? readFileSync(path, 'utf8') : '';
};
const page = parseHTML(readSource('astra.html') || '<html><head></head><body></body></html>').document;
const original = parseHTML(readFileSync(new URL('../src/homepage.html', import.meta.url), 'utf8')).document;
const text = node => node?.textContent.replace(/\s+/g, ' ').trim();
const words = (scope, selector) => Array.from(scope.querySelectorAll(selector), text);
const artwork = '{{BASE}}assets/images/astra-exposure.webp';

test('Exposure gives every independent assignment a photographic aperture, readable scope and ready state', () => {
  const plan = page.querySelector('.parallel-plan');
  assert.ok(plan, 'the visitor can inspect the illustrative assignment plan');
  assert.equal(text(plan.querySelector('h2')), text(original.querySelector('.parallel-plan h2')));
  assert.equal(text(plan.querySelector('p')), 'Illustrative plan, not live activity.');
  const diagram = plan.querySelector('.routing-visual[aria-describedby="plan-note"]');
  assert.ok(diagram && page.getElementById('plan-note'), 'the plan is linked to its dependency and capacity limits');
  const tasks = diagram.querySelector('ul.parallel-tasks');
  assert.ok(tasks, 'the assignments form a native unordered list');
  assert.equal(tasks.children.length, 3);
  for (const [index, assignment] of Array.from(tasks.children).entries()) {
    const approved = original.querySelectorAll('.parallel-tasks li')[index];
    assert.equal(assignment.tagName, 'LI');
    assert.equal(text(assignment.querySelector('strong')), text(approved.querySelector('strong')));
    assert.equal(text(assignment.querySelector('small')), text(approved.querySelector('small')));
    const exposure = assignment.querySelector('img');
    assert.equal(exposure?.getAttribute('src'), artwork, 'each assignment has a locally served exposure');
    assert.equal(exposure.getAttribute('alt'), '', 'the photographic metaphor never speaks for the task');
    assert.ok(Number(exposure.getAttribute('width')) > Number(exposure.getAttribute('height')));
  }
  const boundary = diagram.querySelector('.acceptance-boundary');
  assert.ok(boundary && !tasks.contains(boundary), 'the acceptance stage is separate from ready assignments');
  assert.equal(boundary.querySelector('img'), null, 'waiting acceptance has an unexposed window');
  assert.equal(text(boundary.querySelector('strong')), 'Integrate accepted results');
  assert.equal(text(boundary.querySelector('small')), 'WAITING / REVIEW & DEPENDENCIES');
});

test('Exposure keeps all seven native disclosures, the original destinations, and prefix-safe functional controls', () => {
  const details = page.querySelectorAll('#questions details');
  assert.equal(details.length, 7, 'every approved answer can be opened without a script');
  assert.deepEqual(Array.from(details, item => [text(item.querySelector('summary')), text(item.querySelector('p'))]),
    Array.from(original.querySelectorAll('#questions details'), item => [text(item.querySelector('summary')), text(item.querySelector('p'))]));
  const localLinks = Array.from(page.querySelectorAll('a[href^="#"]'));
  assert.ok(localLinks.length > 0);
  for (const link of localLinks) {
    assert.ok(page.getElementById(link.getAttribute('href').slice(1)), text(link) + ' has an in-page destination');
  }
  const home = page.querySelectorAll('a.preview-return[href="{{BASE}}"]');
  assert.equal(home.length, 1);
  assert.equal(text(home[0]), 'Circuit');
  assert.deepEqual(words(page, '[data-install-panel]'), words(original, '[data-install-panel]'));
  assert.deepEqual(Array.from(page.querySelectorAll('[data-install-panel]'), node => node.hidden), [false, true]);
  assert.deepEqual(words(page, '[data-install-tab]'), ['Codex', 'Claude']);
  assert.equal(page.querySelector('#copy-status')?.getAttribute('role'), 'status');
  assert.ok(page.querySelector('header .header-actions > #theme-toggle:last-child[hidden]'));
});

test('the decorative photographic plate is a small local WebP asset', () => {
  const path = new URL('../public/images/astra-exposure.webp', import.meta.url);
  assert.ok(existsSync(path), 'the three contact frames have an available local photographic plate');
  const image = readFileSync(path);
  assert.equal(image.toString('ascii', 0, 4), 'RIFF');
  assert.equal(image.toString('ascii', 8, 12), 'WEBP');
  assert.ok(image.length > 5000 && image.length < 250_000, 'the first-view photographic plate fits a 250 KB budget');
});
