#!/usr/bin/env python3
"""Refresh GitHub profile stat SVGs. Safe to run locally or in Actions."""

from __future__ import annotations

import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER = "sambhavthakkar"
ACCENT = "455CE9"
BG = "1C1D20"

STATS_URL = (
    f"https://github-readme-stats.zohan.tech/api?username={USER}"
    "&show_icons=true&hide_border=true"
    f"&bg_color={BG}&title_color=FFFFFF&icon_color={ACCENT}"
    "&text_color=C8C9CC&ring_color=455CE9&hide=stars"
)
STREAK_URL = (
    f"https://streak-stats.demolab.com/?user={USER}"
    f"&background={BG}&border={BG}&ring={ACCENT}&fire={ACCENT}"
    "&currStreakLabel=FFFFFF&sideLabels=999A9E&currStreakNum=FFFFFF"
    "&sideNums=C8C9CC&dates=999A9E&stroke=2E2F32"
)
CHART_URL = f"https://ghchart.rshah.org/{ACCENT.lower()}/{USER}"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "sambhav-profile-stats"})
    with urllib.request.urlopen(req, timeout=30) as res:
        return res.read().decode("utf-8", errors="replace")


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


def strip_svg(commits: str, contributions: str, longest: str, rank: str) -> str:
    cells = [
        ("Contributions", contributions, "private graph included", True),
        ("Commits · 2026", commits, "public surface", False),
        ("Longest streak", longest, "days in a row", False),
        ("GitHub rank", rank, "live card", False),
    ]
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="100%" viewBox="0 0 900 168" preserveAspectRatio="xMidYMid meet">',
        '<rect width="900" height="168" fill="#1c1d20"/>',
        "<style>",
        "  .label { font: 500 11px 'Segoe UI', Ubuntu, sans-serif; fill: #999a9e; letter-spacing: 1.4px; }",
        "  .value { font: 400 36px 'Segoe UI', Ubuntu, sans-serif; }",
        "  .hint { font: 400 11px 'Segoe UI', Ubuntu, sans-serif; fill: #999a9e; }",
        "</style>",
    ]
    gap, w, h, x0, y0 = 12, 210, 140, 12, 14
    for i, (label, value, hint, accent) in enumerate(cells):
        x = x0 + i * (w + gap)
        fill = "#455ce9" if accent else "#ffffff"
        parts += [
            f'<rect x="{x}" y="{y0}" width="{w}" height="{h}" rx="16" fill="none" stroke="#2e2f32"/>',
            f'<text class="label" x="{x + 18}" y="{y0 + 32}">{label.upper()}</text>',
            f'<text class="value" x="{x + 18}" y="{y0 + 88}" fill="{fill}">{value}</text>',
            f'<text class="hint" x="{x + 18}" y="{y0 + 114}">{hint}</text>',
        ]
    parts.append("</svg>")
    return "\n".join(parts)


def wrap_chart(raw: str) -> str:
    raw = raw.replace("fill:#EEEEEE", "fill:#2e2f32")
    raw = raw.replace("fill:#767676", "fill:#999a9e")
    inner = "<svg" + raw.split("<svg", 1)[1]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="100%" '
        'viewBox="0 0 743 156" preserveAspectRatio="xMidYMid meet">\n'
        '  <rect width="743" height="156" rx="12" fill="#1c1d20"/>\n'
        '  <g transform="translate(40,24)">\n'
        f"    {inner}\n"
        "  </g>\n"
        "</svg>\n"
    )


def main() -> None:
    stats_raw = fetch(STATS_URL)
    streak_raw = fetch(STREAK_URL)
    chart = fetch(CHART_URL)

    s = parse_stats(stats_raw)
    k = parse_streak(streak_raw)
    stats = freeze(stats_raw)
    streak = freeze(streak_raw)

    (ROOT / "github-stats.svg").write_text(stats)
    (ROOT / "streak.svg").write_text(streak)
    (ROOT / "contrib.svg").write_text(wrap_chart(chart))
    (ROOT / "stats-strip.svg").write_text(
        strip_svg(s["commits"], k["contributions"], k["longest"], s["rank"])
    )
    print(
        "updated",
        f"commits={s['commits']}",
        f"contrib={k['contributions']}",
        f"streak={k['longest']}",
        f"rank={s['rank']}",
    )


if __name__ == "__main__":
    main()
