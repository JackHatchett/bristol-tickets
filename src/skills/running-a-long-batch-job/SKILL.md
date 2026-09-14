---
name: running-a-long-batch-job
description: Designing and driving a job that has to process thousands of items when the shell running it is cut off after a couple of minutes - how to make it resumable, how to pace it, and how to prove it produced the right thing. Use when a one-time conversion, backfill, import or bulk rewrite is bigger than one command's time, or when such a job has already been interrupted.
license: MIT
compatibility: Runs anywhere python3 does; the shell time limit it is written against belongs to the host, not to this repository.
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
---
# running-a-long-batch-job

Input: a body of work with many independent items — a backfill, an import, a
bulk conversion — and a session whose shell returns after a bounded time.
Operation: build it so the work survives being cut off, then drive it to
completion. Output: the finished result, and a count that proves it.

A job like this is finished once rather than run daily, which is exactly why it
is worth building carefully: the bugs in it are found years later, by someone
who cannot tell what it mangled.

## Make the run cheap to abandon

Four properties, and each one answers a way the run gets cut off.

- **Write each item whole, and only where its contents would differ.** An item
  written in pieces leaves a half-written one behind when the shell returns
  mid-write. Comparing before writing also means a re-run leaves the
  destination's modification times alone, which matters wherever a person's
  tooling watches them.
- **Give the job a time budget, and have it say where it stopped.** A run that
  stops on its own inside the limit reports the item to resume from; a run the
  host kills reports nothing, and the next one starts from the beginning.
- **Give it a resume point and a skip.** Resuming from a named item is for
  rebuilding everything after that point; skipping items already done is for
  filling gaps. They are not the same option and using the wrong one is the
  common way a change reaches only part of the corpus.
- **Make a re-run over unchanged input produce the same bytes.** Anything that
  varies between runs — a timestamp of when the run happened, an unordered
  iteration, a set where a list was meant — makes every later run look like it
  changed something, and hides the changes that matter.

## Get the throughput before driving it

- **Measure one item before starting thousands.** The cost per item times the
  count is the whole plan, and it decides whether this is four commands or
  forty.
- **Look for where the time actually goes.** A job that waits on a network is
  not a job that needs a faster transform.
- **Widen the unit of concurrency to the level where the items are
  independent.** Working several sub-items inside one item leaves the machine
  idle whenever an item has only one or two; working several items at once keeps
  the width steady. This is often the difference between half an hour and three
  minutes.
- **Keep the fixed cost out of the loop where the loop will be re-entered.** A
  run that re-reads a whole index before doing anything pays that cost on every
  resume, and it can end up larger than the work.
- **Do not background the job to escape the limit.** A process left running
  between calls is not there on the next one in most hosts, and the run that
  looked like it was progressing produced nothing.

## Prove it afterwards

Two checks, and neither is the job's own report of what it did.

- **Reconcile both directions.** Count the inputs that should have produced an
  output and the outputs that exist, and list the difference each way. One
  number matching is a coincidence; the two empty difference lists are the
  proof. An unexpected output is as much a defect as a missing one.
- **Run the whole thing again and require that nothing changes.** This is the
  check that catches a transform depending on something other than its input.

**Investigate every unreconciled item rather than the count.** A single item out
of hundreds is where the interesting fault lives: the one that does not fit is
usually a whole class the pass was silently dropping, and finding out why is
what turns a plausible result into a correct one.

## Failure modes

- **A second program written for the one-time pass** → it runs once, is never
  exercised again, and drifts from the thing that runs daily. The one-time pass
  is the recurring one with its window opened.
- **A rebuild driven with the skip option** → the change reaches only the items
  that had no output.
- **Concurrency raised without watching for refusals** → a throttled service
  returns short results that read as real ones. Retry with a growing delay, and
  raise rather than return a short result.
- **Progress reported by count alone** → the job says it did the work and the
  reconciliation says what it actually produced.
- **The reconciliation skipped because the counts matched** → they can match
  with an item missing on one side and an extra on the other.

## Audit

- The job can be stopped at any moment and restarted without producing a
  duplicate or a half-written item.
- Running it twice over unchanged input changes nothing.
- Both reconciliation directions come back empty, and any item that did not
  reconcile has an explanation rather than a note.
