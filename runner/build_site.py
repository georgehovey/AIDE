#!/usr/bin/env python3
"""Rewrite the microsite's numbers from results/ so the site cannot drift from the data.

Replaces the rows between the AIDE:TABLE markers in site/index.html and README.md.
Run after analyze.py. Prints what it wrote so you can eyeball it before committing.

    python build_site.py --corpus ../corpus --results ../results --site ../site/index.html
"""
import argparse, json, statistics as st
from collections import defaultdict
from pathlib import Path
import analyze


def cells(corpus, results):
    items, runs, _ = analyze.load(corpus, results)
    rows = analyze.score(items, runs)
    g = defaultdict(list)
    for r in rows:
        if not r.get("errored") and not r["no_select"] and "norm" in r:
            g[(r["item"], r["condition"])].append(r["norm"])
    return items, {k: round(st.mean(v), 2) for k, v in g.items()}


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--corpus", default="../corpus")
    a.add_argument("--results", default="../results")
    a.add_argument("--targets", nargs="*", default=["../site/index.html", "../README.md"])
    args = a.parse_args()

    items, m = cells(args.corpus, args.results)
    models = sorted({c.split(":", 1)[1] for (_, c) in m if c.startswith("agent:")})

    html, md = [], []
    for mod in models:
        for iid in sorted(items):
            ag, ai = m.get((iid, f"agent:{mod}")), m.get((iid, f"aid:{mod}"))
            un = m.get((iid, "unaided"))
            if ag is None or ai is None:
                continue
            gap = round(ag - ai, 2)
            cls = "pos" if abs(gap) >= 0.05 else "flat"
            sign = f"+{gap:.2f}" if gap >= 0 else f"−{abs(gap):.2f}"
            label = f"{mod.split('/')[-1]} · {items[iid]['title'][:36]}"
            html.append(f'        <tr><td>{label}</td><td class="n">{ag:.2f}</td>'
                        f'<td class="n">{ai:.2f}</td><td class="n">{un:.2f}</td>'
                        f'<td class="gap {cls}">{sign}</td></tr>')
            md.append(f"| {label} | {ag:.2f} | {ai:.2f} | {un:.2f} | **{sign}** |")

    for t in args.targets:
        p = Path(t)
        if not p.exists():
            print(f"  skip {t}: not found")
            continue
        txt = p.read_text(encoding="utf-8")
        block = "\n".join(html if p.suffix == ".html" else md)
        head, sep, rest = txt.partition("<!-- AIDE:TABLE -->")
        if not sep:
            print(f"  skip {t}: no <!-- AIDE:TABLE --> marker")
            continue
        _, sep2, tail = rest.partition("<!-- /AIDE:TABLE -->")
        p.write_text(head + sep + "\n" + block + "\n" + sep2 + tail, encoding="utf-8")
        print(f"  wrote {len(md)} rows to {t}")

    print("\n".join(md))


if __name__ == "__main__":
    main()
