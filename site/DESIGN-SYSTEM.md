# ĀloLabs design foundation

An independent, reusable foundation for clear technical products. Optimax is its first application; product copy, routing diagrams and help content are product-specific.

## Principles

- Build hierarchy with type, generous space and fine rules before adding decoration.
- Use signal green sparingly for emphasis, active states and key surfaces. Graphite and warm white carry the reading experience.
- Pair a confident sans-serif with a restrained editorial serif for emphasis. Use system fallbacks so the site remains usable without a font service.
- Vary composition to serve the content: split explanations, editorial lists, dark technical surfaces and open reading pages.

## Tokens

| Role | CSS token | Value |
| --- | --- | --- |
| Primary ink | `--ink` | #171a18 |
| Reading surface | `--paper` | #f5f4ed |
| Secondary text | `--muted` | #646b63 |
| Light divider | `--line` | #d5d8ce |
| Accent surface | `--signal` | #c3f45b |
| Dark divider | `--dark-line` | #454d43 |
| Maximum content width | `--max` | 1320px |

Body typography uses a system sans stack, with Georgia for selective italic display emphasis. Display headings use tight tracking and responsive `clamp()`; body copy uses relaxed line height. Eyebrows use compact uppercase labels with tracking. Avoid using small labels for essential instructions.

## Components and layout

- **Header:** brand, concise navigation and a clear destination; a skip link precedes it.
- **Buttons and links:** solid graphite for primary actions, quiet text links for secondary actions. Provide visible focus.
- **Editorial sections:** an eyebrow, oversized heading and a separate explanatory column; stack at narrower widths.
- **Dark technical panel:** dark background, fine dividers, labels and concise content. Never use decorative status as a claim of live data.
- **Lists and help articles:** horizontal rules and clear titles; articles have readable measure and linked section anchors.
- **Search:** labelled input, keyboard-accessible results, live count and an explicit clear action.

Desktop gutters are 48px and narrow layouts use 20px. The main layout stacks below 850px; compact adjustments begin at 520px. Content must remain readable at zoom and reflow without horizontal page scrolling.

## Interaction and accessibility

Use semantic landmarks, headings and native controls. Maintain a visible keyboard focus indicator and meaningful link text. Search updates a live status and supports arrow keys, Enter and Escape; output must be built with DOM text nodes, not query-derived HTML. Respect reduced-motion preferences; motion should never be required to understand state. Test contrast, keyboard flow and responsive rendering for each new product application rather than treating tokens alone as compliance.

## Reuse

Start with the semantic tokens and principles. Keep product-specific illustration, words and routes outside the foundation. Extend tokens only for a demonstrated need; document new contrast pairs and interaction states.
