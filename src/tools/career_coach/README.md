# Career Coach Tools

Tools maintained by `career_coach` that belong to no single-purpose sibling
folder. `../jd_scraper/` holds the job-alert harvest; `../voice_capture/` holds
the voice interview.

## Index

- **`voice_lint.py`** — the blacklist lint gate over anything written in the
  user's own voice. Load it before packing a draft and again on the packed file.
- **`research_prompt_template.md`** — the fixed company-research request handed
  to the user to run in a search-capable tool. Load it when a verdict or a cold
  letter needs research this agent will not browse for itself.

## voice_lint.py

```
python3 voice_lint.py <draft.txt | draft.docx> [--fiction] [--blacklist PATH]
```

Reports every banned phrase, dash construct and period-emphasis run in the
input, reading `.txt` and `.docx` alike. The blacklist is the user's own
content: it resolves from `agents.career_coach.key_data_paths` plus
`foundation/*_Voice_Blacklist.txt`, and `--blacklist` overrides that. More than
one match under that glob is an error naming the flag.

- **The gate covers everything written in the user's own voice**, not a cover
  letter alone: a resume, a profile section, a post. A skill that produces such
  a draft names this command.
- **The phrase lists bind every form; the two coded patterns do not.** `--fiction`
  drops the dash constraint and period-emphasis, which the voice profile scopes
  to business writing and to non-fiction, and checks the phrase lists alone.
- **A bullet marker at the head of a line is markup, not a dash construct.** A
  resume writes its bullets `-- like this`, and a dash later in the same line is
  still reported.

`src/skills/cover-letter/SKILL.md` owns where the gate sits in drafting a
letter; `src/skills/resume-tailoring/SKILL.md` and
`src/skills/base-resume-update/SKILL.md` own it for the resume.
