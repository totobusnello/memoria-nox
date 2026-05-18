# memoria-nox docs site

Astro Starlight static documentation site for memoria-nox.

Live at: https://totobusnello.github.io/memoria-nox/ (once GitHub Pages is enabled)

## Stack

- **Astro 5** + **Starlight 0.32** — industry-standard docs framework
- **Pagefind** — built-in full-text search (no server required)
- **Dark/light mode** — auto-switches based on system preference
- **GitHub Pages** — static deploy via Actions

## Local development

```bash
cd docs-site
npm install
npm run dev
# Open http://localhost:4321/memoria-nox
```

Hot reload is enabled. Edits to content, styles, or config reflect immediately.

## Adding a new doc page

1. Create `src/content/docs/<section>/<slug>.md`

2. Add frontmatter at the top:
   ```yaml
   ---
   title: Your Page Title
   description: One-sentence description shown in search results and SEO.
   sidebar:
     order: 5   # controls sort order within the section
   ---
   ```

3. Add the page to the sidebar in `astro.config.mjs`:
   ```js
   { label: 'Your Page', slug: '<section>/<slug>' },
   ```

4. Add a link in `../docs/DOCS.md` under the relevant section.

## Sidebar sections

| Section | Slug prefix | Source docs |
|---|---|---|
| Getting Started | `start/` | docs/QUICKSTART.md, docs/CONFIGURATION.md |
| Architecture | `architecture/` | docs/ARCHITECTURE.md, docs/adr/, docs/VISION.md |
| Pillars | `pillars/` | Q/A/P sprint specs |
| Security | `security/` | docs/security/ |
| Operations | `operations/` | docs/ops/, docs/DEPLOY-WAVE-B.md |
| SDKs | `sdks/` | sdk/ |
| API Reference | `api/` | docs/openapi/openapi.yaml |
| Integrations | `integrations/` | integrations/ |
| Strategy | `strategy/` | docs/COMPETITIVE-POSITIONING.md, docs/cost-model.md |
| Contributing | `contributing/` | CONTRIBUTING.md, CODE_OF_CONDUCT.md, CHANGELOG.md |

## Customizing the theme

Edit `src/styles/custom.css`. The color palette is:

```css
--sl-color-accent: #00C896;  /* signature green */
--sl-color-black:  #0d1117;  /* dark background (Palette D) */
```

Logo SVGs are in `src/assets/` — replace `logo-light.svg` and `logo-dark.svg` for branding updates.

## Auto-import from source docs

The import script syncs source markdown files into Starlight-compatible format:

```bash
npm run import-docs            # import all mapped docs
npm run import-docs -- --dry-run  # preview without writing
```

Files with `# MANUAL` anywhere in their content are skipped by the importer — safe to edit by hand.

The import map is in `scripts/import-docs.ts`. Add entries there to wire new source files.

## Build

```bash
npm run build
# Output in dist/
```

The build runs Pagefind indexing automatically as a post-build step (Starlight built-in).

## Deploy

Deployment is automatic via GitHub Actions (`.github/workflows/deploy-docs.yml`) on push to `main` when files in `docs-site/` or `docs/` change.

**First-time setup** (one time, manual):
1. Go to repo Settings → Pages
2. Set Source to "GitHub Actions"
3. The next push to main will deploy automatically

The live URL will be: `https://totobusnello.github.io/memoria-nox/`

## Content structure

```
src/content/docs/
  start/
    install.md
    first-query.md
    configuration.md
  architecture/
    overview.md
    pillars.md
    schema.md
    decisions.md
  pillars/
    quality.md
    autonomy.md
    product.md
    lab.md
  security/
    threat-model.md
    openssf.md
    reporting.md
    dependency-policy.md
  operations/
    deploy.md
    disaster-recovery.md
    backup-runbook.md
    monitoring.md
  sdks/
    overview.md
    typescript.md
    python.md
    rust.md
    go.md
  api/
    openapi-spec.md
  integrations/
    overview.md
    ide.md
    mcp.md
    cli.md
  strategy/
    competitive-positioning.md
    cost-model.md
  contributing/
    how-to.md
    code-of-conduct.md
    changelog.md
```

## Troubleshooting

**Build fails with "image not found":** Check that `src/assets/logo-light.svg` and `logo-dark.svg` exist. Run `cp ../assets/readme/logo-*.svg src/assets/` if missing.

**Search not working locally:** Pagefind requires a production build. Run `npm run build && npm run preview` to test search locally.

**Sidebar item missing:** Check that the `slug` in `astro.config.mjs` matches the file path exactly (case-sensitive, no `.md` extension).

**Port conflict on dev:** Astro defaults to `4321`. Override with `npm run dev -- --port 4322`.
