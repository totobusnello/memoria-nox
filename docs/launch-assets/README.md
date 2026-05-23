# Launch Demo Assets — nox-mem

Recording prep for the Sat 2026-05-30 demo session. Launch target: 2026-06-03.

Plans: `docs/launch-demo-plan.md` | Narration: `docs/launch-demo-narration.md`

---

## Directory layout

```
docs/launch-assets/
  cast/          ← .cast files from asciinema (not committed; in .gitignore)
  gif/           ← intermediate GIFs (not committed; in .gitignore)
  scripts/
    demo-record.sh       ← end-to-end recording script (asciinema)
    cast-to-gif.sh       ← .cast → GIF / SVG pipeline (agg + svg-term)
    preflight-check.sh   ← validate env before demo day
  README.md              ← this file
```

Final assets (committed to git after recording):
```
docs/assets/
  demo-cli.gif           ← primary README hero embed (<2MB)
  demo-cli.svg           ← SVG fallback if GIF >2MB
  demo-dashboard.gif     ← F10 dashboard browser clip (<1MB)
  demo.cast              ← raw recording (reference; not embedded)
```

---

## Dependencies

Install on macOS before recording day (Sat 2026-05-30):

```bash
# Required for recording
brew install asciinema          # terminal recording

# Required for GIF export
brew install asciinema-agg      # .cast → GIF (primary pipeline)

# Optional — SVG fallback if GIF >2MB
npm install -g svg-term-cli

# Optional — F10 dashboard GIF
brew install gifski              # .mov → GIF (macOS QuickTime + gifski)
brew install ffmpeg              # .mov frame extraction (if needed)
```

Verify:

```bash
asciinema --version   # 2.x
agg --version         # 0.x
```

---

## Quick start — recording day

### Step 1: Preflight check

Run this first. Validates endpoint, tools, terminal size, corpus health.

```bash
./docs/launch-assets/scripts/preflight-check.sh
# or for local install:
./docs/launch-assets/scripts/preflight-check.sh --local
```

All PASS = ready to record. Fix any FAIL before proceeding.

### Step 2: Set terminal dimensions

Terminal must be **120 columns × 30 rows** for the recording.

```bash
# Check current size
echo "$(tput cols)×$(tput lines)"

# Resize manually (if your terminal supports it)
printf '\033[8;30;120t'
# or via stty:
stty cols 120 rows 30
```

Recommended font: JetBrains Mono 14pt (or any monospace with ligatures).

### Step 3: Record

```bash
./docs/launch-assets/scripts/demo-record.sh
```

The script:
1. Checks dependencies
2. Validates endpoint health
3. Shows the terminal size reminder
4. Launches `asciinema rec` with `--idle-time-limit 1` (compresses pauses)
5. Runs the full demo flow (help → search → health → answer → stats)
6. Auto-increments output filename (`demo-v1.cast`, `demo-v2.cast`, ...)

Aim for **minimum 3 takes**. Pick the best one.

For local nox-mem (not VPS):

```bash
./docs/launch-assets/scripts/demo-record.sh --local
```

Requires nox-mem running locally on port 18802. See `docs/QUICKSTART.md`.

### Step 4: Convert cast → GIF

```bash
./docs/launch-assets/scripts/cast-to-gif.sh docs/launch-assets/cast/demo-v2.cast
```

Output: `docs/launch-assets/gif/demo-v2.gif`

The script:
- Tries `agg` at fps-cap 20 (primary)
- Auto-retries at fps-cap 15 if GIF >2MB
- Falls back to svg-term if still >2MB (and svg-term is installed)
- Reports final file size

### Step 5: Copy final asset to docs/assets/

Once satisfied with the GIF:

```bash
mkdir -p docs/assets
cp docs/launch-assets/gif/demo-v2.gif docs/assets/demo-cli.gif
ls -lh docs/assets/demo-cli.gif   # confirm <2MB
```

### Step 6: Dashboard GIF (F10 browser clip — separate)

Captured manually via Kap or QuickTime + gifski. See `docs/launch-demo-plan.md §5`.

