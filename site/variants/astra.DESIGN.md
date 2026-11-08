---
name: "Optimax — Exposure (experimental preview)"
description: "Source-derived photographic contact-proof system for versions/astra/ only."
colors:
  bg-dark: "#17111b"
  ink-dark: "#fcf6ff"
  muted-dark: "#c9bbce"
  line-dark: "#62546a"
  surface-dark: "#251b2a"
  lift-dark: "#312237"
  accent-dark: "#dab5ff"
  accent-ink-dark: "#2a103e"
  focus-dark: "#efc5ff"
  stock-dark: "#d6b9e3"
  stock-ink-dark: "#251429"
  stock-muted-dark: "#4e3753"
  stock-line-dark: "#785c80"
  field-dark: "#46285a"
  field-ink-dark: "#fff5ff"
  field-muted-dark: "#ebd7f4"
  field-line-dark: "#977da6"
  negative: "#19101c"
  negative-ink: "#f8effb"
  negative-muted: "#d1bdd6"
  negative-accent: "#e2c2f2"
  bg-light: "#f8f2f9"
  ink-light: "#241a29"
  muted-light: "#594b60"
  line-light: "#a697ac"
  surface-light: "#eee4f1"
  lift-light: "#e4d6e8"
  accent-light: "#60298a"
  accent-ink-light: "#ffffff"
  focus-light: "#65218c"
  stock-light: "#d9c5e2"
  stock-ink-light: "#241329"
  stock-muted-light: "#49344f"
  stock-line-light: "#85708c"
  field-light: "#ddc8e9"
  field-ink-light: "#291537"
  field-muted-light: "#4e375a"
  field-line-light: "#8e779a"
typography:
  display:
    fontFamily: "Fahkwang, 'Mona Sans', sans-serif"
    fontSize: "clamp(64px, 6.35vw, 96px)"
    fontWeight: 600
    lineHeight: 1.02
    letterSpacing: "-0.04em"
  headline:
    fontFamily: "Fahkwang, 'Mona Sans', sans-serif"
    fontSize: "clamp(40px, 4.3vw, 68px)"
    fontWeight: 600
    lineHeight: 1.08
    letterSpacing: "-0.035em"
  title:
    fontFamily: "Fahkwang, 'Mona Sans', sans-serif"
    fontSize: "clamp(23px, 2.15vw, 34px)"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  body:
    fontFamily: "'Mona Sans', system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: "'Mona Sans', system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 700
    lineHeight: 1.3
  caption:
    fontFamily: "'Mona Sans', system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 700
    lineHeight: 1.4
    letterSpacing: "0.02em"
  question:
    fontFamily: "'Mona Sans', system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 700
    lineHeight: 1.45
  code:
    fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  control: "3px"
  selector: "2px"
  circle: "50%"
spacing:
  gutter: "clamp(20px, 4.5vw, 76px)"
  gutter-phone: "clamp(16px, 5vw, 28px)"
  section: "clamp(72px, 8vw, 124px)"
  section-phone: "66px"
components:
  button-primary:
    backgroundColor: "{colors.accent-dark}"
    textColor: "{colors.accent-ink-dark}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "11px 18px"
  button-outline:
    backgroundColor: "transparent"
    textColor: "{colors.ink-dark}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "11px 18px"
  theme-toggle:
    backgroundColor: "transparent"
    textColor: "{colors.ink-dark}"
    rounded: "{rounded.circle}"
    width: "44px"
  host-selector:
    backgroundColor: "transparent"
    textColor: "{colors.negative-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.selector}"
    padding: "10px 16px"
  navigation:
    textColor: "{colors.muted-dark}"
    typography: "{typography.label}"
  disclosure:
    textColor: "{colors.ink-dark}"
    typography: "{typography.question}"
    padding: "17px 2px"
  evidence-pair:
    backgroundColor: "{colors.surface-dark}"
    padding: "clamp(24px, 3vw, 48px)"
---

# Design System: Optimax — Exposure

## Overview

**Creative North Star: "Exposure"**

Exposure is the code-led homepage comparison at `versions/astra/`. It records a photographic contact-proof world for this experimental route only. Circuit remains the production identity; these draft files do not adopt a replacement global system.

