# Homepage comparison previews

The user selected Circuit for the production homepage. Its production adaptation
lives in [`../src/homepage.html`](../src/homepage.html) and
[`../src/homepage.css`](../src/homepage.css), with updated supporting copy and a
separate indexable root funnel. The four previews below remain frozen historical
comparisons with their original copy and styles. Help output and assets remain
unchanged. The production scope is documented in [`../DESIGN.md`](../DESIGN.md).

| Preview | Visual direction | Source | Public path relative to the deployment base |
| --- | --- | --- | --- |
| Circuit | Navy and cobalt, Sora typography | [`circuit.html`](circuit.html), [`circuit.css`](circuit.css) | `versions/circuit/` |
| Prism | Aubergine, lilac and apricot, Bricolage Grotesque typography | [`prism.html`](prism.html), [`prism.css`](prism.css) | `versions/prism/` |
| Stage | Violet-black and lilac light fields, DM Sans typography | [`stage.html`](stage.html), [`stage.css`](stage.css) | `versions/stage/` |
| Press | Carbon ink, warm paper and coral-red, Archivo Narrow typography | [`press.html`](press.html), [`press.css`](press.css) | `versions/press/` |

[`../build.js`](../build.js) emits each HTML file as
`versions/<name>/index.html` and each CSS file as `versions/<name>/style.css`.
It substitutes `{{BASE}}` in both HTML and CSS for deployment beneath a path prefix.
Each preview declares `noindex` and its own canonical URL.

All four previews default to dark mode and honor a saved light preference. They share
[`theme.js`](theme.js) and [`client.js`](client.js), emitted as `versions/theme.js`
and `versions/client.js`. The client imports production
[`installControls`](../src/controls.js) for the install tabs and copy controls.

Fonts are served locally from [`../public/fonts/`](../public/fonts/); no runtime
third-party font request is required. Sora, Bricolage Grotesque, DM Sans and
Archivo Narrow use Fontsource packages pinned to version 5.3.0 and include their
local OFL license files: [`sora-OFL.txt`](../public/fonts/sora-OFL.txt),
[`bricolage-grotesque-OFL.txt`](../public/fonts/bricolage-grotesque-OFL.txt),
[`dm-sans-OFL.txt`](../public/fonts/dm-sans-OFL.txt) and
[`archivo-narrow-OFL.txt`](../public/fonts/archivo-narrow-OFL.txt).

Stage keeps functional labels at a 12px minimum, with 13px status text and section
captions. Press retains a working Get started entry in its narrow header and uses
`-0.03em` brand tracking. These choices apply to the comparison previews.

Run the relevant automated checks from `site/` (through the workstation shell route):

```sh
rtk node --test tests/variants-build.test.js tests/circuit.test.js tests/prism.test.js tests/stage.test.js tests/press.test.js
rtk npm run test:browser
```

The Node checks cover preview build contracts and each direction's source contracts.
[`../e2e/variants.spec.js`](../e2e/variants.spec.js) exercises all four alternatives in
dark and light themes at 320, 390 and 1440 pixels, including controls, local fonts,
and operation with blocked storage. The browser runner executes the configured
browser suite. Run `rtk npm test` and `rtk npm run build` for integrated site checks.
These commands describe validation to run; this document makes no passing-test claim.
