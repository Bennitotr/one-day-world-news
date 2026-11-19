#!/usr/bin/env python3
"""Writes one image summing up the world news of Wednesday 18 November 2026.

Standard library only, no network, deterministic: two runs write the same bytes.
Everything is drawn from scratch with a 5x7 bitmap font and a small rasteriser.
"""

import math
import os
import struct
import zlib

W = H = 1024

BG = (9, 15, 28)
CARD = (246, 243, 234)
INK = (17, 24, 39)
RED = (198, 40, 34)
AMBER = (222, 152, 25)
BLUE = (39, 90, 165)
GREEN = (28, 132, 84)
GREY = (170, 180, 196)

# 5 wide, 7 tall, one entry per glyph as seven rows of five cells.
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#..##", "#...#", "#...#", ".####"),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "#..#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#.#.#", "#..##", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".###.", "#...#", "#....", ".###.", "....#", "#...#", ".###."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "2": (".###.", "#...#", "...#.", "..#..", ".#...", "#...#", "#####"),
    "3": ("#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": ("..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".....", "..#.."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    ",": (".....", ".....", ".....", ".....", ".....", "..#..", ".#..."),
    ":": (".....", "..#..", ".....", ".....", ".....", "..#..", "....."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "'": ("..#..", "..#..", ".....", ".....", ".....", ".....", "....."),
    "&": (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
}

for _ch, _rows in FONT.items():
    assert len(_rows) == 7 and all(len(_r) == 5 for _r in _rows), _ch


class Canvas:
    """A flat RGB bytearray with the few primitives the poster needs."""

    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bytes(bg) * (w * h))

    def put(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(c)

    def rect(self, x, y, w, h, c):
        x0, y0 = max(0, int(round(x))), max(0, int(round(y)))
        x1, y1 = min(self.w, int(round(x + w))), min(self.h, int(round(y + h)))
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(c) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + (x1 - x0) * 3] = row

    def disc(self, cx, cy, r, c):
        r2 = r * r
        for yy in range(max(0, int(cy - r)), min(self.h, int(cy + r) + 1)):
            dy = yy + 0.5 - cy
            for xx in range(max(0, int(cx - r)), min(self.w, int(cx + r) + 1)):
                dx = xx + 0.5 - cx
                if dx * dx + dy * dy <= r2:
                    self.put(xx, yy, c)

    def ring(self, cx, cy, r, t, c):
        for yy in range(max(0, int(cy - r)), min(self.h, int(cy + r) + 2)):
            dy = yy + 0.5 - cy
            for xx in range(max(0, int(cx - r)), min(self.w, int(cx + r) + 2)):
                dx = xx + 0.5 - cx
                d = (dx * dx + dy * dy) ** 0.5
                if r - t < d <= r:
                    self.put(xx, yy, c)

    def line(self, x0, y0, x1, y1, t, c):
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        if L2 == 0:
            return
        half = t / 2.0
        for yy in range(max(0, int(min(y0, y1) - t)), min(self.h, int(max(y0, y1) + t) + 1)):
            for xx in range(max(0, int(min(x0, x1) - t)), min(self.w, int(max(x0, x1) + t) + 1)):
                u = ((xx + 0.5 - x0) * dx + (yy + 0.5 - y0) * dy) / L2
                u = 0.0 if u < 0 else (1.0 if u > 1 else u)
                ex, ey = x0 + u * dx, y0 + u * dy
                if (xx + 0.5 - ex) ** 2 + (yy + 0.5 - ey) ** 2 <= half * half:
                    self.put(xx, yy, c)

    def poly(self, pts, c):
        ys = [p[1] for p in pts]
        for yy in range(max(0, int(min(ys))), min(self.h, int(max(ys)) + 1)):
            yc = yy + 0.5
            xs = []
            for i in range(len(pts)):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % len(pts)]
                if (y0 <= yc < y1) or (y1 <= yc < y0):
                    xs.append(x0 + (yc - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.rect(xs[i], yy, xs[i + 1] - xs[i], 1, c)

    def text(self, s, x, y, sc, c):
        cx = x
        for ch in s.upper():
            rows = FONT[ch]
            for ry in range(7):
                for rx in range(5):
                    if rows[ry][rx] == "#":
                        self.rect(cx + rx * sc, y + ry * sc, sc, sc, c)
            cx += 6 * sc
        return cx

    def text_w(self, s, sc):
        return len(s) * 6 * sc

    def text_c(self, s, y, sc, c):
        self.text(s, (self.w - self.text_w(s, sc)) // 2, y, sc, c)


def wrap(s, cols):
    lines, line = [], ""
    for word in s.split():
        if not line:
            line = word
        elif len(line) + 1 + len(word) <= cols:
            line += " " + word
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def icon_diplomacy(c, x, y):
    for i, col in enumerate((RED, AMBER, BLUE)):
        px = x + 10 + i * 30
        c.rect(px, y + 8, 5, 80, INK)
        c.rect(px + 5, y + 8, 19, 15, col)


def icon_gaza(c, x, y):
    c.rect(x + 4, y + 52, 76, 17, INK)
    c.rect(x + 26, y + 36, 32, 16, INK)
    c.line(x + 58, y + 42, x + 94, y + 42, 8, INK)
    for i in range(3):
        c.disc(x + 18 + i * 26, y + 76, 10, INK)


def icon_ukraine(c, x, y):
    c.rect(x + 2, y + 56, 40, 8, INK)
    c.rect(x + 60, y + 56, 40, 8, INK)
    for px in (x + 12, x + 82):
        c.rect(px, y + 28, 10, 44, INK)
    burst = []
    for i in range(16):
        a = i * math.pi / 8.0
        rr = 22 if i % 2 == 0 else 9
        burst.append((x + 51 + rr * math.cos(a), y + 34 + rr * math.sin(a)))
    c.poly(burst, RED)
    c.rect(x + 30, y + 74, 7, 6, RED)
    c.rect(x + 66, y + 76, 6, 5, RED)


def icon_space(c, x, y):
    c.ring(x + 26, y + 30, 19, 5, INK)
    c.rect(x + 38, y + 42, 30, 16, INK)
    c.line(x + 53, y + 42, x + 53, y + 8, 4, INK)
    c.line(x + 30, y + 58, x + 18, y + 74, 4, INK)
    c.line(x + 48, y + 58, x + 42, y + 76, 4, INK)
    c.ring(x + 86, y + 22, 9, 3, BLUE)
    for dx in (66, 72):
        c.rect(x + dx, y + 21, 3, 3, BLUE)


def icon_markets(c, x, y):
    for i, top in enumerate((16, 31, 46, 61)):
        c.rect(x + 8 + i * 21, y + top, 14, 82 - top, RED)
    c.line(x + 6, y + 12, x + 86, y + 64, 5, INK)
    c.poly([(x + 88, y + 70), (x + 64, y + 64), (x + 82, y + 46)], INK)


def icon_climate(c, x, y):
    cx, cy, r = x + 38, y + 50, 32
    c.ring(cx, cy, r, 4, GREEN)
    for f in (0.5, 0.86):
        d = r * (1 - f * f) ** 0.5
        c.line(cx - r * f, cy - d, cx - r * f, cy + d, 3, GREEN)
        c.line(cx + r * f, cy - d, cx + r * f, cy + d, 3, GREEN)
    c.line(cx - r, cy, cx + r, cy, 3, GREEN)
    c.rect(x + 78, y + 22, 11, 42, RED)
    c.disc(x + 83, y + 72, 10, RED)


STORIES = [
    ("TRUMP MEETS XI AND PUTIN IN CHINA", RED, icon_diplomacy),
    ("ISRAELI TANKS ENTER CENTRAL GAZA", AMBER, icon_gaza),
    ("CRIMEAN BRIDGE STRUCK THIRD TIME", BLUE, icon_ukraine),
    ("VOYAGER 1 REACHES ONE LIGHT-DAY", GREEN, icon_space),
    ("S&P 500 FALLS FIFTH STRAIGHT DAY", RED, icon_markets),
    ("COP31 DRAFT TARGETS FOSSIL FUELS", GREEN, icon_climate),
]


def build():
    c = Canvas(W, H, BG)
    c.text_c("18 NOVEMBER 2026", 40, 8, CARD)
    c.rect(128, 112, 768, 5, RED)
    c.text_c("WEDNESDAY - SIX STORIES", 132, 5, CARD)

    for i, (head, col, icon) in enumerate(STORIES):
        y = 196 + i * 134
        c.rect(24, y, 976, 128, CARD)
        c.rect(24, y, 12, 128, col)
        icon(c, 60, y + 16)
        ty = y + 22
        for line in wrap(head, 22)[:2]:
            c.text(line, 176, ty, 6, INK)
            ty += 50
    return c


def write_png(path, c):
    raw = bytearray()
    stride = c.w * 3
    for y in range(c.h):
        raw.append(0)
        raw += c.px[y * stride:(y + 1) * stride]

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", c.w, c.h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def main():
    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out, exist_ok=True)
    write_png(os.path.join(out, "entry.png"), build())


if __name__ == "__main__":
    main()
