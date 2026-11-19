#!/usr/bin/env python3
"""Writes one image summing up the world news of Wednesday 18 November 2026.

Standard library only, no network, deterministic: two runs write the same bytes.
Layout is a newspaper front page: masthead, two leads, eight illustrated stories,
thirty-five one-line briefs inside region columns, and a footer that names the
date check and the sources. Nothing is fetched at run time.

Everything printed here was checked against a report filed on 18 November 2026
(see FOOT); the digest that produced the story list is kept beside this file.
"""

import itertools
import math
import os
import struct
import zlib

W, H = 1024, 1024   # the competition's cap is 1024 by 1024
M = 22
COLS_W = W - 2 * M
LEAD_Y, LEAD_H, LEAD_GAP = 162, 168, 6
MAJOR_Y, MAJOR_H, MAJOR_GAP = 338, 92, 6
NCOL = 4                      # brief columns across the page
BRIEF_Y, BRIEF_BOTTOM = 596, 786
FOOT_Y, FOOT_PAD = 1344, 10
SEC_HEAD, SEC_PITCH, SEC_GAP = 19, 14, 3

PAPER = (243, 239, 228)
PANEL = (230, 223, 208)
INK = (26, 24, 22)
RED = (168, 32, 28)
BLUE = (28, 62, 120)
GREEN = (24, 92, 60)
PLUM = (96, 40, 96)          # a fourth heading colour so no two columns match
AMBER = (168, 106, 12)
GREY = (108, 103, 94)

