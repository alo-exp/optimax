(function () {
  'use strict';

  var storageKey = 'optimax-theme';
  var storage = null;
  var choice = null;
  var button = null;
  var bound = false;

  function validTheme(value) {
    return value === 'light' || value === 'dark';
  }

  // Storage may be blocked by browser privacy settings.
  try {
    storage = window.localStorage;
  } catch (_) {}
  try {
    var saved = storage && storage.getItem(storageKey);
    if (validTheme(saved)) choice = saved;
  } catch (_) {}

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    var themeMeta = document.querySelector && document.querySelector('meta[name="theme-color"]');
    if (themeMeta) themeMeta.setAttribute('content', theme === 'dark' ? '#082820' : '#f3f1e9');
    if (button) {
      button.setAttribute('aria-label', 'Dark theme');
      button.setAttribute('aria-pressed', String(theme === 'dark'));
      button.title = theme === 'dark' ? 'Use light theme' : 'Use dark theme';
    }
  }

  // This classic script runs in the head before CSS, so the first paint is themed.
  applyTheme(choice || 'dark');

  window.addEventListener('storage', function (event) {
    var cleared = event.key === null && event.newValue === null &&
      storage && event.storageArea === storage;
    if (event.key !== storageKey && !cleared) return;
    // storageArea is absent in some environments; compare it when both exist.
    if (event.storageArea && storage && event.storageArea !== storage) return;
    if (event.newValue !== null && !validTheme(event.newValue)) return;
    choice = event.newValue;
    applyTheme(choice || 'dark');
  });

  function bindToggle() {
    if (bound) return;
    bound = true;
    button = document.getElementById('theme-toggle');
    if (!button) return;
    applyTheme(document.documentElement.dataset.theme);
    button.addEventListener('click', function () {
      choice = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      applyTheme(choice);
      // The in-memory choice remains explicit even when persistence fails.
      try {
        if (storage) storage.setItem(storageKey, choice);
      } catch (_) {}
    });
    button.hidden = false;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindToggle, { once: true });
  } else {
    bindToggle();
  }
})();
