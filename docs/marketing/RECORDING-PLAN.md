# nox-mem — Recording plan

> Version: v1.0 (2026-05-18, Wave G)
> Cross-ref: `docs/marketing/DEMO-VIDEO-SCRIPT.md` (shot list per scene)
> Pre-requisite: Hero cut script reviewed + numbers honesty checklist signed off

---

## 1. Pre-production checklist

### Hardware + space

- [ ] Condenser or cardioid microphone (USB condenser is fine: Blue Yeti, Rode NT-USB, Focusrite Scarlett 2i2 + dynamic mic)
- [ ] Acoustic treatment: closet recording or reflection filter. No hard walls behind mic. Hard floor with no rug = reverb problem.
- [ ] No HVAC/fan noise during VO takes. Check before starting.
- [ ] Monitor: 27" or larger if available — terminal at 18pt Fira Code / JetBrains Mono needs screen space
- [ ] Webcam: if talking-head B-roll is used (optional for this script), any 1080p is fine

### Software — terminal

- **Shell:** zsh, minimal prompt (project name + git branch, nothing else)
- **Theme:** Catppuccin Mocha or matching custom dark scheme (`#1e1e2e` background, `#cdd6f4` text, `#a6e3a1` output highlight)
- **Font:** JetBrains Mono 18pt or Fira Code 18pt
- **No notifications:** Do Not Disturb ON, Slack/Mail/Messages closed, Notification Center cleared
- **No other apps visible:** full-screen terminal only
- **No .env in terminal history:** verify `~/.zsh_history` does not expose API keys
- **iTerm2 setting:** hide tab bar, hide title bar, hide scrollbar — bare terminal only

### Software — screen recording

- **macOS:** QuickTime Player → New Screen Recording (lossless)
  - Alternative: OBS Studio (free, more control over regions)
- **Resolution:** 1920×1080 minimum
- **Frame rate:** 60fps for terminal typing (smooth, no choppiness)
- **Region:** full screen; crop in edit, not during capture
- **Audio:** record VO separately (not via screen recording audio)

### Software — VO recording

- **DAW:** GarageBand (free, pre-installed macOS) or Audacity (free)
- **Format:** WAV 48kHz 24-bit (not MP3 — degrade in editing)
- **Takes:** record 3 per paragraph; label by scene/paragraph (e.g., `S1-P1-take2.wav`)
- **Pattern:** read twice dry, once with expression. Keep all takes for editing.

### Repo state for recording

- [ ] `main` branch clean (`git status` shows nothing staged or modified)
- [ ] Demo corpus loaded: `benchmark/fixtures/demo-corpus/` ingested into `~/demo.db`
- [ ] `NOX_DB_PATH=~/demo.db` set in the recording shell session
- [ ] `GEMINI_API_KEY` set (but masked from camera — use `export GEMINI_API_KEY=$(cat ~/.gemini_key)` so key never appears in terminal)
- [ ] `nox-mem --help` runs without error
- [ ] HTTP API running: `curl http://localhost:18802/api/health | jq .version` returns current version
- [ ] All commands in the script verified as working with the demo corpus (do a full dry run the day before)

### Visual assets — verify before shoot

| Asset | Path | Status needed |
|---|---|---|
| banner-dark.svg | `assets/readme/banner-dark.svg` | Open in browser, renders correctly |
| banner-light.svg | `assets/readme/banner-light.svg` | Backup for light-mode scenes |
| architecture-dark.svg | `assets/readme/architecture-dark.svg` | Open, all labels readable |
| architecture-light.svg | `assets/readme/architecture-light.svg` | Backup |
| logo-dark.svg | `assets/readme/logo-dark.svg` | Renders at 64px |
| stat-scale-dark.svg | `assets/readme/stat-scale-dark.svg` | Number matches current corpus |
| stat-opex-dark.svg | `assets/readme/stat-opex-dark.svg` | Number matches current actuals |
| stat-latency-dark.svg | `assets/readme/stat-latency-dark.svg` | 101ms verified |
| stat-tests-dark.svg | `assets/readme/stat-tests-dark.svg` | 535+ verified |

