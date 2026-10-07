#!/usr/bin/env bash
# Paper B census restoration, step 2: adjudicate the 4,756 stratum-B episodes that the
# September sample left out (5,556 is_error=false minus the 800 sampled), so that stratum B
# becomes a census as PREREG §3 registered.
#
# PREPARED 2026-10-05, NOT RUN. Runs only with CENSUS_AUTHORIZED=1 in the environment, and
# only if GATES.md carries "VERDICT: PASS".
#
# Instrument: run_panel.py UNCHANGED (prompt 5b22f02c…, September settings: --only
# zhipu,xai,google --workers 8 --timeout 180), observed by gate_harness.py (logs usage and
# model headers, changes nothing). DeepSeek enters ONLY as the substitute in episodes
# without the 3-substantive-verdict floor, through run_panel_deepseek6k.py (--workers 8
# --timeout 220), per DEVIATIONS §10.31.
#
# Writes ONLY under ~/.paper2-verdicts/censo-B-20261005/. Never touches ensaio-20260921-*.
# Resumable: every output is written to .partial and renamed on success; a finished file is
# skipped on rerun. Stops at the first failed batch so no calls are wasted.
# caffeinate keeps the Mac awake (idle/system/disk) while this script lives. It does NOT
# stop sleep on a closed lid without external power — leave the Mac on AC, lid open.
set -u

if [ -z "${UNDER_CAFFEINATE:-}" ]; then
  UNDER_CAFFEINATE=1 exec /usr/bin/caffeinate -ims "$0" "$@"
fi

B=$(cd "$(dirname "$0")" && pwd)   # this directory, B-censo/
R=$(cd "$B/../.." && pwd)          # paper2-interventional/
V=$HOME/.paper2-verdicts/censo-B-20261005
L=$V/lotes
LOG=$V/census.log
mkdir -p "$V/calls" "$V/retry-in"
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
say() { echo "[$(ts)] $*" | tee -a "$LOG"; }

[ "${CENSUS_AUTHORIZED:-}" = "1" ] || { echo "refusing: set CENSUS_AUTHORIZED=1 (author's go)"; exit 3; }
if ! grep -q '^VERDICT: PASS' "$B/GATES.md"; then
  # The gates FAILED on 2026-10-05. Running anyway is the author's call, and it must be
  # recorded: CENSUS_GATE_OVERRIDE="<who, when, why>" is written to the log verbatim.
  [ -n "${CENSUS_GATE_OVERRIDE:-}" ] || { echo "refusing: GATES.md is not VERDICT: PASS (set CENSUS_GATE_OVERRIDE='<who/when/why>' to run anyway)"; exit 3; }
  mkdir -p "$V"; echo "[$(date -u +%FT%TZ)] GATE OVERRIDE: $CENSUS_GATE_OVERRIDE" >> "$V/census.log"
fi

# --- pins: instrument, harness, inputs -------------------------------------------------
cd "$B" || exit 1
shasum -a 256 -c census-pins.sha256 >/dev/null || { say "PIN MISMATCH (census-pins.sha256)"; exit 4; }
( cd "$L" && shasum -a 256 -c "$B/census-lotes.sha256" >/dev/null ) || { say "PIN MISMATCH (lotes)"; exit 4; }
n_ids=$(wc -l < "$B/census-ids.txt" | tr -d ' ')
n_eps=$(cat "$L"/censo-lote-*.jsonl | wc -l | tr -d ' ')
[ "$n_ids" = "4756" ] && [ "$n_eps" = "4756" ] || { say "count mismatch ids=$n_ids eps=$n_eps"; exit 4; }

# --- credentials inside the episodes: found 2026-10-05, the author decides --------------
# 6 census episodes carry credential-like strings (a full-length Slack `xoxp-` token in 4,
# an `sk-` key in 2) that the extract_episodes.py redaction did not catch. Running sends
# them to three external providers. Refuse unless the author recorded a decision.
if ! python3 "$B/census_tools.py" secret-scan --episodes-dir "$L" >> "$LOG" 2>&1; then
  [ -n "${CENSUS_SECRETS_DECISION:-}" ] || { say "refusing: credential-like strings in census episodes (see log); set CENSUS_SECRETS_DECISION='<decision>'"; exit 5; }
  say "SECRETS DECISION: $CENSUS_SECRETS_DECISION"
fi

H="python3 $B/gate_harness.py run"
cd "$R" || exit 1

