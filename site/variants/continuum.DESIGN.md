# Continuum comparison design system

Continuum is an experimental, unselected homepage comparison.
It does not replace the live Circuit system or the Help Center.
The implementation is `variants/continuum.html` and `variants/continuum.css`.
Current approved copy is independently checked against `src/homepage.html`.
The route is `versions/continuum/` and carries `noindex`.

## Palette

| Role | Dark | Light |
| --- | --- | --- |
| Ground | #0D0B14 | #F4F2F9 |
| Main ink | #F7F4FC | #181225 |
| Supporting ink | #BEB7CC | #5B526A |
| Quiet surface | #181421 | #E8E3F1 |
| Structural line | #51465F | #ABA0BD |
| Link and action | #BCA5FF | #5530C3 |
| Action ink | #190F35 | #FFFFFF |
| Focus | #D3C1FF | #5530C3 |
| Major field | #5732C6 | #DCD1FF |
| Field ink | #FFFFFF | #241243 |
| Field supporting ink | #E0D6FF | #4E386E |
| Field cut face | #392183 | #AB93DF |
| Command cut face | #2B203C | #49315D |
| Command ground | #0D0B14 | #211432 |
| Command ink | #F7F4FC | #F8F3FF |
| Command supporting ink | #BEB7CC | #C9BDDE |

## Type and spacing

Figtree 400 and 700 are self-hosted Latin WOFF2 with swap loading.
Headlines use balanced lines, 1.02–1.12 leading and tracking no tighter than -0.04em.
The main headline reaches 96px; secondary display reaches 80px.
Body text is 17px on desktop and 16px on mobile, with 1.75 leading.
Task states and control feedback are 13px; functional captions never fall below 12px.
Reading measures are capped at 65–75ch.
The outer measure is 1320px, with 56px desktop and 20px mobile side spacing.
Major section spacing is 112px desktop and 72px mobile.

## Geometry and layout

The hero has one full-width headline, with the definition and actions sharing its right reading rail.
The complete desktop parametric field is 380px high.
Three explicitly specified SVG top surfaces have distinct front cuts, end caps and underside paths.
Cut thicknesses vary by channel (22, 28 and 14 vector units); bend positions and plate starts also vary.
Each top surface has one real parallelogram aperture using an even-odd path and separate inner walls.
Contour registration follows actual front/back edges and the aperture boundaries.
Actual assignment labels remain semantic HTML on solid surfaces before a distinct acceptance plane.
At 700px and below, a 52px native cut-plane signature occupies the opening above the headline.
The complete task diagram then becomes offset structural lanes with every label preserved.
Major violet fields expose an oblique cut face and an open edge aperture.
Proof changes to a broad introduction with paired evidence lanes on registered angled boundaries.
FAQs follow the same quiet open-boundary grammar in one offset reading lane.
Mechanism retains its meaningful three-step sequence; benefits remain open rows.
The command surface has explicit oblique upper and right cut faces.

## Themes, motion and controls

Dark is the initial theme; shared `variants/theme.js` restores an explicit saved choice.
The rightmost theme button remains hidden until its shared binding succeeds.
One 1.4-second cubic-bezier settling moment moves the already-visible geometric field by 12px.
Reduced motion disables animation and smooth scrolling; no content depends on motion.
Theme, installation tabs, copying and status feedback reuse the shared preview runtime.
Buttons and navigation targets are at least 44px high, with a 3px visible focus outline.
Selection, caret and scrollbar use the authored palette.
Disclosures use native details/summary and preserve all seven exact approved answers.
The source contrast tests cover body, quiet surfaces, major fields, links, actions and commands.
Rendered responsive and interactive acceptance is recorded separately by integration.
