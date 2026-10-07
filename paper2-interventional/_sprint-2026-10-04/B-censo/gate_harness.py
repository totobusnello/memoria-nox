#!/usr/bin/env python3
"""
Observing harness around the registered adjudication runner. It changes NOTHING in the
instrument: it imports `run_panel.py` (or the declared substitute `run_panel_deepseek6k.py`)
unmodified, checks their sha256 against the values pinned below, and wraps three names
only to OBSERVE:

  * `urllib.request.urlopen`  -> records the HTTP response headers that carry model/version
                                 information (whitelist; never auth/cookie/key/org headers)
  * `<module>.chamar`          -> records `usage`, `served`, `stop` (already returned by
                                 `chamar`, but `run_panel.py` drops `usage` before writing)
  * `<module>.julgar`          -> tags the thread with (episode_id, panelist) for the log

Call arguments, prompt, temperature, max_tokens, retries and parsing are the module's own.
The API key is passed by the module straight to `chamar`; this harness never logs it (the
argument is dropped before anything is written).

Subcommands
  run    --module run_panel|run_panel_deepseek6k --calls-log F -- <run_panel.py args>
  gate1  --episodes F --out F --calls-log F       (one call per provider: zhipu, xai,
                                                   google via run_panel; deepseek via the 6k
                                                   substitute; plus GET models/gemini-2.5-pro)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

P2 = Path(__file__).resolve().parents[2]  # paper2-interventional/, two levels above B-censo/
sys.path.insert(0, str(P2))

PINNED = {
    "run_panel.py": "b2265d123bdbfec95cef7c99d13873f34b7a1235d6ecbadea6e537cee7c7fb01",
    "run_panel_deepseek6k.py": "0a95b1077d2e49ddd5478e491accc59613b6ce0a30a07cac46f924627829ef08",
    "adjudication_prompt.md": "3767fdb50e31ce41e3de8484501c056a48ccdfa3cc3e283f59e64a8d2c339bd7",
}

KEEP = ("model", "version", "server", "date", "ratelimit", "processing", "region", "x-request-id")
DROP = ("key", "token", "auth", "cookie", "org", "account", "project", "user", "secret")

_tl = threading.local()
_lock = threading.Lock()
_log_path: Path | None = None


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def verify_pins() -> None:
    for name, want in PINNED.items():
        got = _sha(P2 / name)
        if got != want:
            raise SystemExit(f"PIN MISMATCH {name}: {got} != {want} (instrument changed; refusing)")


def _filter_headers(h) -> tuple[dict, list]:
    names = sorted({k.lower() for k in h.keys()}) if h is not None else []
    kept = {}
    for k in names:
        if any(d in k for d in DROP):
            continue
        if any(s in k for s in KEEP):
            kept[k] = h.get(k)
    return kept, names


_orig_urlopen = urllib.request.urlopen


def _urlopen(*a, **kw):
    try:
        r = _orig_urlopen(*a, **kw)
    except urllib.error.HTTPError as e:
        _tl.headers, _tl.header_names = _filter_headers(e.headers)
        _tl.http_status = e.code
        raise
    _tl.headers, _tl.header_names = _filter_headers(r.headers)
    _tl.http_status = getattr(r, "status", None)
    return r


def _write(row: dict) -> None:
    if _log_path is None:
        return
    with _lock:
        with _log_path.open("a") as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def instrument(mod) -> None:
    orig_chamar, orig_julgar = mod.chamar, mod.julgar

    def chamar(protocolo, base, modelo, chave, texto, timeout, max_tokens=300):
        _tl.headers, _tl.header_names, _tl.http_status = {}, [], None
        t0 = time.time()
        row = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "module": mod.__name__, "episode_id": getattr(_tl, "ep", None),
               "panelist": getattr(_tl, "pid", None), "model_requested": modelo,
               "max_tokens": max_tokens}
        try:
            out, meta = orig_chamar(protocolo, base, modelo, chave, texto, timeout, max_tokens)
        except Exception as e:  # recorded, then re-raised so the module's own retry logic runs
            row.update(error=type(e).__name__, http_status=getattr(_tl, "http_status", None),
                       headers=getattr(_tl, "headers", {}), seconds=round(time.time() - t0, 2))
            _write(row)
            raise
        row.update(served=meta.get("served"), stop=meta.get("stop"), usage=meta.get("usage"),
                   blocos=meta.get("blocos"), text_len=len(out or ""),
                   http_status=getattr(_tl, "http_status", None),
                   headers=getattr(_tl, "headers", {}),
                   header_names=getattr(_tl, "header_names", []),
                   seconds=round(time.time() - t0, 2))
        _write(row)
        return out, meta

    def julgar(pan, ep, prompt, timeout):
        _tl.ep, _tl.pid = ep["episode_id"], pan[0]
        return orig_julgar(pan, ep, prompt, timeout)

    mod.chamar, mod.julgar = chamar, julgar


def main() -> int:
    global _log_path
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--module", choices=["run_panel", "run_panel_deepseek6k"], required=True)
    r.add_argument("--calls-log", required=True)
    r.add_argument("rest", nargs=argparse.REMAINDER)
    g = sub.add_parser("gate1")
    g.add_argument("--episodes", required=True)
    g.add_argument("--out", required=True)
    g.add_argument("--calls-log", required=True)
    a = ap.parse_args()

    verify_pins()
    urllib.request.urlopen = _urlopen
    _log_path = Path(a.calls_log)
    _log_path.parent.mkdir(parents=True, exist_ok=True)

    if a.cmd == "run":
        mod = __import__(a.module)
        instrument(mod)
        rest = a.rest[1:] if a.rest[:1] == ["--"] else a.rest
        sys.argv = [f"{a.module}.py", *rest]
        return mod.main()

    # gate1
    import run_panel as rp
    import run_panel_deepseek6k as rpd
    instrument(rp)
    instrument(rpd)
    ep = json.loads(Path(a.episodes).read_text().splitlines()[0])
    out = []
    for mod, pid, timeout in ((rp, "zhipu", 180), (rp, "xai", 180), (rp, "google", 180),
                              (rpd, "deepseek", 220)):
        prompt, phash = mod.carregar_prompt()
        pan = next(p for p in mod.PAINEL if p[0] == pid)
        res = mod.julgar(pan, ep, prompt, timeout)
        res["prompt_sha256"] = phash
        res["module"] = mod.__name__
        out.append(res)
        print(f"{pid}: status={res['status']} requested={res['model']} served={res['model_served']}",
              file=sys.stderr)
    # Is gemini-2.5-pro still listed on the same endpoint? (metadata GET, no generation)
    gp = next(p for p in rp.PAINEL if p[0] == "google")
    info: dict = {"url": f"{gp[4]}/models/{gp[2]}"}
    try:
        req = urllib.request.Request(info["url"], headers={"x-goog-api-key": gp[5]()})
        with _orig_urlopen(req, timeout=60) as resp:
            d = json.loads(resp.read())
            info.update(http_status=resp.status,
                        **{k: d.get(k) for k in ("name", "version", "displayName", "description",
                                                  "inputTokenLimit", "outputTokenLimit",
                                                  "supportedGenerationMethods")})
    except urllib.error.HTTPError as e:
        info.update(http_status=e.code)
    info["checked_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    out.append({"gemini_model_get": info})
    Path(a.out).write_text("\n".join(json.dumps(x, ensure_ascii=False, sort_keys=True)
                                     for x in out) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
