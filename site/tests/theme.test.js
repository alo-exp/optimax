import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { parseHTML } from 'linkedom';

const source = readFileSync(new URL('../src/theme.js', import.meta.url), 'utf8');
const key = 'optimax-theme';

const themeColors = { dark: '#082820', light: '#f3f1e9' };

for (const saved of [undefined, 'light']) {
  test(`theme-color follows ${saved ?? 'default dark'} before DOM readiness`, () => {
    const env = setup({ saved });
    assert.equal(env.document.querySelector('meta[name="theme-color"]').content,
      themeColors[saved ?? 'dark']);
  });
}

test('theme-color follows toggles and cross-tab storage changes without writing back', () => {
  const env = setup({ ready: 'complete' });
  const meta = env.document.querySelector('meta[name="theme-color"]');
  env.button.click();
  assert.equal(meta.content, themeColors.light);
  env.button.click();
  assert.equal(meta.content, themeColors.dark);
  env.storageEvent('light');
  assert.equal(meta.content, themeColors.light);
  env.storageEvent(null, { key: null });
  assert.equal(meta.content, themeColors.dark);
  assert.deepEqual(env.writes, [[key, 'light'], [key, 'dark']]);
});

for (const unavailable of ['meta', 'querySelectorAbsent']) {
  test(`theme-color tolerates unavailable ${unavailable}`, () => {
    const env = setup({ [unavailable]: unavailable === 'meta' ? false : true, ready: 'complete' });
    assertTheme(env, 'dark');
    env.button.click();
    assertTheme(env, 'light');
    env.storageEvent('dark');
    assertTheme(env, 'dark');
  });
}

function setup(options = {}) {
  const { document } = parseHTML('<!doctype html><html><head>' +
    (options.meta === false ? '' : '<meta name="theme-color" content="#stale">') + '</head><body>' +
    (options.button === false ? '' : '<button id="theme-toggle" type="button" aria-label="Dark theme" hidden><span aria-hidden="true">◐</span><span>Theme</span></button>') +
    '</body></html>');
  Object.defineProperty(document, 'readyState', { value: options.ready ?? 'loading', configurable: true });
  const windowListeners = new Map();
  const mediaListeners = [];
  let mediaAccesses = 0;
  const writes = [];
  const storage = {
    getItem(name) {
      assert.equal(name, key);
      if (options.readError) throw new Error('Storage blocked');
      return options.saved ?? null;
    },
    setItem(name, value) {
      if (options.writeError) throw new Error('Quota exceeded');
      writes.push([name, value]);
    }
  };
  const media = {
    matches: options.dark ?? false,
    addEventListener(type, handler) {
      assert.equal(type, 'change');
      mediaListeners.push(handler);
    }
  };
  if (options.legacyMedia) {
    delete media.addEventListener;
    media.addListener = handler => mediaListeners.push(handler);
  }
  const window = {
    document,
    addEventListener(type, handler) {
      windowListeners.set(type, [...(windowListeners.get(type) ?? []), handler]);
    }
  };
  Object.defineProperty(window, 'localStorage', { get() {
    if (options.storageError) throw new Error('Storage access denied');
    return options.storageAbsent ? undefined : storage;
  } });
  if (!options.mediaAbsent) {
    Object.defineProperty(window, 'matchMedia', { get() {
      mediaAccesses += 1;
      if (options.mediaGetterError) throw new Error('Media unavailable');
      return query => {
        assert.equal(query, '(prefers-color-scheme: dark)');
        if (options.mediaError) throw new Error('Media blocked');
        return media;
      };
    } });
  }
  if (options.querySelectorAbsent) document.querySelector = undefined;
  runInNewContext(source, { window, document });
  return {
    document, storage, writes, mediaListeners,
    get mediaAccesses() { return mediaAccesses; },
    button: document.getElementById('theme-toggle'),
    ready() { document.dispatchEvent(new document.defaultView.Event('DOMContentLoaded')); },
    os(dark) {
      media.matches = dark;
      for (const handler of mediaListeners) handler({ matches: dark });
    },
    storageEvent(newValue, overrides = {}) {
      for (const handler of windowListeners.get('storage') ?? []) {
        handler({ key, newValue, storageArea: storage, ...overrides });
      }
    }
  };
}

