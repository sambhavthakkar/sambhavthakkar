#!/usr/bin/env python3
"""Grayscale hero marquee — black field, off-white type."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H = 1280, 400
FRAMES = 96
SECONDS = 8
FONT400 = "/tmp/archivo/Archivo-400.ttf"
FONT500 = "/tmp/archivo/Archivo-500.ttf"
BG = (0x14, 0x14, 0x14)
INK = (0xF2, 0xF2, 0xF2)


def text_w(font: ImageFont.FreeTypeFont, text: str, tracking: float = 0.0) -> float:
    extra = tracking * font.size
    width = 0.0
    for i, ch in enumerate(text):
        width += font.getlength(ch)
        if i < len(text) - 1:
            width += extra
    return width


def draw_tracked(draw, xy, text, font, fill, tracking=0.0):
    x, y = xy
    extra = tracking * font.size
    for i, ch in enumerate(text):
        draw.text((x, y), ch, font=font, fill=fill)
        x += font.getlength(ch) + extra
    return x


def frame(shift: float) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    role = ImageFont.truetype(FONT400, 26)
    loc = ImageFont.truetype(FONT400, 13)
    loc_b = ImageFont.truetype(FONT500, 14)
    name = ImageFont.truetype(FONT400, 118)

    draw_tracked(draw, (52, 40), "Freelance", role, INK, -0.03)
    draw_tracked(draw, (52, 70), "Designer & Developer", role, INK, -0.03)

    rx = W - 52
    y = 40
    for text, font in (("Located", loc), ("in the", loc), ("Delhi, India", loc_b)):
        tw = text_w(font, text, -0.01)
        draw_tracked(draw, (rx - tw, y), text, font, INK, -0.01)
        y += 18

    copy = "Sambhav Thakkar — "
    tracking = -0.045
    copy_w = text_w(name, copy, tracking)
    name_y = H - 26 - 100
    x = 46 - (shift % copy_w)
    while x < W + 20:
        draw_tracked(draw, (x, name_y), copy, name, INK, tracking)
        x += copy_w
    return img


def main() -> None:
    out = ROOT / "header.gif"
    name = ImageFont.truetype(FONT400, 118)
    copy_w = text_w(name, "Sambhav Thakkar — ", -0.045)
    rgb = [frame(copy_w * i / FRAMES) for i in range(FRAMES)]
    pal = rgb[0].quantize(colors=24, method=Image.Quantize.MEDIANCUT)
    frames = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in rgb]
    duration = int(round(1000 * SECONDS / FRAMES))
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print("wrote", out, "bytes", out.stat().st_size)


if __name__ == "__main__":
    main()
