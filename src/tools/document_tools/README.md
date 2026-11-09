# Document Tools

Changing a document's format or shape. Inspecting and moving files is
`file_management/`.

## Tools

### pdf_to_markdown.py

`python3 pdf_to_markdown.py` — prompts for a directory, then OCRs every PDF in
it and extracts the text. Each `<name>.pdf` yields `<name>_OCR.pdf` and
`<name>.md` beside it, and the source moves into `processed_pdfs/` on success.
Needs `ocrmypdf` and `pdftotext` on the path.

### check_prompts.py

```
python3 check_prompts.py
```

Reads every note in `markdown_notebook.assistant_prompts_dir` and reports where
it departs from the contract in `src/skills/notebook-prompt-library/SKILL.md`:
a missing `copilot-command-*` key, a missing `ai/prompt` tag, a repeated
context-menu order, a wiki-link resolving to no note in
`markdown_notebook.notes_dir`, and — in a frontmatter block a prompt tells the
assistant to emit — a Templater expression or a key set carrying no template's
keys. It takes no path argument and repairs nothing; exit status is 1 when any
check matched.

### normalize_recipes.py

```
python3 normalize_recipes.py [--write] [--rename] [--dir PATH] [--notebook PATH]
```

Validates every `.md` file in `markdown_notebook.recipes_dir` against the recipe
formatting standard, repairs what does not conform, and writes
`recipe_audit_log.md` into that folder. Dry-run by default; `--write` commits.
`--dir` and `--notebook` override the two configured folders.

- **Run `--write` wherever your `notebook_access` gives `recipes_dir` write**,
  after reading the dry run (`src/tools/config_tools/notebook.py access
  <agent>`).
- **Run `--rename` only where your access gives the whole notebook write**,
  because it rewrites links in every folder.
- **Without the grant, report what the dry run would change** and file a card
  for an agent that has it — never a command for the user to run.
- **The filename convention is `recipe_<snake_case>.md`.** A name disagreeing
  with its H1 is flagged rather than renamed, because every recipe is reached by
  wiki-link from the hub. `--rename` opts in and rewrites the links across the
  notebook in the same run.
- **A file whose name starts with `_` is a hub or index and is skipped.** It is
  never renamed and never given recipe frontmatter.
- **The first alias is the H1 exactly**, so a wiki-link by title resolves from
  the hub and from any page; further aliases are kept after it.
- **One blank line separates every heading from its block** and every block
  from the next heading.
- **`rating` sits directly after `source_url`, and contains the user's own
  score**, a decimal from 1 to 5 that he writes. An existing value is kept
  unchanged and a missing key is added blank; no tool or agent fills it from a
  source's stars or reviews.
