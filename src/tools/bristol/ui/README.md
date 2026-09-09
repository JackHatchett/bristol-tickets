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

A theme pairs a light scheme with a dark one, and a mode says which half is
drawn: `appearance.theme` and `appearance.mode` in `config/config.local.json`
are the two, and `resolve_scheme()` collapses them and the OS state into one
scheme name. A theme whose dark half is `None` draws its light scheme whatever
either says, and `theme_has_dark()` is what a control asks before offering Dark.
`appearance_choice()` reads a configuration written before the two keys existed.

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
  a header — name and count, nothing else — over a stack with no fill and no
  border; the well behind the cards is `CANVAS`, not a container.
- **A control sits on the narrowest surface its effect reaches.** An action over
  the Board's cards, whichever column it reads, goes on the control row above
  the columns; one that reaches every tab goes in the header bar beside Create.
  A column header carries no control, so the three names and counts read across
  one line.
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

## Adding a scheme

Copy an existing palette in `theme.py`, change the values, register it in
`SCHEMES`, and pair it in `THEMES` under the theme it is a half of — `None` for
a dark half that does not exist yet. Add the theme's name to `THEME_CHOICES`,
which is what this build calls each theme it ships. `check_schemes()` reports
any key the new palette is missing; the smoke check runs it.

**`SCHEMES` and `THEMES` are rewritten at every launch** by
`install_collection()`, from the collection an installation actually offers.
The module-level values are what the build ships and what the shipped snapshot
holds; nothing may read either dict expecting a particular theme to be in it.

**A theme's schemes are named for the theme**: `<id>_light` and `<id>_dark`.
The pairing is mechanical, so a theme the user adds and a theme this build
ships have schemes named the same way.

**`THEME_CHOICES` is ordered alphabetically by caption.** A picker holding two
dozen names is read by scanning to the letter, so a theme seated anywhere else
in the list is one nobody finds — and the collection is ordered by name for the
same reason, which is what `order_collection()` does.

**A borrowed scheme takes its source's own name and its source's own colours.**
The grounds, the text and the signal colours are that scheme's; the fills, the
pills and the button states are those colours tinted onto that scheme's own
ground. Where a source palette puts a pair under `CONTRAST_MIN` — an accent too
pale for the text on a primary button, a comment grey too dim to read — the
member that moves is the one carrying the text, and it moves the least distance
that clears the floor.

**A key added to one scheme is added to every one of them, and to
`KEY_CAPTIONS`.** A palette form offers a field per key the reference palette
defines, and a key with no caption is offered under its own name.

**`REFERENCE_PALETTE` is the key set and the fill, not `SCHEMES[REFERENCE_SCHEME]`.**
A user who deletes Pumpkin takes `warm_light` out of `SCHEMES`, so a completion
that read it there would have nothing left to read.

**A dark half completes against `REFERENCE_DARK_PALETTE`**, the light one
against `REFERENCE_PALETTE`. A dark palette wearing light values for the keys
it lacks draws a half-lit board that shows itself only once the OS goes dark,
which is hard to attribute to the theme it came from.

## The collection

Which themes an installation offers is not the build's to decide. `theme.py`
ships the ones in `THEME_CHOICES`; `config/config.local.json` carries the
difference under `appearance.themes`, and `resolve_collection()` puts the two
together into records — a name, a light palette, and a dark palette or `None` —
under ids that never change.

- **The configuration stores differences, never the collection.** A theme
  nobody has touched appears in no key, which is what lets the themes a later
  release ships reach an installation already in use. Copying the shipped
  themes into the configuration on first run would seal that installation
  against every theme added afterwards.
- **The three differences are `added`, `edited` and `deleted`**, and
  `collection_differences()` is what computes them. Restore Shipped Themes
  drops the last two and keeps the first.
- **A shipped theme is edited in the configuration, never in `theme.py`.** A
  personal deletion written into a tracked file would leave every clone
  different and `git status` never clean, and `payload.refresh()` replaces
  `src/` whenever a newer app opens an installation, so it would be undone by
  the next release without a word.
- **A theme's id is stable and its name is not.** What a stored choice names is
  the id, so renaming a theme migrates nothing. `theme_id_for()` mints one.
- **A palette built when the picker offered one Custom option is an ordinary
  theme.** `appearance.custom_scheme` is read, never written, and joins the
  collection under the id `custom` that the old choice stored.

## Managing themes

Settings' Manage Themes button opens `theme_manager.py`: every theme listed
down the left, and the selected one's name and colours on the right, in the
rows `palette_form.py` draws.

- **The collection goes behind a door and the choice does not.** A control sits
  on the narrowest surface its effect reaches; the theme is picked every
  session and the collection is touched rarely.
- **Nothing reaches the configuration until Save.** The window holds a working
  copy, previews the running app as it is edited, and a Cancel puts the
  installed collection and the theme in force back.
- **The last theme cannot be deleted**, and deleting the theme in force moves
  the app to the one that takes its place in the list.
- **A dark half is turned on whole or not at all.** Add Dark Half seeds every
  colour of it at once, so there is no partial half to define a minimum for,
  and Remove Dark Half makes the theme light-only again. The Light and Dark
  switch says which half the rows hold; on a light-only theme Dark is
  unclickable and carries the reason, the way Settings offers a mode a theme
  cannot draw.
- **The half being edited is the half the board previews**, whatever mode is
  stored, and the stored mode comes back when the window closes.
- **`KEY_GROUPS` is the order a palette form offers the keys in**, and
  `palette_rows()` places a key no group names rather than dropping it.

## Contrast

`TEXT_PAIRS` is every run of text and the surface it is read on;
`contrast_ratio()` reads a pair on the WCAG 1:1–21:1 scale and
`contrast_complaints()` names each one under `CONTRAST_MIN`, which is 4.5:1,
AA for body text. Every shipped scheme clears every pair, and the smoke check
asserts it.

- **Name a failure; never refuse one.** A palette the user built is his to
  choose, so the window says which pair falls short and asks once before
  saving. Silence and refusal are both wrong.
- **The unclickable pair is deliberately absent from the set.** Text a control
  greys out is meant to be hard to read.
- **`readable_on()` is the one colour not taken from a scheme.** A palette is
  previewed live, so the notice naming what cannot be read is drawn in the
  palette that broke it; that one line takes black or white against the canvas
  instead. Nothing else in the app derives a colour this way.
