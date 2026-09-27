# Profile maintenance

The README has a plain introduction, three public project links, and one
[Metrics Classic](https://github.com/lowlighter/metrics/blob/latest/source/templates/classic/README.md)
graphic. The original photo remains in `assets/profile-photo.png` but is not
shown on the profile.

## Automatic updates

The workflow renders `assets/metrics/profile.svg` daily at approximately
08:23 Asia/Manila and can also be run manually from Actions → Profile metrics.
It combines a public account overview, repository languages, notable
contributions, and featured repositories. It does not render activity or a
contribution calendar.
The graphic uses a white background so Classic's default text stays readable
when GitHub is in dark mode.

The repository secret `METRICS_TOKEN` must be a classic personal access token
with no scopes. It reads public GitHub data only. The workflow's separate
`GITHUB_TOKEN` commits the SVG with `contents: write`. Never put either token in
a file, commit, issue, or chat.

The workflow validates the completed SVG before replacing the tracked graphic.
If the token expires, rendering fails, or the output is malformed, the last
committed graphic remains available. The SVG is excluded from push triggers so
an update does not start another workflow run.

## Edit and verify

- Edit the introduction and project links in `README.md`.
- Change the Classic template options, featured repositories, or schedule in
  `.github/workflows/metrics.yml`.
- Run `python scripts/publish_metrics.py --self-test` to check that failed
  renders preserve the previous graphic.
- After workflow changes, run Profile metrics manually and confirm that both
  jobs pass and the generated SVG renders in GitHub's light and dark themes at
  desktop and phone widths. Check the project and contact links too.

The action is configured using [Metrics' GitHub Action documentation](https://github.com/lowlighter/metrics/blob/latest/.github/readme/partials/documentation/setup/action.md).
