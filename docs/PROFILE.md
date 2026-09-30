# Profile maintenance

The README has a concise introduction, portfolio and LinkedIn links, three
clickable public repository links below the graphic, and one
[Metrics Classic](https://github.com/lowlighter/metrics/blob/latest/source/templates/classic/README.md)
graphic. The original photo remains in `assets/profile-photo.png` but is not
shown on the profile.

## Automatic updates

The workflow renders `assets/metrics/profile.svg` daily at approximately
08:23 Asia/Manila and can also be run manually from Actions → Profile metrics.
It combines public repository statistics, a full-year isometric contribution
calendar, repository languages, notable contributions, and featured repositories.
The publisher creates light and dark SVG variants from the same validated render.
Both use transparent backgrounds, contrasting text and repository labels, and
theme-appropriate calendar colors. GitHub's theme-specific image fragments select
the matching graphic. The surrounding README uses GitHub's native theme colors.
Both graphics fill the README container width, scale with smaller screens, and have
full-size links. Project descriptions appear in the graphic without a duplicate
Selected work section.

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