Assets not yet as SVG (create as text cards in Figma/Keynote with palette D):
- Provider overhead: `0.0025ms / call`
- Bundle size: `11.7 KB`
- nDCG@10: `0.6813 (+9.8pp over baseline)`

Text card spec: 400×200px, `#1e1e2e` background, `#00C896` number (48pt bold), `#cdd6f4` label (16pt regular), 24px padding.

---

## 2. Recording sequence (order to shoot)

Record in this order — least re-takeable to most re-takeable:

### Day 1 — Terminal sessions (deterministic)

1. **Scene 2: Quick start** — most re-takeable, record first as warmup
2. **Scene 4: KG demo** — two sub-sessions (`kg-build` + `search --kg`); record in one continuous take if possible
3. **Scene 3: Provider swap** — requires `nox-mem vectorize --reembed`; may be slow; record early
4. **Scene 5: Shadow discipline** — `api/health` endpoint; record real terminal, not mocked
5. **Scene 8–12: Long cut extras** — record after Hero cut terminal sessions are done

**Terminal recording protocol:**
- Open a fresh shell session (no history pollution)
- `export NOX_DB_PATH=~/demo.db` first
- Type all commands at ~70% normal speed (reviewers will have keyboard sounds in edit)
- If you mistype: do not delete with backspace on camera. `Ctrl+C`, start the command again cleanly.
- Record each scene as a separate QuickTime capture (named by scene: `s2-quick-start.mov`, `s4-kg-demo.mov`, etc.)

### Day 1 afternoon — Architecture / stat cards

6. **Scene 3 visual:** Export architecture-dark.svg as 1920×1080 PNG; create zoom sequence in Keynote
7. **Scene 5 visual:** Create shadow-mode timeline diagram (Keynote or Figma, 1920×1080)
8. **Scene 6 visual:** Assemble stat card sequence as Keynote deck

### Day 2 — Voiceover

Record VO after terminal sessions are done and roughly edited — this way VO can match exact pacing of what's on screen.

9. **Scene 1** (hook VO): most important, record last after all other VO is settled
10. **Scenes 2–7** in order
11. **Re-takes pass**: listen back at 1.0× speed, flag any takes with mouth noise, stumbles, wrong emphasis
12. **Scene 1 re-take** if the hook doesn't feel right on first pass

**VO protocol:**
- Stand (not sit) while recording — better breath support, better energy in voice
- Warm up: 2 min of reading aloud before any takes
- Script in large font (18pt) printed or displayed on secondary monitor (not on recording monitor)
- Each paragraph is its own take; do not try to record full scenes in one breath
- Name files: `vo-s1-p1-take1.wav`, `vo-s1-p1-take2.wav`, etc.

### Day 3 — B-roll and stills

13. Finder window showing `nox-mem.db` (file tangibility visual)
14. Screenshot of `nox-mem --help` scrolled to show command count (26+ commands)
15. README scroll (browser, GitHub, dark mode)
16. Screenshot of stat cards in context (README numbers section)
17. End card assets: QR code generated + paper bibtex card

---

## 3. Asset shopping list

### From `assets/readme/` — use as-is

- `banner-dark.svg` — Scene 1 opener
- `architecture-dark.svg` — Scenes 3, 4 (zoom/highlight needed)
- `logo-dark.svg` — Scene 1 title card, end card
- `stat-scale-dark.svg`, `stat-opex-dark.svg`, `stat-latency-dark.svg`, `stat-tests-dark.svg` — Scene 6

### Create for this video

| Asset | Format | Notes |
|---|---|---|
| Shadow-mode timeline diagram | 1920×1080 PNG/Keynote | Decision flow: change → shadow → 7d baseline → activate/revert |
| Text stat cards (3) | 400×200 PNG × 3 | Provider overhead, bundle size, nDCG (see palette D spec above) |
| End card (GitHub + QR + paper) | 1920×1080 Keynote slide | Dark bg, #00C896 accents |
| QR code for GitHub URL | 500×500 PNG | Generate via qr.io; verify scan before recording |

### Music — royalty-free suggestions

