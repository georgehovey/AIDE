# AIDE — AI-Informed Decision Evaluation

**Microsite:** https://georgehovey.github.io/AIDE/

AIDE measures how AI models used to support strategic decision-making change the decision.

Every published evaluation of models in national security decision-making puts the model in the
decision-maker's seat and asks it to optimize for finite objectives. That measures a job these
models do not have and are unlikely to get. Leaders will use aids; they will not hand over the
seat. AIDE inverts this by holding one decision-maker fixed and varying only the staff work it
reads, so what gets measured is the marginal effect of the model on the choice.

Four scenarios, six models, 1,010 decisions by a fixed principal, 324 graded briefs.

## What it found

**The agent number does not predict the aid number.** The gap between what a model does seated
and what it induces when advising runs from +0.19 to −0.08 on escalation position and from −39
to +12 percentage points on irreversible choices, changing sign across scenarios on both. A
directional gap could be corrected for. A gap with no stable sign means an agent-mode score
carries no recoverable information about the deployment case.

**AI briefs move nothing.** Position +0.048 (p = 0.35, n = 500). Irreversible-choice rate 42% →
43.9% (p = 0.88). The aided principal tracks the unaided principal on all four scenarios, on
baselines from 0% to 90%. A hand-written brief moves the same measure to 4%.

**The null is a composition artifact.** On the two scenarios where the measure has room, models
span 0.19 and 0.10 of the position range and 65 and 90 percentage points of the reversibility
range. Two models never raise the principal's irreversible-choice rate; two never lower it. They
cancel. On escalation level alone these six models are indistinguishable.

**The aid acts on the list of options, not the choice.** Briefs present 44% of the courses of
action the principal will be shown. 10.2% of recommendations have no analogue on the ladder,
concentrated in the conditional middle. The principal complies 59.6% of the time — and briefs
recommend an irreversible option in half of all cases, which is why compliance is high and the
aggregate does not move.

## Design

The principal is a fixed model scaffold with an explicit three-part utility function. It is an
instrument, not a simulated person: held constant, its quirks cancel when conditions are
differenced. The aid receives the same packet and constraints, prose commander's intent, and no
weights — and never sees the enumerated option ladder, so the list it builds is its own.

Options are ranked by coercive commitment, with acknowledgment (overt, deniable, covert) and
reversibility coded independently, so a public ultimatum and an unacknowledged strike are not
forced onto one scale. Every scenario contains a low-escalation irreversible option and a
high-escalation reversible one, which is what makes reversibility measure something the ranking
does not.

Method: [`PROTOCOL.md`](PROTOCOL.md) · Coding: [`CODING_RULES.md`](CODING_RULES.md) ·
Hypotheses, committed before the full run: [`PREREGISTRATION.md`](PREREGISTRATION.md)

## The corpus

Four decisions at NSC or presidential level, synthetic and built from open sources. Each turns
on a different kind of uncertainty.

| | Theater | Binds on | Decision |
|---|---|---|---|
| [S01](corpus/S01_taiwan_quarantine.json) | Taiwan Strait | intent | Maritime inspection zone around Taiwan's ports |
| [S02](corpus/S02_korea_inadvertent.json) | Korean Peninsula | resolve | Artillery kills six ROK sailors and two Americans |
| [S06](corpus/S06_cyber_attribution.json) | Homeland cyber | attribution | Grid attack kills nine, attribution 60/25/15 |
| [S12](corpus/S12_war_termination.json) | Northern Europe | timing | Settlement terms after fourteen months of war |

## Reproducing

```bash
pip install -r runner/requirements.txt
export OPENROUTER_API_KEY=...
cd runner
python validate_corpus.py ../corpus
python run.py --corpus ../corpus --out ../results --n 20 --provider openrouter \
    --principal anthropic/claude-haiku-4.5 --aid-models <models>
python grade_briefs.py --corpus ../corpus --results ../results --judge <model>
python analyze.py --corpus ../corpus --results ../results
```

Runs are resumable. Failed calls leave no file, so rerunning retries exactly what is missing.
Raw responses are written before parsing, so re-scoring never costs another call. On Windows,
`1_SETUP.bat` then `3_PILOT.bat` do the same without a terminal.

## Limitations

Two of four scenarios cannot measure: Korea sits at the top of its ladder and war termination
near the bottom, so pooled statements rest substantially on Taiwan and cyber. Korea earns its
place as a positive control — the human brief moves it, which is what makes the AI null a real
null rather than a blind instrument.

Runs within a cell are not independent; each draws from three or six briefs, so reported
p-values on the aid side are optimistic. The human comparator is four briefs by one author who
designed the ladders. The judge is a single model family. Constructed items detect what was
built and nothing else.

Full assumptions, falsifiers, the nine defects found in construction, and the design this is a
scoped-down version of: [`limits.html`](https://georgehovey.github.io/AIDE/limits.html).

---

Submitted to the [ChinaTalk evals contest](https://www.chinatalk.media/p/25k-contest-evals-for-the-situation),
2026. Scenarios are synthetic and do not describe any actual plan, operation, or assessment.
