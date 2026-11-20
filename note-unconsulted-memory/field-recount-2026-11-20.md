# Field recount for the note, 2026-11-20

Read-only recount of the two field figures in section 6 of `NOTE.md` that came from queries on the
production host, so that each has a source in this repository. Run by the author on 2026-11-20 at
21:48 UTC, with a second pass at 22:37 UTC that dates each call (below). Only counts and dates
were printed; no query text, reply or transcript content was read out.

## Agent transcripts after the deployment

Command, run in the agents' transcript root on the production host (`<agent-transcripts>`):

```sh
python3 - <<'PY'
import json, collections, os, datetime
cut = datetime.datetime(2026, 11, 8, 17, 45, tzinfo=datetime.timezone.utc).timestamp()
files = [os.path.join(r, f) for r, _, fs in os.walk('.') for f in fs
         if f.endswith('.jsonl') and os.path.getmtime(os.path.join(r, f)) > cut]
print('files_after_deploy', len(files))
c, per = collections.Counter(), collections.Counter()
for f in files:
    for line in open(f, errors='replace'):
        try: o = json.loads(line)
        except Exception: continue
        m = o.get('message') or {}
        cont = m.get('content') if isinstance(m, dict) else None
        if not isinstance(cont, list): continue
        for b in cont:
            if isinstance(b, dict) and b.get('type') == 'tool_use' \
                    and str(b.get('name', '')).startswith('mcp__nox-mem__'):
                c[b['name']] += 1; per[f.split('/')[1]] += 1
print('tool_counts', dict(c)); print('per_project_dir', dict(per))
PY
```

Output:

```
files_after_deploy 83
tool_counts {'mcp__nox-mem__nox_mem_search': 13, 'mcp__nox-mem__nox_mem_get': 1}
per_project_dir {'-root--openclaw-workspace-agents-lex': 14}
```

13 search calls and 1 full-text read, all from one agent (`lex`), whose weekly deadline sweep was
switched off on 2026-11-17 (openclaw-vps PR #89). The first count, on 2026-11-17, found the same 13
and 1 in 65 files; the 18 more files now are transcripts modified in the three days since, and none
of them adds a memory call.

### Each call dated by its own timestamp

The first pass selects files by modification time and counts every call in them, so a call made
before the deployment inside a file touched after it would be counted too (openclaw-vps PR #89
describes the sweep's searches as running from 2026-10-23). The second pass keeps the same files
and splits each call by the `timestamp` of its transcript line:

```sh
python3 - <<'PY'
import json, collections, os, datetime
DEP = datetime.datetime(2026, 11, 8, 17, 45, tzinfo=datetime.timezone.utc)
cut = DEP.timestamp()
files = [os.path.join(r, f) for r, _, fs in os.walk('.') for f in fs
         if f.endswith('.jsonl') and os.path.getmtime(os.path.join(r, f)) > cut]
print('files_after_deploy', len(files))
by, days, no_ts = collections.Counter(), collections.Counter(), 0
for f in files:
    for line in open(f, errors='replace'):
        try: o = json.loads(line)
        except Exception: continue
        m = o.get('message') or {}
        cont = m.get('content') if isinstance(m, dict) else None
        if not isinstance(cont, list): continue
        for b in cont:
            if isinstance(b, dict) and b.get('type') == 'tool_use' \
                    and str(b.get('name', '')).startswith('mcp__nox-mem__'):
                ts = o.get('timestamp')
                if not ts: no_ts += 1; continue
                t = datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
                side = 'after' if t >= DEP else 'before'
                by[(side, b['name'].split('__')[-1], f.split('/')[1])] += 1
                days[(side, t.date().isoformat())] += 1
for k in sorted(by): print('calls', k, by[k])
for k in sorted(days): print('day', k, days[k])
print('no_timestamp', no_ts)
PY
```

Output:

```
files_after_deploy 83
calls ('after', 'nox_mem_get', '-root--openclaw-workspace-agents-lex') 1
calls ('after', 'nox_mem_search', '-root--openclaw-workspace-agents-lex') 13
day ('after', '2026-11-09') 6
day ('after', '2026-11-16') 8
no_timestamp 0
```

All 14 calls are after the deployment, on two Mondays a week apart; the sweep's cron line was
`0 11 * * 1`, every Monday (openclaw-vps PR #89). The earlier searches PR #89 mentions are not
in any file still on disk. The count covers the files examined; transcripts the host has already
pruned cannot be counted.

## Server telemetry, MCP searches by caller

```sql
SELECT requesting_agent, COUNT(*) FROM search_telemetry
WHERE ts >= '2026-10-18' AND ts < '2026-11-18' GROUP BY 1;
```

Output (`sqlite3 -readonly` on `$NOX_DB_PATH`):

```
answer:unknown|3
cli:unknown|19
mcp:unknown|109
probe:diag-fts-26out|5
probe:kg-corpus-scope|110
probe:probe-reativacao|6
probe:semantic-canary|1490
```

109 MCP searches with an unknown caller; the telemetry does not say which client made them. The
draft of 2026-11-17 printed 108 from the same query without the upper bound, run that afternoon.
The latest rows explain the difference:

```sql
SELECT ts FROM search_telemetry WHERE requesting_agent='mcp:unknown' AND ts >= '2026-10-18'
ORDER BY ts DESC LIMIT 4;
```

```
2026-11-17 16:12:46
2026-11-17 16:07:48
2026-11-17 14:32:41
2026-11-16 15:15:33
```

No `mcp:unknown` row came after 16:12:46 on 2026-11-17. The unbounded query returns 108 when run
between 16:07:48 and 16:12:46 that afternoon, which fits the draft's figure; the time of that
first reading was not recorded. The bounded window gives the same 109 whenever it is run.
