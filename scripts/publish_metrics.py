"""Validate the Classic render before replacing the checked-in graphic."""

from pathlib import Path
import sys
import tempfile
import xml.etree.ElementTree as ET

NAMES = ("profile",)


def themed_svg(svg: str, dark: bool) -> str:
    text, muted, accent = ("#e6edf3", "#9da7b3", "#58a6ff") if dark else ("#1f2328", "#57606a", "#0969da")
    css = f"""svg {{ background: transparent; color: {text}; }}
    h2, h3, .repository .name span:first-child {{ color: {accent}; }}
    .field svg {{ fill: {muted}; }}
    .repository .name span:last-child, .repository .description, .repository .infos,
    .field.language.details small, .field.license.details small {{ color: {muted}; }}"""
    if dark:
        for light, shade in (("#ebedf0", "#161b22"), ("#9be9a8", "#0e4429"),
                             ("#40c463", "#006d32"), ("#30a14e", "#26a641"), ("#216e39", "#39d353")):
            svg = svg.replace(f'fill="{light}"', f'fill="{shade}"')
    return svg.rsplit("</svg>", 1)[0] + f"<style>{css}</style></svg>"


def publish(source: Path, target: Path) -> None:
    files = [source / f"{name}.svg" for name in NAMES]
    for path in files:
        root = ET.parse(path).getroot()
        if root.tag != "{http://www.w3.org/2000/svg}svg":
            raise ValueError(f"Not an SVG: {path.name}")
        if not any(node.tag.endswith(("text", "foreignObject")) for node in root.iter()):
            raise ValueError(f"Empty render: {path.name}")
        if any("error" in node.get("class", "").split() for node in root.iter()):
            raise ValueError(f"Metrics error in {path.name}")
    renders = {}
    for path in files:
        svg = path.read_text(encoding="utf-8")
        for dark in (False, True):
            name = f"{path.stem}{'-dark' if dark else ''}.svg"
            renders[name] = themed_svg(svg, dark)
            ET.fromstring(renders[name])
    target.mkdir(parents=True, exist_ok=True)
    for name, svg in renders.items():
        (target / name).write_text(svg, encoding="utf-8")


def self_test() -> None:
    with tempfile.TemporaryDirectory() as folder:
        source, target = Path(folder) / "renders", Path(folder) / "published"
        source.mkdir()
        target.mkdir()
        good = '<svg xmlns="http://www.w3.org/2000/svg"><text>Public data</text></svg>'
        for name in NAMES:
            (source / f"{name}.svg").write_text(good, encoding="utf-8")
            (target / f"{name}.svg").write_text("last good version", encoding="utf-8")
            (target / f"{name}-dark.svg").write_text("last good version", encoding="utf-8")
        for invalid in ("broken XML", '<svg xmlns="http://www.w3.org/2000/svg"/>',
                        '<svg xmlns="http://www.w3.org/2000/svg"><text class="field error">Error</text></svg>'):
            (source / "profile.svg").write_text(invalid, encoding="utf-8")
            try:
                publish(source, target)
            except (ValueError, ET.ParseError):
                pass
            else:
                raise AssertionError("Invalid renders must fail")
            assert all(p.read_text(encoding="utf-8") == "last good version" for p in target.iterdir())
        (source / "profile.svg").unlink()
        try:
            publish(source, target)
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("Missing render must fail")
        assert all(p.read_text(encoding="utf-8") == "last good version" for p in target.iterdir())
        (source / "profile.svg").write_text(good, encoding="utf-8")
        publish(source, target)
        assert all("Public data" in p.read_text(encoding="utf-8") for p in target.iterdir())
        assert "#e6edf3" in (target / "profile-dark.svg").read_text(encoding="utf-8")
        assert "#1f2328" in (target / "profile.svg").read_text(encoding="utf-8")
    print("PASS: invalid renders preserve the previous graphic; a valid render publishes.")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    elif len(sys.argv) == 3:
        publish(Path(sys.argv[1]), Path(sys.argv[2]))
    else:
        raise SystemExit("Usage: publish_metrics.py <renders> <destination> | --self-test")
