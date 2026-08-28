"""The version in the header. Derived, never edited."""
from pathlib import Path

from ninanatur.version import (
    MAJOR,
    UNKNOWN,
    VERSION_ENV,
    app_version,
    completed_waves,
    compute_version,
    merge_count,
)


def test_the_baked_value_wins_over_anything_computed(monkeypatch) -> None:
    """Inside the container there is no git history and no .mdd, so a computed
    fallback there would be wrong rather than merely missing."""
    monkeypatch.setenv(VERSION_ENV, "V0.9.42")
    assert app_version() == "V0.9.42"


def test_a_blank_env_var_does_not_win(monkeypatch) -> None:
    monkeypatch.setenv(VERSION_ENV, "   ")
    assert app_version() != "   "


def test_the_computed_version_has_the_documented_shape(monkeypatch) -> None:
    monkeypatch.delenv(VERSION_ENV, raising=False)
    version = app_version()
    assert version == UNKNOWN or version.startswith(f"V{MAJOR}.")


def test_completed_waves_counts_only_completed_ones(tmp_path: Path) -> None:
    (tmp_path / "ninanatur-wave-1.md").write_text("---\nstatus: complete\n---\n")
    (tmp_path / "ninanatur-wave-2.md").write_text("---\nstatus: complete\n---\n")
    (tmp_path / "ninanatur-wave-3.md").write_text("---\nstatus: planned\n---\n")
    assert completed_waves(tmp_path) == 2


def test_a_completed_later_wave_wins_over_a_planned_earlier_one(tmp_path: Path) -> None:
    """The highest complete, not the count — waves are not always finished in order."""
    (tmp_path / "ninanatur-wave-1.md").write_text("---\nstatus: complete\n---\n")
    (tmp_path / "ninanatur-wave-7.md").write_text("---\nstatus: complete\n---\n")
    assert completed_waves(tmp_path) == 7


def test_no_waves_directory_is_zero_not_an_error(tmp_path: Path) -> None:
    assert completed_waves(tmp_path / "nope") == 0


def test_merge_count_outside_a_repo_is_none(tmp_path: Path) -> None:
    """Better an honest None than a confidently wrong zero."""
    assert merge_count(tmp_path) is None


def test_the_version_matches_this_repository() -> None:
    """Ties the format to reality rather than to a fixture."""
    version = compute_version()
    assert version is not None, "this test runs inside the repository"
    major, wave, merges = version.removeprefix("V").split(".")
    assert int(major) == MAJOR
    assert int(wave) >= 5, "waves 1-5 are complete"
    assert int(merges) >= 7


def test_the_version_never_contains_whitespace_or_newlines() -> None:
    version = app_version()
    assert version == version.strip()
    assert "\n" not in version
