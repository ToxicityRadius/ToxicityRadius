# Profile maintenance

The README contains a responsive navy/cyan introduction, the original profile photo,
three verified public project links, and five public-data graphics.

## Enable automatic updates

1. Create a **classic personal access token with no scopes** in GitHub Settings →
   Developer settings → Personal access tokens. Give it a description and expiry
   date that you can recognize later. No private repository access is needed.
2. Save it as `METRICS_TOKEN` in this repository's Settings → Secrets and variables
   → Actions. Never put it in a file, commit, issue, or chat.
3. On your GitHub profile, leave **Contribution settings → Private contributions**
   disabled. Even a scope-less token can receive hidden contribution totals when
   that setting is enabled; the workflow checks for them before rendering.
4. After this workflow is on `main`, open Actions → **Profile metrics** → **Run workflow**.
   Confirm that `validate` and `render` pass and that the bot commits five SVGs.

The schedule is daily at approximately **08:23 Asia/Manila**. GitHub can delay or
disable scheduled workflows in inactive repositories; a manual run is available.
An expired/missing token fails with instructions while retaining the last images.

`METRICS_TOKEN` reads public account data. GitHub's automatic `GITHUB_TOKEN`, with
`contents: write`, commits the output. Do not give the personal token extra scopes.

## Existing snapshots and future renders

The initial graphics are dated **26 September 2026** and use GitHub public repository,
language, event, and contribution data. They are real snapshots, not sample stats.
The snapshot collector excluded every repository marked private before using or
saving contribution data. Language shares sum language bytes in public, non-fork
repositories. The initial calendar and contribution totals cover the past 90 days;
the graph labels that range. Activity shows recent public events, excluding this
profile repository so graphic refreshes do not dominate the list.

Once enabled, lowlighter/Metrics replaces these snapshots with its activity,
languages, notable contributions, featured repositories, and full-year isometric
calendar renders. Each includes generation metadata. Counts and time ranges may
differ from the initial snapshots; neither language shares nor commit counts are
presented as a measure of proficiency.

All five images render into `/metrics_renders` before any tracked image is replaced.
Plugin failures are fatal. `scripts/publish_metrics.py` checks the complete set for
missing, malformed, empty, and error renders; only a successful full set is committed.
Push triggers watch workflow/configuration sources, not the generated SVG paths.
Updates are serialized and use ordinary pushes; no force push is performed.

## Edit and verify

- Edit profile copy and links in `README.md`.
- Edit the self-contained SVG hero sources `dark.svg`, `light.svg`, and the mobile
  variants in `assets/`. Each embeds the unchanged `assets/profile-photo.png`.
- Edit generated card colors in `assets/metrics.css`.
- Change plugins, featured repositories, or the schedule in `.github/workflows/metrics.yml`.

Run the focused failure-preservation check locally:

```powershell
python scripts/publish_metrics.py --self-test
```

Preview the README on GitHub in both themes at desktop and phone widths. Confirm
that the mobile hero is selected, cards wrap without horizontal scrolling, images
load, and project/contact links resolve. After the first authenticated Metrics run,
repeat that visual check because upstream plugin layouts differ from the snapshots.

Upstream references: [Action setup](https://github.com/lowlighter/metrics/blob/latest/.github/readme/partials/documentation/setup/action.md)
and [plugin documentation](https://github.com/lowlighter/metrics/tree/latest/source/plugins).
