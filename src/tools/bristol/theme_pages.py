"""theme_pages.py — writes the design system's theme pages from theme.py.

One note per shipped theme, in the `themes` folder of the notebook folder
`markdown_notebook.design_system_dir` gives: every color role in light and dark,
then the ratio of every pair in `TEXT_PAIRS` and `MARK_PAIRS`, marked where it
reads under its minimum. A page that already exists keeps its frontmatter.

    python3 src/tools/bristol/theme_pages.py [--out <design system folder>]

Run it in the commit that changes a shipped palette, so the pages and the code
give the same values.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
# theme.py imports nothing from the rest of ui, so it is loaded on its own
# rather than through the package, whose __init__ builds the main window.
sys.path.insert(0, str(HERE / "ui"))

import theme  # noqa: E402

READ_CONFIG = HERE.parent / "config_tools" / "read_config.py"


def design_system_dir() -> Path:
    """The design system folder config names."""
    value = subprocess.run(
        [sys.executable, str(READ_CONFIG), "markdown_notebook.design_system_dir"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return Path(value).expanduser()


def ratio_cell(foreground: str, background: str, palette: dict | None,
               minimum: float) -> tuple[str, bool]:
    """A pair's ratio as a table cell, and whether it is under its minimum."""
    if palette is None:
        return "—", False
    ratio = theme.contrast_ratio(palette[foreground], palette[background])
    under = ratio < minimum
    return f"{ratio:.1f}:1" + (" (under)" if under else ""), under


def palette_for(scheme: str | None) -> dict | None:
    """A scheme's palette, filled from the reference as the app fills it."""
    if scheme is None:
        return None
    palette = dict(theme.REFERENCE_PALETTE)
    palette.update(theme.SCHEMES[scheme])
    return palette


def page(theme_id: str, name: str, frontmatter: str) -> str:
    """The whole note for one theme."""
    light_scheme, dark_scheme = theme.THEMES[theme_id]
    light, dark = palette_for(light_scheme), palette_for(dark_scheme)

    roles = []
    for heading, keys in theme.KEY_GROUPS:
        roles.append(f"## {heading}\n")
        roles.append("| Role | On Screen | Light | Dark |")
        roles.append("| --- | --- | --- | --- |")
        for key in keys:
            dark_value = f"`{dark[key]}`" if dark else "—"
            roles.append(f"| `{key}` | {theme.key_caption(key)} | "
                         f"`{light[key]}` | {dark_value} |")
        roles.append("")

    under = 0
    total = 0
    tables = []
    for title, column, pairs, minimum in (
            ("Text Contrast", "Text", theme.TEXT_PAIRS, theme.CONTRAST_MIN),
            ("State Mark Contrast", "Mark", theme.MARK_PAIRS, theme.MARK_MIN)):
        tables.append(f"## {title}\n")
        tables.append(f"| {column} | On | Light | Dark |")
        tables.append("| --- | --- | --- | --- |")
        for foreground, background in pairs:
            cells = []
            for palette in (light, dark):
                cell, short = ratio_cell(foreground, background, palette, minimum)
                cells.append(cell)
                if palette is not None:
                    total += 1
                    under += short
            tables.append(f"| `{foreground}` | `{background}` | "
                          f"{cells[0]} | {cells[1]} |")
        tables.append("")

    dark_line = (f"its dark scheme `{dark_scheme}`" if dark_scheme
                 else "it has no dark scheme")
    details = [
        f"- The theme's id is `{theme_id}`; its light scheme is "
        f"`{light_scheme}` and {dark_line}, in `SCHEMES` in "
        "`src/tools/bristol/ui/theme.py`.",
        "- What each role colors is [[bristol_color|Bristol Color]], and the "
        "ratios a pair must reach are "
        "[[bristol_contrast_minimums|Bristol Contrast Minimums]].",
    ]
    if under:
        details.append(f"- {under} of the {total} pairs below read under "
                       "their minimum.")

    body = [
        frontmatter.rstrip("\n"),
        "",
        f"# {name} Theme",
        "",
        f"Every color role of the {name} theme in light and dark, and the "
        "contrast of every pair that must be read",
        "",
        "## Details",
        "",
        *details,
        "",
        *roles,
        *tables,
        "## Related Notes",
        "",
        "- [[_bristol_design_system|Bristol Tickets Design System]]",
        "",
    ]
    return "\n".join(body)


def existing_frontmatter(path: Path, name: str) -> str:
    """The note's own frontmatter where it has one, else a new one."""
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if text.startswith("---\n"):
            end = text.find("\n---\n", 4)
            if end != -1:
                return text[:end + 5]
    created = datetime.now().strftime("%Y-%m-%d %H:%M")
    return (f"---\naliases:\n  - {name} Theme\ntags:\n  - ai/answer\n"
            f"created: {created}\n---\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path,
                        help="the design system folder; config's by default")
    args = parser.parse_args()
    folder = (args.out or design_system_dir()) / "themes"
    folder.mkdir(parents=True, exist_ok=True)
    for theme_id, name in theme.THEME_CHOICES:
        path = folder / f"bristol_theme_{theme_id}.md"
        path.write_text(page(theme_id, name, existing_frontmatter(path, name)),
                        encoding="utf-8")
        print(f"wrote {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
