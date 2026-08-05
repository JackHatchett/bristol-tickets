# The styling contract

What an agent needs to style a new piece of Bristol Tickets. `theme.py` holds
every visual constant the app draws with; this file says what each one means and
which one to reach for.

- **Take a colour from the live palette `C`, never from a literal.** `C` is a
  dict the current scheme fills; reading it at paint time is what lets a scheme
  swap reach already-built widgets.
- **Take a gap, a corner or a font size from a token scale, never from a
  number.** `space("md")`, `radius("lg")`, `type_size("title")`.
- **Read `C` and the token functions at paint time, not at import time.** A name
  bound once at import holds the value the app started with.

## Scheme keys

A scheme is one complete palette under a name in `theme.py`'s `SCHEMES`. Every
scheme carries every key below; `check_schemes()` names any that does not.

| Key | What it colours |
| --- | --- |
| `INK` | Primary text. |
| `INK_SOFT` | Secondary text: metadata, captions, an inactive tab. |
| `CANVAS` | The window and dialog background — the ground everything sits on. |
| `SURFACE` | A raised thing: a card, an input, a menu, a panel. |
| `BORDER` | A hairline separating two surfaces. |
| `ACCENT` | The brand colour. Primary buttons, the selected tab, focus. |
| `ACCENT_DK` | Accent text, at a contrast that reads on `SURFACE`. |
| `ON_ACCENT` | Text and marks drawn on top of an `ACCENT` fill. |
| `AMBER_BG` / `AMBER_TX` | The epic badge. |
| `BUILD_BG` / `BUILD_TX` | The Build record-type pill. |
| `FIX_BG` / `FIX_TX` | The Fix record-type pill. |
| `SEL_BG` | The fill of a selected row or card. |
| `HOVER_BG` | The fill under the pointer, on a card or a view tab. |
| `LIST_BG` | A scrolling list recessed from `CANVAS`, and a monospace path row. |
| `BTN_BG` / `BTN_BORDER` / `BTN_HOVER` / `BTN_PRESSED` | An ordinary button, in its four states. |
| `CREATE_HOVER` | The primary button under the pointer. |
| `DELETE_BG` / `DELETE_HOVER` | A destructive button. |
| `MISSING` | A required field that is empty. |
| `DISABLED_BG` / `DISABLED_TX` | A control that cannot be clicked yet. |
| `NEUTRAL_BG` / `NEUTRAL_TX` | A pill carrying a fact that ranks nothing: effort. |
| `SHADOW` | The soft drop shadow that makes a card the raised surface on a flat canvas. Written `#AARRGGBB`, so it carries its own alpha. |

Families pair a light scheme with a dark one, so `appearance.scheme` in
`config/config.local.json` names either a family (follow the OS) or one scheme
(pinned). `resolve_choice()` collapses the two into a scheme name.

## Tokens

Three fixed scales, scheme-independent: a scheme changes what a thing is
coloured, never how far apart two things sit.

| Scale | Steps | Governs |
| --- | --- | --- |
| `SPACE` | `xs` `sm` `md` `lg` `xl` `2xl` | Every gap, pad, margin, stripe width and inset. |
| `RADIUS` | `sm` `md` `lg` `xl` `pill` | Corners. `sm` a checkbox, `md` a control, `lg` a card or panel, `xl` a modal, `pill` a full round. |
| `TYPE` | `caption` `body` `title` `section` `display` | Font point size. `caption` a badge or metadata line, `body` running text, `title` a card title, `section` a section heading, `display` the largest thing on screen. |

`LAYOUT` sits beside the scales and holds what sizes the window rather than the
space inside it: the window's minimum and opening size, the splitter's opening
split, a column's minimum width, the epic filter's width and the wizard's
minimum size. Reach for it only when the thing being sized is a window or a
pane, never for a gap.

**Size a row from its font's metrics plus a spacing step, never from a fixed
height.** A pill row is `QFontMetrics(font).height() + space("sm")`, so a change
to the type scale carries the row with it.

## Answering an instruction given as intent

An instruction arrives as a feeling — "calmer," "this should read as a warning,"
"make it breathe." Name the token or key that carries it and change that; never
answer with a hex value or a pixel count.

| Intent | What carries it |
| --- | --- |
| Calmer, quieter, less shouty | `INK_SOFT` in place of `INK`; drop one step on `TYPE`; remove a border rather than lightening it. |
| More prominent, draw the eye | `ACCENT` fill with `ON_ACCENT` text; up one step on `TYPE`. |
| Reads as a warning | `FIX_BG` / `FIX_TX` for a label, `MISSING` for a field, `DELETE_BG` for an action. |
| Reads as settled or complete | `BUILD_BG` / `BUILD_TX`. |
| Ranks nothing, just a fact | `NEUTRAL_BG` / `NEUTRAL_TX`. Pressure and effort are read this way: neither sorts anything. |
| Make it breathe | Up one step on `SPACE` for the gaps, unchanged for the pads. |
| Tighter, denser | Down one step on `SPACE`. |
| Softer, friendlier | Up one step on `RADIUS`. |
| Crisper, more precise | Down one step on `RADIUS`; `BORDER` hairline instead of a fill. |
| Recessed, in the background | `LIST_BG` on `CANVAS`. |
| Raised, in front | `SURFACE` with a `SHADOW`; a `BORDER` hairline at most. |

**Where no key or token carries the intent, say so and stop.** A new key is a
key every scheme has to gain, which is a change to `theme.py` and to this file.

## What the board is made of

- **The canvas is flat and the cards are the only raised surfaces.** A column is
  a header — name, count, overflow menu — over a stack with no fill and no
  border; the well behind the cards is `CANVAS`, not a container.
- **An action that operates on one column lives in that column's menu**, and the
  control row above the columns holds only what applies to the whole board.
- **A view tab is text on the canvas**: `HOVER_BG` under the pointer, and the
  selected one marked by weight and an `ACCENT` underline rather than a fill.
- **A combo box carries a chevron drawn by `chevron_image()`**, cached under the
  system temp folder in the colour it is asked for.
  // Qt stops drawing the style's own drop-down arrow as soon as the combo is
  // styled, and a stylesheet cannot draw a triangle.

## Adding a scheme

Copy an existing palette in `theme.py`, change the values, register it in
`SCHEMES`, and pair it in `FAMILIES` if it has a light and dark member. Add its
name to `CHOICES` to offer it in Settings. `check_schemes()` reports any key the
new palette is missing; the smoke check runs it.
