"""The Draft Sketch converter (doc 97): his style file in, a theme out.

Everything here runs without the network and, except the last two tests,
without his file: the PNG reading, the CIM reading and the emitting are tested
on small examples made here. The byte-for-byte regeneration runs wherever the
pinned file has been fetched.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import struct
import zlib
from pathlib import Path

import pytest

from scripts.draft_sketch import cim, emit, png
from scripts.draft_sketch.layers import layers_of
from scripts.draft_sketch.lines import line_overlays_of
from scripts.draft_sketch.tiles import Images
from scripts.stylx_to_theme import SOURCE, PinMismatch, generate, verified

ROOT = Path(__file__).resolve().parents[1]


def _rgba(width: int, height: int) -> bytes:
    """A small image with every channel varying, so filters have work to do."""
    return bytes(
        value
        for y in range(height)
        for x in range(width)
        for value in ((x * 40) % 256, (y * 60) % 256, (x * y * 7) % 256, (255 - x * 20) % 256)
    )


def _filtered(kind: int, line: bytes, previous: bytes) -> bytes:
    """PNG's five row filters, forwards — written here independently of the
    decoder, so a round trip checks one against the other."""
    out = bytearray()
    for i, value in enumerate(line):
        left = line[i - 4] if i >= 4 else 0
        up, upleft = previous[i], previous[i - 4] if i >= 4 else 0
        guess = left + up - upleft
        paeth = min((abs(guess - left), 0, left), (abs(guess - up), 1, up),
                    (abs(guess - upleft), 2, upleft))[2]
        predicted = [0, left, up, (left + up) // 2, paeth][kind]
        out.append((value - predicted) % 256)
    return bytes(out)


def _png(width: int, height: int, rgba: bytes, row_filter: int = 0) -> bytes:
    def chunk(kind: bytes, body: bytes) -> bytes:
        crc = struct.pack(">I", zlib.crc32(kind + body))
        return struct.pack(">I", len(body)) + kind + body + crc

    stride, raw, previous = width * 4, bytearray(), bytes(width * 4)
    for row in range(height):
        line = rgba[row * stride:(row + 1) * stride]
        raw += bytes([row_filter]) + _filtered(row_filter, line, previous)
        previous = line
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (png.SIGNATURE + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(raw)))
            + chunk(b"IEND", b""))


# --- png --------------------------------------------------------------------------------

def test_every_filter_a_png_may_use_is_read() -> None:
    """His images were written by another encoder, which chooses its own row
    filters; all five are decoded."""
    pixels = _rgba(6, 5)
    for kind in range(5):
        decoded = png.decode(_png(6, 5, pixels, row_filter=kind))
        assert (decoded.width, decoded.height, decoded.rgba) == (6, 5, pixels), f"filter {kind}"
    assert png.dimensions(_png(6, 5, pixels)) == (6, 5)


def test_what_it_cannot_read_it_refuses() -> None:
    with pytest.raises(ValueError, match="not a PNG"):
        png.decode(b"GIF89a")
    sixteen_bit = bytearray(_png(1, 1, bytes(4)))
    sixteen_bit[24] = 16  # IHDR's bit depth
    with pytest.raises(ValueError, match="unsupported"):
        png.decode(bytes(sixteen_bit))


def test_a_wash_is_white_and_ink_is_not() -> None:
    white = png.Image(2, 1, bytes([255, 255, 255, 200, 255, 255, 255, 0]))
    ink = png.Image(2, 1, bytes([0, 0, 0, 255, 255, 255, 255, 0]))
    assert png.brightness(white) == pytest.approx(1.0) and png.is_wash(white)
    # Weighted by what is painted: the transparent white pixel does not count.
    assert png.brightness(ink) == 0.0 and not png.is_wash(ink)
    assert png.coverage(white) == pytest.approx(200 / 510)


# --- cim --------------------------------------------------------------------------------

def _picture(width: int = 2, height: int = 2) -> str:
    data = base64.b64encode(_png(width, height, bytes([255] * width * height * 4))).decode()
    return f"data:image/png;base64,{data[:10]}\r\n{data[10:]}"  # his are broken into lines


def test_colours_are_read_whatever_model_they_are_given_in() -> None:
    assert cim.colour({"type": "CIMRGBColor", "values": [171, 205, 102, 100]}) == ("#abcd66", 1.0)
    assert cim.colour({"type": "CIMRGBColor", "values": [0, 0, 0, 20]}) == ("#000000", 0.2)
    # HSV with saturation and value in per cent, as CIM stores them.
    assert cim.colour({"type": "CIMHSVColor", "values": [120, 100, 50, 100]}) == ("#008000", 1.0)


def test_a_symbols_layers_are_read_top_first_with_what_they_need() -> None:
    symbol = {
        "type": "CIMPolygonSymbol",
        "symbolLayers": [
            {"type": "CIMPictureStroke", "enable": True, "width": 2, "url": _picture(),
             "tintColor": {"type": "CIMRGBColor", "values": [0, 0, 0, 100]},
             "effects": [{"type": "CIMGeometricEffectWave", "amplitude": 1, "period": 18,
                          "seed": 1, "waveform": "Random"}]},
            {"type": "CIMPictureMarker", "enable": True, "size": 32, "rotation": 45,
             "url": _picture(),
             "tintColor": {"type": "CIMRGBColor", "values": [176, 205, 103, 100]},
             "markerPlacement": {"type": "CIMMarkerPlacementInsidePolygon", "stepX": 30,
                                 "stepY": 98, "seed": 41, "gridType": "Random", "randomness": 100}},
            {"type": "CIMPictureMarker", "enable": False, "size": 9, "url": _picture()},
            {"type": "CIMSolidFill", "enable": True,
             "color": {"type": "CIMHSVColor", "values": [96.84, 25, 90, 100]},
             "effects": [{"type": "CIMGeometricEffectMove", "offsetX": 6, "offsetY": -6}]},
        ],
    }
    layers = layers_of(symbol)
    assert [layer.kind for layer in layers] == ["stroke", "scatter", "fill"]
    stroke, scatter, fill = layers
    assert stroke.width_pt == 2 and stroke.wave == cim.Wave(amplitude=1, period=18, seed=1)
    assert png.dimensions(stroke.image) == (2, 2)
    assert scatter.size_pt == 32 and scatter.step_pt == (30, 98) and scatter.seed == 41
    assert scatter.colour == ("#b0cd67", 1.0) and scatter.randomness == 1.0
    assert fill.move_pt == (6, -6)


def test_a_layer_it_does_not_draw_is_refused_by_name() -> None:
    with pytest.raises(ValueError, match="CIMCharacterMarker"):
        layers_of({"symbolLayers": [{"type": "CIMCharacterMarker", "enable": True}]})


def test_his_rings_and_serrations_are_read_as_what_they_are() -> None:
    """His Tree 2 (doc 98): a stroke round the outline drawn smaller about its
    middle, and marks along it that swell and shrink."""
    wave = {"type": "CIMGeometricEffectWave", "amplitude": 8, "period": 8, "seed": 15}
    symbol = {"symbolLayers": [
        {"type": "CIMPictureMarker", "enable": True, "size": 1, "rotation": 90, "url": _picture(),
         "tintColor": {"type": "CIMRGBColor", "values": [0, 0, 0, 100]},
         "markerPlacement": {"type": "CIMMarkerPlacementAlongLineVariableSize",
                             "placementTemplate": [8], "numberOfSizes": 4, "minZoom": 0.5,
                             "maxZoom": 1.5, "seed": 13,
                             "variationMethod": "IncreasingThenDecreasing"}},
        {"type": "CIMSolidStroke", "enable": True, "width": 2,
         "color": {"type": "CIMRGBColor", "values": [0, 0, 0, 100]},
         "effects": [wave, {"type": "CIMGeometricEffectScale", "xScaleFactor": 0.6,
                            "yScaleFactor": 0.6}]},
    ]}
    along, ring = layers_of(symbol)
    assert along.kind == "along" and along.step_pt == (8, 0)
    assert along.sizes == (0.5, 0.8333, 1.1667, 1.5, 1.1667, 0.8333)
    assert ring.kind == "stroke" and ring.scale == 0.6


def test_a_line_symbol_is_laid_along_a_line() -> None:
    """His Wood Fence (doc 98): posts every 36 points, and his line."""
    place = {"type": "CIMMarkerPlacementAlongLineSameSize", "placementTemplate": [36],
             "offsetAlongLine": 5}
    square = {"type": "CIMMarkerGraphic",
              "geometry": {"rings": [[[-5, 5], [5, 5], [5, -5], [-5, -5], [-5, 5]]]},
              "symbol": {"symbolLayers": [{"type": "CIMSolidFill",
                                           "color": {"type": "CIMRGBColor",
                                                     "values": [255, 255, 255, 100]}}]}}
    symbol = {"symbolLayers": [
        {"type": "CIMVectorMarker", "enable": True, "size": 6, "markerPlacement": place,
         "frame": {"xmin": -5, "ymin": -5, "xmax": 5, "ymax": 5}, "markerGraphics": [square]},
        {"type": "CIMSolidStroke", "enable": True, "width": 3,
         "color": {"type": "CIMRGBColor", "values": [0, 0, 0, 100]}},
    ]}
    drawn, masks = line_overlays_of("ds-fence", layers_of(symbol), Images())
    assert [o["kind"] for o in drawn] == ["line-ink", "line-boxes"]
    assert drawn[1]["colour"] == "#ffffff" and drawn[1]["spacing"] == pytest.approx(3.175, abs=1e-3)
    assert masks == set()


def test_his_json_is_read_up_to_its_nul() -> None:
    assert cim.load('{"type": "CIMPolygonSymbol", "symbolLayers": []}\x00') == {
        "type": "CIMPolygonSymbol", "symbolLayers": []}


# --- emit -------------------------------------------------------------------------------

def test_the_symbols_file_names_whose_marks_it_holds_and_loads_nothing_inline() -> None:
    source = emit.symbols_file(
        [emit.Pattern(id="ds-grass", width=6.0, height=6.0, base="#b8d08a",
                      pieces=(emit.Mark("ds-f08c1e65", 0.5, 1.0, 2.0, 2.0, 45.0, "#abcd66"),))],
        [], {"ds-f08c1e65": "images/ds-f08c1e65.png"}, stylx_sha256="4ef38ef8")
    assert source.startswith("/**\n * Provenance: Warren Davison (Draft Sketch)\n")
    assert "import ds_f08c1e65 from './images/ds-f08c1e65.png';" in source
    assert "data:" not in source
    assert 'id="ds-grass"' in source
    # A tint is his colour through the image's alpha.
    assert 'fill="#abcd66" mask="url(#ds-f08c1e65-mask)"' in source
    # And every image is there by its key, for marks laid along a line.
    assert "  'ds-f08c1e65': ds_f08c1e65," in source
    assert '<mask id="ds-f08c1e65-mask"' in source and 'mask-type="alpha"' in source


def test_a_mark_on_a_sheet_gets_its_mask_too() -> None:
    """A tinted mark drawn without its mask is a hard-edged square of colour —
    which is what every splotch became when marks moved onto sheets and the
    masks were looked for on the tile alone."""
    sheet = emit.Sheet(2.0, 2.0, (emit.Mark("ds-1bb4640e", 1.0, 1.0, 1.0, 1.0, 0.0, "#5c8944"),))
    source = emit.symbols_file([emit.Pattern(id="ds-tree", width=4.0, height=4.0, pieces=(sheet,))],
                               [], {"ds-1bb4640e": "images/ds-1bb4640e.png"}, stylx_sha256="0" * 64)
    assert '<mask id="ds-1bb4640e-mask"' in source


def test_nothing_but_ids_numbers_and_colours_reaches_the_markup() -> None:
    with pytest.raises(ValueError, match="refused"):
        emit.symbols_file([emit.Pattern(id='ds-x" onload="alert(1)', width=1, height=1)],
                          [], {}, stylx_sha256="0" * 64)
    with pytest.raises(ValueError, match="refused"):
        emit.symbols_file([emit.Pattern(id="ds-x", width=1, height=1, base="red")],
                          [], {}, stylx_sha256="0" * 64)


def test_numbers_are_written_to_the_millimetre() -> None:
    written = [emit.number(v) for v in (1.0, 0.12345, -0.0001, 17.7777)]
    assert written == ["1", "0.123", "0", "17.778"]


# --- the file itself --------------------------------------------------------------------

def test_a_file_that_is_not_the_pinned_one_is_refused(tmp_path: Path) -> None:
    impostor = tmp_path / "Draft_Sketch.stylx"
    impostor.write_bytes(b"not his style")
    with pytest.raises(PinMismatch):
        verified(impostor, json.loads(SOURCE.read_text()))


def test_the_pin_says_where_the_file_comes_from() -> None:
    pin = json.loads(SOURCE.read_text())
    assert pin["url"].startswith("https://www.arcgis.com/sharing/rest/content/items/")
    assert pin["bytes"] == 17_096_704
    assert len(pin["sha256"]) == 64


STYLX = ROOT / "assets" / "draft-sketch" / "Draft_Sketch.stylx"
GENERATED = ROOT / "frontend" / "src" / "themes" / "draft-sketch" / "generated"
fetched = pytest.mark.skipif(not STYLX.exists(), reason="the pinned .stylx is not fetched here")


@fetched
def test_the_theme_is_a_derivation_regenerated_byte_for_byte(tmp_path: Path) -> None:
    generate(STYLX, tmp_path)
    made = {p.relative_to(tmp_path): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    kept = {p.relative_to(GENERATED): p.read_bytes() for p in GENERATED.rglob("*") if p.is_file()}
    assert made.keys() == kept.keys()
    changed = [str(name) for name in made if made[name] != kept[name]]
    assert changed == []


@fetched
def test_everything_his_markup_refers_to_is_in_it() -> None:
    symbols = (GENERATED / "symbols.ts").read_text()
    rules = (GENERATED / "rules.ts").read_text()
    defined = set(re.findall(r'id="([^"]+)"', symbols))
    wanted = set(re.findall(r"url\(#([^)]+)\)", symbols + rules))
    wanted |= set(re.findall(r'"mask": "([^"]+)"', rules))
    assert wanted - defined == set()


@fetched
def test_only_the_images_the_theme_uses_are_kept() -> None:
    symbols = (GENERATED / "symbols.ts").read_text() + (GENERATED / "rules.ts").read_text()
    for image in (GENERATED / "images").glob("*.png"):
        assert f"./images/{image.name}" in symbols, f"{image.name} is kept and never used"
    total = sum(p.stat().st_size for p in (GENERATED / "images").glob("*.png"))
    assert total < 1_500_000, f"{total} bytes of images"
    pinned = json.loads(SOURCE.read_text())["sha256"]
    assert hashlib.sha256(STYLX.read_bytes()).hexdigest() == pinned
