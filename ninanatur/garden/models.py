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
    #: `circle` | `rect` | `polygon`. What shape it is — a resize handle edits
    #: two numbers and an angle, not four corners that could disagree.
    shape: str = "circle"
    #: Metres. For a circle this is the diameter and `depth` is unused.
    width: float = 1.0
    depth: float | None = None
    #: Degrees clockwise from north, like the compass and the solar azimuth.
    rotation: float = 0.0
    #: Metres relative to (x, y), for freehand shapes only.
    points: list[list[float]] | None = None
    #: None where nothing has a height — a street, a surface. Never a zero,
    #: which would be a measurement nobody took.
    height: float | None = None
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


#: The one kind that holds plants. Everything else is ground, structure or
#: planting-free surface — and which is which is a property of the element now,
#: not a separate table.
PLANTING_KIND = "bed"


@dataclass(frozen=True)
class Element:
    """Anything drawn on the plan.

    Wave 11 merged `Bed` and `Obstacle` into this. Being a planting site is a
    property, which is what lets the user draw a shape first and say what it is
    afterwards — the site attributes below are simply null on a paving slab.
    """

    element_id: int
    kind: str
    #: 'polygon' | 'circle' | 'line'.
    shape: str
    x: float
    y: float
    #: Outline for a polygon, centreline for a line, None for a circle.
    points: list[list[float]] | None = None
    #: A circle's diameter or a line's band width.
    width: float | None = None
    #: 'rect' when the corners are meant to stay square. A promise about how
    #: handles behave, not a second geometry.
    constraint_hint: str | None = None
    height: float | None = None
    height_source: str = "user"
    label: str | None = None

    # --- what a planting site needs, null on everything else ----------------
    name: str | None = None
    soil_type: str | None = None
    moisture: str | None = None
    ellenberg_l: float | None = None
    ellenberg_m: float | None = None
    ellenberg_n: float | None = None
    ellenberg_r: float | None = None
    sun_hours: float | None = None
    light_computed_at: str | None = None
    #: A raised bed stands above the low things around it, and its light is
    #: computed from up there.
    height_above_ground: float = 0.0
    plantings: list[Planting] = field(default_factory=list)

    @property
    def is_planting_site(self) -> bool:
        return self.kind == PLANTING_KIND

    @property
    def footprint(self) -> list[tuple[float, float]]:
        """The ground this covers. One function for shading, sightlines and
        drawing alike — three answers is how they drift."""
        from ninanatur.garden.footprint import Shape, footprint_of

        return footprint_of(
            shape=Shape(self.shape), x=self.x, y=self.y, width=self.width,
            # Gone from storage in Wave 11: a rectangle is its points, and
            # rotation is applied to them rather than stored beside them.
            depth=None, rotation=0.0, points=self.points,
        )

    @property
    def polygon(self) -> Polygon:
        """The outline in absolute metres, for callers that want a plain list."""
        return [[px, py] for px, py in self.footprint]

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

    # --- names the rest of the project still speaks --------------------------
    # Transitional, and said so plainly: features 43-46 move the API and the
    # frontend onto `element_id`, and these go with the last of them. They exist
    # so the merge lands in one piece instead of as a forty-file rewrite.

    @property
    def bed_id(self) -> int:
        return self.element_id

    @property
    def obstacle_id(self) -> int:
        return self.element_id


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
    #: Asked once and used as the starting point for beds drawn afterwards.
    soil_type: str | None = None
    moisture: str | None = None
    #: Flower colours this garden recorded itself. Never the catalogue's.
    observed_colours: dict[int, str] = field(default_factory=dict)
    elements: list[Element] = field(default_factory=list)

    @property
    def beds(self) -> list[Element]:
        """The elements you can plant in. A view, not a second store — which is
        the whole point of the merge."""
        return [e for e in self.elements if e.is_planting_site]

    @property
    def obstacles(self) -> list[Element]:
        """Everything else. It still casts shade and blocks a view."""
        return [e for e in self.elements if not e.is_planting_site]
