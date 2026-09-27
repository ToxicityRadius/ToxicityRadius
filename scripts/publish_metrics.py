"""Validate the Classic render before replacing the checked-in graphic."""

from pathlib import Path
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

NAMES = ("profile",)


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
    target.mkdir(parents=True, exist_ok=True)
    for path in files:
        shutil.copyfile(path, target / path.name)


def self_test() -> None:
    with tempfile.TemporaryDirectory() as folder:
        source, target = Path(folder) / "renders", Path(folder) / "published"
        source.mkdir()
        target.mkdir()
        good = '<svg xmlns="http://www.w3.org/2000/svg"><text>Public data</text></svg>'
        for name in NAMES:
            (source / f"{name}.svg").write_text(good, encoding="utf-8")
            (target / f"{name}.svg").write_text("last good version", encoding="utf-8")
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
        assert all(p.read_text(encoding="utf-8") == good for p in target.iterdir())
    print("PASS: invalid renders preserve the previous graphic; a valid render publishes.")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    elif len(sys.argv) == 3:
        publish(Path(sys.argv[1]), Path(sys.argv[2]))
    else:
        raise SystemExit("Usage: publish_metrics.py <renders> <destination> | --self-test")
