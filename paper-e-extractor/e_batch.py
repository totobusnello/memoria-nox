"""Gemini Batch API over REST, standard library only (ai.google.dev batch-mode docs, read 2026-11-08).

Every network call goes through TRANSPORT so the offline tests can replace it. The key is read
from GEMINI_API_KEY at call time and never written anywhere.
"""
import json
import os
import urllib.error
import urllib.request

BASE = "https://generativelanguage.googleapis.com"
TERMINAL_OK = {"BATCH_STATE_SUCCEEDED", "JOB_STATE_SUCCEEDED"}
TERMINAL_BAD = {"BATCH_STATE_FAILED", "BATCH_STATE_CANCELLED", "BATCH_STATE_EXPIRED",
                "JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"}


def _key():
    return os.environ["GEMINI_API_KEY"]


def _http(method, url, body=None, headers=None, timeout=300):
    """-> (status, headers dict, body bytes)."""
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read()


TRANSPORT = _http


def _json(status, body, what):
    if status != 200:
        raise RuntimeError(f"{what}: HTTP {status}: {body[:300].decode(errors='replace')}")
    return json.loads(body)


def upload_jsonl(path, display_name):
    """Resumable upload of a JSONL file to the File API. -> 'files/<id>'."""
    data = open(path, "rb").read()
    st, hd, body = TRANSPORT("POST", f"{BASE}/upload/v1beta/files?key={_key()}",
                             json.dumps({"file": {"display_name": display_name}}).encode(),
                             {"X-Goog-Upload-Protocol": "resumable",
                              "X-Goog-Upload-Command": "start",
                              "X-Goog-Upload-Header-Content-Length": str(len(data)),
                              "X-Goog-Upload-Header-Content-Type": "application/jsonl",
                              "Content-Type": "application/json"})
    if st != 200:
        raise RuntimeError(f"upload start: HTTP {st}: {body[:300]!r}")
    url = {k.lower(): v for k, v in hd.items()}.get("x-goog-upload-url")
    if not url:
        raise RuntimeError("upload start: no X-Goog-Upload-URL header")
    st, _, body = TRANSPORT("POST", url, data, {"Content-Length": str(len(data)),
                                                "X-Goog-Upload-Offset": "0",
                                                "X-Goog-Upload-Command": "upload, finalize"})
    return _json(st, body, "upload")["file"]["name"]


def create(model, file_name, display_name):
    """-> batch name 'batches/<id>'. NOT idempotent: the caller records it at once."""
    st, _, body = TRANSPORT("POST", f"{BASE}/v1beta/models/{model}:batchGenerateContent?key={_key()}",
                            json.dumps({"batch": {"display_name": display_name,
                                                  "input_config": {"file_name": file_name}}}).encode(),
                            {"Content-Type": "application/json"})
    return _json(st, body, "create")["name"]


def get(name):
    """-> (state, responses file name or None, raw metadata)."""
    st, _, body = TRANSPORT("GET", f"{BASE}/v1beta/{name}?key={_key()}")
    d = _json(st, body, "get")
    md = d.get("metadata") or d
    state = md.get("state") or d.get("state")
    out = md.get("output") or (d.get("response") or {})
    rf = out.get("responsesFile") or out.get("responses_file")
    return state, rf, md


def list_display_names():
    """-> {display_name: batch name} for every batch the key can see (duplicate guard)."""
    out, tok = {}, None
    while True:
        url = f"{BASE}/v1beta/batches?pageSize=100&key={_key()}" + (f"&pageToken={tok}" if tok else "")
        st, _, body = TRANSPORT("GET", url)
        d = _json(st, body, "list")
        for op in d.get("operations") or d.get("batches") or []:
            md = op.get("metadata") or op
            dn = md.get("displayName") or md.get("display_name")
            if dn:
                out[dn] = op.get("name") or md.get("name")
        tok = d.get("nextPageToken")
        if not tok:
            return out


def download(file_name):
    """-> list of parsed JSONL lines of the responses file."""
    st, _, body = TRANSPORT("GET", f"{BASE}/download/v1beta/{file_name}:download?alt=media&key={_key()}")
    if st != 200:
        raise RuntimeError(f"download: HTTP {st}: {body[:300]!r}")
    return [json.loads(l) for l in body.decode().splitlines() if l.strip()]
