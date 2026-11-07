---
name: Optimax
description: A component manifest for clear ownership and accepted work.
colors:
  bg: "#082820"
  ink: "#eceae9"
  muted: "#b7c9c0"
  border: "#547467"
  control-border: "#93aaa0"
  elevated: "#10372d"
  selected: "#204b3e"
  accent: "#dbba68"
  focus: "#f3d78e"
  mineral: "#eceae9"
  on-mineral: "#082820"
  mineral-muted: "#535f5f"
  brass: "#dbba68"
  on-brass: "#082820"
  panel: "#061d17"
  on-panel: "#eceae9"
  panel-muted: "#b7c9c0"
  panel-accent: "#dbba68"
  panel-border: "#547467"
  bg-light: "#f3f1e9"
  ink-light: "#082820"
  muted-light: "#4b5e55"
  border-light: "#a9b6aa"
  control-border-light: "#6a8071"
  elevated-light: "#ffffff"
  selected-light: "#e0e7dc"
  accent-light: "#4a5b24"
  focus-light: "#245a44"
  mineral-light: "#e5e8df"
  on-mineral-light: "#082820"
  mineral-muted-light: "#4b5e55"
typography:
  display:
    fontFamily: "Mona Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(44px,5.34vw,82px)"
    fontWeight: 700
    lineHeight: 1.07
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "Mona Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(36px,3.78vw,58px)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.03em"
  title:
    fontFamily: "Mona Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "27px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.03em"
  body:
    fontFamily: "Mona Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1.8
  navigation:
    fontFamily: "Mona Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "24px"
    fontWeight: 400
    lineHeight: 1.2
  action:
    fontFamily: "Mona Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 700
  article-title:
    fontFamily: "Mona Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(39px,4.3vw,64px)"
    fontWeight: 700
    lineHeight: 1.08
    letterSpacing: "-0.03em"
  article-deck:
    fontFamily: "Mona Sans, ui-sans-serif, system-ui, sans-serif"
    fontSize: "22px"
    fontWeight: 400
    lineHeight: 1.55
  code:
    fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.8
rounded:
  task-number: "4px"
  acceptance-check: "3px"
  theme-control: "8px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  control: "18px"
  field: "20px"
  lg: "24px"
  row-gap: "25px"
  xl: "30px"
  reading-section: "40px"
  section-wide: "108px"
  section-medium: "75px"
  section-compact: "60px"
components:
  button-primary:
    backgroundColor: "{colors.brass}"
    textColor: "{colors.on-brass}"
    typography: "{typography.action}"
    padding: "17px 23px"
    height: "54px"
  nav-cta:
    backgroundColor: "{colors.brass}"
    textColor: "{colors.on-brass}"
    padding: "12px 23px"
    height: "56px"
  theme-toggle:
    textColor: "{colors.ink}"
    rounded: "{rounded.theme-control}"
    padding: "13px 18px"
    height: "44px"
  theme-toggle-hover:
    backgroundColor: "{colors.selected}"
  input-search:
    backgroundColor: "{colors.elevated}"
    textColor: "{colors.ink}"
    padding: "18px 0"
  navigation:
    textColor: "{colors.ink}"
    typography: "{typography.navigation}"
  tab-install:
    textColor: "{colors.panel-muted}"
    padding: "10px 30px"
    height: "48px"
  tab-install-selected:
    backgroundColor: "{colors.brass}"
    textColor: "{colors.on-brass}"
  task-label:
    backgroundColor: "{colors.mineral}"
    textColor: "{colors.on-mineral}"
    padding: "14px 20px"
    height: "88px"
  acceptance-boundary:
    backgroundColor: "{colors.brass}"
    textColor: "{colors.ink}"
    padding: "13px 29px"
    height: "76px"
  terminal:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.on-panel}"
    padding: "26px 30px 20px"
  article-link:
    textColor: "{colors.ink}"
    padding: "21px 0"
---

# Design System: Optimax

## Overview

**Creative North Star: "The Component Manifest"**

Optimax uses the material language of component labels and a parts register: robust sans type, clipped fields, aligned rows and visible boundaries. The juniper ground, mineral fields and dull brass actions make ownership and acceptance easy to distinguish. These are durable visual materials; the homepage's particular composition remains in its [surface brief](.impeccable/surfaces/build-js.md).

