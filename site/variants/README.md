# Homepage comparison previews

These are two independent, unaccepted homepage alternatives. Neither replaces the
production homepage or establishes a new global design system. The production
[`DESIGN.md`](../DESIGN.md) remains unchanged; existing main-site and Help output
must remain unchanged when these previews are built.

| Preview | Visual direction | Source | Public path relative to the deployment base |
| --- | --- | --- | --- |
| Circuit | Navy and cobalt, Sora typography | [`circuit.html`](circuit.html), [`circuit.css`](circuit.css) | `versions/circuit/` |
| Prism | Aubergine, lilac and apricot, Bricolage Grotesque typography | [`prism.html`](prism.html), [`prism.css`](prism.css) | `versions/prism/` |

[`../build.js`](../build.js) emits each HTML file as
`versions/<name>/index.html` and each CSS file as `versions/<name>/style.css`.
It substitutes `{{BASE}}` in both HTML and CSS for deployment beneath a path prefix.
Each preview declares `noindex` and its own canonical URL.

Both previews default to dark mode and honor a saved light preference. They share
[`theme.js`](theme.js) and [`client.js`](client.js), emitted as `versions/theme.js`
and `versions/client.js`. The client imports production
[`installControls`](../src/controls.js) for the install tabs and copy controls.

Fonts are served locally from [`../public/fonts/`](../public/fonts/); no runtime
third-party font request is required. Sora and Bricolage Grotesque include their local
OFL license files, [`sora-OFL.txt`](../public/fonts/sora-OFL.txt) and
[`bricolage-grotesque-OFL.txt`](../public/fonts/bricolage-grotesque-OFL.txt).

Run the relevant automated checks from `site/` (through the workstation shell route):

```sh
rtk node --test tests/variants-build.test.js tests/circuit.test.js tests/prism.test.js
rtk npm run test:browser
```

The Node checks cover preview build contracts and each direction's source contracts.
[`../e2e/variants.spec.js`](../e2e/variants.spec.js) exercises both alternatives in
dark and light themes at 320, 390 and 1440 pixels, including controls, local fonts,
and operation with blocked storage. The browser runner executes the configured
browser suite. Run `rtk npm test` and `rtk npm run build` for integrated site checks.
These commands describe validation to run; this document makes no passing-test claim.
