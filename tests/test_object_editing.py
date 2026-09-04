"""Editing what an object is, after it has been drawn."""
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ninanatur.api.deps import get_connection
from ninanatur.ingest.db import connect, init_schema
from ninanatur.web.app import app

SQUARE = [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]]


@pytest.fixture()
def client() -> Iterator[TestClient]:
    conn = connect(":memory:", same_thread=False)
    init_schema(conn)
    app.dependency_overrides[get_connection] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def _garden(client: TestClient) -> tuple[str, int]:
    token = client.post(
        "/api/v1/gardens", json={"name": "G", "latitude": 52.5, "longitude": 13.4}
    ).json()["share_token"]
    bed = client.post(
        f"/api/v1/gardens/{token}/beds",
        json={"name": "B", "polygon": SQUARE, "soil_type": "loam", "moisture": "fresh"},
    ).json()["beds"][0]
    return token, int(bed["bed_id"])


def test_a_bed_can_be_raised_and_says_so(client: TestClient) -> None:
    token, bed_id = _garden(client)
    response = client.patch(
        f"/api/v1/gardens/{token}/beds/{bed_id}",
        json={"height_above_ground": 0.8, "label": "Hochbeet an der Mauer"},
    )
    assert response.status_code == 200, response.text
    bed = response.json()["beds"][0]
    assert bed["height_above_ground"] == 0.8
    assert bed["label"] == "Hochbeet an der Mauer"


def test_raising_a_bed_recomputes_its_light(client: TestClient) -> None:
    """Otherwise the number on screen describes a bed that no longer exists."""
    token, bed_id = _garden(client)
    client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "fence", "x": 0.0, "y": -1.0, "radius": 0.3, "height": 1.4},
    )
    before = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]["sun_hours"]

    client.patch(
        f"/api/v1/gardens/{token}/beds/{bed_id}", json={"height_above_ground": 1.6}
    )
    after = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]["sun_hours"]
    assert after > before


def test_an_obstacle_gets_a_kind_from_the_vocabulary(client: TestClient) -> None:
    token, _ = _garden(client)
    created = client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "tree", "x": 2.0, "y": -5.0, "radius": 3.0, "height": 8.0},
    )
    assert created.status_code in (200, 201), created.text
    obstacle = created.json()["obstacles"][0]

    response = client.patch(
        f"/api/v1/gardens/{token}/obstacles/{obstacle['obstacle_id']}",
        json={"kind": "hedge", "height": 2.5, "label": "Liguster zum Nachbarn"},
    )
    assert response.status_code == 200, response.text
    edited = response.json()["obstacles"][0]
    assert edited["kind"] == "hedge"
    assert edited["height"] == 2.5
    assert edited["label"] == "Liguster zum Nachbarn"


def test_an_invented_kind_is_refused(client: TestClient) -> None:
    """A free string means the shading table silently misses a value."""
    token, _ = _garden(client)
    response = client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "hedgehog", "x": 0.0, "y": 0.0, "radius": 1.0, "height": 1.0},
    )
    assert response.status_code == 422


def test_editing_an_obstacle_recomputes_the_light(client: TestClient) -> None:
    token, _ = _garden(client)
    created = client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "fence", "x": 0.0, "y": -1.0, "radius": 0.3, "height": 1.2},
    ).json()["obstacles"][0]
    before = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]["sun_hours"]

    client.patch(
        f"/api/v1/gardens/{token}/obstacles/{created['obstacle_id']}",
        json={"height": 6.0},
    )
    after = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]["sun_hours"]
    assert after < before, "a 6 m wall casts more shade than a 1.2 m fence"


def test_a_label_is_stored_as_text_not_interpreted(client: TestClient) -> None:
    token, bed_id = _garden(client)
    nasty = "<script>alert(1)</script>"
    body = client.patch(
        f"/api/v1/gardens/{token}/beds/{bed_id}", json={"label": nasty}
    ).json()
    assert body["beds"][0]["label"] == nasty


def test_editing_a_bed_of_another_garden_is_404(client: TestClient) -> None:
    _, bed_id = _garden(client)
    other = client.post(
        "/api/v1/gardens", json={"name": "H", "latitude": 52.5, "longitude": 13.4}
    ).json()["share_token"]
    response = client.patch(
        f"/api/v1/gardens/{other}/beds/{bed_id}", json={"height_above_ground": 1.0}
    )
    assert response.status_code == 404


def test_a_negative_height_is_refused(client: TestClient) -> None:
    token, bed_id = _garden(client)
    response = client.patch(
        f"/api/v1/gardens/{token}/beds/{bed_id}", json={"height_above_ground": -1.0}
    )
    assert response.status_code == 422


