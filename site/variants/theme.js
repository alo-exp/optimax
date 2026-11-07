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
    // Each preview owns its CSS palette; DOM readiness refreshes this after CSS loads.
    var background = window.getComputedStyle && window.getComputedStyle(document.documentElement).getPropertyValue('--bg').trim();
    if (themeMeta && background) themeMeta.setAttribute('content', background);
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
    if (event.storageArea && storage && event.storageArea !== storage) return;
    if (event.newValue !== null && !validTheme(event.newValue)) return;
    choice = event.newValue;
    applyTheme(choice || 'dark');
  });

  function bindToggle() {
    if (bound) return;
    bound = true;
    button = document.getElementById('theme-toggle');
    applyTheme(document.documentElement.dataset.theme);
    if (!button) return;
    button.addEventListener('click', function () {
      choice = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      applyTheme(choice);
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