function assertTheme(env, expected, bound = true) {
  assert.equal(env.document.documentElement.dataset.theme, expected);
  if (bound && env.button) {
    assert.equal(env.button.getAttribute('aria-label'), 'Dark theme');
    assert.equal(env.button.getAttribute('aria-pressed'), String(expected === 'dark'));
    assert.equal(env.button.hidden, false);
    assert.equal(env.button.title, expected === 'dark' ? 'Use light theme' : 'Use dark theme');
  }
}

test('applies the initial theme synchronously before DOM readiness', () => {
  const env = setup({ saved: 'light' });
  assertTheme(env, 'light', false);
  assert.equal(env.button.hidden, true);
  env.ready();
  assertTheme(env, 'light');
});

for (const saved of ['light', 'dark']) {
  test(`saved ${saved} wins over the opposite OS preference`, () => {
    assertTheme(setup({ saved, dark: saved === 'light', ready: 'complete' }), saved);
  });
}

for (const saved of [null, '', 'DARK', ' light ', 'auto', '__proto__']) {
  test(`invalid saved preference ${JSON.stringify(saved)} defaults to dark despite a light OS`, () => {
    assertTheme(setup({ saved, dark: false, ready: 'interactive' }), 'dark');
  });
}

test('defaults to dark when no preference APIs exist', () => {
  assertTheme(setup({ storageAbsent: true, mediaAbsent: true, ready: 'complete' }), 'dark');
});

for (const failure of ['storageError', 'readError']) {
  test(`${failure} preserves the dark default and button binding`, () => {
    const env = setup({ [failure]: true, dark: false });
    env.ready();
    assertTheme(env, 'dark');
    env.button.click();
    assertTheme(env, 'light');
  });
}

for (const failure of ['mediaError', 'mediaGetterError', 'mediaAbsent']) {
  test(`${failure} defaults to dark without blocking saved light values`, () => {
    assertTheme(setup({ [failure]: true, ready: 'complete' }), 'dark');
    assertTheme(setup({ [failure]: true, saved: 'light', ready: 'complete' }), 'light');
  });
}

test('toggle updates state and persistence, and binds only once', () => {
  const env = setup();
  env.ready();
  env.ready();
  env.button.click();
  assertTheme(env, 'light');
  assert.deepEqual(env.writes, [[key, 'light']]);
  env.button.click();
  assertTheme(env, 'dark');
  assert.deepEqual(env.writes, [[key, 'light'], [key, 'dark']]);
  assert.equal(env.button.textContent, '◐Theme');
});

test('OS changes never override the dark default or explicit click', () => {
  const env = setup({ ready: 'complete' });
  assertTheme(env, 'dark');
  env.os(true);
  env.os(false);
  assertTheme(env, 'dark');
  env.button.click();
  env.os(true);
  env.os(false);
  assertTheme(env, 'light');
});

test('failed persistence still preserves the explicit choice against OS changes', () => {
  const env = setup({ writeError: true, ready: 'complete' });
  env.button.click();
  env.os(true);
  env.os(false);
  assertTheme(env, 'light');
  assert.deepEqual(env.writes, []);
});

test('removing a saved preference returns to dark and keeps ignoring the OS', () => {
  const env = setup({ saved: 'light', ready: 'complete' });
  env.os(true);
  assertTheme(env, 'light');
  env.storageEvent(null);
  assertTheme(env, 'dark');
  env.os(false);
  assertTheme(env, 'dark');
});

test('valid storage changes synchronize the toggle without writing back', () => {
  const env = setup({ ready: 'complete' });
  env.storageEvent('dark');
  assertTheme(env, 'dark');
  env.os(false);
  assertTheme(env, 'dark');
  env.storageEvent('light');
  assertTheme(env, 'light');
  assert.deepEqual(env.writes, []);
});

