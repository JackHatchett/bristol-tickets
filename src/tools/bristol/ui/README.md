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
- **Check what you changed against Bristol running on the user's machine**, with
  whatever the runtime offers for seeing a window there. Say so and stop where it
  offers nothing, rather than substituting a render of a different platform.
- **Never install Qt into the session's own sandbox to look at the app.** An
  offscreen render settles geometry at most, and draws the wrong control set,
  fonts and pixel ratio. // The install has cost more sessions than it has saved.

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
split, the column and detail-pane minimum widths, the filter panel's width and
the height its option list scrolls past, and the minimum sizes of the wizard and
the dialogs. Reach for it only when the thing being sized is a window or a pane,
never for a gap.

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

## Words on screen

- **A name is Title Case; a sentence is sentence case.** A tab, a section
  heading, a field label, a picker option and a button all name something and are
  Title Cased. A tooltip, a placeholder, a notice and a checkbox whose label is a
  clause all say something and are not. "Hide Closed Items" names a mode; "Open
  this installation when Bristol Tickets starts" is a sentence.
- **A picker holds the stored value in its item data and shows a caption.** The
  two move independently, so a vocabulary is reworded without a migration and a
  column keeps the spelling every writer already uses. `settled_combo.fill_words`
  loads one from `(value, caption)` pairs; `theme.py` holds the pairs.
- **An option is a name, and its explanation is the picker's tooltip.** Effort
  offers Small through Extra Large and hovers the budget anchors; Blocked offers
  four names and hovers what each means. An option carrying its own explanation
  makes every row as wide as the longest sentence in it.
- **A caption is ours to choose; a protocol string is not** — `src/tools/README.md`
  §A borrowed format's words, and our own. Nothing on this page is a protocol
  string.

## Where a card is edited

Two surfaces write a card, and each has its own job.

- **Settings writes each choice at the moment it is made**, one key per
  control, and carries no Save button. The status line names the row it wrote.
- **The detail pane edits a selected card in place**: status, stage, owner,
  epic, effort, pressure and Blocked are live controls, and comments, links and
  image attachments post from it. Blocked says what kind of thing has stopped the
  card and never which one — that is a `blocks` link under Links — and moving a
  card to Done clears it. Every pane write goes down the same connection as
  every other writer, so the change-log triggers record it identically.
- **The Edit Record dialog is where a record is created** — both kinds — **and
  where the fields that do not fit a pane are rewritten**: the title, the
  description, the record type, the kind, the originator, an epic's type and
  status, and deletion.
- **The pane's width and collapsed state persist** under `appearance.detail_width`
  and `appearance.detail_collapsed` in `config/config.local.json`, written by
  the main window as the user moves them.

## Where a person types

- **Every field a person types more than a word into is
  `growing_edit.GrowingTextEdit`.** It wraps, grows downward with the text to
  its `max_lines` ceiling and scrolls vertically after that, so nothing typed
  leaves the view. A `QLineEdit` is for a value a glance takes in whole — a
  ticket number, a slug.
- **`submitted` is that field's Return**: it fires where the field posts or
  accepts, and Shift+Return always opens a line. A field whose Return belongs to
  the text takes `newline_on_return=True`.
- **A button beside a growing field aligns to `Qt.AlignBottom`**, so it keeps
  the field's foot as the field grows.

## Where a question is asked

- **Ask a yes/no question with `dialogs.confirm()`, a question with other
  answers with `dialogs.choose()`, and state something unanswerable with
  `dialogs.notify()`.** Never a `QMessageBox`: the platform's box arrives with
  its own glyph, its own button ranks and its own palette.
- **Give the action a label that names it** — "Delete", "Move to Archive" —
  rather than Yes, and pass `destructive=True` where it cannot be undone, which
  is what puts it at the `DELETE_BG` rank.
- **The way out is always the ordinary rank and always the default**, so Enter,
  Esc and the title-bar close all land on it.

## What the board is made of

- **The canvas is flat and the cards are the only raised surfaces.** A column is
  a header — name, count, overflow menu — over a stack with no fill and no
  border; the well behind the cards is `CANVAS`, not a container.
- **An action that operates on one column lives in that column's menu**, and the
  control row above the columns holds only what applies to the whole board.
- **Everything that narrows the board is one panel behind the Filter button**,
  and what it is narrowed to stands on the control row as a chip that removes
  itself. A second control that hides cards is a second place to look for why a
  card is missing.
- **A control that narrows the board is never a setting.** It changes what is on
  screen now and is gone at the next launch; a setting changes how the app
  behaves and is written to `config/config.local.json`. Which surface a control
  belongs on follows from that: the Filter panel, or the Settings tab.
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