# 5 wide, 7 tall. One string per row, '#' set, '.' clear.
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
    "N": ("#...#", "##..#", "###.#", "#.###", "#..##", "#...#", "#...#"),
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
    ",": (".....", ".....", ".....", ".....", ".....", "..#..", ".#..."),
    ":": (".....", "..#..", ".....", ".....", ".....", "..#..", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "'": ("..#..", "..#..", ".....", ".....", ".....", ".....", "....."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "&": (".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "+": (".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", "#..##", "#..##"),
}

for _ch, _rows in FONT.items():
    assert len(_rows) == 7 and all(len(_r) == 5 for _r in _rows), _ch

ADV = 6             # glyph advance in font cells: 5 wide, 1 of air
LEADING = 1         # blank rows between lines, in cells


def line_h(sc):
    return (7 + LEADING) * sc + 1


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


def cols_for(width, sc):
    return width // (ADV * sc)


class Canvas:
    """Flat RGB bytearray with the primitives a front page needs."""

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
        inner = max(0.0, (r - t)) ** 2
        outer = r * r
        for yy in range(max(0, int(cy - r)), min(self.h, int(cy + r) + 2)):
            dy = yy + 0.5 - cy
            for xx in range(max(0, int(cx - r)), min(self.w, int(cx + r) + 2)):
                dx = xx + 0.5 - cx
                d2 = dx * dx + dy * dy
                if inner < d2 <= outer:
                    self.put(xx, yy, c)

    def line(self, x0, y0, x1, y1, t, c):
        dx, dy = x1 - x0, y1 - y0
        L2 = dx * dx + dy * dy
        if L2 == 0:
            return
        half = max(0.5, t / 2.0) ** 2
        for yy in range(max(0, int(min(y0, y1) - t)), min(self.h, int(max(y0, y1) + t) + 1)):
            for xx in range(max(0, int(min(x0, x1) - t)), min(self.w, int(max(x0, x1) + t) + 1)):
                u = ((xx + 0.5 - x0) * dx + (yy + 0.5 - y0) * dy) / L2
                u = 0.0 if u < 0 else (1.0 if u > 1 else u)
                ex, ey = x0 + u * dx, y0 + u * dy
                if (xx + 0.5 - ex) ** 2 + (yy + 0.5 - ey) ** 2 <= half:
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
        for ch in s.upper():
            rows = FONT.get(ch)
            if rows:
                for ry in range(7):
                    for rx in range(5):
                        if rows[ry][rx] == "#":
                            self.rect(x + rx * sc, y + ry * sc, sc, sc, c)
            x += ADV * sc

    def text_w(self, s, sc):
        return len(s) * ADV * sc

    def text_c(self, s, y, sc, c):
        self.text(s, (self.w - self.text_w(s, sc)) // 2, y, sc, c)

    def lines(self, s, x, y, cols, sc, c, limit=None):
        ls = wrap(s, cols)
        if limit:
            ls = ls[:limit]
        for i, ln in enumerate(ls):
            self.text(ln, x, y + i * line_h(sc), sc, c)
        return len(ls)


# Icons are drawn in a 96x96 box scaled by u, so one description serves every
# size the page asks for: 44px beside a major story, 84px beside a lead.
def R(c, x, y, u, a, b, w, h, col):
    c.rect(x + a * u, y + b * u, w * u, h * u, col)


def D(c, x, y, u, a, b, r, col):
    c.disc(x + a * u, y + b * u, r * u, col)


def G(c, x, y, u, a, b, r, t, col):
    c.ring(x + a * u, y + b * u, r * u, t * u, col)


def L(c, x, y, u, a, b, a2, b2, t, col):
    c.line(x + a * u, y + b * u, x + a2 * u, y + b2 * u, t * u, col)


def P(c, x, y, u, pts, col):
    c.poly([(x + a * u, y + b * u) for a, b in pts], col)


def ic_summit(c, x, y, u):
    """Three leaders at lecterns, flags above."""
    for i, col in enumerate((RED, AMBER, BLUE)):
        a = 6 + i * 30
        D(c, x, y, u, a + 14, 14, 8, col)
        R(c, x, y, u, a + 4, 26, 20, 14, col)
        R(c, x, y, u, a, 40, 28, 4, INK)
        R(c, x, y, u, a + 2, 44, 4, 42, INK)
        R(c, x, y, u, a + 18, 44, 4, 42, INK)
        R(c, x, y, u, a - 4, 86, 36, 7, INK)


def ic_missile(c, x, y, u):
    """A missile over a struck base, drones around it."""
    R(c, x, y, u, 4, 74, 88, 12, INK)
    R(c, x, y, u, 12, 62, 16, 12, BLUE)
    R(c, x, y, u, 62, 62, 22, 12, BLUE)
    P(c, x, y, u, [(46, 4), (57, 40), (35, 40)], RED)
    L(c, x, y, u, 46, 40, 46, 58, 5, RED)
    L(c, x, y, u, 30, 56, 18, 44, 3, INK)
    L(c, x, y, u, 62, 56, 74, 44, 3, INK)
    for a in (26, 46, 66):
        R(c, x, y, u, a, 86, 8, 6, AMBER)


def ic_tank(c, x, y, u):
    """An armoured column: hull, turret, gun, wheels."""
    R(c, x, y, u, 6, 56, 84, 16, INK)
    R(c, x, y, u, 30, 38, 36, 18, INK)
    L(c, x, y, u, 66, 44, 92, 44, 7, INK)
    for a in (12, 30, 48, 66, 84):
        D(c, x, y, u, a, 76, 8, INK)
    R(c, x, y, u, 40, 30, 8, 8, AMBER)


def ic_bridge(c, x, y, u):
    """A span broken by a burst."""
    R(c, x, y, u, 2, 62, 38, 8, INK)
    R(c, x, y, u, 60, 62, 36, 8, INK)
    R(c, x, y, u, 10, 40, 9, 30, INK)
    R(c, x, y, u, 80, 40, 9, 30, INK)
    R(c, x, y, u, 22, 80, 8, 6, RED)
    R(c, x, y, u, 70, 82, 7, 5, RED)
    pts = []
    for i in range(16):
        r = 22 if i % 2 == 0 else 9
        a = i * math.pi / 8
        pts.append((51 + r * math.cos(a), 34 + r * math.sin(a)))
    P(c, x, y, u, pts, RED)


def ic_coin(c, x, y, u):
    """A loan: stacked coins beside a currency mark."""
    for i, b in enumerate((58, 46, 34)):
        R(c, x, y, u, 6, b, 40, 10, BLUE if i % 2 else AMBER)
    G(c, x, y, u, 70, 44, 22, 5, BLUE)
    L(c, x, y, u, 62, 32, 62, 56, 4, BLUE)
    L(c, x, y, u, 55, 40, 69, 40, 3, BLUE)
    L(c, x, y, u, 55, 50, 69, 50, 3, BLUE)


def ic_probe(c, x, y, u):
    """Voyager: dish, bus, booms, Earth far behind."""
    for i in range(3):
        G(c, x, y, u, 26 + i, 34, 22 - i * 6, 4, INK)
    R(c, x, y, u, 40, 48, 26, 14, INK)
    L(c, x, y, u, 53, 48, 53, 16, 4, INK)
    L(c, x, y, u, 40, 62, 24, 78, 3, INK)
    L(c, x, y, u, 60, 62, 70, 80, 3, INK)
    G(c, x, y, u, 84, 20, 9, 3, BLUE)


def ic_market(c, x, y, u):
    """A mixed session: bars and a jagged close."""
    for i, b in enumerate((20, 34, 48, 62)):
        R(c, x, y, u, 6 + i * 21, b, 13, 86 - b, GREY if i % 2 else INK)
    pts = [(4, 30), (24, 46), (44, 24), (64, 40), (90, 18)]
    for i in range(len(pts) - 1):
        L(c, x, y, u, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], 4, RED)


def ic_globe(c, x, y, u):
    """A warming globe beside a smokestack."""
    G(c, x, y, u, 38, 52, 34, 4, GREEN)
    for f in (0.5, 0.86):
        d = 34 * (1 - f * f) ** 0.5
        L(c, x, y, u, 38 - 34 * f, 52 - d, 38 - 34 * f, 52 + d, 3, GREEN)
        L(c, x, y, u, 38 + 34 * f, 52 - d, 38 + 34 * f, 52 + d, 3, GREEN)
    L(c, x, y, u, 4, 52, 72, 52, 3, GREEN)
    R(c, x, y, u, 80, 40, 12, 46, INK)
    R(c, x, y, u, 78, 82, 16, 8, INK)
    for a, b in ((86, 26), (90, 18), (84, 10)):
        D(c, x, y, u, a, b, 5, GREY)


def ic_flag(c, x, y, u):
    """Two crossed flags over a signed page."""
    L(c, x, y, u, 16, 6, 24, 90, 5, INK)
    L(c, x, y, u, 80, 6, 72, 90, 5, INK)
    R(c, x, y, u, 24, 10, 32, 6, RED)
    R(c, x, y, u, 24, 16, 32, 6, PAPER)
    R(c, x, y, u, 24, 22, 32, 6, RED)
    R(c, x, y, u, 44, 10, 12, 18, BLUE)
    P(c, x, y, u, [(64, 10), (80, 10), (72, 26)], AMBER)
    R(c, x, y, u, 34, 76, 30, 14, INK)


def ic_virus(c, x, y, u):
    """An outbreak: a spiked virion with a warning cross."""
    for i in range(16):
        a = i * math.pi / 8
        L(c, x, y, u, 42 + 20 * math.cos(a), 46 + 20 * math.sin(a),
          42 + 30 * math.cos(a), 46 + 30 * math.sin(a), 3, GREEN)
    D(c, x, y, u, 42, 46, 20, GREEN)
    D(c, x, y, u, 36, 40, 5, PAPER)
    D(c, x, y, u, 48, 52, 4, PAPER)
    R(c, x, y, u, 78, 20, 8, 34, RED)
    R(c, x, y, u, 70, 28, 24, 8, RED)


def ic_ship(c, x, y, u):
    """A carrier turning away: hull, island, jets, wake."""
    P(c, x, y, u, [(4, 62), (92, 62), (82, 82), (14, 82)], INK)
    R(c, x, y, u, 30, 50, 52, 12, INK)
    R(c, x, y, u, 54, 30, 14, 20, INK)
    L(c, x, y, u, 61, 30, 61, 14, 4, INK)
    R(c, x, y, u, 20, 42, 6, 8, BLUE)
    for a in (16, 30, 44):
        L(c, x, y, u, a, 90, a - 8, 94, 2, GREY)


def ic_fire(c, x, y, u):
    """Flames over a broken roofline."""
    P(c, x, y, u, [(46, 6), (60, 34), (54, 46), (76, 46), (70, 74), (22, 74),
                   (18, 46), (34, 40)], RED)
    P(c, x, y, u, [(46, 34), (52, 50), (44, 62), (36, 50)], AMBER)
    R(c, x, y, u, 8, 82, 80, 8, INK)


def ic_bank(c, x, y, u):
    """A bank and a rising price line."""
    P(c, x, y, u, [(48, 6), (92, 32), (4, 32)], INK)
    for a in (14, 38, 62):
        R(c, x, y, u, a, 36, 10, 40, GREY)
    R(c, x, y, u, 4, 80, 88, 10, INK)
    for i in range(4):
        L(c, x, y, u, 10 + i * 24, 74 - i * 6, 10 + (i + 1) * 24, 68 - i * 8, 4, RED)


def ic_wheat(c, x, y, u):
    """A harvest: grain under a rain cloud."""
    L(c, x, y, u, 46, 90, 46, 34, 5, INK)
    for i in range(4):
        yy = 38 + i * 13
        L(c, x, y, u, 46, yy, 30, yy - 8, 4, AMBER)
        L(c, x, y, u, 46, yy, 62, yy - 8, 4, AMBER)
    D(c, x, y, u, 76, 24, 14, BLUE)
    for a in (66, 76, 86):
        L(c, x, y, u, a, 40, a - 4, 54, 3, BLUE)


ICONS = (ic_summit, ic_missile, ic_tank, ic_bridge, ic_coin, ic_probe,
         ic_market, ic_globe, ic_flag, ic_virus, ic_ship, ic_fire,
         ic_bank, ic_wheat)

LEADS = [
    ("WORLD", "TRUMP MEETS XI AND PUTIN IN CHINA", RED, ic_summit,
     "APEC IN SHENZHEN: TRADE, ARMS AND TWO WARS."),
    ("GULF", "IRAN STRIKES US BASE IN KUWAIT", BLUE, ic_missile,
     "KUWAIT BASE HIT, THREE TANKERS MINED."),
]

MAJORS = [
    ("GULF AND LEVANT", "ISRAEL OPENS GAZA GROUND DRIVE", AMBER, ic_tank),
    ("EUROPE", "CRIMEAN BRIDGE PARTLY SEVERED", BLUE, ic_bridge),
    ("EUROPE", "EU PROPOSES 45BN EURO LOAN", BLUE, ic_coin),
    ("SCIENCE", "VOYAGER 1 ONE LIGHT-DAY OUT", GREEN, ic_probe),
    ("ECONOMY", "NVIDIA RECORD, WALL ST MIXED", RED, ic_market),
    ("WORLD", "OPEC DEFENDS FOSSIL FUELS", GREEN, ic_globe),
    ("AFRICA", "CONGO EBOLA STILL EMERGENCY", GREEN, ic_virus),
    ("ASIA", "BANGLADESH UNREST SHUTS PLANTS", RED, ic_fire),
]

SECTIONS = [
    ("ASIA", RED, [
        "MARCOS AT APEC",
        "ROHINGYA RULING",
        "KULGAM SIEGE ENDS",
        "YUNUS HOME BURNED",
        "DHAKA PROTESTS",
    ]),
    ("EUROPE", BLUE, [
        "UK INFLATION HIGH",
        "ITALY HATE LAW",
        "UNICREDIT DEAL",
        "IMAMOGLU BANNED",
        "DUTCH ROLE ASKED",
    ]),
    ("GULF AND LEVANT", AMBER, [
        "SAUDIS SEEK ARMS",
        "YEMEN CHILD TOLL",
        "LEBANON STRIKE",
        "IRAN DENIES PLOT",
        "YEMEN WAR TO 2027",
    ]),
    ("AFRICA", GREEN, [
        "ETHIOPIA BUILDUP",
        "SUDAN ICC DEMAND",
        "SUDAN DRONE TOLL",
        "NIGERIA 261 DEAD",
        "EGYPT WAGE RISE",
        "SAHEL SMUGGLING",
    ]),
    ("AMERICAS", AMBER, [
        "COLOMBIA SAYS NO",
        "HAITI GANG HOME",
        "US LOSES MEASLES",
        "BRAZIL BUDGET OK",
        "KAST MEETS XI",
        "POPE LEO IN PERU",
        "ECUADOR US TROOPS",
    ]),
    ("ECONOMY", RED, [
        "BITCOIN DOWN 14%",
        "GOLD ONE-YEAR LOW",
        "TSMC AI STAKES",
        "OIL SURPLUS 2027",
    ]),
    ("SCIENCE", GREEN, [
        "STARSHIP CATCH",
        "ISLAM TOP BY 2035",
        "CYGNUS NOV 29",
    ]),
]

N_STORIES = len(LEADS) + len(MAJORS) + sum(len(x[2]) for x in SECTIONS)

FOOT = [
    ("SOURCES", "WIKIPEDIA, REUTERS, AP, BBC, PBS, NPR, CNBC, UN NEWS, NASA, "
                "PEW, HUMAN RIGHTS WATCH", GREY),
    ("DATE CHECK", "EVERY ITEM WAS FIRST REPORTED ON 18 NOVEMBER 2026 IN SOME "
                   "TIME ZONE. LEFT OUT: ITEMS DATED 17 OR 19 NOVEMBER, AND ANY "
                   "ITEM WITH NO DAY.", GREY),
    ("SCOPE", f"{N_STORIES} STORIES, SEVEN SECTIONS, ONE PAGE: {len(LEADS)} LEADS, "
              f"{len(MAJORS)} DRAWN STORIES, {N_STORIES - len(LEADS) - len(MAJORS)} BRIEFS.",
     GREY),
]

MASTHEAD = ("THE WORLD IN ONE DAY", "18 NOVEMBER 2026",
            f"WEDNESDAY - {N_STORIES} STORIES - SEVEN SECTIONS")


def check_glyphs():
    out = [MASTHEAD[0], MASTHEAD[1], MASTHEAD[2]]
    for tag, head, _c, _i, deck in LEADS:
        out += [tag, head, deck]
    for tag, head, _c, _i in MAJORS:
        out.append(head)
    for name, _c, items in SECTIONS:
        out.append(name)
        out += items
    for tag, body, _c in FOOT:
        out += [tag, body]
    for s in out:
        bad = set(s.upper()) - set(FONT)
        assert not bad, (s, bad)


LEAD_W = (COLS_W - 14) // 2


def lead_block(c, x, y, lead):
    """Half a row: a tag, an icon in the corner, a headline over two columns."""
    tag, head, colr, icon, deck = lead
    w = LEAD_W
    c.rect(x, y, w, LEAD_H, PANEL)
    c.rect(x, y, w, 6, colr)
    icon(c, x + 12, y + 22, 76 / 96.0)
    tx = x + 100
    cols = cols_for(w - 100 - 12, 4)
    c.text(tag, tx, y + 12, 2, colr)
    n = c.lines(head, tx, y + 26, cols, 4, INK)
    assert n <= 3, (n, head)
    dcols = cols_for(w - 24, 2)
    dn = c.lines(deck, x + 12, y + 26 + n * line_h(4) + 6, dcols, 2, GREY)
    assert dn <= 2, (dn, deck)
    assert y + 26 + n * line_h(4) + 6 + dn * line_h(2) <= y + LEAD_H, (head, n, dn)


MAJOR_W = (COLS_W - 3 * 8) // 4


def major_cell(c, x, y, major):
    """A quarter row: coloured spine, tag, icon, headline over three of four rows."""
    tag, head, colr, icon = major
    w = MAJOR_W
    c.rect(x, y, w, MAJOR_H, PANEL)
    c.rect(x, y, 4, MAJOR_H, colr)
    icon(c, x + 8, y + 13, 22 / 96.0)
    tx = x + 36
    cols = cols_for(w - 36 - 7 - 10, 2)      # 10 px clear of the panel's right edge
    c.text(tag, tx, y + 8, 2, colr)
    ls = wrap(head, cols)
    n = len(ls)
    # centre the headline in what the tag and icon leave, so two-line and three-line
    # cells sit alike instead of hugging the top
    dy = max(0, (MAJOR_H - 6 - 29 - n * line_h(2)) // 2)
    for i, ln in enumerate(ls):
        c.text(ln, tx, y + 29 + dy + i * line_h(2), 2, INK)
    assert n <= 5, (n, head)
    assert y + 29 + n * line_h(2) <= y + MAJOR_H, (head, n)


def plan_columns(blocks):
    """Split region blocks over three columns, keeping each block whole."""
    target = BRIEF_BOTTOM - BRIEF_Y
    best, best_key = None, None
    for assign in itertools.product(range(NCOL), repeat=len(blocks)):
        totals = [0] * NCOL
        for b, a in zip(blocks, assign):
            totals[a] += b[2]
        if max(totals) > target:
            continue
        key = (max(totals), max(totals) - min(totals))
        if best_key is None or key < best_key:
            best_key, best = key, assign
    assert best is not None, "briefs do not fit: " + str(
        [b[2] for b in blocks]) + " target " + str(target)
    cols = [[] for _ in range(NCOL)]
    for b, a in zip(blocks, assign_cols(best, blocks)):
        cols[a].append(b)
    for col in cols:
        col.sort(key=lambda b: b[3])
    return cols


def assign_cols(assign, blocks):
    return assign


def build():
    check_glyphs()
    gap = 10
    cw = (COLS_W - (NCOL - 1) * gap) // NCOL
    bcols = cols_for(cw - 18, 2)
    for _name, _c, items in SECTIONS:
        for it in items:
            assert len(it) <= bcols, ("brief too long for one line", it, len(it), bcols)

    blocks = [(name, colr, SEC_HEAD + SEC_PITCH * len(items) + SEC_GAP, i, items)
              for i, (name, colr, items) in enumerate(SECTIONS)]

    c = Canvas(W, H, PAPER)
    c.rect(0, 0, W, 9, INK)

    c.text_c(MASTHEAD[0], 16, 3, GREY)
    c.text_c(MASTHEAD[1], 34, 10, INK)
    c.rect(M, 116, COLS_W, 3, INK)
    c.text_c(MASTHEAD[2], 126, 3, RED)
    c.rect(M, 154, COLS_W, 1, GREY)

    for i, lead in enumerate(LEADS):
        lead_block(c, M + i * (LEAD_W + 14), LEAD_Y, lead)

    for i, major in enumerate(MAJORS):
        major_cell(c, M + (i % 4) * (MAJOR_W + 8),
                   MAJOR_Y + (i // 4) * (MAJOR_H + MAJOR_GAP), major)

    # each brief takes one slot row; columns are packed by story count, not by section,
    # so the briefs fill the page edge to edge and every column ends on the same row
    # briefs: seven sections dealt out to four columns, tallest first, so the
    # columns pack within a row of each other and the page fills edge to edge
    heights = [0] * NCOL
    place = [[] for _ in range(NCOL)]
    for sec in sorted(blocks, key=lambda b: -len(b[4])):
        i = heights.index(min(heights))
        place[i].append(sec)
        heights[i] += SEC_HEAD + SEC_PITCH * len(sec[4]) + SEC_GAP
    for ci in range(NCOL):
        x = M + ci * (cw + gap)
        c.rect(x, BRIEF_Y - 12, cw, 3, INK)
        y = BRIEF_Y
        hcol = (RED, BLUE, GREEN, PLUM)[ci]
        for name, colr, _need, _ord, items in place[ci]:
            c.text(name, x, y, 2, hcol)
            c.rect(x, y + 16, cw - 18, 2, hcol)
            y += SEC_HEAD
            for it in items:
                c.rect(x, y + 4, 5, 5, colr)
                c.text(it, x + 11, y, 2, INK)
                y += SEC_PITCH
            y += SEC_GAP
        assert y <= BRIEF_BOTTOM + 8, (ci, y)

    c.rect(M, 796, COLS_W, 3, INK)

    # the footer runs in two half-page columns, tag on the line above its body
    fgap = 16
    fcw = (COLS_W - fgap) // 2
    fcols = cols_for(fcw, 2)
    fblocks = [(tag, wrap(body, fcols), colr) for tag, body, colr in FOOT]
    col = [fblocks[:2], fblocks[2:]]
    heights = [sum(22 + 16 * len(ls) + 6 for _t, ls, _c in blk) for blk in col]
    y = H - 26 - FOOT_PAD - max(heights)
    assert y >= BRIEF_BOTTOM + 8, y
    for ci, blk in enumerate(col):
        fx = M + ci * (fcw + fgap)
        fy = y
        for tag, ls, colr in blk:
            c.text(tag, fx, fy, 2, RED)
            for i, ln in enumerate(ls):
                c.text(ln, fx, fy + 22 + i * 16, 2, colr)
            fy += 22 + 16 * len(ls) + 6
    c.rect(0, H - 9, W, 9, INK)
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