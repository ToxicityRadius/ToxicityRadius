#!/usr/bin/env python3
"""Generate a color character portrait as a GitHub-compatible SVG."""

from __future__ import annotations

import argparse
import html
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps, UnidentifiedImageError


VIEWBOX_SIZE = 700
FONT_STACK = (
    'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, '
    '"Liberation Mono", "Courier New", monospace'
)
DENSITY_RAMP = (
    "  .'`^\",:;⠁⠂⠄⡀⢀Il!i~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZ"
    "mwqpdbkhao*#MW&8%B@$░▒▓█"
)
FORBIDDEN_SVG_TOKENS = ("<image", "base64", "foreignobject", "<path", "<polygon")
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a source photo entirely as colored text glyphs in SVG."
    )
    parser.add_argument("--input", type=Path, default=Path("assets/profile-photo.png"))
    parser.add_argument(
        "--output", type=Path, default=Path("assets/character-portrait.svg")
    )
    parser.add_argument("--columns", type=int, default=180)
    parser.add_argument("--palette", choices=("realistic", "cyber"), default="realistic")
    parser.add_argument("--background", help="Six-digit hex color, such as #FFFFFF")
    parser.add_argument("--colors", type=int, default=72, help="Quantized SVG color count")
    parser.add_argument(
        "--coverage-floor",
        type=float,
        default=0.0,
        help="Minimum glyph density for non-background cells (0.0 to 1.0)",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> str:
    if not args.input.is_file():
        raise ValueError(f"Input image not found: {args.input}")
    if args.input.resolve() == args.output.resolve():
        raise ValueError("--input and --output must be different files")
    if not 80 <= args.columns <= 240:
        raise ValueError("--columns must be between 80 and 240")
    if not 16 <= args.colors <= 256:
        raise ValueError("--colors must be between 16 and 256")
    if not 0.0 <= args.coverage_floor <= 1.0:
        raise ValueError("--coverage-floor must be between 0.0 and 1.0")
    background = args.background or ("#FFFFFF" if args.palette == "realistic" else "#07111F")
    if not HEX_COLOR.fullmatch(background):
        raise ValueError("--background must be a six-digit hex color")
    return background.upper()


def load_square(path: Path) -> Image.Image:
    try:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError(f"Unable to read input image: {path}") from exc

    width, height = image.size
    if width == height:
        return image

    # ponytail: padding preserves the entire ID-photo composition; add landmark
    # detection only if this renderer must support varied poses or loose crops.
    side = max(width, height)
    corners = (
        image.getpixel((0, 0)),
        image.getpixel((width - 1, 0)),
        image.getpixel((0, height - 1)),
        image.getpixel((width - 1, height - 1)),
    )
    background = tuple(sum(pixel[channel] for pixel in corners) // 4 for channel in range(3))
    square = Image.new("RGB", (side, side), background)
    square.paste(image, ((side - width) // 2, (side - height) // 2))
    return square


def grid_geometry(columns: int) -> tuple[int, float, float, float]:
    cell_width = VIEWBOX_SIZE / columns
    font_size = cell_width / 0.60
    line_height = font_size * 0.96
    rows = max(1, round(VIEWBOX_SIZE / line_height))
    line_height = VIEWBOX_SIZE / rows
    return rows, cell_width, font_size, line_height


def feature_weight(x: float, y: float) -> float:
    """Weight edges in the expected regions of a centered, front-facing ID photo."""
    weight = 1.0
    regions = (
        (0.22, 0.78, 0.06, 0.34, 1.18),  # hair and hairline
        (0.22, 0.47, 0.29, 0.43, 1.55),  # left eyebrow and eye
        (0.53, 0.78, 0.29, 0.43, 1.55),  # right eyebrow and eye
        (0.41, 0.59, 0.36, 0.59, 1.45),  # nose
        (0.34, 0.66, 0.53, 0.66, 1.40),  # lips
        (0.20, 0.80, 0.38, 0.72, 1.22),  # jawline and ears
        (0.20, 0.80, 0.68, 0.88, 1.30),  # collar
        (0.42, 0.58, 0.72, 1.00, 1.50),  # necktie
        (0.05, 0.95, 0.67, 1.00, 1.18),  # coat edges
    )
    for x0, x1, y0, y1, boost in regions:
        if x0 <= x <= x1 and y0 <= y <= y1:
            weight = max(weight, boost)
    return weight


def edge_metrics(pixels: list[int], width: int, height: int, x: int, y: int) -> tuple[float, float, float]:
    def value(px: int, py: int) -> int:
        return pixels[min(height - 1, max(0, py)) * width + min(width - 1, max(0, px))]

    left = value(x - 1, y)
    right = value(x + 1, y)
    top = value(x, y - 1)
    bottom = value(x, y + 1)
    gx = right - left
    gy = bottom - top
    neighborhood = [value(x + dx, y + dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
    return gx, gy, max(neighborhood) - min(neighborhood)


def directional_character(gx: float, gy: float) -> str:
    if abs(gx) > abs(gy) * 1.8:
        return "│"
    if abs(gy) > abs(gx) * 1.8:
        return "─"
    return "╱" if gx * gy > 0 else "╲"


def choose_character(
    luminance: int,
    gx: float,
    gy: float,
    local_contrast: float,
    weight: float,
    coverage_floor: float,
) -> str:
    edge = min(1.0, math.hypot(gx, gy) / 210.0)
    contrast = min(1.0, local_contrast / 105.0)
    darkness = 1.0 - luminance / 255.0

    if luminance >= 249 and edge < 0.08 and contrast < 0.08:
        return " "
    if edge * weight > 0.48 and 0.03 < darkness < 0.94:
        if coverage_floor >= 0.95:
            return "▓"
        return directional_character(gx, gy)

    density = min(1.0, darkness * 0.86 + contrast * 0.07 + edge * weight * 0.10)
    if luminance < 245:
        density = max(density, coverage_floor)
    return DENSITY_RAMP[round(density * (len(DENSITY_RAMP) - 1))]


def cyber_color(rgb: tuple[int, int, int], x: float) -> tuple[int, int, int]:
    luminance = (2126 * rgb[0] + 7152 * rgb[1] + 722 * rgb[2]) / 10000
    if x < 0.5:
        t = x * 2
        left, right = (124, 58, 237), (34, 211, 238)
    else:
        t = (x - 0.5) * 2
        left, right = (34, 211, 238), (16, 185, 129)
    accent = tuple(round(left[i] + (right[i] - left[i]) * t) for i in range(3))
    brightness = 0.58 + 0.56 * (luminance / 255.0)
    return tuple(min(255, round(channel * brightness + 10)) for channel in accent)


def realistic_color(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Compensate for the white gaps inside glyphs while preserving source hue."""
    luminance = (2126 * rgb[0] + 7152 * rgb[1] + 722 * rgb[2]) / 10000
    factor = 0.72 + 0.18 * (1.0 - luminance / 255.0)
    return tuple(round(channel * factor) for channel in rgb)


def flat_pixels(image: Image.Image) -> list[int] | list[tuple[int, int, int]]:
    if hasattr(image, "get_flattened_data"):
        return list(image.get_flattened_data())
    return list(image.getdata())


def quantized_colors(
    sampled: Image.Image,
    palette: str,
    color_count: int,
    coverage_floor: float,
) -> Image.Image:
    if palette == "cyber":
        width, height = sampled.size
        mapped = Image.new("RGB", sampled.size)
        mapped.putdata([
            cyber_color(rgb, (index % width) / max(1, width - 1))
            for index, rgb in enumerate(flat_pixels(sampled))
        ])
    elif coverage_floor >= 0.95:
        mapped = sampled
    else:
        mapped = Image.new("RGB", sampled.size)
        mapped.putdata([realistic_color(rgb) for rgb in flat_pixels(sampled)])
    return mapped.quantize(
        colors=color_count,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    ).convert("RGB")


def build_grid(
    image: Image.Image,
    columns: int,
    palette: str,
    color_count: int,
    coverage_floor: float,
) -> tuple[list[list[str]], list[list[str]], float, float, float]:
    rows, cell_width, font_size, line_height = grid_geometry(columns)
    detail = ImageEnhance.Contrast(image).enhance(1.12)
    detail = detail.filter(
        ImageFilter.UnsharpMask(radius=1.1, percent=80, threshold=4)
    )
    sampled = detail.resize((columns, rows), Image.Resampling.LANCZOS)
    grayscale = ImageOps.grayscale(image)
    grayscale = ImageEnhance.Contrast(grayscale).enhance(1.08)
    grayscale = grayscale.filter(ImageFilter.UnsharpMask(radius=1.1, percent=75, threshold=3))
    grayscale = grayscale.resize((columns, rows), Image.Resampling.LANCZOS)
    luminance_pixels = flat_pixels(grayscale)
    colors = quantized_colors(sampled, palette, color_count, coverage_floor)
    color_pixels = flat_pixels(colors)

    glyph_rows: list[list[str]] = []
    color_rows: list[list[str]] = []
    for y in range(rows):
        glyph_row: list[str] = []
        color_row: list[str] = []
        for x in range(columns):
            index = y * columns + x
            gx, gy, contrast = edge_metrics(luminance_pixels, columns, rows, x, y)
            weight = feature_weight(x / max(1, columns - 1), y / max(1, rows - 1))
            glyph = choose_character(
                luminance_pixels[index],
                gx,
                gy,
                contrast,
                weight,
                coverage_floor,
            )
            glyph_row.append(glyph)
            red, green, blue = color_pixels[index]
            if glyph == "▓" and coverage_floor >= 0.95:
                edge_factor = 0.68 if palette == "cyber" else 0.72
                red, green, blue = (
                    round(red * edge_factor),
                    round(green * edge_factor),
                    round(blue * edge_factor),
                )
            elif glyph in "│─╱╲":
                edge_factor = 0.72 if palette == "cyber" else 0.55
                red, green, blue = (
                    round(red * edge_factor),
                    round(green * edge_factor),
                    round(blue * edge_factor),
                )
            color_row.append(f"#{red:02X}{green:02X}{blue:02X}")
        glyph_rows.append(glyph_row)
        color_rows.append(color_row)
    return glyph_rows, color_rows, cell_width, font_size, line_height


def row_runs(glyphs: list[str], colors: list[str]) -> list[tuple[int, str, str]]:
    runs: list[tuple[int, str, str]] = []
    start = 0
    while start < len(glyphs):
        if glyphs[start] == " ":
            start += 1
            continue
        color = colors[start]
        end = start + 1
        while end < len(glyphs) and glyphs[end] != " " and colors[end] == color:
            end += 1
        runs.append((start, color, "".join(glyphs[start:end])))
        start = end
    return runs


def render_svg(
    glyph_rows: list[list[str]],
    color_rows: list[list[str]],
    cell_width: float,
    font_size: float,
    line_height: float,
    background: str,
    palette: str,
) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{VIEWBOX_SIZE}" height="{VIEWBOX_SIZE}" viewBox="0 0 {VIEWBOX_SIZE} {VIEWBOX_SIZE}" role="img" aria-labelledby="title desc">',
        f"  <title id=\"title\">Dexter Soriano {palette} character portrait</title>",
        "  <desc id=\"desc\">A front-facing formal portrait rendered entirely with colored text glyphs.</desc>",
        f'  <rect width="{VIEWBOX_SIZE}" height="{VIEWBOX_SIZE}" fill="{background}"/>',
        f"  <g id=\"portrait-glyphs\" font-family='{FONT_STACK}' font-size=\"{font_size:.3f}\" font-weight=\"600\">",
    ]

    baseline = font_size * 0.82
    for row_index, (glyphs, colors) in enumerate(zip(glyph_rows, color_rows)):
        runs = row_runs(glyphs, colors)
        if not runs:
            continue
        y = baseline + row_index * line_height
        lines.append(f'    <text y="{y:.3f}">')
        for start, color, text in runs:
            escaped = html.escape(text, quote=False)
            x = start * cell_width
            width = len(text) * cell_width
            lines.append(
                f'      <tspan x="{x:.3f}" fill="{color}" textLength="{width:.3f}" lengthAdjust="spacingAndGlyphs">{escaped}</tspan>'
            )
        lines.append("    </text>")
    lines.extend(("  </g>", "</svg>", ""))
    return "\n".join(lines)


def validate_svg(svg: str) -> None:
    lowered = svg.lower()
    for token in FORBIDDEN_SVG_TOKENS:
        if token in lowered:
            raise ValueError(f"Generated SVG contains forbidden token: {token}")
    root = ET.fromstring(svg)
    namespace = {"svg": "http://www.w3.org/2000/svg"}
    if len(root.findall(".//svg:text", namespace)) < 30:
        raise ValueError("Generated SVG does not contain enough character rows")
    if not root.findall(".//svg:tspan", namespace):
        raise ValueError("Generated SVG contains no visible glyph runs")


def main() -> int:
    args = parse_args()
    try:
        background = validate_args(args)
        image = load_square(args.input)
        grid = build_grid(
            image,
            args.columns,
            args.palette,
            args.colors,
            args.coverage_floor,
        )
        svg = render_svg(*grid, background, args.palette)
        validate_svg(svg)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(svg, encoding="utf-8", newline="\n")
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(
        f"Generated {args.output} ({args.columns} columns, {len(grid[0])} rows, {args.palette} palette)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
