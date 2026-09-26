"""Render recent public GitHub events without relying on optional event fields."""

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET


EVENT_NAMES = {
    "PushEvent": "Pushed commits",
    "PullRequestEvent": "Worked on a pull request",
    "IssuesEvent": "Updated an issue",
    "IssueCommentEvent": "Commented on an issue",
    "WatchEvent": "Starred a repository",
    "ForkEvent": "Forked a repository",
    "CreateEvent": "Created a branch or repository",
    "ReleaseEvent": "Published a release",
}


def render(events: list[dict], updated: datetime) -> str:
    rows = []
    for event in events:
        repo = event.get("repo", {}).get("name")
        created = event.get("created_at")
        label = EVENT_NAMES.get(event.get("type"))
        if not repo or repo.lower() == "toxicityradius/toxicityradius" or not created or not label:
            continue
        try:
            when = datetime.fromisoformat(created.replace("Z", "+00:00")).strftime("%d %b")
        except ValueError:
            continue
        rows.append((label, repo, when))
        if len(rows) == 5:
            break

    title = "Public activity"
    subtitle = f"Recent public events · updated {updated:%d %b %Y}"
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="254" viewBox="0 0 480 254" role="img">',
        f"<title>{escape(title)} — {escape(subtitle)}</title>",
        '<style>svg{--bg:#f3f8fc;--ink:#10243c;--muted:#435c75;--accent:#00798e;background:var(--bg);font-family:Segoe UI,Helvetica,Arial,sans-serif}@media(prefers-color-scheme:dark){svg{--bg:#101e31;--ink:#edf5ff;--muted:#b4c6db;--accent:#67e8f9}}.ink{fill:var(--ink)}.muted{fill:var(--muted)}.accent{fill:var(--accent)}</style>',
        '<rect width="480" height="254" rx="12" fill="var(--bg,#f3f8fc)"/>',
        f'<text class="ink" x="24" y="36" font-size="23" font-weight="650">{escape(title)}</text>',
        f'<text class="muted" x="24" y="60" font-size="14">{escape(subtitle)}</text>',
    ]
    if not rows:
        svg.append('<text class="muted" x="24" y="112" font-size="15">No recent public events to display.</text>')
    for index, (label, repo, when) in enumerate(rows):
        y = 99 + index * 29
        svg.extend([
            f'<circle cx="30" cy="{y - 4}" r="4" fill="var(--accent,#00798e)"/>',
            f'<text class="ink" x="44" y="{y}" font-size="14">{escape(label)}</text>',
            f'<text class="muted" x="44" y="{y + 15}" font-size="12">{escape(repo)}</text>',
            f'<text class="muted" x="442" y="{y}" font-size="12" text-anchor="end">{escape(when)}</text>',
        ])
    svg.extend([
        f'<text class="muted" x="24" y="238" font-size="11">PUBLIC EVENTS · {updated:%d %b %Y}</text>',
        "</svg>",
    ])
    return "\n".join(svg) + "\n"


def fetch(token: str) -> list[dict]:
    request = Request(
        "https://api.github.com/users/ToxicityRadius/events/public?per_page=100",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )
    try:
        with urlopen(request, timeout=30) as response:
            events = json.load(response)
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(f"GitHub's public activity query failed ({type(error).__name__}); existing graphics remain intact.") from None
    if not isinstance(events, list):
        raise RuntimeError("GitHub returned invalid public activity; existing graphics remain intact.")
    return events


def self_test() -> None:
    events = [
        {"type": "PushEvent", "repo": {"name": "ToxicityRadius/demo<&"}, "created_at": "2026-09-25T10:00:00Z"},
        {"type": "WatchEvent", "repo": {"name": "ToxicityRadius/ToxicityRadius"}, "created_at": "2026-09-25T10:00:00Z"},
        {"type": "IssuesEvent", "created_at": "2026-09-25T10:00:00Z"},
    ]
    svg = render(events, datetime(2026, 9, 26, tzinfo=timezone.utc))
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg") and "Pushed commits" in svg and "ToxicityRadius/demo&lt;&amp;" in svg
    assert "ToxicityRadius/ToxicityRadius" not in svg and "Updated an issue" not in svg
    print("PASS: public activity safely renders valid public events and skips missing fields/profile-repository events.")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    elif len(sys.argv) == 2 and os.environ.get("GH_TOKEN"):
        Path(sys.argv[1]).write_text(render(fetch(os.environ["GH_TOKEN"]), datetime.now(timezone.utc)), encoding="utf-8")
    else:
        raise SystemExit("Usage: public_activity.py <output.svg> with GH_TOKEN set | --self-test")
