"""ui/tokens.py — the design tokens: spacing, corner radius, type size, window
geometry and the scrim.

Spacing, corner radius and font size are named steps rather than literals, so a
change to a scale reaches every painter and the stylesheet at once. Tokens are
scheme-independent: a scheme changes what a surface is coloured, never how far
apart two things sit.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Design tokens — spacing, corner radius, type size
# ---------------------------------------------------------------------------
# Three fixed scales. A module needing a gap, a pad, a corner or a font size
# names a step instead of writing a number, so re-tuning the app's density is an
# edit here. Steps are in device-independent pixels, except TYPE, which is in
# points.
SPACE = {"xs": 2, "sm": 4, "md": 7, "lg": 11, "xl": 16, "2xl": 24}
RADIUS = {"sm": 4, "md": 7, "lg": 10, "xl": 12, "pill": 999}
TYPE = {"caption": 10, "body": 13, "title": 13, "section": 15, "display": 17}

# Window geometry, in device-independent pixels, and the splitter's opening
# split. Not a spacing scale — these size the window itself, and a module that
# needs one names it here rather than writing the number.
LAYOUT = {
    "control_h": 34,  # every button, field and picker on a row: one height
    "toolbar_control_h": 28,  # a control in the top bar
    "header_icon": 16,  # an icon in the top bar
    "toolbar_box_w": 34,  # an icon button in the top bar
    "header_mark_h": 20,  # the app's mark beside its name in the top bar
    "traffic_lights_tall_w": 80,  # the traffic lights in the tall title bar, and room past them
    "title_bar_h": 28,  # the Mac's title bar, which the top bar shares
    "tall_title_bar_h": 40,  # the compact unified title bar with a toolbar: the top bar's height
    "switch_track_w": 30,  # a switch's rounded track
    "switch_track_h": 18,
    "switch_knob_inset": 3,  # the room between the track's edge and its round knob
    "check_mark": 9,  # a checkbox's check, inside its SPACE lg box
    "traffic_lights_w": 80,  # the close, minimize and zoom buttons, and room past them
    "filter_field_max_w": 420,  # a Filter field, before its pickers
    "window_min_w": 1240,
    "window_min_h": 780,
    "window_w": 1960,
    "window_h": 1080,
    "split_board": 1180,  # opening width of the board side
    "split_detail": 720,  # opening width of the detail side
    "column_min_w": 260,  # a board column narrower than this is unreadable
    "detail_min_w": 320,  # the detail pane narrower than this is unreadable
    "filter_menu_w": 300,  # the filter panel, wide enough for an epic name
    "filter_menu_max_h": 420,  # its option list, before it scrolls
    "wizard_min_w": 720,
    "wizard_min_h": 480,
    "dialog_min_w": 760,  # the record dialog
    "agent_dialog_min_w": 1180,  # the agent form: two columns, side by side
    "agent_dialog_min_h": 820,
    "agent_fields_min_w": 480,  # its left column, the entry's own fields
    "charter_min_w": 520,  # its right column, the charter document
    "skill_list_min_h": 170,  # its tick list of skills
    "path_list_min_h": 132,  # a list of declared paths, with its picker
    "path_row_min_h": 40,  # one row in it: a path, its access, its ✕
    "env_name_w": 210,  # an environment variable's name box
    "env_choose_w": 34,  # the pick and remove buttons beside its value
    "extra_min_h": 90,  # its JSON field for keys this build predates
    "small_dialog_min_w": 420,  # a single-purpose modal: add link
    "preview_min_w": 480,  # the image preview modal
    "preview_min_h": 360,
    "theme_dialog_min_w": 1000,  # manage themes: the list, and a palette beside it
    "theme_dialog_min_h": 700,
    "theme_list_min_w": 230,  # its left column, wide enough for a theme's name
    "palette_caption_w": 210,  # what a colour row is called, at its longest
    "palette_swatch_w": 44,  # the block of colour a row opens the picker from
    "palette_hex_w": 110,  # its hex value, wide enough for #AARRGGBB
    "settings_w": 880,  # the Settings modal, drawn over the window
    "settings_h": 640,
    "settings_nav_w": 200,  # its side nav, wide enough for every tab's name
}

# The tint laid over the window behind a modal the app draws itself, written
# #AARRGGBB so it carries its own alpha. The same in every theme: it darkens a
# light window and lightens a dark one, so the modal's canvas stands out.
SCRIM = {"light": "#66000000", "dark": "#26FFFFFF"}


def space(step: str) -> int:
    """A gap or pad, by name."""
    return SPACE[step]


def control_height() -> int:
    """The one height every button, text field, picker and date field is drawn
    at, so controls sharing a row line up whatever kind each one is."""
    return LAYOUT["control_h"]


def radius(step: str) -> int:
    """A corner radius, by name."""
    return RADIUS[step]


def type_size(step: str) -> int:
    """A font point size, by name."""
    return TYPE[step]
