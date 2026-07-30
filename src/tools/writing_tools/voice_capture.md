# voice_capture.md — sample-first prose voice capture, generic method

Extracted from `writers_room`'s Grammatizator/Quartermaster voice system,
generalized for any agent that needs to capture and preserve how a specific
person writes. Reference implementation:
`playbooks/writers_room/voice_distillation.md`, applied to one author's
fiction voice.

**Not the same tool as `tools/voice_capture/voice_capture_interview.md`.**
That one is a direct-interview method (100 structured questions, good for
a business/content voice that the person can articulate under questioning).
This one is sample-first: it assumes self-report is unreliable for prose
craft specifically, and instead mines or elicits actual specimens. Pick
whichever fits the voice being captured — they are not competing versions of
the same idea, and a domain can use both (interview for stance/opinions,
sample-mining for sentence-level craft).

## Governing philosophy

1. **Never ask the person to describe a technique before they've performed
   it.** Self-report about one's own craft produces plausible fiction, not
   an accurate account. Either mine a specimen from existing writing, or
   elicit one with an exercise, then read the specimen for the move.
2. **One thing at a time.** Issue a single exercise, or ingest a single
   batch, per turn — never dump a menu of options.
3. **Distil, don't hoard.** Every specimen becomes a rule plus the verbatim
   line that proves it. Only the sharpest, most frequent moves get promoted
   into the always-on core profile.
4. **The core stays small; the library grows.** Don't inflate the always-on
   profile — deepen the per-technique card library instead.
5. **Verbatim is sacred.** Specimens are quoted exactly, punctuation and
   line breaks included. A paraphrase is no longer evidence of the actual
   voice.

## Two roles

- **Scout** — reads the person's prose (existing corpus or a fresh exercise
  page) and returns verbatim specimens with a short per-specimen analysis.
  Never writes to the profile/library itself. Can be an external AI or a
  separate mode of the same agent — what matters is the separation of
  concerns, not who runs it.
- **Distiller** — receives specimens only (never the raw source), sets each
  card's confidence threshold, decides promotion into the core profile, and
  is the sole writer of the voice library. This is normally the owning
  agent itself.

Splitting these two roles means the distiller can set a threshold without
ever having read (and been influenced by) the full source corpus — it only
sees what the scout reports finding.

## Two intake paths

**Path A — elicit (exercise-based).** Pick the next unfilled technique from
the inventory. Issue its exercise — setup, constraint, cap — with no
preamble about what it's testing (naming the target contaminates the
sample). The person writes; the scout reads the page and returns one or a
few specimens naming the target technique.

**Path B — mine (bulk corpus).** Point the scout at a pile of the person's
existing writing in one pass. It returns specimens across every technique
the corpus happens to demonstrate, not just the one you were looking for,
plus an opportunistic lexicon (favored words, avoided words, register,
tics). Mining first is cheap and fills many cards from one pass; the
exercise queue afterward is just whatever the corpus didn't yield or yielded
weakly. Mining sets the agenda for eliciting, not the other way around.

## Distillation loop (per specimen)

1. Read the specimen for its target move only — not for quality, not to
   edit it.
2. Write or update that technique's card: the rule, the verbatim specimen,
   a confidence threshold, a failure-mode note, cross-links to related
   cards.
3. Set the threshold from how clean the exemplar is and how often the move
   recurs in the source. A single specimen rarely justifies the strongest
   threshold tier; raise confidence as corroborating specimens accumulate.
4. Update the technique's status in the inventory
   (`empty → specimen-collected → distilled → promoted`).
5. If the move is signature or high-frequency, promote its sharpest line
   into the core profile.
6. One specimen may legitimately feed several cards — distil it into every
   card it serves rather than forcing a one-to-one match.

## The layered architecture

Mirrors a router/wiki pattern (see `tools/wiki_tools/`'s on-demand-lookup
principle) so a drafting job never has to load the whole library:

| Layer | Loaded when | Size discipline |
|---|---|---|
| Core profile | Every job | Stays tight on purpose — a page or two, never grows with the library |
| Inventory | Deciding what a job needs | One lookup table; doubles as progress tracker |
| Technique cards | Only when a job exercises that specific technique | Unbounded library, pulled à la carte |
| Specimens (raw) | Audit trail only | Not loaded by any drafting job |

## The growth command

When the person says something like "show me how I write \<X\>": add a new
inventory row for it, write or reuse an exercise, run Path A, distil. This
is the scaling mechanism — new situational technique cards without touching
the always-on core.

## Resumability

The inventory **is** the state. Re-entering voice-capture work after a gap:
read the inventory, its status column shows exactly what's filled and
what's next. No separate progress file needed — the tracker and the router
are the same table by design.

## Provenance discipline (use when a domain mixes registers or genres)

If the person writes across genuinely different registers or genres, tag
every captured fact with which register/genre it came from and never blend
across tags — a habit true of one register is not automatically true of
another. Corpus that isn't a clean sample of the person's actual voice (a
draft in a deliberately different voice, a co-written piece, in-world
sketch prose that isn't meant to reflect the real author) should yield only
abstract method facts, never verbatim specimens or word lists — the
concrete language isn't safe to treat as the person's own.