def test_an_edited_height_becomes_the_users_word_on_it(client: TestClient) -> None:
    """Wave 8 places buildings with assumed heights. Correcting one has to make
    it authoritative, or the sightline keeps marking it as a guess."""
    token, _ = _garden(client)
    created = client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "house", "x": 0.0, "y": -6.0, "radius": 4.0, "height": 7.0},
    ).json()["obstacles"][0]
    assert created["height_source"] == "user"

    edited = client.patch(
        f"/api/v1/gardens/{token}/obstacles/{created['obstacle_id']}",
        json={"height": 11.0, "height_source": "user"},
    ).json()["obstacles"][0]
    assert edited["height"] == 11.0
    assert edited["height_source"] == "user"


def test_dragging_a_vertex_drops_the_rectangle_promise(client: TestClient) -> None:
    """A rectangle's corners stay square only as long as it says they should.

    Editing one out of true ends that promise. The geometry never converts —
    it was points all along — so the only thing that changes is the hint.
    """
    token, _bed_id = _garden(client)
    made = client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "shed", "x": 0, "y": 0, "shape": "rect", "width": 4,
              "depth": 3, "height": 2},
    ).json()
    assert "obstacles" in made, made
    element = made["obstacles"][0]
    assert element["constraint_hint"] == "rect"

    moved = client.patch(
        f"/api/v1/gardens/{token}/obstacles/{element['obstacle_id']}",
        json={
            "points": [[-2, -1.5], [2, -1.5], [3.5, 1.5], [-2, 1.5]],
            "constraint_hint": None,
        },
    ).json()
    changed = moved["obstacles"][0]
    assert changed["constraint_hint"] is None
    assert len(changed["footprint"]) == 4
    # The dragged corner is where it was put, not snapped back to square.
    assert [3.5, 1.5] in changed["points"]


def test_resizing_a_rectangle_keeps_it_rectangular(client: TestClient) -> None:
    """The handles send a width, a depth and an angle — that is what a resize
    handle produces. The store turns them into points and keeps the promise."""
    token, _bed_id = _garden(client)
    made = client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "house", "x": 0, "y": 0, "shape": "rect", "width": 10,
              "depth": 8, "height": 6},
    ).json()["obstacles"][0]

    wider = client.patch(
        f"/api/v1/gardens/{token}/obstacles/{made['obstacle_id']}",
        json={"width": 14, "depth": 8, "rotation": 90},
    ).json()["obstacles"][0]

    assert wider["constraint_hint"] == "rect"
    assert len(wider["footprint"]) == 4
    xs = [p[0] for p in wider["footprint"]]
    ys = [p[1] for p in wider["footprint"]]
    # Turned a quarter turn: the 14 m side now runs north-south.
    assert max(ys) - min(ys) == pytest.approx(14, abs=0.05)
    assert max(xs) - min(xs) == pytest.approx(8, abs=0.05)


def test_moving_an_element_leaves_its_shape_alone(client: TestClient) -> None:
    """Dragging the body is a move, not a redraw. An update that named only
    x and y once reset the shape to its default, because the geometry
    conversion ran on whatever was left."""
    token, _bed_id = _garden(client)
    made = client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "pond", "x": 0, "y": 0, "shape": "circle", "width": 5},
    ).json()["obstacles"][0]

    moved = client.patch(
        f"/api/v1/gardens/{token}/obstacles/{made['obstacle_id']}",
        json={"x": 7, "y": -3},
    ).json()["obstacles"][0]
    assert moved["shape"] == "circle"
    assert moved["width"] == pytest.approx(5)
    assert moved["x"] == pytest.approx(7)


def test_an_element_never_loses_the_points_it_was_not_asked_about(
    client: TestClient,
) -> None:
    """Resizing a free polygon by width and depth used to null its points.

    The element then had no geometry, and *reading the garden at all* raised
    "a polygon footprint needs at least three points" — one resize of one
    triangle made the whole plan unreadable. Whatever the caller means by a
    width on a shape that has none, it cannot mean "throw the outline away".
    """
    token, _bed_id = _garden(client)
    made = client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "other", "x": 0, "y": 0, "shape": "polygon",
              "points": [[0, 3], [3, -3], [-3, -3]]},
    ).json()["obstacles"][0]

    resized = client.patch(
        f"/api/v1/gardens/{token}/obstacles/{made['obstacle_id']}",
        json={"x": 0, "y": 0, "width": 8, "depth": 6, "rotation": 0},
    )
    assert resized.status_code == 200, resized.json()
    kept = resized.json()["obstacles"][0]
    assert kept["points"] is not None
    assert len(kept["footprint"]) == 3

    # And the garden is still readable, which is the part that actually broke.
    assert client.get(f"/api/v1/gardens/{token}").status_code == 200