Aubergine ground, lilac stock and wide Fahkwang lettering frame three crops from one original still life. A separate unexposed aperture holds the waiting inspection state. The built preview, rather than the selection brief, is the source for the values below.

**Key Characteristics:**

- Rectangular photographic apertures and a perforated stock edge.
- Wide display lettering paired with compact functional captions.
- Paired surface and ink roles in dark and light themes.
- Flat reading surfaces, visible keyboard outlines and a separate waiting boundary.

Source: [built preview template](astra.html), [stylesheet](astra.css) and [surface brief](../.impeccable/surfaces/homepage-astra.md). The companion [extension sidecar](astra.design.json) is scoped to this draft. The route declares its own canonical URL and `noindex`; neither establishes global adoption.

## Colors

The palette moves between aubergine-black and pale paper while retaining lilac contact stock and a violet process field. Frontmatter owns the exact values. Dark is the default; `-light` tokens supply the light-theme overrides. The four `negative` roles are shared by both themes. Sidecar theme bindings map all 21 CSS color roles in each theme.

### Primary

- **Lilac action / violet action:** `accent-dark` and `accent-light` color links, selected headline text and primary actions. Each uses its paired `accent-ink` for filled controls.
- **Keyboard focus:** the theme-specific `focus` roles mark ordinary page controls; the installation stock and command print use their separately documented outline colors.

### Secondary

- **Contact stock:** the `stock` family supplies photographic mounting paper, its captions and its separator lines.
- **Process field:** the `field` family supplies the violet section, its body copy and manuscript row separators.

### Neutral

- **Page and reading surfaces:** the `bg`, `ink`, `muted`, `line`, `surface` and `lift` families define the page, reading panels, rules and hover fill.
- **Command print:** the shared `negative`, `negative-ink`, `negative-muted` and `negative-accent` roles keep commands readable on a fixed dark surface in both editions.

**The Paired Ink Rule.** Each material uses its own ink roles; the command print keeps its dark ground in both themes.

## Typography

**Display Font:** Fahkwang 600, with Mona Sans and sans-serif fallbacks.
**Body Font:** Mona Sans 400 and 700, with system-ui and sans-serif fallbacks.
**Code Font:** the UI monospace stack recorded in frontmatter.

Fahkwang supplies the wide counters and compact display rhythm; Mona Sans carries reading text, actions and status captions. All three shipped WOFF2 files are self-hosted with `font-display: swap`. Fahkwang is pinned to `@fontsource/fahkwang@5.3.0`; the existing Mona Sans package is also pinned to 5.3.0. Their SIL Open Font License 1.1 notices ship at [Fahkwang OFL](../public/fonts/fahkwang-OFL.txt) and [Mona Sans OFL](../public/fonts/OFL.txt). Font paths live in the sidecar.

### Hierarchy

- **Display, headline and title:** frontmatter records the base desktop h1, h2 and h3 ramps. The hero deck also uses Fahkwang 600 at `clamp(21px, 1.8vw, 29px)` with 1.22 line height.
- **Body:** the base body role has a 70ch paragraph limit. At 640px and below the body becomes 16px; individual support copy uses its own observed compact sizes.
- **Label and caption:** actions use the label role; ready and waiting captions use the caption role. The 12px functional captions do not establish a reusable decorative kicker pattern.
- **Question and code:** native disclosure questions use the question role; installation commands use the code role and wrap safely.
- **Responsive headings:** at 820px and below h1 becomes `clamp(54px, 8.3vw, 69px)`. At 640px and below h1 becomes `clamp(41px, 11.8vw, 66px)` with 1.03 line height, h2 becomes `clamp(33px, 7.2vw, 46px)`, and h3 becomes 24px. Base heading tracking remains in force.

## Layout

The working column is capped at 1440px and centered within fluid side gutters. Reused gutter and section-spacing values live in frontmatter; the phone versions apply at 640px and below. Desktop hero text uses a 1.47fr / 1fr grid, while the photographic strip and waiting aperture occupy a 3fr / 1fr grid.

