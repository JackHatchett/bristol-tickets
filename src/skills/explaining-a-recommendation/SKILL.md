---
name: explaining-a-recommendation
description: Shape a document that ends on a recommendation.
license: MIT
metadata:
  bristol.kind: playbook
  bristol.maintainer: chief_of_staff
---
# explaining-a-recommendation

Input: several findings and the options they open. Operation: the order below.
Output: one document a reader who was not in the session can act on.

Load it for a document carrying more than one finding. A single finding, a
report, a ticket body and an answer in chat are governed by `src/app.md`
Phase 4 alone, which every session already holds.

## Procedure

1. **State the problems first**, before any option.
2. **Define the terms those problems are stated in**, one plain sentence each,
   with a concrete case where the definition is abstract.
3. **Give every option considered, the ones that fail among them, and why each
   fails.** An option omitted because it lost is a recommendation the reader
   cannot check.
4. **End on the one recommended**, in the terms defined in step 2.

## Failure modes

- **The document opens on the recommendation** → steps 1 to 3 became an
  appendix, and the reader has nothing to weigh it against.
- **Only the winning option appears** → step 3 did not fire.
- **A heading names something the reader has not met** → the term wanted step 2.

## Audit

**Whether one term in the document is never defined in it.** One is the whole
failure: the reader stops there, and nothing after it lands.