Reading surfaces keep the same palette and type family while giving prose a calm measure. Dark is the default. Light is an authored alternate, with an explicit saved choice retained. The system records the implementation in [src/style.css](src/style.css), [build.js](build.js) and [src/theme.js](src/theme.js); frontmatter contains normative values, and [.impeccable/design.json](.impeccable/design.json) extends them with motion, breakpoints and component samples.

**Key Characteristics:**

- Deep juniper ground, mineral fields and brass actions.
- One self-hosted sans family with regular and bold weights.
- Cut corners identify structural fields and actions.
- Independent assignment labels share a spanning acceptance boundary.
- Article typography remains measured, legible and quiet.

## Colors

Brass marks actions and acceptance; juniper and mineral carry the structure. The frontmatter keys match CSS custom-property names. A `-light` suffix records the override applied by `html[data-theme="light"]`; keys without that suffix record the dark root. The sidecar's eight-step tonal strips are synthesized preview metadata, not additional implementation tokens.

### Primary

- **Dull Brass** (`brass`, `accent`): primary actions, selected installation platform and acceptance edge. `on-brass` supplies its text.
- **Olive Accent** (`accent-light`): links and interactive emphasis on light reading surfaces. Brass actions keep their fixed brass pair in both themes.
- **Focus Brass / Focus Green** (`focus`, `focus-light`): general keyboard focus on each theme's reading ground. Mineral and technical surfaces locally select their own focus ink.

### Neutral

- **Deep Juniper / Warm Paper** (`bg`, `bg-light`): the reading ground.
- **Mineral Ink / Juniper Ink** (`ink`, `ink-light`): principal text.
- **Sage / Slate Green** (`muted`, `muted-light`): supporting prose and metadata.
- **Structural Rule** (`border`, `border-light`) and **Control Rule** (`control-border`, `control-border-light`): separate general dividers from stronger interactive boundaries.
- **Raised Juniper / White** (`elevated`, `elevated-light`): search-field surface; **Selected Juniper / Pale Sage** (`selected`, `selected-light`) marks hover or selection.
- **Mineral Field** (`mineral`, `mineral-light`), with `on-mineral` and `mineral-muted` pairs: light manifest and installation fields.
- **Technical Juniper** (`panel`) with `on-panel`, `panel-muted`, `panel-accent` and `panel-border`: terminal, code, footer and dark sections. These tokens remain fixed in light mode.

**The Local Pair Rule.** Choose the text and focus pair belonging to the actual surface; a technical panel keeps its panel tokens inside either page theme.

## Typography

**Display Font:** Mona Sans, followed by the sans fallback stack in the frontmatter.

**Body Font:** The same family. Regular (400) and bold (700) are self-hosted WOFF2 assets with `font-display: swap` and `font-synthesis: none`.

**Code Font:** The platform monospace stack recorded in `typography.code`.

The family is direct and compact, with tight bold headings and open paragraph spacing. Tabular numerals align task numbers and technical values. There is no second display face.

### Hierarchy

- **Display:** the mineral-field headline; the base clamp is in `typography.display`. The actual wide-screen override is 88px at a minimum width of 1650px. At 1100px and below it uses `clamp(53px,7.2vw,76px)`; at 600px and below, `clamp(39px,9.6vw,57px)` with a 1.04 line height; at 370px and below, 36px.
- **Headline / Title:** section headings and subordinate headings use the recorded headline and title roles. Compact section headings use 36px with a 1.13 line height.
- **Body:** article text uses the body role, a 72ch maximum article measure and a 1.8 line height. It becomes 17px at 600px and below. General marketing paragraphs use a 1.65 line height, with sizes set by their context.
- **Article title / deck:** a distinct document hierarchy; at 600px and below, the title is 41px and the deck is 20px.
- **Navigation / Action:** clear sentence-case controls, with responsive reductions described in Layout.
- **Code:** wraps with `pre-wrap` and `overflow-wrap: anywhere`; terminal and article code reduce to 12px on compact screens.

**The Reading Measure Rule.** Preserve the article's 72ch measure and paragraph rhythm when extending the Help Center.

## Layout

The main container has a 1600px maximum. Its width is the viewport minus 68px by default, minus 40px at 900px and below, and minus 32px at 600px and below. The header has its own 1668px maximum and right-aligned action group; the theme button is the last control in that group.

The parts register uses three equal assignment columns with a 16px gap above one full-width acceptance boundary. At 900px and below, the assignments become separate full-width rows. At 600px and below, each label keeps its number beside the task title and secondary status below. The acceptance title remains visible while secondary dependency microcopy is hidden at 900px and below.

