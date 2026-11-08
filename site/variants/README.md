# Circuit homepage preview

Circuit is the selected production direction. Its production adaptation lives in
[`../src/homepage.html`](../src/homepage.html) and
[`../src/homepage.css`](../src/homepage.css), with the current supporting copy and
an indexable root funnel. The retained preview keeps its earlier copy and styling,
without navigation to removed comparisons.

[`circuit.html`](circuit.html) and [`circuit.css`](circuit.css) publish at
`versions/circuit/`, relative to the deployment base. The preview declares
`noindex` and its own canonical URL. The build substitutes `{{BASE}}` in HTML and
CSS for root and project-prefix deployments.

[`theme.js`](theme.js) and [`client.js`](client.js) publish at `versions/theme.js`
and `versions/client.js`. Circuit defaults to dark mode and honors a saved light
preference. The client imports production [`installControls`](../src/controls.js)
for install tabs and copy controls. The production homepage also reuses the theme
implementation as `assets/homepage-theme.js`; Help retains its existing assets.

Fonts are self-hosted in [`../public/fonts/`](../public/fonts/). Circuit uses Sora
Latin normal 400 and 700, pinned to Fontsource 5.3.0, with its
[`SIL Open Font License`](../public/fonts/sora-OFL.txt). Help uses the retained Mona
Sans faces and [`license`](../public/fonts/OFL.txt). No runtime third-party font
request is needed.

Run the checks from `site/` through the workstation shell route:

```sh
rtk npm test
rtk npm run build
rtk npm run test:browser
```

The Circuit-only build tests check both deployment bases, removal of obsolete
routes and unused assets, retained public-file hashes, and local links and
fragments. Browser checks cover Circuit's responsive layouts, both themes, local
font loading, install controls, clipboard behavior, and blocked storage.
