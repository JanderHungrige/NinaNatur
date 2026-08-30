"""Garden domain types, independent of how they are stored or served."""
from __future__ import annotations

from dataclasses import dataclass, field

Polygon = list[list[float]]


@dataclass(frozen=True)
class BedInput:
    """What a caller supplies to create or update a bed."""

    name: str
    polygon: Polygon
    soil_type: str | None = None
    moisture: str | None = None


@dataclass(frozen=True)
class ObstacleInput:
    """Anything that casts a shadow — a wall, hedge, tree or shed."""

    kind: str
    x: float
    y: float
    radius: float
    height: float
    label: str | None = None
    height_source: str = "user"


@dataclass(frozen=True)
class Planting:
    """One species in one bed, with how many of it."""

    planting_id: int
    # None when the catalogue could not name it. The raw name is then the only
    # thing identifying the plant, and it is the user's own words.
    taxon_id: int | None
    canonical_name: str | None
    quantity: int
    added_at: str
    raw_name: str | None = None

    @property
    def identified(self) -> bool:
        return self.taxon_id is not None

    @property
    def display_name(self) -> str:
        """What to call it. The user's words win when we have no name of ours."""
        return self.canonical_name or self.raw_name or "unbenannt"


@dataclass(frozen=True)
class Bed:
    """A stored bed, with its derived site vector and the evidence behind it."""

    bed_id: int
    name: str
    polygon: Polygon
    soil_type: str | None
    moisture: str | None
    ellenberg_l: float | None
    ellenberg_m: float | None
    ellenberg_n: float | None
    ellenberg_r: float | None
    sun_hours: float | None
    light_computed_at: str | None
    # A raised bed stands above the low things around it, and its light is
    # computed from up there.
    height_above_ground: float = 0.0
    label: str | None = None
    plantings: list[Planting] = field(default_factory=list)

    @property
    def site_axes(self) -> dict[str, float]:
        """The axes that are actually known — absent ones are omitted, not zeroed."""
        pairs = (
            ("ellenberg_l", self.ellenberg_l),
            ("ellenberg_m", self.ellenberg_m),
            ("ellenberg_n", self.ellenberg_n),
            ("ellenberg_r", self.ellenberg_r),
        )
        return {key: value for key, value in pairs if value is not None}


@dataclass(frozen=True)
class Obstacle:
    obstacle_id: int
    kind: str
    x: float
    y: float
    radius: float
    height: float
    label: str | None = None
    height_source: str = "user"


@dataclass(frozen=True)
class Garden:
    """A whole plan. The share token is its only access control."""

    garden_id: int
    share_token: str
    owner_id: str | None
    name: str
    latitude: float
    longitude: float
    created_at: str
    updated_at: str
    beds: list[Bed] = field(default_factory=list)
    obstacles: list[Obstacle] = field(default_factory=list)
