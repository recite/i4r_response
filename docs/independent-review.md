# Independent design review

An independent GPT-6 Astra review of the design, current registry and feasibility
code on 2026-11-04 supported **narrow and test**, not an established novelty claim.
This was a design/code review, not independent human annotation of source texts.

Five consequential issues were identified and addressed before publication:

- Later critiques/replies could contaminate earlier citation coding. Every queue
  record now carries a pending temporal-packet review, with explicit as-of rules
  and examples of later additions in dp_294 and dp_226.
- Coding fields did not uniquely define outcome shares. The protocol now specifies
  eight categories, linkage errors, missing text, background mentions, and the
  distinction between unconditional and affected-claim-use denominators.
- `assessment_id` can identify multiple claims. The pilot is explicitly a bundle
  sample; atomic claims and versions must be resolved before claim-level inference.
- An assessment without an event could silently disappear. Exact claim/event
  coverage is now enforced, with a regression test.
- The initial population wording was too broad. The design now restricts the
  pilot to the 38 inherited curated bundles, not the entire assessment inventory.

The review found no material causal overstatement. It endorsed the fixed
first-post-year sampling, missing-versus-zero distinction, and explicit dependence
limitations. Full-text retrieval, two independent reader judgments, and empirical
coding reliability remain outstanding.
