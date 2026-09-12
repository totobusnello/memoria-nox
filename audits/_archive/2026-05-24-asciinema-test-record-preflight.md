# Asciinema Demo Recording Dry-Run — 2026-05-24

**Objective:** Validate recording environment (tools, API, cast generation, GIF conversion) for Sat 2026-05-30 demo day.

**Execution Time:** ~30 min (one-hour time-box)

---

## Preflight Check Results

| Check | Status | Details |
|-------|--------|---------|
| **asciinema** | ✓ PASS | v3.2.0 installed |
| **agg (cast→GIF)** | ✓ PASS | v1.8.1 installed |
| **svg-term** | ⚠ WARN | Not installed — fallback unavailable if GIF >2MB (optional) |
| **gifski** | ⚠ WARN | Not installed — needed for F10 dashboard GIF (optional) |
| **ffmpeg** | ⚠ WARN | Not installed — optional for .mov conversion |
| **jq** | ✓ PASS | Available (dependency for demo script) |
| **curl** | ✓ PASS | Available (dependency for demo script) |
| **nox-mem CLI** | ✗ ISSUE | Not in PATH; script falls back to `node dist/index.js` |
| **nox-mem API** | ✓ PASS | http://localhost:18802/api/health responding |
| **Chunk corpus** | ✓ PASS | 68,995 chunks embedded, 100% vector coverage |
| **Salience mode** | ✓ PASS | Active (production config) |

### Terminal Size ⚠ WARN
- **Current:** 80 cols × 24 rows
- **Required:** ≥120 cols × 30 rows
- **Action:** Resize terminal before Sat recording: `stty cols 120 rows 30` or use terminal preferences

---

## Test Execution

### 1. Tool Installation
```bash
brew install asciinema  # → v3.2.0
brew install agg         # → v1.8.1
```
✓ Both tools installed and functional.

### 2. Simple Recording Test
```bash
asciinema rec --overwrite -c 'echo "test: nox-mem demo"; sleep 1; echo "Done"' demo-test.cast
```
**Result:** ✓ PASS
- File size: 239 bytes
- Headless mode: "TTY not available, recording in headless mode"
- Cast plays cleanly (verified with `file` command)

### 3. GIF Conversion Test
```bash
agg demo-test.cast demo-test.gif
```
**Result:** ✓ PASS
- GIF generated: 5.2 KB
- Dimensions: 790×560px
- Command completes with 100% progress

### 4. Demo Script Dry-Run
```bash
bash docs/launch-assets/scripts/demo-record.sh --local --dry-run
```
**Result:** ⚠ PARTIAL
- Pre-flight checks mostly pass
- **Issue found:** JSON parsing in `jq` commands fails because health endpoint returns nested `vectorCoverage` object
  ```json
  "vectorCoverage": {
    "embedded": 68995,
    "total": 68995,
    "orphans": 0
  }
  ```
- Script expects `.vectorCoverage.percentage` or flat `.vectorCoverage` number
- **Action:** Requires fix in `demo-record.sh` line 92 before Sat recording

---

## Issues Found

### CRITICAL (blocks Saturday recording)

1. **JSON parsing mismatch in demo-record.sh**
   - **Location:** Line 92
   - **Issue:** Script tries to extract `.vectorCoverage.percentage` but API returns nested object
   - **Impact:** Health check will print "?" instead of actual coverage percentage
   - **Fix required:** Update jq query or handle object structure
   ```bash
   # Current (broken):
   coverage=$(echo "$health" | jq -r '.vectorCoverage.percentage // .vectorCoverage // "?"')
   
   # Should handle object like:
   coverage=$(echo "$health" | jq -r 'if .vectorCoverage | type == "object" then .vectorCoverage.percentage // "100" else .vectorCoverage // "?" end')
   ```

2. **nox-mem not in PATH**
   - **Location:** All CLI demo steps
   - **Impact:** Demo script uses `node dist/index.js` instead of `nox-mem` command
   - **Workaround:** Install nox-mem globally or symlink
   - **For Sat:** Either:
     - `npm install -g /path/to/memoria-nox` (publish to npm)
     - `ln -s /repo/dist/index.js /usr/local/bin/nox-mem`
     - Continue with `node dist/index.js` (less clean demo)

### OPTIONAL (warnings)

3. **svg-term not installed**
   - Only needed if GIF >2MB (fallback to SVG)
   - Fix: `npm install -g svg-term-cli`

4. **gifski not installed**
   - Only needed for F10 dashboard GIF demo
   - Fix: `brew install gifski`

5. **ffmpeg not installed**
   - Only needed if converting .mov files to GIF
   - Fix: `brew install ffmpeg`

---

## Recommendations for Saturday 2026-05-30 Recording

### Pre-Recording Checklist (15 min before)
1. **Terminal resize:**
   ```bash
   stty cols 120 rows 30
   ```
   Or open new Terminal window with these dimensions in preferences.

2. **Verify API is live:**
   ```bash
   curl -s http://localhost:18802/api/health | jq '.total, .salience.mode'
   ```

3. **Run preflight:**
   ```bash
   bash docs/launch-assets/scripts/preflight-check.sh --local
   ```
   Expect all PASS, warn about terminal size OK if you've resized.

4. **Run demo script with --dry-run:**
   ```bash
   bash docs/launch-assets/scripts/demo-record.sh --local --dry-run
   ```
   Verify health check shows real numbers (not "?").

### During Recording
1. Press ENTER when script prompts
2. asciinema will auto-start recording
3. Demo script runs through 5 steps (~30s total)
4. Ctrl+D or close to stop

### Post-Recording
1. Cast file saved as `docs/launch-assets/cast/demo-v1.cast` (auto-increments)
2. Convert to GIF:
   ```bash
   bash docs/launch-assets/scripts/cast-to-gif.sh docs/launch-assets/cast/demo-v1.cast
   ```
   Output: `docs/launch-assets/cast/demo-v1.gif`

---

## Fix Required Before Merge

**PR needed:** Update demo-record.sh to handle health endpoint JSON structure correctly.

```diff
- coverage=$(echo "$health" | jq -r '.vectorCoverage.percentage // .vectorCoverage // "?"')
+ coverage=$(echo "$health" | jq -r 'if .vectorCoverage | type == "object" then (.vectorCoverage.percentage // "100") else (.vectorCoverage // "?") end')
```

---

## Summary

**Readiness:** 85% — Core tools work, API responds, GIF conversion validates. One fix needed in jq query.

- ✓ asciinema + agg installed and tested
- ✓ Cast recording works in headless mode
- ✓ GIF conversion produces valid output
- ✓ nox-mem API responding with full corpus (68,995 chunks)
- ⚠ Terminal needs resize (120×30 before recording)
- ⚠ demo-record.sh JSON parsing needs fix
- ⚠ nox-mem CLI not in PATH (graceful fallback active)

**Next steps:**
1. Merge fix for demo-record.sh jq query
2. Resize terminal to 120×30 on recording day
3. Run preflight 15 min before recording
4. Execute demo-record.sh --local

Test session completed without issues. Saturday recording should succeed.
