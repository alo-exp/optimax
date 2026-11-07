(function () {
  'use strict';

  var storageKey = 'optimax-theme';
  var storage = null;
  var media = null;
  var choice = null;
  var button = null;
  var bound = false;

  function validTheme(value) {
    return value === 'light' || value === 'dark';
  }

  // Preference APIs may be blocked independently by browser privacy settings.
  try {
    storage = window.localStorage;
  } catch (_) {}
  try {
    var saved = storage && storage.getItem(storageKey);
    if (validTheme(saved)) choice = saved;
  } catch (_) {}
  try {
    if (typeof window.matchMedia === 'function') {
      media = window.matchMedia('(prefers-color-scheme: dark)');
    }
  } catch (_) {}

  function systemTheme() {
    try {
      return media && media.matches ? 'dark' : 'light';
    } catch (_) {
      return 'light';
    }
  }

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    if (button) {
      button.setAttribute('aria-label', 'Dark theme');
      button.setAttribute('aria-pressed', String(theme === 'dark'));
      button.title = theme === 'dark' ? 'Use light theme' : 'Use dark theme';
    }
  }

  // This classic script runs in the head before CSS, so the first paint is themed.
  applyTheme(choice || systemTheme());

  function onSystemChange() {
    if (!choice) applyTheme(systemTheme());
  }
  try {
    if (media && typeof media.addEventListener === 'function') {
      media.addEventListener('change', onSystemChange);
    } else if (media && typeof media.addListener === 'function') {
      media.addListener(onSystemChange);
    }
  } catch (_) {}

  window.addEventListener('storage', function (event) {
    var cleared = event.key === null && event.newValue === null &&
      storage && event.storageArea === storage;
    if (event.key !== storageKey && !cleared) return;
    // storageArea is absent in some environments; compare it when both exist.
    if (event.storageArea && storage && event.storageArea !== storage) return;
    if (event.newValue !== null && !validTheme(event.newValue)) return;
    choice = event.newValue;
    applyTheme(choice || systemTheme());
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
