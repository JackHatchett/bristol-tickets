# base_resume_update — career_coach playbook

Changes what the master resume itself says, with no job description in play.
Triggered on request. `resume_tailoring.md` owns JD-driven output and the
formatted/plain-text conventions both files rely on; nothing here produces a
tailored document.

## Preconditions

- **Run `resume_tailoring.md` instead where a job description is in play.** A
  request that names a role, a company or a posting is tailoring, even when it
  also adds new material.
- **Take every new fact from a context module or from the user in this
  session.** The charter's guardrails own invention.
- **Read `data/*/career/foundation/header_design_spec.md` before touching the
  formatted docx.** Design tokens are locked there.

## The three masters

All three live in `data/*/career/foundation/`, and an update touches all three:

```
[User_Name]_Resume.docx     -- formatted, human-facing, two pages
Resume_Plain_Text.docx      -- ATS, single-column, unrestricted length
Resume_Plain_Text.txt       -- the plain-text source of truth
```

## Procedure

1. **Reconcile the three before writing.** Where they already disagree on a
   role, a date or a bullet's substance, name the difference to the user and
   settle it as part of this update; new content never lands on a stale file.

2. **Place the content by what it is.**
   - A new role at an existing employer — a sub-row under that company header
     in the formatted resume, its own fully labeled block in the plain-text
     files.
   - A new employer — a company header in reverse-chronological position, and
     the same labeled block in the plain-text files.
   - Work outside employment — an experience entry where it carries dated,
     describable responsibility, otherwise Education and Recognition. Its
     framing register and the scope its outcomes may claim come from the
     context modules.
   - A new skill — the instance's master skills list in config first, then the
     competencies table and the plain-text Skills list.
   - A correction — in place, in every file that carries the line.

3. **Hold density to `foundation/context/core.txt`.** Every line of body text
   nearly full, or the bullet one clean line. That file's paragraph floor
   measures tailored output against the base and says nothing here: the base is
   the baseline, and content added to it raises the number later tailoring is
   measured against. The formatted resume's two-page limit still binds.

4. **Write the masters in place.** The result is the master. No second copy, no
   version suffix, no dated variant — `src/app.md` §What a file may say.

5. **Confirm a removal before writing it.** Where the update takes content out
   rather than putting it in, get the user's word first; a prior version kept
   as a file is the duplicate step 4 bars.

6. **Close through `session_closure.md`**, which carries the context-module
   additions this update surfaced.

## Failure modes

- **The formatted resume would run past two pages** → expand or compress
  elsewhere. Never force a page break, and never drop a positioning frame to
  buy room.
- **The user asks for the change against a tailored output** → a tailored file
  is not the master. Make the change in the master and let the next tailoring
  session inherit it.

## Audit

- The formatted and plain-text masters carry the same roles, dates and bullet
  substance.
- No file in `foundation/` is a copy, a version or a dated variant of a master.
