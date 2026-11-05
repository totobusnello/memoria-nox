"""The six strata of the holdout frame (PREREGISTRATION.md §3), in one place.

Imported by holdout-draw.py, derive-quotas.py and frame-census.py. It reads no file at import, so
deriving quotas.json can never depend on quotas.json (the second review found that
`derive-quotas.py > quotas.json` truncated the file before the import that read it).
"""
MIN_CHARS = 200


def stratum(f):
    if f.startswith("shared/imports/"):
        return "A"
    if f.startswith("memory/entities/"):
        return "D"
    if f.startswith("memory/lessons/") or (f.startswith("memory/") and "/" not in f[7:]):
        return "B"
    if f.startswith("events/mac/"):
        return "C"
    if f.startswith("shared/"):
        return "E"
    if "/" not in f or f.startswith(("sessions/", "agents/", "../agents/", "docs/")):
        return "F"
    return None          # outside the frame
