#!/usr/bin/env python3
"""Flatten result files written before model slugs were sanitized.

Model slugs contain '/', which on write became a directory separator. Files
landed in results/briefs/S01__anthropic/claude-opus-4.1__low__withheld__0.json
instead of results/briefs/S01__anthropic-claude-opus-4.1__low__withheld__0.json.

The data is intact. This renames it to the flat scheme so the runner's resume
logic sees it and does not re-pay for calls already made.

Safe to run repeatedly. Never aborts: a locked file or undeletable directory is
reported and skipped. Empty-directory cleanup is cosmetic and failure there is
ignored, which matters on OneDrive and other syncing folders that hold handles.
"""
import shutil, sys
from pathlib import Path

out = Path(sys.argv[1] if len(sys.argv) > 1 else "../results")
moved = kept = dupes = 0
locked = []

for kind in ("briefs", "runs"):
    root = out / kind
    if not root.exists():
        print(f"  no {kind}/ folder found at {root}")
        continue

    for f in sorted(root.rglob("*.json")):
        rel = f.relative_to(root)
        if len(rel.parts) == 1:
            kept += 1
            continue
        flat = root / "-".join(rel.parts)
        try:
            if flat.exists():
                f.unlink()
                dupes += 1
            else:
                shutil.move(str(f), str(flat))
                moved += 1
        except Exception as e:
            locked.append((str(rel), type(e).__name__))

    # cosmetic only; a sync client holding a handle must not abort the job
    for d in sorted(root.rglob("*"), reverse=True):
        try:
            if d.is_dir() and not any(d.iterdir()):
                d.rmdir()
        except Exception:
            pass

print(f"\n  moved   {moved:>5}  nested files flattened")
print(f"  already {kept:>5}  flat")
if dupes:
    print(f"  dupes   {dupes:>5}  duplicate copies removed")
if locked:
    print(f"\n  {len(locked)} file(s) could not be moved:")
    for rel, err in locked[:10]:
        print(f"    {err}: {rel}")
    print("\n  These are locked, most likely by OneDrive or an open window.")
    print("  Pause OneDrive sync, close any Explorer windows in results/,")
    print("  and run this again.")
elif moved:
    print("\n  Existing results are now visible. Nothing was re-paid for.")

for kind in ("briefs", "runs"):
    root = out / kind
    if root.exists():
        n = len(list(root.glob("*.json")))
        nested = len(list(root.rglob("*.json"))) - n
        print(f"  {kind}: {n} readable" + (f", {nested} still nested" if nested else ""))
