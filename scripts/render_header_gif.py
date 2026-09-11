#!/usr/bin/env python3
"""Render the hero marquee: mode-color field + smooth scrolling name."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
W, H = 1280, 400
FRAMES = 96
SECONDS = 8
FONT400 = "/tmp/archivo/Archivo-400.ttf"
FONT500 = "/tmp/archivo/Archivo-500.ttf"

# cinematic.heroSurface / heroInk — studio, rust, design, go, mobile, back
STOPS = [
    ((0x99, 0x9D, 0x9E), (0x1C, 0x1D, 0x20)),
    ((0xE0, 0x5A, 0x24), (0x1A, 0x0C, 0x08)),
    ((0xC4, 0xB5, 0xFD), (0x1A, 0x12, 0x28)),
    ((0x5E, 0xC4, 0xD8), (0x06, 0x20, 0x28)),
    ((0x5E, 0xC8, 0xF0), (0x06, 0x10, 0x18)),
    ((0x99, 0x9D, 0x9E), (0x1C, 0x1D, 0x20)),
]


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def lerp_rgb(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = t * t * (3 - 2 * t)
    return (
        int(lerp(a[0], b[0], t)),
        int(lerp(a[1], b[1], t)),
        int(lerp(a[2], b[2], t)),
    )


def palette_at(t: float) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    t = t % 1.0
    pos = t * (len(STOPS) - 1)
    i = int(pos)
    f = pos - i
    bg0, ink0 = STOPS[i]
    bg1, ink1 = STOPS[min(i + 1, len(STOPS) - 1)]
    return lerp_rgb(bg0, bg1, f), lerp_rgb(ink0, ink1, f)


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


def frame(shift: float, t: float) -> Image.Image:
    bg, ink = palette_at(t)
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)
    role = ImageFont.truetype(FONT400, 26)
    loc = ImageFont.truetype(FONT400, 13)
    loc_b = ImageFont.truetype(FONT500, 14)
    name = ImageFont.truetype(FONT400, 118)

    draw_tracked(draw, (52, 40), "Freelance", role, ink, -0.03)
    draw_tracked(draw, (52, 70), "Designer & Developer", role, ink, -0.03)

    rx = W - 52
    y = 40
    for text, font in (("Located", loc), ("in the", loc), ("Delhi, India", loc_b)):
        tw = text_w(font, text, -0.01)
        draw_tracked(draw, (rx - tw, y), text, font, ink, -0.01)
        y += 18

    copy = "Sambhav Thakkar — "
    tracking = -0.045
    copy_w = text_w(name, copy, tracking)
    name_y = H - 26 - 100
    x = 46 - (shift % copy_w)
    while x < W + 20:
        draw_tracked(draw, (x, name_y), copy, name, ink, tracking)
        x += copy_w
    return img


def quantize_all(rgb_frames: list[Image.Image]) -> list[Image.Image]:
    sample = Image.new("RGB", (W, H * 6))
    step = max(1, len(rgb_frames) // 6)
    for i in range(6):
        sample.paste(rgb_frames[min(i * step, len(rgb_frames) - 1)], (0, i * H))
    pal = sample.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    return [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in rgb_frames]


def main() -> None:
    out = ROOT / "header.gif"
    name = ImageFont.truetype(FONT400, 118)
    copy_w = text_w(name, "Sambhav Thakkar — ", -0.045)
    rgb = [frame(copy_w * i / FRAMES, i / FRAMES) for i in range(FRAMES)]
    frames = quantize_all(rgb)
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
    print("wrote", out, "bytes", out.stat().st_size, "fps", round(FRAMES / SECONDS, 2))


if __name__ == "__main__":
    main()
