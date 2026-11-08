---
name: Optimax
description: User-selected Circuit homepage with preserved Help document surfaces.
colors:
  bg: "#081525"
  ink: "#F3F7FF"
  muted: "#B9C8DB"
  accent: "#4D87FF"
  on-accent: "#081525"
  focus: "#81AAFF"
  surface: "#0D2037"
  line: "#395470"
  command-bg: "#081525"
  command-ink: "#F3F7FF"
  command-muted: "#B9C8DB"
  command-accent: "#81AAFF"
  bg-light: "#F3F7FF"
  ink-light: "#081525"
  muted-light: "#425B73"
  accent-light: "#1959C6"
  on-accent-light: "#F3F7FF"
  focus-light: "#1959C6"
  surface-light: "#E6EEF9"
  line-light: "#8A9FB8"
typography:
  display:
    fontFamily: "Sora, sans-serif"
    fontSize: "clamp(3rem, 7.1vw, 6rem)"
    fontWeight: 700
    lineHeight: 1.055
    letterSpacing: "-0.04em"
  headline:
    fontFamily: "Sora, sans-serif"
    fontSize: "clamp(2rem, 3.7vw, 3.5rem)"
    fontWeight: 700
    lineHeight: 1.17
    letterSpacing: "-0.035em"
  body:
    fontFamily: "Sora, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.75
  action:
    fontFamily: "Sora, sans-serif"
    fontSize: "14px"
    fontWeight: 700
  metadata:
    fontFamily: "Sora, sans-serif"
    fontSize: "13px"
    fontWeight: 700
    lineHeight: 1.6
  code:
    fontFamily: "ui-monospace, SFMono-Regular, Consolas, monospace"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 2
rounded:
  action: "6px"
  theme-control: "8px"
  terminal: "12px"
  junction: "50%"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "24px"
  hero: "72px"
  section: "112px"
  section-compact: "70px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    typography: "{typography.action}"
    rounded: "6px"
    padding: "12px 24px"
    height: "54px"
  nav-cta:
    textColor: "{colors.ink}"
    height: "44px"
  theme-toggle:
    textColor: "{colors.ink}"
    rounded: "8px"
    height: "44px"
  parallel-assignment:
    textColor: "{colors.ink}"
    padding: "0 20px 46px"
  acceptance-boundary:
    textColor: "{colors.ink}"
    padding: "46px 0 0"
  terminal:
    backgroundColor: "{colors.command-bg}"
    textColor: "{colors.command-ink}"
    rounded: "12px"
    padding: "30px"
---

# Optimax design system

The user selected Circuit for the production homepage. Inherit its navy/cobalt grounds, self-hosted Sora type, broad flush-left offer, open space and connected independent assignments. Supporting copy is adapted for the production funnel. This adopts the existing direction.

The frontmatter describes `/` only. [src/homepage.html](src/homepage.html), [src/homepage.css](src/homepage.css) and the [production contract](.impeccable/surfaces/homepage-production-circuit.md) are authoritative. [.impeccable/design.json](.impeccable/design.json) records components and explicit surface scopes.

## Preserved surfaces

Help, articles and the error page retain Mona Sans, the existing juniper/mineral/brass document palette, [src/style.css](src/style.css) and [src/theme.js](src/theme.js). Article prose retains its 72ch reading measure and existing responsive behavior. Homepage adoption does not retheme these surfaces.

Circuit is applied at the production root. Standalone homepage previews, `/versions/` routes and comparison navigation are removed.

## Homepage color and type

Dark uses navy #081525, light ink #F3F7FF, cobalt #4D87FF, muted blue #B9C8DB, raised #0D2037 and structural #395470 rules. Light uses #F3F7FF grounds, navy ink, #1959C6 actions, #425B73 muted text, #E6EEF9 surfaces and #8A9FB8 rules. The command panel retains its navy/light pair. Match text and focus to the actual surface.

Sora 400/700 are local WOFF2 files with font-display swap and a retained OFL license. Code uses the system monospace stack. Display and section clamps are in the frontmatter. Functional text is at least 12px, task states and section captions use 13px, and substantive paragraphs are at least 15px. Commands inherit their preformatted 14px desktop or 12px compact size. Keep full wording and intrinsic content growth.

## Layout and connections

The homepage container is at most 1280px. It uses viewport-minus-112px space by default, minus 72px below 1100px, minus 40px below 700px and minus 32px below 359px. Hero top space is 72px, reducing to 64px below 1100px and 48px below 700px. Sections use 112px padding, reducing to 70px on compact screens.

Three semantic independent assignments have circular junctions, separate reading lanes and connecting rules. A separate acceptance boundary follows the group. The reviewed change already exists; the diagram never presents review of its own unfinished input as parallel work. Below 700px, assignments become a single column with an isolated left connector lane. Long labels wrap within their own rows. The caption and note explicitly identify an illustration rather than live activity.

Intro, proof, FAQ and installation use measured split layouts and become one column below 700px. Mechanism steps become a vertical sequence. Footer content reflows in source order. Copy may grow sections; preserve breathing room, full wording, connector clearance and fragment destinations.

## Controls and production funnel

Install Optimax targets #install; the secondary hero link targets #mechanism. Keep a fully visible installation action in the first viewport at 320, 390, 768 and 1440px in both themes. The theme control remains last in the right-aligned header actions, has a 44px target and starts hidden until bound. Its accessible name stays Dark theme; pressed state reflects the choice.

Root uses the palette-aware implementation in [src/homepage-theme.js](src/homepage-theme.js), published as assets/homepage-theme.js. Help retains assets/theme.js. Both share the saved preference key, default dark without a valid choice and honor saved light. Root theme metadata follows its palette after CSS readiness and toggles. Production client and installation controls remain shared.

Codex/Claude tabs retain pressed states, exact marketplace command bytes, wrapping code, copy action and visible status. Source inspection, usage charges, host limits and off controls accompany the offer. Seven native FAQ disclosures retain full answers; differentiation follows them and precedes installation. The root is indexable with absolute canonical and matching title, description and Open Graph metadata for SITE_URL. Assets and Help links respect the deployment prefix.

## Accessibility and motion

Links, buttons and summaries use a contrasting 3px focus outline with 6px outside offset. Rounded controls leave the outline visible and do not inherit the Help system\'s clipped focus treatment. Text and states clear junctions and connector artwork, stay in their reading lanes and do not overlap adjacent sections.

The acceptance trace has one 1.6-second emphasis with cubic-bezier(.16,1,.3,1). Reduced motion removes animations, transitions and smooth scrolling. Semantic HTML, inline SVG and CSS geometry implement the selected direction; no shipping raster is needed.

## Extension rules

Keep Circuit colors and geometry, captions below headings, exact approved hero/subtitle, honest evidence qualifiers and independent scopes. Do not introduce ornamental section counters, fake live dashboards, quantified savings, new font families or a new visual concept. Help remains governed by its existing document stylesheet and hierarchy.