test('ignores unrelated keys, foreign storage areas, and invalid storage values', () => {
  const env = setup({ saved: 'light', ready: 'complete' });
  env.storageEvent('dark', { key: 'unrelated' });
  env.storageEvent('dark', { storageArea: {} });
  env.storageEvent('DARK');
  assertTheme(env, 'light');
  env.os(true);
  assertTheme(env, 'light');
});

test('storage events can synchronize when storageArea is unavailable', () => {
  const env = setup({ ready: 'complete' });
  env.storageEvent('dark', { storageArea: undefined });
  assertTheme(env, 'dark');
});

test('storage getter failures during events do not prevent a theme update', () => {
  const env = setup({ storageError: true, ready: 'complete' });
  env.storageEvent('dark');
  assertTheme(env, 'dark');
  env.storageEvent(null);
  assertTheme(env, 'dark');
});

test('OS changes before DOMContentLoaded preserve the dark default when binding', () => {
  const env = setup();
  env.os(true);
  env.os(false);
  assertTheme(env, 'dark', false);
  env.ready();
  assertTheme(env, 'dark');
});

test('does not access OS media APIs or register modern or legacy listeners', () => {
  for (const legacyMedia of [false, true]) {
    const env = setup({ legacyMedia, ready: 'complete' });
    assert.equal(env.mediaAccesses, 0);
    assert.equal(env.mediaListeners.length, 0);
    env.os(true);
    env.os(false);
    assertTheme(env, 'dark');
  }
});

test('missing toggle does not prevent initialization or synchronization', () => {
  const env = setup({ button: false });
  env.ready();
  assertTheme(env, 'dark');
  env.os(true);
  assertTheme(env, 'dark');
  env.storageEvent('light');
  assertTheme(env, 'light');
});

test('head execution binds a toggle added by the later body parse', () => {
  const env = setup({ button: false, saved: 'dark' });
  assertTheme(env, 'dark', false);
  env.document.body.innerHTML = '<button id="theme-toggle" type="button" hidden>Theme</button>';
  const button = env.document.getElementById('theme-toggle');
  assert.equal(button.hidden, true);
  env.ready();
  assert.equal(button.hidden, false);
  assert.equal(button.getAttribute('aria-pressed'), 'true');
  button.click();
  assertTheme(env, 'light', false);
  assert.deepEqual(env.writes, [[key, 'light']]);
});

test('stored click choice restores on the next page initialization', () => {
  const first = setup({ ready: 'complete' });
  first.button.click();
  const saved = first.writes[0][1];
  assert.equal(saved, 'light');
  const next = setup({ saved, dark: true });
  assertTheme(next, 'light', false);
  assert.equal(next.button.hidden, true);
  next.ready();
  assertTheme(next, 'light');
});

test('storage changes before the body is ready bind with the latest choice', () => {
  const env = setup();
  env.storageEvent('dark');
  assertTheme(env, 'dark', false);
  assert.equal(env.button.hidden, true);
  env.ready();
  assertTheme(env, 'dark');
});

test('clearing localStorage in another tab restores the dark default', () => {
  const env = setup({ saved: 'light', ready: 'complete' });
  assertTheme(env, 'light');
  env.storageEvent(null, { key: null });
  assertTheme(env, 'dark');
  env.os(true);
  assertTheme(env, 'dark');
  assert.deepEqual(env.writes, []);
});

test('clear-all ignores foreign storage and malformed or unattributed events', () => {
  const env = setup({ saved: 'light', ready: 'complete' });
  env.storageEvent(null, { key: null, storageArea: {} });
  env.storageEvent(null, { key: 'unrelated' });
  env.storageEvent('light', { key: null });
  env.storageEvent(undefined, { key: null });
  env.storageEvent(null, { key: undefined });
  env.storageEvent(null, { key: null, storageArea: undefined });
  env.storageEvent(null, { key: null, storageArea: null });
  assertTheme(env, 'light');
  env.os(false);
  assertTheme(env, 'light');
});