Marketing sections use the section spacing steps in the frontmatter. Split sections become one column at 900px and below. The header wraps at 1100px; at 900px its navigation occupies a full row. At 600px, the Help library groups stack, footer content reflows and article padding reduces. The 370px adjustment keeps the theme control's text while removing its icon. The sidecar records six viewport breakpoints, reduced motion and forced-color component adaptations.

## Elevation & Depth

The system is flat: the stylesheet defines no box or text shadows. Surface changes, real rules and inset clipped boundaries provide depth. The parts register and acceptance boundary use a two-layer silhouette with a 2px inset. Interaction uses underline, border, surface or focus changes; there is no general hover lift.

**The Structural Depth Rule.** Carry hierarchy with tonal surfaces and boundaries, preserving the flat material vocabulary.

## Shapes

The principal field uses an eight-point polygon with clipped corners. Its default cut is 30px and becomes 18px on compact screens. Component-specific cuts are 8px for brass actions, 13px for assignment labels, 20px for the register and 9px for the acceptance edge; their inset layers use their own matching cuts. The terminal uses an 18px cut.

Small radii have specific jobs: task-number tiles, acceptance-check tiles and the theme button use the frontmatter's three rounded tokens. Search fields, article lists and installation tabs use straight rule-based boundaries. A cut corner is structural, not an all-purpose decoration.

## Components

### Actions and theme control

Primary actions use brass with juniper text, a clipped silhouette and an underline on hover. Frontmatter component heights describe the observed **minimum heights**, not fixed heights; retain intrinsic content growth. The navigation CTA is the compact sibling. Clipped actions use a 3px local ink focus outline placed 7px inside the edge so the clip does not erase it.

The theme button has a visible Theme label, a stable accessible Dark theme name and an `aria-pressed` state. It has at least a 44px target in both dimensions, never shrinks, sits rightmost and is hidden until its controller binds successfully. The head script applies a valid explicit saved choice before CSS; otherwise it chooses dark. Theme changes do not animate.

### Search and article links

Search is a labeled native field on the elevated surface, with a stronger control boundary and a focus-within border change. The input keeps its own 3px keyboard focus ring, offset by 2px. Results use ruled rows; the selected result gains the selected surface and a 2px outline. Article links keep a bold title and muted description; hover underlines and accents the title.

### Installation tabs and terminal

Installation platform buttons use `aria-pressed`. The selected platform has a brass fill and 3px bottom rule; hover underlines. The terminal keeps the fixed technical palette, wraps commands and provides a labeled copy button with a visible status region. Controls inside the clipped terminal use the panel's brass focus pair.

### Assignment label and acceptance boundary

Each assignment has its own mineral label, contrasting number tile, task title and secondary status. The acceptance component spans the register beneath them; its inset ground and brass check tile separate acceptance from independent work. These are semantic task labels, not decorative page kickers.

The only keyframe animation emphasizes that acceptance edge once: 1100ms with `cubic-bezier(.16,1,.3,1)`, after 400ms, one iteration, with both fill modes. Content is visible before it starts. Reduced motion removes that animation and smooth scrolling. Forced colors restores system surfaces, borders and text, and removes clipping from the register and acceptance boundary.

### General focus

Links, buttons, inputs and summaries receive a 3px focus outline offset by 5px, with the local exceptions above. Preserve the native details disclosure and its visible focus. Disabled buttons use wait cursor and 0.65 opacity.

## Do's and Don'ts

### Do:

- **Do** retain dark as the default and honor an explicit saved light or dark choice.
- **Do** keep the theme control last in the right-aligned header action group and retain its visible label.
- **Do** use the matching text and focus pair for each mineral or technical surface.
- **Do** keep clipped-control focus inside its visible edge.
- **Do** preserve a calm 72ch article measure, wrapping commands and reduced-motion support.
- **Do** use inline SVG for structural icons and meaningful text for task states.

### Don't:

- **Don't** restore the superseded purple palette, gradient treatment or serif display emphasis.
- **Don't** turn the one-time acceptance emphasis into a continuous or content-hiding animation.
- **Don't** infer live activity from illustrative task labels.
- **Don't** propagate retained editorial eyebrows as a canonical label or typography role.

Not canonized: retained editorial eyebrows are present in source but are excluded from this system's reusable tokens and component examples under the documenter craft floor. This documentation does not certify the missing quality-bar board or complete the pending Impeccable engine phase; neither workflow state is a design token.
