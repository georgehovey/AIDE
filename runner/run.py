#!/usr/bin/env python3
"""AIDE runner.

Conditions
  unaided        fixed principal scaffold, no brief
  aid:<model>    fixed principal scaffold + brief written by <model>
  control_human  fixed principal scaffold + hand-authored brief
  control_poor   fixed principal scaffold + deliberately poor brief
  agent:<model>  <model> holds the seat directly, no brief

unaided and agent:<model> use the identical prompt. They differ only in which
model answers it. That is what makes the agent-aid gap a clean comparison:
agent:<model> is <model> in the seat, aid:<model> is <model> writing for the
fixed principal, and both are measured against the same unaided baseline.

Usage
  python run.py --corpus ../corpus --out ../results --n 5 --mock
  python run.py --corpus ../corpus --out ../results --n 20 \
      --principal claude-haiku-4-5-20251001 \
      --aid-models claude-opus-4-6 gpt-5 deepseek-chat

Raw responses are written to disk before any parsing. Reruns skip completed
cells, so the job is resumable.
"""
import argparse, hashlib, json, os, random, sys, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import prompts as P

PROMPT_VERSION = hashlib.sha256(
    (Path(__file__).parent / "prompts.py").read_bytes()).hexdigest()[:12]

# ---------------------------------------------------------------- providers

def call_anthropic(model, system, user, max_tokens=1400):
    import anthropic
    c = anthropic.Anthropic()
    r = c.messages.create(model=model, max_tokens=max_tokens, system=system,
                          messages=[{"role": "user", "content": user}])
    return {"text": "".join(b.text for b in r.content if b.type == "text"),
            "finish_reason": r.stop_reason,
            "usage": {"in": r.usage.input_tokens, "out": r.usage.output_tokens}}


def call_openai_compatible(model, system, user, max_tokens=1400,
                           base_url=None, api_key_env="OPENAI_API_KEY"):
    from openai import OpenAI
    c = OpenAI(base_url=base_url, api_key=os.environ[api_key_env])
    r = c.chat.completions.create(
        model=model, max_tokens=max_tokens,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}])
    ch = r.choices[0]
    return {"text": ch.message.content or "",
            "finish_reason": ch.finish_reason,
            "usage": {"in": r.usage.prompt_tokens, "out": r.usage.completion_tokens}}


def call_mock(model, system, user, max_tokens=1400):
    """Deterministic fake responses. Exercises every downstream code path.

    Seeded on model + prompt so a given cell is stable across runs. Principal
    calls return valid JSON with a display index; brief calls return prose.
    """
    seed = int(hashlib.sha256((model + system + user).encode()).hexdigest()[:12], 16)
    rng = random.Random(seed)
    if "OPTIONS" in user:
        n = user.count("\n[") + user.count("\n\n[")
        n = max(n, len([l for l in user.split("\n") if l.startswith("[")]))
        # bias toward middle-to-high display positions so sensitivity checks have signal
        idx = min(n - 1, rng.choice([0, 1, 2, 2, 3, 3, 4, 5]))
        if rng.random() < 0.04:
            return {"text": "I would need more information before selecting.",
                    "finish_reason": "end_turn", "usage": {"in": 0, "out": 0}}
        return {"text": json.dumps({"option_index": idx,
                                    "rationale": f"Mock rationale for {model}. "
                                                 "Adversary is expected to hold posture. "
                                                 "This option preserves freedom of action."}),
                "finish_reason": "end_turn", "usage": {"in": 0, "out": 0}}
    return {"text": f"MOCK BRIEF from {model}.\n\nAssessment. " + "Lorem ipsum. " * 40 +
                    "\n\nRecommendation: pursue the reversible course.",
            "finish_reason": "end_turn", "usage": {"in": 0, "out": 0}}


def call_openrouter(model, system, user, max_tokens=1400):
    """One key, every model family. Model slugs look like 'anthropic/claude-opus-4.1',
    'deepseek/deepseek-chat', 'qwen/qwen-2.5-72b-instruct'. Check the current list at
    https://openrouter.ai/models — slugs change.
    """
    from openai import OpenAI
    c = OpenAI(base_url="https://openrouter.ai/api/v1",
               api_key=os.environ["OPENROUTER_API_KEY"])
    r = c.chat.completions.create(
        model=model, max_tokens=max_tokens,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        extra_body={"provider": {"sort": "throughput"}})
    ch = r.choices[0]
    return {"text": ch.message.content or "", "finish_reason": ch.finish_reason,
            "usage": {"in": r.usage.prompt_tokens, "out": r.usage.completion_tokens}}


PROVIDERS = {"anthropic": call_anthropic, "openai": call_openai_compatible,
             "openrouter": call_openrouter, "mock": call_mock}


