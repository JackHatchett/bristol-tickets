# Career Coach Tools

Tools maintained by `career_coach` that belong to no single-purpose sibling
folder. `../jd_scraper/` holds the job-alert harvest; `../voice_capture/` holds
the voice interview.

## Index

- **`cl_lint.py`** — the blacklist lint gate over a cover-letter draft. Load it
  before packing a draft and again on the packed file.
- **`research_prompt_template.md`** — the fixed company-research request handed
  to the user to run in a search-capable tool. Load it when a verdict or a cold
  letter needs research this agent will not browse for itself.

## cl_lint.py

```
python3 cl_lint.py <draft.txt | letter.docx> [--blacklist PATH]
```

Reports every banned phrase, dash construct and period-emphasis run in the
input, reading `.txt` and `.docx` alike. The blacklist is the user's own
content: it resolves from `agents.career_coach.key_data_paths` plus
`applications/cover_letters/*_CL_Blacklist.txt`, and `--blacklist` overrides
that. More than one match under that glob is an error naming the flag.

`playbooks/career_coach/cover_letter.md` owns where the gate sits in drafting.