def test_an_element_can_be_deleted(client: TestClient) -> None:
    """Nothing could be removed from a plan until now. A shape drawn by mistake
    stayed on it."""
    token, _bed_id = _garden(client)
    made = client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "other", "x": 0, "y": 0, "shape": "polygon",
              "points": [[-2, -2], [2, -2], [2, 2], [-2, 2]]},
    ).json()["obstacles"][0]

    left = client.delete(
        f"/api/v1/gardens/{token}/obstacles/{made['obstacle_id']}"
    )
    assert left.status_code == 200, left.json()
    assert left.json()["obstacles"] == []


def test_deleting_a_bed_takes_its_plants(client: TestClient) -> None:
    """They cannot outlive the bed: `planting` hangs off `element_id`, and a
    row whose parent is gone is a query that fails at the worst moment."""
    token, bed_id = _garden(client)
    # By name rather than by taxon: the plant does not have to be in the
    # catalogue for the bed to hold it, and this test is about the bed.
    planted = client.post(
        f"/api/v1/gardens/{token}/beds/{bed_id}/plantings",
        json={"raw_name": "Nachbars Rose", "quantity": 2},
    )
    assert planted.status_code in {200, 201}, planted.json()
    assert planted.json()["unidentified_plantings"] == 1

    after = client.delete(f"/api/v1/gardens/{token}/obstacles/{bed_id}")
    assert after.status_code == 200
    assert after.json()["beds"] == []
    assert after.json()["unidentified_plantings"] == 0


def test_deleting_something_that_is_not_there_is_404(client: TestClient) -> None:
    token, _bed_id = _garden(client)
    assert client.delete(f"/api/v1/gardens/{token}/obstacles/9999").status_code == 404


def test_a_kind_with_no_height_is_given_none_rather_than_zero(
    client: TestClient,
) -> None:
    """Wave 8's rule, at the one edge that still broke it.

    A street, a lawn, a pond have no height. The endpoint turned the
    vocabulary's `None` into `0.0`, which is a measurement nobody took — and it
    is the difference between "nothing stands here" and "something stands here,
    zero metres tall".
    """
    token, _bed_id = _garden(client)
    made = client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "street", "x": 0, "y": 0, "shape": "line", "width": 6,
              "points": [[0, 0], [20, 0]]},
    ).json()["obstacles"][0]
    assert made["height"] is None


def test_a_kind_that_stands_still_gets_its_usual_height(client: TestClient) -> None:
    """The default is still filled in where the vocabulary has one."""
    token, _bed_id = _garden(client)
    made = client.post(
        f"/api/v1/gardens/{token}/obstacles",
        json={"kind": "shed", "x": 0, "y": 0},
    ).json()["obstacles"][0]
    assert made["height"] is not None
    assert made["height"] > 0


def test_a_bed_carries_the_geometry_it_can_be_reshaped_by(client: TestClient) -> None:
    """Wave 15, feature 2. `BedOut` used to carry only `polygon` — the outline in
    absolute metres, with no origin, no points and no shape.

    The canvas draws beds and obstacles from one array, but handles are built
    from `x`/`y`/`points`, so a bed had nothing to hang them on. Labelling a
    shape "Blumenbeet" moved it into the other array and it silently stopped
    being reshapeable.
    """
    token, _bed_id = _garden(client)
    bed = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]

    for field in ("kind", "shape", "x", "y", "points", "width", "constraint_hint"):
        assert field in bed, f"a bed cannot be reshaped without {field}"
    assert bed["kind"] == "bed"
    assert bed["shape"] == "polygon"


def test_a_bed_can_actually_be_reshaped(client: TestClient) -> None:
    """The fields are only worth having if the edit goes through. `element` is
    one table and `update_obstacle` never looked at the kind, so this half
    always worked — nothing in the client could reach it."""
    token, bed_id = _garden(client)

    triangle = [[0.0, 0.0], [4.0, 0.0], [2.0, 3.0]]
    response = client.patch(
        f"/api/v1/gardens/{token}/obstacles/{bed_id}",
        json={"points": triangle, "constraint_hint": None},
    )

    assert response.status_code == 200
    after = client.get(f"/api/v1/gardens/{token}").json()["beds"][0]
    assert after["points"] == triangle
    assert len(after["polygon"]) == 3, "the outline follows the points"
