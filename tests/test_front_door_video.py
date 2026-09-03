"""The film behind the front door, as an asset that ships.

The component decides when to play it; these are the facts about the file
itself, and they are asserted against the copy in the repository rather than
against a build output. `ninanatur/web/dist` exists only after somebody has run
`npm run build`, and a test that passes or fails on that is the mistake Wave 1
made and CLAUDE.md records.
"""
from __future__ import annotations

from pathlib import Path

VIDEO = Path(__file__).resolve().parents[1] / "frontend" / "public" / "meadow.mp4"

# Generous against what it is (3.2 MB), tight against what it could become. The
# source was 11.6 MB; re-encoding it is a thing somebody has to remember to do,
# and this is the reminder.
BUDGET_BYTES = 4 * 1024 * 1024


def test_the_film_ships_with_the_front_end() -> None:
    assert VIDEO.is_file(), f"the front door's background is missing: {VIDEO}"


def test_it_stays_within_its_budget() -> None:
    """Every first visit downloads this. The shipped catalogue is 10 MB and the
    whole JS bundle is 242 kB — an unencoded clip would be the largest thing on
    the site by a wide margin."""
    size = VIDEO.stat().st_size
    assert size <= BUDGET_BYTES, (
        f"{size / 1048576:.1f} MB exceeds the {BUDGET_BYTES / 1048576:.0f} MB budget; "
        "re-encode with x264 (CRF 34, preset veryslow) rather than raising this"
    )


def test_it_carries_no_audio() -> None:
    """A background that can make a sound is a background that will, on
    somebody's machine, at the wrong moment. It is also bytes spent on silence.

    `smhd` is the sound media header, present in every audio track and nowhere
    else, so its absence is the whole assertion.
    """
    assert b"smhd" not in VIDEO.read_bytes(), "the clip has an audio track"


def test_it_is_h264_in_an_mp4_every_browser_takes() -> None:
    """AV1 would be smaller and Safari before 17 would show nothing at all.
    One file that works everywhere beats two that need a `<source>` list and
    twice the space in the repository."""
    head = VIDEO.read_bytes()[:4096]
    assert b"ftyp" in head, "not an MP4 container"
    assert b"avc1" in head, "not H.264 — check what every browser will do with it"