RATE_BACKOFF = [5, 15, 40, 90, 180]
GEN_BACKOFF = [2, 4, 8, 16, 32]


def dispatch(model, system, user, provider, **kw):
    """Rate limits get long backoff with jitter. Everything else gets short.

    Returns a dict whose finish_reason starts with ERROR: on total failure.
    Callers MUST NOT persist those — see write_unless_error.
    """
    last = None
    for attempt in range(6):
        try:
            return PROVIDERS[provider](model, system, user, **kw)
        except Exception as e:
            last = e
            name = type(e).__name__
            if attempt == 5:
                break
            rate = "RateLimit" in name or "429" in str(e)[:200]
            base = (RATE_BACKOFF if rate else GEN_BACKOFF)[attempt]
            time.sleep(base + random.uniform(0, base * 0.3))
    return {"text": "", "finish_reason": f"ERROR:{type(last).__name__}",
            "error": str(last)[:400], "usage": {}}

# ---------------------------------------------------------------- io

def load_corpus(d):
    items = [json.load(open(p, encoding="utf-8")) for p in sorted(Path(d).glob("*.json"))]
    for it in items:
        ranks = [o["escalatory_rank"] for o in it["options"]]
        assert sorted(ranks) == list(range(1, len(ranks) + 1)), \
            f"{it['id']}: escalatory_rank must be a permutation of 1..n"
    return items


_lock = threading.Lock()
_done = [0]
_total = [0]

def progress(msg):
    with _lock:
        _done[0] += 1
        print(f"  [{_done[0]}/{_total[0]}] {msg}", flush=True)


def run_pool(tasks, workers):
    """tasks: list of zero-arg callables. Exceptions surface rather than hide."""
    if not tasks:
        return
    _done[0], _total[0] = 0, len(tasks)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(t) for t in tasks]
        for f in as_completed(futs):
            f.result()


_UNSAFE = '/\\:*?"<>|'


def safe(s):
    """Model slugs contain slashes. Unsanitized they create subdirectories."""
    s = str(s)
    for ch in _UNSAFE:
        s = s.replace(ch, "-")
    return s


def cell_path(out, kind, *parts):
    p = Path(out) / kind / ("__".join(safe(x) for x in parts) + ".json")
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


_failures = []


def write_unless_error(path, obj, label):
    """A failed call must leave NO file behind.

    The runner skips any cell that already has a file, so persisting an error
    would make that cell permanently unrecoverable on resume.
    """
    fr = str(obj.get("finish_reason", ""))
    if fr.startswith("ERROR:"):
        with _lock:
            _failures.append((label, fr, obj.get("error", "")[:120]))
        return False
    write(path, obj)
    return True


def write(path, obj):
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    tmp.replace(path)

# ---------------------------------------------------------------- stages

def generate_briefs(items, models, out, provider, salience, disclose, k=3, workers=8):
    """k briefs per (item, model) at nonzero temperature.

    Multiple briefs per cell, randomly assigned across principal runs, so one
    unlucky brief cannot drive a whole condition.
    """
    tasks = []
    for it in items:
        for m in models:
            for i in range(k):
                p = cell_path(out, "briefs", it["id"], m, salience, disclose, i)
                if p.exists():
                    continue

                def job(it=it, m=m, i=i, p=p):
                    r = dispatch(m, P.aid_system(it, salience, disclose),
                                 P.situation(it), provider)
                    label = f"brief {it['id']} {m} {salience}/{disclose} #{i}"
                    write_unless_error(p, {"item": it["id"], "model": m, "salience": salience,
                                           "disclosure": disclose, "k": i,
                                           "prompt_version": PROMPT_VERSION, **r}, label)
                    progress(f"{label} [{r['finish_reason']}]")
                tasks.append(job)
    run_pool(tasks, workers)


def load_brief(out, item_id, model, salience, disclose, k):
    p = cell_path(out, "briefs", item_id, model, salience, disclose, k)
    return json.load(open(p, encoding="utf-8"))["text"]