- **1050px and below:** header and photographic gaps tighten; the hero columns become 1.05fr / 1fr.
- **820px and below:** navigation occupies a second header row. The ready strip and waiting aperture stack; the waiting area becomes a horizontal row. Intro, FAQ and installation grids become single-column.
- **640px and below:** the photographic leader appears before the offer. The hero becomes a block, ready assignments become rows with 72px cropped prints beside captions, and the waiting frame follows them. Evidence entries and the footer reflow for phones.
- **380px and below:** the header wordmark is 19px with a 22px mark and 5px internal gap. Header actions use a 6px gap; the install action has 8px inline padding and hides only its decorative arrow. Its readable label remains. The brand link, install action and theme control retain their 44px minimum hit areas.

**The Separate Exposure Rule.** The three ready task captions and the waiting inspection aperture remain visibly distinct within this preview.

## Elevation & Depth

The stylesheet uses no box shadows or text shadows. Depth comes from adjoining tonal fields, the photographic still life, hairline separators and the dashed inspection frame. Hover fill uses the existing `lift` role; it does not introduce another elevation scale. Motion is limited to smooth anchor scrolling and state changes; no keyframe animation or timed transition is defined. The reduced-motion query forces automatic scrolling and disables animation and transitions.

## Shapes

Photographic windows, evidence surfaces, command prints and the waiting aperture remain rectangular. The photographic stock alone has a narrow perforated edge. Four easel corners recur in the product mark and inspection aperture. Filled and outlined actions have the control radius; host selectors use the smaller selector radius; the theme control is circular. Border and focus details are preserved in the sidecar rather than invented as frontmatter token groups.

## Components

### Buttons and header

Primary actions use the accent and paired action ink, with an underlined, slightly brighter hover state. The outlined header install action uses page ink, a page rule and the hover fill. The circular theme button is the last header control. Navigation and standalone controls retain 44px minimum targets; primary actions have a 50px base minimum height and 46px on phones.

Keyboard focus uses a 3px outline with a 4px offset. The installation stock overrides the outline to `#451461`, while the dark command print uses its negative accent. Controls retain their existing accessible labels and browser semantics.

### Contact proof and reading surfaces

Three ready items share the photographic stock. Captions remain selectable document text; decorative images have empty alternative text. The waiting item has a separate dashed frame and a readable dependency state. The process uses three numbered manuscript rows. Public verification uses two adjoining evidence entries inside one flat reading surface.

The [single photographic plate](../public/images/astra-exposure.webp) is a 2172 × 724 WebP of 78,162 bytes, reused by the phone leader and all three crops. Delivery SHA-256: `0e5bf40bf1a6349710b411ce131aaa964a7ef9eaac8c5f28205c0b7ba482ad7c`. The [development provenance record](astra-exposure.webp.json) preserves the exact 1,854-character prompt, source and delivery digests, dimensions and encoding. The WebP XMP embeds the exact prompt and source digest. Its origin is the built-in OpenAI ImageGen tool; a generation-model identity is not reported.

### Disclosures and installation

Seven FAQ items use native details and summary elements. A CSS chevron changes orientation with the open state; the source does not define a timed animation. The command print contains two host selectors, a wrapping command block, copy feedback and existing supporting links. The sidecar reproduces representative visual states; runtime host selection, command copying and theme preferences remain owned by the existing site helpers. No input field or speculative component is added to this system.

## Do's and Don'ts

### Do:

- **Do** keep each surface paired with its theme-specific text and focus treatment.
- **Do** preserve readable task names and readiness or waiting states outside the decorative photographs.
- **Do** retain visible keyboard outlines and the established minimum standalone hit areas when compacting the header.
- **Do** reuse the single original plate through its three crops and phone leader, with its provenance record.

### Don't:

- **Don't** treat this experimental route as approval to replace the global Circuit system.
- **Don't** present the waiting inspection frame as an additional ready exposure.
- **Don't** infer a generation-model identity or independent human approval from the image provenance.

Not canonized: section metadata is not a future kicker or eyebrow rule. These source-derived draft notes do not stand in for the separate finish review, runtime acceptance or a user decision to adopt the world.
