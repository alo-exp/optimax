# ĀloLabs design foundation

A reusable foundation for clear technical products. Optimax is its first application; copy, delegation illustrations and help content remain product-specific.

## Principles

- Build hierarchy with type, generous space and fine rules before decoration.
- Use a restrained violet-to-purple gradient for primary actions, hero emphasis and short transition surfaces. Keep paragraphs on solid surfaces.
- Treat light and dark themes equally: reading, search, code, controls and focus states all use semantic tokens.
- Pair a system sans-serif with Georgia for selective editorial emphasis. Content remains usable without external fonts, gradients or JavaScript.
- Explain parallel work with task rows and dependency labels. Illustrative status is not a claim of live activity.

## Semantic tokens

The stylesheet is the source of truth. Light is the default; `html[data-theme="dark"]` selects dark. The matching `prefers-color-scheme: dark` fallback applies only without an explicit theme, including without JavaScript. Each palette sets native `color-scheme`.

| Role / CSS token | Light | Dark |
| --- | --- | --- |
| Reading surface / `--bg` | #faf8ff | #171124 |
| Primary ink / `--ink` | #261a39 | #f5efff |
| Secondary text / `--muted` | #665a75 | #c0b4d0 |
| Decorative divider / `--border` | #d9cfea | #51435f |
| Control boundary / `--control-border` | #89749f | #9883af |
| Elevated surface / `--elevated` | #ffffff | #21182f |
| Selected surface / `--selected` | #ede5fb | #2d2042 |
| Accent / `--accent` | #6d28d9 | #c4b5fd |
| Focus / `--focus` | #6d28d9 | #c4b5fd |
| Technical surface / `--panel` | #241a35 | #100b1a |
| Technical ink / `--on-panel` | #f5efff | #f5efff |
| Technical secondary text / `--panel-muted` | #c0b4d0 | #c0b4d0 |
| Technical accent / `--panel-accent` | #d8c8ff | #d8c8ff |
| Technical divider / `--panel-border` | #63516f | #63516f |
| Gradient / `--gradient-start` → `--gradient-end` | #6d28d9 → #9333ea | #6d28d9 → #9333ea |
| Gradient ink / `--on-gradient` | #ffffff | #ffffff |
| Hero gradient / `--display-start` → `--display-end` | #6d28d9 → #9333ea | #c4b5fd → #e9d5ff |
| Offset shadow / `--shadow` | #e8dff5 | #30203f |

Use panel tokens for terminal, code, footer and dark editorial sections. Technical components override `--focus` with `--panel-accent`; the closing gradient uses white focus. Decorative dividers carry no essential state. Controls receive stronger boundaries and explicit labels.

Automated tests extract actual stylesheet tokens and calculate WCAG relative luminance. They require 4.5:1 for normal text on reading, elevated, selected and technical surfaces; sample each gradient at 101 positions; and require 3:1 for focus against its corresponding surface. These checks qualify the color contract, not complete accessibility or rendered layout.

## Typography and layout

Use the system sans stack for body copy and Georgia for selective display emphasis. Headings have responsive sizing and tight tracking; paragraphs use relaxed line height. Eyebrows use compact uppercase labels. Essential instructions belong in normal body text.

Content is capped at 1320px. Desktop gutters are 48px; narrow gutters are 20px. Main compositions stack below 850px; compact adjustments begin at 520px. Compact headlines scale to viewport width. Code wraps using `pre-wrap` and `overflow-wrap: anywhere`.

## Components and interaction states

- **Header:** brand, concise navigation and `.header-actions`. Actions place the CTA first and theme button last. Below 850px the CTA disappears; below 520px primary navigation disappears while the theme control stays at the right edge.
- **Theme button:** native button, visible Theme label, stable accessible Dark theme name and `aria-pressed` state. Minimum target is 44px square; it does not shrink. JavaScript reveals it only when operational; `.theme-toggle[hidden]` overrides flex display.
- **Primary action:** white text on a violet-to-purple gradient, with a solid-color fallback. Hover adds an underline and an outer surface-colored ring while preserving the text contrast pair.
- **Hero emphasis:** accent text is the fallback; supporting browsers add clipped gradient text. Forced-color mode restores system text.
- **Technical panel:** dark purple surface, subtle offset shadow, fine rules and readable labels. Dependent WAITING rows have a dashed boundary; words convey status independently of color.
- **Editorial sections:** eyebrow, large heading and explanatory column. Keep prose on solid surfaces; gradients are reserved for short ticker and closing sections.
- **Terminal:** readable commands, explicit platform buttons, visible selected underline and copy feedback. Commands wrap on narrow viewports.
- **Search:** labeled input, explicit text and placeholder colors, rule-separated results, and a selected surface with outline. Search content is built with text nodes.
- **Footer:** technical-surface tokens, readable secondary text and underlined hover links.
- **Focus:** a 3px ring with 4px offset for links, buttons, inputs and summaries. Keyboard-selected search results also receive a 2px outline. State must never depend only on color.

## Preferences and validation

Reduced motion disables smooth scrolling. Theme changes do not animate. Forced-color mode restores system text and borders on gradient components.

The controller owns explicit state, persistence and system-preference changes. CSS owns the no-JavaScript preference fallback and native color scheme. Verify both layers, including blocked storage and unavailable browser APIs.

Before release, inspect light and dark views at 320px and desktop widths, keyboard flow, search, installation controls, article code and zoom/reflow in the built-in browser. Automated color and DOM checks are targeted evidence; visual quality and complete WCAG conformance require rendered inspection.

## Reuse

Keep semantic tokens, responsive conventions, control states and accessibility rules. Replace product copy, diagrams, commands and help taxonomy with independently verified content.
