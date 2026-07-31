# tools/career_coach

Tools specific to career_coach that don't belong to either of its two
single-purpose sibling folders:

- `../jd_scraper/` — the job-alert harvest and JD-acquisition pipeline
  (Gmail harvest, local scraping, the LinkedIn in-session recipe, secrets
  handling). See its own README for the full tiered-acquisition design.
- `../voice_capture/` — the dormant voice-capture interview tool.

## What's here

- `cl_lint.py` — the mandatory voice/blacklist lint gate. Scans a cover-letter
  draft (or packed docx) against the instance's own blacklist file and reports
  every banned phrase, dash construct, and period-emphasis run. Run on the
  draft text before packing, and again on the packed docx; both must pass
  before delivery. See `cover_letter.md` for how this fits into the drafting
  flow.

Usage:

```
python3 cl_lint.py <draft.txt | letter.docx>
```

The blacklist is the user's own content, so it lives in their career data root
(`agents.career_coach.key_data_paths`, then
`applications/cover_letters/*_CL_Blacklist.txt`) and never in this shared tool.
The script resolves it from config; `--blacklist PATH` overrides that for a
one-off file.
