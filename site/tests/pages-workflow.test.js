import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import {parse} from 'yaml';

const path = new URL('../../.github/workflows/pages.yml', import.meta.url);
test('Pages publishes tested static output with scoped permissions and a serialized deployment', () => {
  assert.ok(existsSync(path), 'GitHub Pages deployment workflow must exist');
  const workflow = parse(readFileSync(path, 'utf8'));
  assert.deepEqual(workflow.on.push.branches, ['main']);
  assert.ok(Object.hasOwn(workflow.on, 'workflow_dispatch'));
  assert.equal(workflow.on.pull_request_target, undefined);
  assert.deepEqual(workflow.permissions, {contents: 'read'});
  assert.equal(workflow.concurrency.group, 'github-pages');
  assert.equal(workflow.concurrency['cancel-in-progress'], false);
  const {build, deploy} = workflow.jobs;
  assert.deepEqual(build.permissions, {contents: 'read', pages: 'read'});
  assert.equal(build.defaults.run['working-directory'], 'site');
  assert.equal(deploy.needs, 'build');
  assert.equal(deploy.if, "github.ref == 'refs/heads/main'");
  assert.deepEqual(deploy.permissions, {pages: 'write', 'id-token': 'write'});
  assert.equal(deploy.environment.name, 'github-pages');
  assert.equal(deploy.environment.url, '${{ steps.deployment.outputs.page_url }}');
  for (const job of [build, deploy]) {
    assert.ok(job['timeout-minutes'] > 0 && job['timeout-minutes'] <= 10);
    for (const step of job.steps) {
      assert.notEqual(step['continue-on-error'], true);
      if (step.uses) assert.match(step.uses, /^actions\/[a-z-]+@[a-f0-9]{40}$/, 'actions must be pinned to official immutable commits');
    }
  }
  const checkout = build.steps.findIndex(step => step.uses === 'actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803');
  const setup = build.steps.findIndex(step => step.uses === 'actions/setup-node@249970729cb0ef3589644e2896645e5dc5ba9c38');
  const pages = build.steps.findIndex(step => step.uses === 'actions/configure-pages@983d7736d9b0ae728b81ab479565c72886d7745b');
  assert.ok(checkout >= 0 && setup > checkout && pages > setup, 'known official checkout, Node setup, and Pages configuration must run in order');
  assert.equal(build.steps[checkout].with['persist-credentials'], false);
  assert.equal(build.steps[setup].with['node-version'], '22');
  assert.equal(build.steps[setup].with.cache, 'npm');
  assert.equal(build.steps[setup].with['cache-dependency-path'], 'site/package-lock.json');
  assert.equal(build.steps[pages].id, 'pages');
  const install = build.steps.findIndex(step => step.run === 'npm ci');
  const tests = build.steps.findIndex(step => step.run === 'npm test');
  const compile = build.steps.findIndex(step => step.run === 'npm run build');
  const upload = build.steps.findIndex(step => step.uses?.startsWith('actions/upload-pages-artifact@'));
  assert.ok(install > pages && tests > install && compile > tests && upload > compile);
  for (const index of [checkout, setup, pages, install, tests, compile]) {
    assert.equal(build.steps[index].if, undefined, `${build.steps[index].name} must use normal success gating`);
  }
  assert.equal(build.steps[compile].env.SITE_URL, '${{ steps.pages.outputs.base_url }}');
  const artifact = build.steps[upload];
  assert.deepEqual(artifact.with, {path: 'site/dist', 'retention-days': 1});
  assert.equal(artifact.if, undefined, 'failed tests/build must not upload an artifact');
  assert.equal(deploy.steps.length, 1);
  assert.ok(deploy.steps[0].uses.startsWith('actions/deploy-pages@'));
  assert.equal(deploy.steps[0].id, 'deployment');
});


test('Pages gates publication on rendered browser acceptance after the build',()=>{
 const {build}=parse(readFileSync(path,'utf8')).jobs;
 const compile=build.steps.findIndex(step=>step.run==='npm run build');
 const browserInstall=build.steps.findIndex(step=>step.run==='npx playwright install --with-deps chromium');
 const browserTest=build.steps.findIndex(step=>step.run==='npm run test:browser');
 const upload=build.steps.findIndex(step=>step.uses?.startsWith('actions/upload-pages-artifact@'));
 assert.ok(browserInstall>compile,'browser installation follows the build');
 assert.ok(browserTest>browserInstall&&upload>browserTest,'rendered acceptance must pass before upload');
 assert.equal(build.steps[browserTest].if,undefined);
 assert.notEqual(build.steps[browserTest]['continue-on-error'],true);
});


test('browser diagnostics have an identified failure-only consumer and minimal retention',()=>{
 const steps=parse(readFileSync(path,'utf8')).jobs.build.steps;
 const diagnostics=steps.find(step=>step.uses?.startsWith('actions/upload-artifact@'));
 assert.ok(diagnostics,'failed browser screenshots must be available to the repair reviewer');
 assert.equal(diagnostics.if,"failure() && steps.browser.outcome == 'failure'");
 assert.deepEqual(diagnostics.with,{name:'browser-failure-diagnostics',path:'site/test-results/**/test-failed-*.png','retention-days':1,'if-no-files-found':'ignore'});
 assert.equal(steps.find(step=>step.run==='npm run test:browser').id,'browser');
});
