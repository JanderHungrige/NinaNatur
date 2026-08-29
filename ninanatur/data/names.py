"""Finding a plant by the name someone actually types.

Users type what their keyboard makes easy, not what the botanist wrote. Folding
umlauts, hyphens and case is what turns three spellings of Schlüsselblume into
one lookup.
"""
from __future__ import annotations

import re
import sqlite3

# Umlauts fold to the BARE vowel, not to the "ue" digraph.
#
# Both spellings are typed in practice — "Schlüsselblume", "Schluesselblume" and
# "schlusselblume" are all real search input. Folding to "ue" only catches the
# first two; folding to "u" catches the first and third, and GBIF supplies the
# "ue" spelling as a name of its own, which then matches itself. So bare-vowel
# folding plus the data covers all three.
#
# The tempting alternative — additionally collapsing "ue" to "u" — turns "Feuer"
# into "Feur" and would silently mangle every word where the digraph is not an
# umlaut at all.
_FOLD = (
    ("ß", "ss"),
    ("ä", "a"), ("ö", "o"), ("ü", "u"),
)
_STRIP = re.compile(r"[^a-z0-9]+")


def normalise(name: str) -> str:
    """Fold a name to the form search matches on.

    Lowercased, umlauts expanded, everything else that is not a letter or digit
    removed — so `Sal-Weide`, `Sal Weide` and `Salweide` are one key, and
    `Schlüsselblume`, `Schluesselblume` and `schlusselblume` are another.

    Idempotent, because it is applied both when storing and when querying.
    """
    folded = name.lower()
    for source, target in _FOLD:
        folded = folded.replace(source, target)
    return _STRIP.sub("", folded)


def preferred_name(names: list[str]) -> str | None:
    """The one to show. None when there is no German name at all.

    Shortest wins, but a parenthetical qualifier loses regardless of length: a
    display name is read, not parsed, and "Salweide (Artengruppe)" answers a
    question nobody asked.

    Returning None rather than a placeholder lets the caller fall back to the
    binomial, which *is* the species' name when no other exists.
    """
    if not names:
        return None
    plain = [n for n in names if "(" not in n] or names
    return min(plain, key=lambda n: (len(n), n))


def search_names(conn: sqlite3.Connection, query: str, limit: int = 50) -> list[int]:
    """Taxon ids whose German or scientific name contains the query.

    **Contains, not prefix.** German plant names are overwhelmingly
    adjective-noun — *Echte Schlüsselblume*, *Wiesen-Salbei*, *Gemeine
    Schafgarbe* — and people type the noun. Prefix matching would find none of
    them, which looks like an empty catalogue rather than a mismatched query.

    Not fuzzy either: fuzzy matching over 3,000 species produces confident
    nonsense, while a substring that finds nothing is honest and the user can
    type less.

    A leading wildcard means the index on `normalised` cannot be used. At roughly
    46,000 name rows that scan is sub-millisecond, and buying it back would mean
    a token table whose complexity this does not yet justify.
    """
    folded = normalise(query)
    if not folded:
        # Not an error: "%" and "-" both fold to nothing, and neither is a request
        # for the whole catalogue.
        return []

    pattern = f"%{folded}%"
    rows = conn.execute(
        """
        SELECT DISTINCT taxon_id FROM (
            SELECT taxon_id FROM vernacular_name WHERE normalised LIKE ?
            UNION
            SELECT taxon_id FROM taxon
            WHERE REPLACE(REPLACE(LOWER(canonical_name), ' ', ''), '-', '') LIKE ?
        )
        LIMIT ?
        """,
        (pattern, pattern, limit),
    ).fetchall()
    return [int(r["taxon_id"]) for r in rows]


def resolve_one(conn: sqlite3.Connection, name: str) -> int | None:
    """The single taxon a typed name means, or None when that is not certain.

    Exact before contains, and **ambiguity resolves to None**: a search that
    matches four species has not identified a plant, and picking the first is
    how someone ends up with *Achillea millefolium* when they meant a cultivar
    that behaves nothing like it. Unresolved is a normal, storable answer here.
    """
    wanted = normalise(name)
    if not wanted:
        return None

    exact = conn.execute(
        "SELECT taxon_id FROM vernacular_name WHERE normalised = ?", (wanted,)
    ).fetchall()
    ids = {int(r["taxon_id"]) for r in exact}
    if len(ids) == 1:
        return ids.pop()
    if len(ids) > 1:
        return None

    scientific = conn.execute(
        "SELECT taxon_id FROM taxon WHERE LOWER(canonical_name) = LOWER(?)", (name.strip(),)
    ).fetchall()
    ids = {int(r["taxon_id"]) for r in scientific}
    if len(ids) == 1:
        return ids.pop()
    if len(ids) > 1:
        return None

    candidates = search_names(conn, name, limit=2)
    return candidates[0] if len(candidates) == 1 else None