# --- phase 1: three families over 48 batches of <=100 -----------------------------------
for f in "$L"/censo-lote-*.jsonl; do
  k=$(basename "$f" .jsonl)
  out="$V/$k-3fam.jsonl"
  if [ -s "$out" ]; then say "$k already done ($(wc -l < "$out" | tr -d ' '))"; continue; fi
  ne=$(wc -l < "$f" | tr -d ' ')
  say "$k start ($ne episodes, $((ne*3)) calls)"
  rm -f "$out.partial"
  $H --module run_panel --calls-log "$V/calls/$k-3fam.calls.jsonl" -- \
     --episodes "$f" --out "$out.partial" --only zhipu,xai,google --workers 8 --timeout 180 \
     >> "$LOG" 2>&1
  rc=$?
  nv=$( [ -s "$out.partial" ] && wc -l < "$out.partial" | tr -d ' ' || echo 0 )
  if [ "$rc" != "0" ] || [ "$nv" != "$((ne*3))" ]; then
    say "FAILED $k exit=$rc verdicts=$nv/$((ne*3)) — stopping (rerun resumes here)"; exit 1
  fi
  mv "$out.partial" "$out"; say "$k ok ($nv verdicts)"
done

# --- phase 2: ONE retry pass for quota/missing rows, per panelist (as September's retry-xai)
if [ ! -e "$V/.retry-done" ]; then
  python3 "$B/census_tools.py" retry-sets --verdicts "$V"/censo-lote-*-3fam.jsonl \
      --episodes-dir "$L" --out-dir "$V/retry-in" | tee -a "$LOG"
  for f in "$V"/retry-in/retry-*.jsonl; do
    [ -e "$f" ] || continue
    pid=$(basename "$f" .jsonl); pid=${pid#retry-}
    out="$V/censo-retry-$pid.jsonl"
    [ -s "$out" ] && { say "retry $pid already done"; continue; }
    say "retry $pid ($(wc -l < "$f" | tr -d ' ') episodes)"
    $H --module run_panel --calls-log "$V/calls/retry-$pid.calls.jsonl" -- \
       --episodes "$f" --out "$out.partial" --only "$pid" --workers 8 --timeout 180 >> "$LOG" 2>&1 \
      && mv "$out.partial" "$out" || { say "FAILED retry $pid — stopping"; exit 1; }
  done
  touch "$V/.retry-done"
fi

# --- phase 3: DeepSeek ONLY where the 3 families left no floor (DEVIATIONS §10.31) -------
ds_in="$V/ds-substituto-in.jsonl"; ds_out="$V/censo-ds-substituto.jsonl"
if [ ! -s "$ds_out" ]; then
  python3 "$B/census_tools.py" floorless --verdicts "$V"/censo-lote-*-3fam.jsonl \
      $(ls "$V"/censo-retry-*.jsonl 2>/dev/null) --episodes-dir "$L" --out "$ds_in" | tee -a "$LOG"
  if [ -s "$ds_in" ]; then
    $H --module run_panel_deepseek6k --calls-log "$V/calls/ds-substituto.calls.jsonl" -- \
       --episodes "$ds_in" --out "$ds_out.partial" --only deepseek --workers 8 --timeout 220 \
       >> "$LOG" 2>&1 && mv "$ds_out.partial" "$ds_out" || { say "FAILED deepseek substitute"; exit 1; }
  else
    : > "$ds_out"; say "no floorless episode: DeepSeek not called"
  fi
fi

# --- phase 4: assemble (lotes in order, then retries) + hashes + cost --------------------
cat "$V"/censo-lote-*-3fam.jsonl $(ls "$V"/censo-retry-*.jsonl 2>/dev/null) > "$V/censo-B-PRIMARIO-3fam.jsonl"
( cd "$V" && shasum -a 256 censo-B-PRIMARIO-3fam.jsonl censo-ds-substituto.jsonl censo-lote-*-3fam.jsonl \
    $(ls censo-retry-*.jsonl 2>/dev/null) > SHA256SUMS )
python3 "$B/census_tools.py" cost "$V"/calls/*.calls.jsonl > "$V/COST.json"
say "CENSUS DONE: $(wc -l < "$V/censo-B-PRIMARIO-3fam.jsonl" | tr -d ' ') rows; cost $(python3 -c "import json;print(json.load(open('$V/COST.json'))['TOTAL_usd'])") USD"