```bash
# After exporting .mov from QuickTime, extract frames and convert:
ffmpeg -i screen-recording.mov -r 10 /tmp/frames/frame%04d.png
gifski --fps 10 --width 800 -o docs/assets/demo-dashboard.gif /tmp/frames/*.png
ls -lh docs/assets/demo-dashboard.gif  # target <1MB
```

Kap alternative (GUI, simpler): https://getkap.co — export directly as GIF.

### Step 7: Commit assets

```bash
git add docs/assets/demo-cli.gif docs/assets/demo-dashboard.gif
# optionally include the raw cast for reference:
git add docs/launch-assets/cast/demo-v2.cast
git commit -m "feat(launch): add demo assets — CLI GIF + dashboard GIF"
git push origin feat/launch-demo-recording
```

Then open a PR against main, verify rendering on github.com preview before merge.

---

## Demo flow (from launch-demo-plan.md §2)

| # | Command | Expected duration | Purpose |
|---|---------|------------------|---------|
| Intro | title card | 1.5s | branding |
| 1 | `nox-mem --help` | ~3s | Shows 26+ subcommands |
| 2 | `nox-mem search "G10 conditional mutex"` | ~5s | Hybrid search BM25+Gemini+RRF |
| 3 | `curl /api/health \| jq .` | ~5s | 69k chunks, 100% vec, salience active |
| 4 | `curl /api/answer -d '{"query":"..."}' \| jq .` | ~10s | Flagship: grounded answer + citations |
| 5 | `nox-mem stats --json \| jq '{chunks,entities,relations,coverage}'` | ~5s | KG numbers |
| Outro | title card | 2s | GitHub + MIT |

Total: ~70s. Asciinema idle-time-limit 1 compresses any pauses.

Browser segment (§6–7 of plan) captured separately as `demo-dashboard.gif`.

---

## Troubleshooting

### agg not found after brew install

```bash
# agg binary may be named differently or not in PATH
ls /opt/homebrew/bin/agg
# add homebrew to PATH if needed
export PATH="/opt/homebrew/bin:$PATH"
```

### GIF too large (>2MB)

```bash
# Reduce fps-cap further
agg demo.cast demo.gif --fps-cap 10 --theme dracula --font-size 14

# Or use SVG (smaller, but check GitHub rendering)
cat demo.cast | svg-term --out demo.svg --window --width 120 --height 30
```

### Endpoint unreachable (VPS)

The demo can run in local mode:

```bash
# Terminal 1: start nox-mem locally
set -a; source .env; set +a
node dist/index.js api  # starts HTTP API on port 18802

# Terminal 2: record
./docs/launch-assets/scripts/demo-record.sh --local
```

Requires local DB with sufficient chunks for realistic output.
See `docs/QUICKSTART.md` for local install steps.

### asciinema command not found in subshell

The demo-record.sh script uses `--command` to run the demo inside asciinema. If `nox-mem` or `node` is not in PATH within that subshell, prefix with full path:

```bash
# In demo-record.sh, change NOX_CMD to absolute path:
NOX_CMD="/usr/local/bin/nox-mem"
# or
NOX_CMD="node /path/to/memoria-nox/dist/index.js"
```

---

## What Toto still needs to do manually (recording day)

See full checklist in `docs/launch-demo-plan.md §6`.

Summary:

1. Install `asciinema`, `agg` (and optionally `gifski`, `Kap`)
2. Run `./docs/launch-assets/scripts/preflight-check.sh` — fix any FAIL
3. Set terminal to 120×30, font ≥13pt
4. Run `./docs/launch-assets/scripts/demo-record.sh` — minimum 3 takes
5. Pick best take, run `./docs/launch-assets/scripts/cast-to-gif.sh <take>.cast`
6. Record F10 dashboard clip separately (Kap or QuickTime → gifski)
7. Copy finals to `docs/assets/`, commit, PR, verify rendering on github.com

Scripts automate everything else.

---

*Created: 2026-05-24 as part of feat/launch-demo-recording. Recording session: Sat 2026-05-30. Launch: Wed 2026-06-03.*
