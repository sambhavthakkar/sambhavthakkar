#!/usr/bin/env python3
"""Refresh GitHub profile stat SVGs. Safe to run locally or in Actions.

Pipeline:
  1. Fetch upstream cards with retries. On failure keep the previous SVG and
     exit 0, so a flaky card service never blanks the profile or reddens CI.
  2. Only when card content actually changed: bump the ?v= embed versions in
     README.md (busts GitHub Camo) and rewrite the <!--STATS_UPDATED--> stamp.
  3. Save the cache only on an actual change, so fallback runs make no commits.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER = "sambhavthakkar"
README_PATH = ROOT / "README.md"
CACHE_PATH = ROOT / ".stats-cache.json"

# ink / paper — no hue
BG = "1C1D20"
ACCENT = "F2F2F2"
MUTED = "999A9E"
INK = "F2F2F2"
LINE = "2E2F32"

STATS_URL = (
    f"https://github-readme-stats.zohan.tech/api?username={USER}"
    "&show_icons=true&hide_border=true"
    f"&bg_color={BG}&title_color={INK}&icon_color={ACCENT}"
    f"&text_color={MUTED}&ring_color={ACCENT}&hide=stars"
)
STREAK_URL = (
    f"https://streak-stats.demolab.com/?user={USER}"
    f"&background={BG}&border={BG}&ring={ACCENT}&fire={ACCENT}"
    f"&currStreakLabel={INK}&sideLabels={MUTED}&currStreakNum={INK}"
    f"&sideNums={MUTED}&dates={MUTED}&stroke={LINE}"
)
CHART_URL = f"https://ghchart.rshah.org/{ACCENT.lower()}/{USER}"

EMBEDDED = ("stats-strip.svg", "github-stats.svg", "streak.svg", "contrib.svg")
LAST_REFRESH_KEY = "last_refresh"
EMBED_VERSION_KEY = "embed_version"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "sambhav-profile-stats"})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read().decode("utf-8", errors="replace")


def fetch_with_retry(url: str, attempts: int = 3) -> str | None:
    """Retry flaky upstreams. None beats a red run: caller keeps the old file."""
    for attempt in range(attempts):
        try:
            return fetch(url)
        except Exception as exc:  # upstream cards flake; tolerate everything
            print(f"  fetch failed ({exc}); attempt {attempt + 1}/{attempts}: {url}")
            if attempt < attempts - 1:
                time.sleep(5 * (attempt + 1))
    return None


def load_cache() -> dict[str, object]:
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_cache(version: int) -> None:
    payload = {
        LAST_REFRESH_KEY: datetime.now(timezone.utc).isoformat(timespec="seconds"),
        EMBED_VERSION_KEY: version,
    }
    CACHE_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _freeze_style(style: str) -> str:
    style = re.sub(r"opacity\s*:\s*0(\.\d+)?", "opacity: 1", style)
    style = re.sub(r"animation\s*:[^;]+", "animation: none", style)
    return style


def freeze(svg: str) -> str:
    svg = re.sub(
        r"style=(['\"])(.*?)\1",
        lambda m: f"style={m.group(1)}{_freeze_style(m.group(2))}{m.group(1)}",
        svg,
        flags=re.S,
    )
    svg = re.sub(r"(\.stagger\s*\{[^}]*?)opacity:\s*0", r"\1opacity: 1", svg)
    svg = re.sub(r"(0%\s*\{\s*opacity:\s*)0", r"\g<1>1", svg)
    return svg


def theme(svg: str) -> str:
    svg = freeze(svg)
    for old, new in (
        ("#C8C9CC", f"#{MUTED}"),
        ("#c8c9cc", f"#{MUTED.lower()}"),
        ("#455CE9", f"#{ACCENT}"),
        ("#455ce9", f"#{ACCENT.lower()}"),
    ):
        svg = svg.replace(old, new)
    return svg


def visible_text(svg: str) -> list[str]:
    return [t.strip() for t in re.findall(r">([^<>]+)<", svg) if t.strip()]


def parse_stats(svg: str) -> dict[str, str]:
    desc = re.search(r"<desc[^>]*>(.*?)</desc>", svg, re.S)
    title = re.search(r"<title[^>]*>(.*?)</title>", svg, re.S)
    blob = (desc.group(1) if desc else "") + " " + (title.group(1) if title else "")
    commits = re.search(r"Total Commits[^:]*:\s*(\d[\d,]*)", blob)
    rank = re.search(r"Rank:\s*([A-Z+]+)", blob)
    return {
        "commits": commits.group(1).rstrip(",") if commits else "—",
        "rank": rank.group(1) if rank else "—",
    }


def parse_streak(svg: str) -> dict[str, str]:
    texts = [
        re.sub(r"\s+", " ", t).strip()
        for t in re.findall(r"<text[^>]*>(.*?)</text>", svg, re.S)
        if re.sub(r"\s+", " ", t).strip()
    ]
    nums = [t for t in texts if re.fullmatch(r"[\d,]+", t)]
    data = {"contributions": "—", "longest": "—", "current": "—"}
    if len(nums) >= 3:
        data["contributions"] = nums[0]
        data["current"] = nums[1]
        data["longest"] = nums[2]
    return data


def parse_or_prev(
    raw: str | None, path: Path, parser: Callable[[str], dict[str, str]]
) -> dict[str, str]:
    """Parse fresh content, or the frozen file when the upstream call failed."""
    if raw:
        return parser(raw)
    if path.exists():
        return parser(path.read_text(encoding="utf-8", errors="replace"))
    return {}


def write_if_differs(path: Path, content: str) -> bool:
    try:
        if path.read_text(encoding="utf-8") == content:
            return False
    except OSError:
        pass
    path.write_text(content, encoding="utf-8")
    return True


def stamp_readme(version: int) -> None:
    """Bump ?v= on embedded stat SVGs (busts GitHub Camo) and rewrite the
    freshness marker. Indentation and surrounding tags are preserved."""
    if not README_PATH.exists():
        return
    text = README_PATH.read_text(encoding="utf-8")
    for name in EMBEDDED:
        text = re.sub(rf"{re.escape(name)}(\?v=\d+)?", f"{name}?v={version}", text)
    stamp = f"Updated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC <!--STATS_UPDATED-->"
    text = re.sub(r"[^\n<]*<!--STATS_UPDATED-->", stamp, text)
    README_PATH.write_text(text, encoding="utf-8")


def strip_svg(commits: str, contributions: str, longest: str, rank: str) -> str:
    cells = [
        ("Contributions", contributions, "private graph included", True),
        ("Commits · 2026", commits, "public surface", False),
        ("Longest streak", longest, "days in a row", False),
        ("GitHub rank", rank, "live card", False),
    ]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 900 168" preserveAspectRatio="xMidYMid meet">',
        f'<rect width="900" height="168" fill="#{BG.lower()}"/>',
        "<style>",
        f"  .label {{ font: 500 11px 'Segoe UI', Ubuntu, sans-serif; fill: #{MUTED.lower()}; letter-spacing: 1.4px; }}",
        "  .value { font: 400 36px 'Segoe UI', Ubuntu, sans-serif; }",
        f"  .hint {{ font: 400 11px 'Segoe UI', Ubuntu, sans-serif; fill: #{MUTED.lower()}; }}",
        "</style>",
    ]
    gap, w, h, x0, y0 = 12, 210, 140, 12, 14
    for i, (label, value, hint, accent) in enumerate(cells):
        x = x0 + i * (w + gap)
        fill = f"#{ACCENT.lower()}" if accent else f"#{INK.lower()}"
        parts += [
            f'<rect x="{x}" y="{y0}" width="{w}" height="{h}" rx="16" fill="none" stroke="#{LINE.lower()}"/>',
            f'<text class="label" x="{x + 18}" y="{y0 + 32}">{label.upper()}</text>',
            f'<text class="value" x="{x + 18}" y="{y0 + 88}" fill="{fill}">{value}</text>',
            f'<text class="hint" x="{x + 18}" y="{y0 + 114}">{hint}</text>',
        ]
    parts.append("</svg>")
    return "\n".join(parts)


def _hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def _mix(bg: str, accent: str, t: float) -> str:
    a, b = _hex_rgb(bg), _hex_rgb(accent)
    return _rgb_hex(tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3)))  # type: ignore[return-value]


def wrap_chart(raw: str) -> str:
    # Site contribution log: mix(background, brand) at 0.1 / 0.28 / 0.5 / 0.74 / brand
    levels = [
        _mix(f"#{BG}", f"#{ACCENT}", 0.10),
        _mix(f"#{BG}", f"#{ACCENT}", 0.28),
        _mix(f"#{BG}", f"#{ACCENT}", 0.50),
        _mix(f"#{BG}", f"#{ACCENT}", 0.74),
        f"#{ACCENT.lower()}",
    ]
    for score in range(5):
        raw = re.sub(
            rf'data-score="{score}"([^>]*?)fill:#[0-9A-Fa-f]{{6}}',
            f'data-score="{score}"\\1fill:{levels[score]}',
            raw,
        )
        raw = re.sub(
            rf'fill:#[0-9A-Fa-f]{{6}}([^>]*?)data-score="{score}"',
            f'fill:{levels[score]}\\1data-score="{score}"',
            raw,
        )
    raw = raw.replace("fill:#767676", f"fill:#{MUTED.lower()}")
    inner = "<svg" + raw.split("<svg", 1)[1]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="100%" '
        'viewBox="0 0 743 156" preserveAspectRatio="xMidYMid meet">\n'
        f'  <rect width="743" height="156" rx="12" fill="#{BG.lower()}"/>\n'
        '  <g transform="translate(40,24)">\n'
        f"    {inner}\n"
        "  </g>\n"
        "</svg>\n"
    )


def write_summary(
    prev_s: dict[str, str], prev_k: dict[str, str], s: dict[str, str], k: dict[str, str]
) -> None:
    rows = [
        ("Commits 2026", prev_s.get("commits", "—"), s.get("commits", "—")),
        ("Contributions", prev_k.get("contributions", "—"), k.get("contributions", "—")),
        ("Longest streak", prev_k.get("longest", "—"), k.get("longest", "—")),
        ("Current streak", prev_k.get("current", "—"), k.get("current", "—")),
        ("GitHub rank", prev_s.get("rank", "—"), s.get("rank", "—")),
    ]
    for metric, before, after in rows:
        print(f"  {metric}: {before} -> {after}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        table = ["| metric | before | after |", "| --- | --- | --- |"]
        table += [f"| {m} | {b} | {a} |" for m, b, a in rows]
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("### Stats refresh\n\n" + "\n".join(table) + "\n")


def main() -> None:
    cache = load_cache()
    version = int(cache.get(EMBED_VERSION_KEY, 0)) or 1

    prev_s = parse_or_prev(None, ROOT / "github-stats.svg", parse_stats)
    prev_k = parse_or_prev(None, ROOT / "streak.svg", parse_streak)

    stats_raw = fetch_with_retry(STATS_URL)
    streak_raw = fetch_with_retry(STREAK_URL)
    chart_raw = fetch_with_retry(CHART_URL)

    if stats_raw is None and streak_raw is None and chart_raw is None:
        print("WARNING: all upstream card services failed; keeping previous SVGs.")
        return

    s = parse_or_prev(stats_raw, ROOT / "github-stats.svg", parse_stats)
    k = parse_or_prev(streak_raw, ROOT / "streak.svg", parse_streak)

    changed = False
    if stats_raw:
        changed |= write_if_differs(ROOT / "github-stats.svg", theme(stats_raw))
    if streak_raw:
        changed |= write_if_differs(ROOT / "streak.svg", theme(streak_raw))
    if chart_raw:
        changed |= write_if_differs(ROOT / "contrib.svg", wrap_chart(chart_raw))
    changed |= write_if_differs(
        ROOT / "stats-strip.svg",
        strip_svg(
            s.get("commits", "—"),
            k.get("contributions", "—"),
            k.get("longest", "—"),
            s.get("rank", "—"),
        ),
    )

    if changed:
        version += 1
        stamp_readme(version)
        save_cache(version)

    write_summary(prev_s, prev_k, s, k)

    if changed:
        print(f"Cards refreshed; README embeds bumped to ?v={version}.")
    else:
        print("Cards unchanged; no commit needed.")


if __name__ == "__main__":
    main()
