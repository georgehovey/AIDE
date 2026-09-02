#!/usr/bin/env python3
"""Structural validation for AIDE corpus items. Run before any paid run."""
import json, sys
from pathlib import Path

corpus = Path(sys.argv[1] if len(sys.argv) > 1 else "../corpus")
fail = []

for f in sorted(corpus.glob("*.json")):
    d = json.load(open(f, encoding="utf-8"))
    o, iid = d["options"], d["id"]
    rungs = [x["rung"] for x in o]
    ranks = [x["escalatory_rank"] for x in o]

    def chk(cond, msg):
        if not cond:
            fail.append(f"{iid}: {msg}")

    chk(sorted(ranks) == list(range(1, len(o) + 1)), "escalatory_rank must be a permutation of 1..n")
    chk([min(rungs), max(rungs)] == d["rung_range"], "rung_range does not match options")
    chk(d["rank_range"] == [1, len(o)], "rank_range does not match option count")
    chk(len({x["index"] for x in o}) == len(o), "duplicate option index")
    chk(all(0 <= x["rung"] <= 16 for x in o), "rung out of range")
    chk(all(x["acknowledgment"] in ("overt", "deniable", "covert", "n/a") for x in o), "bad acknowledgment")
    chk(all(x["reversibility"] in ("reversible", "costly-reversible", "irreversible") for x in o), "bad reversibility")

    lowirr = [x["index"] for x in o if x["reversibility"] == "irreversible" and x["rung"] <= 3]
    highrev = [x["index"] for x in o if x["reversibility"] == "reversible" and x["rung"] >= 4]
    chk(lowirr, "no low-rung irreversible option; reversibility would track rung")
    chk(highrev, "no high-rung reversible option; reversibility would track rung")

    ds = d["coding_key"]["defensible_set"]
    chk(len(ds) >= 2, "fewer than two defensible options")
    chk(len(o) - len(ds) >= 3, f"only {len(o)-len(ds)} clear errors; need at least 3")
    chk(all(i in {x['index'] for x in o} for i in ds), "defensible_set references a missing index")

    byrank = [x["rung"] for x in sorted(o, key=lambda y: y["escalatory_rank"])]
    inv = sum(1 for a, b in zip(byrank[:-1], byrank[1:]) if a > b)
    chk(inv >= 1, "rank tracks rung perfectly; item has no diagnostic crossing")

    print(f"{iid}  {len(o)} opts  rung{d['rung_range']}  unc={d['binding_uncertainty']:<11} "
          f"defensible={len(ds)} errors={len(o)-len(ds)} crossings={inv}")

print()
if fail:
    print("FAILURES:")
    for x in fail:
        print("  " + x)
    sys.exit(1)
print(f"all {len(list(corpus.glob('*.json')))} items pass")
