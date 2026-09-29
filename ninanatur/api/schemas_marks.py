"""What the shadow marks take and answer with (doc 122)."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, field_validator

from ninanatur.api.schemas_garden_in import Metres

#: The earliest moment a mark may name: the sun's formula is good for this
#: century and the last, and nobody saw a shadow in their garden before it.
EARLIEST_YEAR = 2000


class ShadowMarkIn(BaseModel):
    """Where the gardener saw the shadow of one standing thing end, and when."""

    #: The house, wall, hedge or tree whose shadow it is.
    element_id: int
    x: Metres
    y: Metres
    #: When it was seen, with its offset: the page sends its own clock's time.
    seen_at: AwareDatetime

    @field_validator("seen_at")
    @classmethod
    def _a_moment_the_model_knows(cls, value: datetime) -> datetime:
        """In UTC, and in a year the sun's formula is good for. Year 1 in an
        offset east of Greenwich cannot even be turned into UTC (review,
        2026-09-28), and answered with a 500."""
        try:
            moment = value.astimezone(UTC)
        except (OverflowError, ValueError) as error:
            raise ValueError("kein Zeitpunkt, den das Modell kennt") from error
        if moment.year < EARLIEST_YEAR:
            raise ValueError(f"vor {EARLIEST_YEAR} rechnet das Modell die Sonne nicht")
        return moment


class ShadowReadingOut(BaseModel):
    """The model's shadow edge against the mark, worked out now."""

    #: The sun at the mark's moment, as the model places it.
    altitude: float
    azimuth: float
    #: The model's shadow of the thing then, as rings in garden metres.
    rings: list[list[list[float]]]
    #: The nearest point of that shadow's edge on the ground, and how far it is.
    nearest: list[float]
    offset_m: float
    #: Which way that edge faces: away from the sun — a top cast it — towards
    #: it, where a shadow begins (a crown's base), or along it, its side.
    edge: Literal["far", "near", "side"]
    #: Whether the mark lies inside the model's shadow: the model's shadow
    #: reaches past where the gardener saw it end.
    model_longer: bool
    #: The way from the mark to that point along the shadow's direction
    #: (positive: the model's edge further from the sun) and across it.
    along_m: float
    across_m: float
    #: What it amounts to: a height (positive, the model's thing as though
    #: taller) where it runs along the sun to a far edge; an angle (positive
    #: anticlockwise) where it runs across and round the thing. Null otherwise.
    height_m: float | None
    turned_deg: float | None


class ShadowMarkOut(BaseModel):
    mark_id: int
    element_id: int
    x: float
    y: float
    #: UTC, ISO 8601.
    seen_at: str
    #: Null where there is no reading: the thing no longer casts a shadow.
    reading: ShadowReadingOut | None


__all__ = ["ShadowMarkIn", "ShadowMarkOut", "ShadowReadingOut"]
