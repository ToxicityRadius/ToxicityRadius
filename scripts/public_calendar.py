"""Render a contribution calendar from public repositories only."""

from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


QUERY = """query($from:DateTime!,$to:DateTime!){user(login:\"ToxicityRadius\"){contributionsCollection(from:$from,to:$to){commitContributionsByRepository(maxRepositories:100){repository{nameWithOwner isPrivate} contributions(first:100){nodes{occurredAt commitCount} pageInfo{hasNextPage}}}}}}"""


def contribution_days(data: dict) -> tuple[Counter, date, date]:
    commits = Counter()
    groups = data["data"]["user"]["contributionsCollection"]["commitContributionsByRepository"]
    for group in groups:
        if group["repository"]["isPrivate"]:
            continue
        connection = group["contributions"]
        if connection["pageInfo"]["hasNextPage"]:
            raise ValueError(f"Public contribution history is incomplete for {group['repository']['nameWithOwner']}; no images were changed.")
        for node in connection["nodes"]:
            commits[node["occurredAt"][:10]] += node["commitCount"]
    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=89)
    return commits, start, end


def render(commits: Counter, start: date, end: date, updated: date) -> str:
    ink, muted, accent = "var(--ink,#10243c)", "var(--muted,#435c75)", "var(--accent,#00798e)"
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="254" viewBox="0 0 480 254" role="img">',
        f"<title>Public repository commit calendar, {start:%d %b} to {end:%d %b %Y}, updated {updated:%d %b %Y}</title>",
        '<style>svg{--bg:#f3f8fc;--ink:#10243c;--muted:#435c75;--accent:#00798e;background:var(--bg);font-family:Segoe UI,Helvetica,Arial,sans-serif}@media(prefers-color-scheme:dark){svg{--bg:#101e31;--ink:#edf5ff;--muted:#b4c6db;--accent:#67e8f9}}.ink{fill:var(--ink)}.muted{fill:var(--muted)}.accent{fill:var(--accent)}</style>',
        '<rect width="480" height="254" rx="12" fill="var(--bg,#f3f8fc)"/>',
        f'<text class="ink" x="24" y="36" font-size="23" font-weight="650" fill="{ink}">Public commit calendar</text>',
        f'<text class="muted" x="24" y="60" font-size="14" fill="{muted}">{start:%d %b} – {end:%d %b %Y} · public repositories only</text>',
    ]
    total = sum(commits.values())
    svg.append(f'<text class="accent" x="24" y="112" font-size="40" font-weight="650" fill="{accent}">{total:,}</text>')
    svg.append(f'<text class="muted" x="145" y="108" font-size="14" fill="{muted}">public commits · past 90 days</text>')
    grid_start = start - timedelta(days=(start.weekday() + 1) % 7)
    first_column = 58
    for offset in range((end - grid_start).days + 1):
        current = grid_start + timedelta(days=offset)
        if current < start:
            continue
        count = commits[current.isoformat()]
        color = "#d6e3ed" if count == 0 else "#bae6fd" if count < 3 else "#38bdf8" if count < 8 else "#0891b2" if count < 20 else "#155e75"
        x, y = first_column + (offset // 7) * 26, 133 + (offset % 7) * 14
        svg.append(f'<g><title>{current.isoformat()}: {count} public commits</title><rect x="{x}" y="{y}" width="20" height="12" rx="2" fill="{color}"/></g>')
    svg.extend([
        f'<text class="muted" x="24" y="143" font-size="11" fill="{muted}">S</text>',
        f'<text class="muted" x="24" y="175" font-size="11" fill="{muted}">W</text>',
        f'<text class="muted" x="24" y="207" font-size="11" fill="{muted}">S</text>',
        f'<text class="muted" x="24" y="238" font-size="11" fill="{muted}">PUBLIC DATA · {updated:%d %b %Y}</text>',
        "</svg>",
    ])
    return "\n".join(svg) + "\n"


def fetch(token: str, today: date) -> tuple[Counter, date, date]:
    finish = datetime.combine(today + timedelta(days=1), time.min, timezone.utc)
    first = finish - timedelta(days=90)
    cursor = first
    commits = Counter()
    while cursor < finish:
        stop = min(cursor + timedelta(days=14), finish)
        request = Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": QUERY, "variables": {"from": cursor.isoformat(), "to": stop.isoformat()}}).encode(),
            headers={"Authorization": f"bearer {token}", "Content-Type": "application/json", "Accept": "application/vnd.github+json"},
        )
        try:
            with urlopen(request, timeout=30) as response:
                data = json.load(response)
        except (HTTPError, URLError, TimeoutError) as error:
            raise RuntimeError(f"GitHub's public contribution query failed ({type(error).__name__}); existing graphics remain intact.") from None
        if data.get("errors") or not data.get("data", {}).get("user"):
            raise RuntimeError("GitHub returned incomplete contribution data; existing graphics remain intact.")
        daily, _, _ = contribution_days(data)
        commits.update(daily)
        cursor = stop + timedelta(seconds=1)
    return commits, first.date(), today


def self_test() -> None:
    end = date(2026, 9, 26)
    groups = [
        {"repository": {"nameWithOwner": "ToxicityRadius/public", "isPrivate": False}, "contributions": {"nodes": [{"occurredAt": "2026-09-25T10:00:00Z", "commitCount": 3}], "pageInfo": {"hasNextPage": False}}},
        {"repository": {"nameWithOwner": "ToxicityRadius/private", "isPrivate": True}, "contributions": {"nodes": [{"occurredAt": "2026-09-25T10:00:00Z", "commitCount": 500}], "pageInfo": {"hasNextPage": False}}},
    ]
    data = {"data": {"user": {"contributionsCollection": {"commitContributionsByRepository": groups}}}}
    commits, start, finish = contribution_days(data)
    assert sum(commits.values()) == 3 and "2026-09-25" in commits
    svg = render(commits, start, finish, end)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg") and "3 public commits" in svg and "500" not in svg
    groups[0]["contributions"]["pageInfo"]["hasNextPage"] = True
    try:
        contribution_days(data)
    except ValueError:
        pass
    else:
        raise AssertionError("Incomplete public history must fail before publishing")
    print("PASS: public commits render, private contributions are excluded, and incomplete data fails safely.")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    elif len(sys.argv) == 2 and os.environ.get("GH_TOKEN"):
        days, first, last = fetch(os.environ["GH_TOKEN"], datetime.now(timezone.utc).date())
        Path(sys.argv[1]).write_text(render(days, first, last, datetime.now(timezone.utc).date()), encoding="utf-8")
    else:
        raise SystemExit("Usage: public_calendar.py <output.svg> with GH_TOKEN set | --self-test")
