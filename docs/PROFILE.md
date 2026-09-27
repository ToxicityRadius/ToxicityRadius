# Profile maintenance

The README has a plain introduction, three public project links, and one
[Metrics Classic](https://github.com/lowlighter/metrics/blob/latest/source/templates/classic/README.md)
graphic. GitHub selects its light or dark version from the viewer's theme. The
original photo remains in `assets/profile-photo.png` but is not shown.

## Automatic updates

The workflow renders `assets/metrics/profile-light.svg` and
`assets/metrics/profile-dark.svg` daily at approximately
08:23 Asia/Manila and can also be run manually from Actions → Profile metrics.
It combines a public account overview, repository languages, notable
contributions, featured repositories, and a six-month contribution calendar.
Each graphic uses theme-matched colors for readable labels and text.

The repository secret `METRICS_TOKEN` must be a classic personal access token
with no scopes. It reads public GitHub data only. The workflow's separate
`GITHUB_TOKEN` commits the SVG with `contents: write`. Never put either token in
a file, commit, issue, or chat.

The workflow validates both completed SVGs before replacing either tracked
graphic.
If the token expires, rendering fails, or the output is malformed, the last
committed graphic remains available. The SVG is excluded from push triggers so
an update does not start another workflow run.

## Edit and verify

- Edit the introduction and project links in `README.md`.
- Change the Classic template options, featured repositories, or schedule in
  `.github/workflows/metrics.yml`.
- Run `python3 scripts/publish_metrics.py --self-test` to check that a failed
  second render preserves both previous graphics.
- After workflow changes, run Profile metrics manually and confirm that both
  jobs pass and the generated SVG renders in GitHub's light and dark themes at
  desktop and phone widths. Check the project and contact links too.

The action is configured using [Metrics' GitHub Action documentation](https://github.com/lowlighter/metrics/blob/latest/.github/readme/partials/documentation/setup/action.md).