All three options below are CC0 or royalty-free verified. Choose the one that matches the energy:

| Track | Source | Vibe | Notes |
|---|---|---|---|
| "Equinox" by Scott Buckley | scottbuckley.com.au (CC4.0) | Minimal electronic, understated | Good for technical tone |
| "Dreamer" by Hanu Dixit | freemusicarchive.org (CC4.0) | Light, forward motion | Slightly warmer; good for GTM version |
| "Ambient 1 (Music for Airports)" inspiration track from Pixabay | pixabay.com/music (royalty-free) | Atmospheric, sparse | Best for shadow discipline scene |

Use music at -18dB under VO. Duck to -24dB during any terminal command that has audible feedback. No music during the shadow discipline scene explanation — silence amplifies the point.

### Sound effects

- Terminal typing: subtle mechanical key sound, -30dB under VO (Freesound #242855 or similar CC0)
- Command completion: soft `ding` or silent — do not over-SFX
- Do NOT use retro/sci-fi terminal sounds. Understatement is the brand.

---

## 4. Editing workflow

### Software recommendation

**DaVinci Resolve 19 (free version)** — sufficient for this edit. Handles multi-track audio, color grading, titles, export presets.

Alternative: **Final Cut Pro** (macOS, paid) — faster for Apple Silicon, better proxy workflow if exporting from QuickTime .mov.

### Project setup

- Resolution: 1920×1080
- Frame rate: 60fps (match terminal recordings)
- Color space: Rec.709
- Audio: 48kHz 24-bit stereo
- Sequence: 5 min 30 s (Hero cut); plan 10 min 30 s for long cut

### Color grading

The visual brand is dark mode aesthetic matching the `assets/readme/` palette:

- Backgrounds: near-black `#1e1e2e` or `#0d0d14`
- Accent color: `#00C896` — use on text highlights, stat card numbers, line dividers
- Body text: `#cdd6f4`
- Terminal output: `#a6e3a1` (green) for success lines; `#f38ba8` (red) for warnings/errors if shown
- No heavy LUT — this is a dev tool, not a lifestyle product. Clean, honest grade.

**Color correction for terminal recordings:**
- Boost contrast slightly (terminal text must be legible on every monitor)
- Do NOT add film grain or cinematic treatment to terminal footage
- Architecture diagrams: leave as designed (no grading)

### Cuts

- No transition longer than 12 frames (0.2s at 60fps) — cut hard or quick dissolve only
- Between terminal commands: cut on command entry (moment of pressing Return), not on output
- Between VO and visuals: visual leads VO by 0.5s — show before tell
- Dead air rule: if VO is not happening and no new information is on screen, cut

### Captions

**Burned-in captions required** for both PT-BR and EN tracks:

- PT-BR: yellow `#FFFF00` or white `#FFFFFF`, lower-third position (20% from bottom)
- EN: white `#FFFFFF`, above PT-BR line or displayed after VO in alternating segments
- Font: same as terminal (JetBrains Mono or Fira Code) for code portions; sans-serif for VO captions
- Never use auto-generated captions from YouTube — they are unreliable for PT-BR technical content

Consider: upload PT-BR and EN as separate `.srt` files to YouTube (allows viewer to toggle). Burn-in for Twitter/LinkedIn (no audio autoplay).

### Export presets

| Format | Resolution | Bitrate | Container | For |
|---|---|---|---|---|
| YouTube Hero | 1920×1080 | 16 Mbps | H.264 MP4 | YouTube upload |
| Twitter/X teaser | 1080×1080 | 8 Mbps | H.264 MP4 | Twitter; square crop |
| LinkedIn cut | 1920×1080 | 12 Mbps | H.264 MP4 | LinkedIn video post |
| Archive master | 1920×1080 | lossless | ProRes 422 or DNxHR | Local archive |

---

## 5. Distribution plan

### YouTube (primary)

- Title: `nox-mem — Pain-weighted hybrid memory with shadow discipline | 5-min demo`
- Description: open with 3-line value prop → key links (GitHub, paper, QUICKSTART) → timestamp chapters → full number table with PR links
- Tags: `agent memory`, `sqlite`, `RAG`, `hybrid retrieval`, `Claude Code`, `MCP`, `open source`
- Chapters in description:
  ```
  0:00 Hook — the third path
  0:30 Quick start in 60 seconds
  1:30 Yours by design — data autonomy
  2:30 Hybrid intelligence — BM25 + vectors + KG
  3:30 Shadow discipline
  4:30 Real numbers
  5:00 Call to action
  ```
- Thumbnail: dark background, `nox-mem` text in #00C896, stat "0.68 nDCG@10" subtext, architecture SVG crop. High contrast for mobile.
- Upload: unlisted first → verify chapters/captions → public (do NOT publish before Q4 gate if numbers change)

### Twitter/X

- Post template:
  ```
  Built a hybrid memory layer for AI agents — local-first, SQLite, no lock-in.

  Shadow discipline: every ranking change runs 7d in shadow-mode before activating.
  p95 = 101ms · <$11/mo · 69k chunks · MIT

  [30s clip]
  github.com/totobusnello/memoria-nox
  ```
- Post separately (without video) when arXiv paper is live: link paper + repo

### LinkedIn

- Post: 150-word professional framing → 60s clip → GitHub URL
- Audience: founders evaluating memory for products; investors in AI infra
- Lead with autonomy + cost angle (not just benchmarks)

### Hacker News

- Title: `Show HN: nox-mem – hybrid memory for AI agents, local SQLite, shadow discipline`
- Body: 300 words, technical, honest about pending Q-gate
- Timing: weekday 9am–11am PT (peak traffic)
- Rule: do NOT post to HN before LoCoMo/LongMemEval numbers are final and Q4 COMPARISON.md is published. The benchmark honesty is the HN pitch.

### Reddit

- r/MachineLearning: post when paper preprint is on arXiv (link paper + code)
- r/LocalLLaMA: post focused on local-first angle + SQLite portability
- r/programming: post focused on engineering (shadow discipline as software pattern)

### README embed

After Hero cut is published:

```markdown
## Demo

[![5-min demo](https://img.youtube.com/vi/YOUTUBE_ID/maxresdefault.jpg)](https://www.youtube.com/watch?v=YOUTUBE_ID)

> *Pain-weighted hybrid memory with shadow discipline — yours by design. 5 min.*
```

Place after the "Why memoria-nox" section, before Architecture.

---

## 6. Timeline

| Phase | Duration | Gate |
|---|---|---|
| Pre-production (this doc + script) | Done | Wave G |
| Asset verification + demo corpus prep | 1 day | Before shoot |
| Day 1: Terminal sessions + B-roll | 1 day | — |
| Day 2: VO recording | half day | Terminal sessions locked |
| Day 3: Remaining B-roll + stills | half day | — |
| Edit Hero cut rough | 1 day | All raw assets in |
| Edit Hero cut fine + captions | 1 day | Rough approved |
| Export + distribute | 1 day | Q4 gate cleared (LoCoMo/LongMemEval) |

**Total wall-clock time from go-signal to YouTube upload: ~1 week.**

The bottleneck is Q4 gate — do not rush to publish Hero cut before `COMPARISON.md` is real data. The video will be used in GTM Phase 2, which is conditional on Q4 winning.

---

## 7. Contingency

### If Q4 numbers are not ready

Publish a "Lab preview" cut instead:
- Remove Scene 6 stat cards with pending-gate numbers
- Add explicit "Q1/Q2/Q3 benchmarks in progress" card at Scene 6
- Distribute only to GitHub (not HN, not Twitter amplification push)
- Title: `nox-mem — early preview | local-first hybrid memory`

This allows the repo to have a demo video for README embed without misleading anyone about benchmark status.

### If a number changes before publish

Any shipped PR that changes a verified number (corpus growth, latency improvement, test count change) requires:
1. Update `DEMO-VIDEO-SCRIPT.md` honesty checklist
2. Re-record the affected Scene 6 stat card (usually one card, 10min re-record)
3. Re-export the affected segment only (no full re-edit)
