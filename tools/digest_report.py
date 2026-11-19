#!/usr/bin/env python3
"""Check digest.json against what main.py draws, then print the provenance.

Two things are worth checking before the page is trusted:

1. the record's counts agree with the page's own lists, and
2. every headline in the record is a headline on the page, and the page has no
   story the record does not.

digest.json keeps each headline only as a hash, so this script hashes the page's
strings to compare. That keeps one copy of the copy: main.py's.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, os.pardir))

import main as page  # noqa: E402  the generator is the source of the copy


def digest_headlines():
    return [s["sha1"] for s in DIGEST["stories"]]


def page_headlines():
    out = [head for _tag, head, _c, _i, _d in page.LEADS]
    out += [head for _tag, head, _c, _i in page.MAJORS]
    for _name, _colr, items in page.SECTIONS:
        out += items
    return out


def h(s):
    return hashlib.sha1(s.encode()).hexdigest()[:12]


def main():
    c = DIGEST["counts"]
    print(DIGEST["weekday"], DIGEST["day"], "-", c["total"], "stories:",
          c["leads"], "leads,", c["majors"], "drawn,", c["briefs"], "briefs")
    print("excluded:", DIGEST["excluded"])

    assert c["total"] == c["leads"] + c["majors"] + c["briefs"], c
    assert page.N_STORIES == c["total"], (page.N_STORIES, c["total"])

    rec = digest_headlines()
    drawn = [h(s) for s in page_headlines()]
    assert len(set(rec)) == len(rec), "digest records one story twice"
    assert len(set(drawn)) == len(drawn), "the page prints one story twice"
    missing = [s for s in page_headlines() if h(s) not in set(rec)]
    extra = [s for s in rec if s not in set(drawn)]
    assert not missing, ("on the page, absent from the record", missing)
    assert not extra, ("recorded, not on the page", extra)

    late = [t for s in DIGEST["stories"] for t in s["first_reported"]
            if not t.startswith(DIGEST["day"])]
    # a story filed in the small hours of the next UTC day still reports this day
    assert all(t[:10] in (DIGEST["day"], "2026-11-19") for t in late), late
    assert all(s["outlets"] for s in DIGEST["stories"]), "story with no outlet"

    print("ok:", len(rec), "stories, each on the page and in the record")
    for s in DIGEST["stories"]:
        print(" ", s["sha1"], s["section"][:16].ljust(16),
              ",".join(s["outlets"])[:60])


with open(os.path.join(HERE, os.pardir, "digest.json")) as _f:
    DIGEST = json.load(_f)

if __name__ == "__main__":
    main()
