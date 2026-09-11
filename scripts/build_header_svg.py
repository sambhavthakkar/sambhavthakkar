#!/usr/bin/env python3
"""Crisp SVG marquee — browser-interpolated, no GIF frames."""

from __future__ import annotations

from pathlib import Path

from fontTools.misc.transform import Transform
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONT400 = "/tmp/archivo/Archivo-400.ttf"
FONT500 = "/tmp/archivo/Archivo-500.ttf"
W, H = 1280, 400
BG = "#141414"
INK = "#f2f2f2"
DUR = "22s"


def draw_text(font_path: str, text: str, x: float, y: float, size: float, tracking_em: float = 0.0) -> tuple[str, float]:
    font = TTFont(font_path)
    upem = font["head"].unitsPerEm
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    scale = size / upem
    tracking = tracking_em * size
    parts: list[str] = []
    cursor = x
    for i, ch in enumerate(text):
        gname = cmap.get(ord(ch))
        if gname is None:
            cursor += size * 0.3 + tracking
            continue
        glyph = gs[gname]
        pen = SVGPathPen(gs)
        # SVG y-down: flip around baseline y
        tpen = TransformPen(pen, Transform(scale, 0, 0, -scale, cursor, y))
        glyph.draw(tpen)
        d = pen.getCommands()
        if d:
            parts.append(f'<path d="{d}" fill="{INK}"/>')
        cursor += glyph.width * scale
        if i < len(text) - 1:
            cursor += tracking
    font.close()
    return "\n".join(parts), cursor - x


def main() -> None:
    role1, _ = draw_text(FONT400, "Freelance", 52, 62, 26, -0.03)
    role2, _ = draw_text(FONT400, "Designer & Developer", 52, 92, 26, -0.03)

    loc_lines = [("Located", 13, FONT400), ("in the", 13, FONT400), ("Delhi, India", 14, FONT500)]
    loc_paths = []
    ly = 52
    for text, size, fp in loc_lines:
        paths, tw = draw_text(fp, text, 0, ly, size, -0.01)
        loc_paths.append(f'<g transform="translate({W - 52 - tw}, 0)">{paths}</g>')
        ly += 18

    copy = "Sambhav Thakkar — "
    name_y = H - 48
    name_paths, copy_w = draw_text(FONT400, copy, 0, name_y, 118, -0.045)
    copy_w = round(copy_w, 2)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">
  <rect width="{W}" height="{H}" fill="{BG}"/>
  {role1}
  {role2}
  {"".join(loc_paths)}
  <clipPath id="marquee">
    <rect x="0" y="{H - 160}" width="{W}" height="160"/>
  </clipPath>
  <g clip-path="url(#marquee)">
    <g>
      <animateTransform attributeName="transform" type="translate"
        from="46 0" to="{46 - copy_w} 0" dur="{DUR}" repeatCount="indefinite"/>
      <g>{name_paths}</g>
      <g transform="translate({copy_w}, 0)">{name_paths}</g>
    </g>
  </g>
</svg>
'''
    out = ROOT / "header.svg"
    out.write_text(svg)
    print("wrote", out, "bytes", out.stat().st_size, "copy_w", copy_w)


if __name__ == "__main__":
    main()