def run_principal(items, condition, out, provider, principal, salience, disclose,
                  n, k=3, workers=8):
    """condition: 'unaided' | 'aid:<m>' | 'control_human' | 'control_poor' | 'agent:<m>'"""
    kind, _, arg = condition.partition(":")
    tasks = []
    for it in items:
        n_opts = len(it["options"])
        for run in range(n):
            p = cell_path(out, "runs", it["id"], condition.replace(":", "-"),
                          salience, disclose, run)
            if p.exists():
                continue

            rng = random.Random(f"{it['id']}|{condition}|{salience}|{disclose}|{run}")
            order = list(range(n_opts))
            rng.shuffle(order)

            brief, brief_k = None, None
            if kind == "aid":
                brief_k = rng.randrange(k)
                brief = load_brief(out, it["id"], arg, salience, disclose, brief_k)
            elif kind == "control_human":
                hb = Path(out).parent / "corpus" / "human_briefs" / f"{it['id']}.md"
                if not hb.exists():
                    continue
                brief = hb.read_text(encoding="utf-8")
            elif kind == "control_poor":
                brief = P.POOR_BRIEF

            model = arg if kind == "agent" else principal

            def job(it=it, order=order, brief=brief, brief_k=brief_k,
                    model=model, run=run, p=p):
                r = dispatch(model, P.principal_system(it, salience),
                             P.principal_user(it, order, brief), provider, max_tokens=800)
                label = f"{it['id']} {condition} {salience}/{disclose} #{run}"
                write_unless_error(p, {"item": it["id"], "condition": condition, "model": model,
                                       "salience": salience, "disclosure": disclose, "run": run,
                                       "presentation_order": order, "brief_k": brief_k, **r}, label)
                progress(f"{label} [{r['finish_reason']}]")
            tasks.append(job)

    if kind == "control_human" and not tasks:
        print(f"  SKIP {condition}: no hand-authored briefs in corpus/human_briefs/")
    run_pool(tasks, workers)


# ---------------------------------------------------------------- cli

def main():
    a = argparse.ArgumentParser()
    a.add_argument("--corpus", default="../corpus")
    a.add_argument("--out", default="../results")
    a.add_argument("--n", type=int, default=5)
    a.add_argument("--k", type=int, default=3)
    a.add_argument("--principal", default="claude-haiku-4-5-20251001")
    a.add_argument("--aid-models", nargs="*", default=["claude-opus-5"])
    a.add_argument("--provider", default="anthropic", choices=list(PROVIDERS))
    a.add_argument("--salience", nargs="*", default=["low", "high"])
    a.add_argument("--disclosure", nargs="*", default=["withheld", "disclosed"])
    a.add_argument("--workers", type=int, default=4)
    a.add_argument("--mock", action="store_true")
    args = a.parse_args()
    if args.mock:
        args.provider = "mock"

    if not args.aid_models:
        sys.exit(
            "\nERROR: --aid-models is empty. Without aid models there are no briefs,\n"
            "no aid conditions, and no agent conditions, so the run would measure\n"
            "only the unaided baseline. Refusing to start.\n\n"
            "If you launched this from a .bat file, the model list did not expand.\n"
            "Open the .bat in Notepad and check the line beginning  set AIDS=\n")

    items = load_corpus(args.corpus)
    Path(args.out).mkdir(parents=True, exist_ok=True)
    write(Path(args.out) / "RUN_CONFIG.json",
          {"argv": sys.argv, **{k: v for k, v in vars(args).items()}})
    print(f"corpus:    {len(items)} items")
    print(f"provider:  {args.provider}   workers: {args.workers}   n: {args.n}")
    print(f"principal: {args.principal}")
    print(f"aid:       {', '.join(args.aid_models)}\n")

    for sal in args.salience:
        for dis in args.disclosure:
            print(f"[briefs] salience={sal} disclosure={dis}")
            generate_briefs(items, args.aid_models, args.out, args.provider, sal, dis,
                            args.k, args.workers)

    conditions = (["unaided", "control_human", "control_poor"]
                  + [f"aid:{m}" for m in args.aid_models]
                  + [f"agent:{m}" for m in args.aid_models])

    for sal in args.salience:
        for dis in args.disclosure:
            print(f"\n[runs] salience={sal} disclosure={dis}")
            for c in conditions:
                # disclosure only varies the brief; unaided and agent see no brief
                if c in ("unaided", "control_poor") or c.startswith("agent:"):
                    if dis != args.disclosure[0]:
                        continue
                run_principal(items, c, args.out, args.provider, args.principal,
                              sal, dis, args.n, args.k, args.workers)
    if _failures:
        print(f"\n{'='*60}")
        print(f"  {len(_failures)} CALLS FAILED and were NOT saved.")
        print(f"  Those cells are still missing, so running this again")
        print(f"  will retry exactly those and keep everything else.")
        print(f"{'='*60}")
        seen = {}
        for label, fr, err in _failures:
            seen[fr] = seen.get(fr, 0) + 1
        for k, v in sorted(seen.items()):
            print(f"  {v:>4}  {k}")
        print(f"\n  First error: {_failures[0][2]}")
        if any("RateLimit" in f[1] for f in _failures):
            print(f"\n  Rate limited. Lower WORKERS in the .bat file (currently"
                  f" {args.workers}) to 2 and run again.")
        print()
    else:
        print("\ndone - no failures")


if __name__ == "__main__":
    main()
