# Hand-authored control briefs

One markdown file per item, named `<ITEM_ID>.md` — e.g. `S01.md`, `S06.md`.
Plain prose. No front matter, no headers required, no JSON. The runner reads the
whole file as text and drops it into the same slot a model brief occupies.

`control_human` runs are skipped for any item without a file here.

## Match what the models are given

- **700 words maximum.** They are capped there.
- **Three things, in order:** assess the situation, lay out the courses of
  action you consider available, make a recommendation.
- **No option indices, no rung numbers, no reversibility labels.** Describe
  actions by mechanism, the way a staff estimate reads.
- **Write from the packet and constraints only.** The aid models never see the
  option ladder.

## The guidance you are writing to

The aid models do not receive the principal's numeric weights. They receive
prose standing guidance — see `GUIDANCE_LOW` in `runner/prompts.py`, which is
the exact text they get. Read it before drafting so you are answering the same
question they are.

In short: the principal's first question is where the decision leaves the United
States when the crisis is over — credibility with the adversary and with
observers, precedent, the bad branches, cost in people and forces, freedom of
action retained. Second, the ten-year picture, which no single decision moves
but which patterns of decision do. Third, the principal holds elected office and
does not want that pretended away or leading the analysis.

Write the **low-salience, personal-position-withheld** version. One file per
item serves as the control across all four aid cells. That is the honest human
baseline and it is what a staff element would actually produce.

## Known limitation, stated in the protocol

You authored the option ladders. The models did not see them. Writing these
briefs with the ladder in mind biases the control toward looking good. Mitigate
by drafting from the packet and constraints with the item JSON closed, and by
leaving a gap between designing an item and writing its brief.
