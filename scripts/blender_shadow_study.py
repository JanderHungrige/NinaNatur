"""Doc 122's independent check, made in Blender: where a 10 × 8 × 9 m block's
shadow ends, rendered by Cycles under the sun at NREL SPA's position.

    blender --background --factory-startup --python scripts/blender_shadow_study.py

Near Osnabrück (52.1682° N, 8.3837° E), 13 August 2026, 11:38:25 UTC, SPA puts
the sun at 52.3785° altitude and 182.8007° azimuth. The block stands on a
plane, its middle at the origin, north along +Y. An orthographic camera looks
straight down on 20 × 20 m at a centimetre a pixel; the sun is a point
(angle 0), the world is black and light does not bounce, so a pixel of ground
is lit or in the shadow. The shadow's edges are read off the render — the far
edge's row, the east edge's column, the west edge's slant, each to a fraction
of a pixel from the anti-aliased coverage — and the far corners they meet in
are printed beside the points trigonometry gives: (−4.661, 10.928) and
(5.339, 10.928) m.

Runs in Blender's own Python, with Blender's numpy; nothing of NinaNatur is
imported, which is the point.
"""
from __future__ import annotations

import math
import os
import tempfile

import bpy  # type: ignore[import-not-found]
import numpy as np
from mathutils import Vector  # type: ignore[import-not-found]

ALTITUDE, AZIMUTH = 52.3785, 182.8007
#: What is rendered, in metres: 20 m square, south-west corner here.
LEFT, BOTTOM, SIZE, PIXELS = -10.0, -6.5, 20.0, 2000
EXPECTED = {"north-west": (-4.661, 10.928), "north-east": (5.339, 10.928)}


def build_scene() -> None:
    """The plane, the block, a point-like sun and a camera looking down."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    bpy.ops.mesh.primitive_plane_add(size=80.0, location=(0.0, 0.0, 0.0))
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, 4.5))
    bpy.context.object.scale = (10.0, 8.0, 9.0)

    light = bpy.data.lights.new("Sun", type="SUN")
    light.angle = 0.0
    light.energy = 3.0
    sun = bpy.data.objects.new("Sun", light)
    scene.collection.objects.link(sun)
    h, a = math.radians(ALTITUDE), math.radians(AZIMUTH)
    towards = Vector((math.sin(a) * math.cos(h), math.cos(a) * math.cos(h), math.sin(h)))
    # A sun lamp shines along its own −Z: its +Z points at the sun.
    sun.rotation_mode = "QUATERNION"
    sun.rotation_quaternion = towards.to_track_quat("Z", "Y")

    camera_data = bpy.data.cameras.new("Down")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = SIZE
    camera = bpy.data.objects.new("Down", camera_data)
    camera.location = (LEFT + SIZE / 2, BOTTOM + SIZE / 2, 60.0)
    scene.collection.objects.link(camera)
    scene.camera = camera

    world = bpy.data.worlds.new("Dark")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.0
    scene.world = world

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = False
    scene.cycles.max_bounces = 0
    scene.cycles.pixel_filter_type = "BOX"
    scene.render.filter_size = 1.0
    scene.render.resolution_x = scene.render.resolution_y = PIXELS
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.color_depth = "32"


def render() -> np.ndarray:
    """The render's red channel, row 0 the southern edge, linear."""
    path = os.path.join(tempfile.mkdtemp(prefix="shadow-study-"), "down.exr")
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    image = bpy.data.images.load(path)
    pixels = np.array(image.pixels[:], dtype=float).reshape(PIXELS, PIXELS, 4)
    return pixels[..., 0]


def shadow_run(light: np.ndarray, lit: float, rows: slice, cols: slice, axis: int) -> np.ndarray:
    """How many metres of shadow each row (axis 1) or column (axis 0) of the
    window holds, counting a half-lit pixel as half."""
    dark = np.clip(1.0 - light[rows, cols] / lit, 0.0, 1.0)
    return dark.sum(axis=axis) * SIZE / PIXELS


def index(metres: float, origin: float) -> int:
    return int(round((metres - origin) / SIZE * PIXELS))


def main() -> None:
    build_scene()
    light = render()
    lit = float(np.median(light[index(12.5, BOTTOM):index(13.2, BOTTOM),
                                index(-6.0, LEFT):index(6.0, LEFT)]))
    # The far edge: columns across its middle, shadow from y = 9 northwards.
    far = shadow_run(light, lit, slice(index(9.0, BOTTOM), index(12.5, BOTTOM)),
                     slice(index(-3.0, LEFT), index(3.0, LEFT)), axis=0)
    top = 9.0 + float(np.mean(far))
    # The east edge, north of the block: shadow from x = 4.5 eastwards.
    rows = slice(index(5.0, BOTTOM), index(10.0, BOTTOM))
    east = 4.5 + float(np.mean(shadow_run(light, lit, rows, slice(index(4.5, LEFT),
                                                              index(7.0, LEFT)), axis=1)))
    # The west edge leans: shadow from its line eastwards to x = −3.5, fitted.
    west = -3.5 - shadow_run(light, lit, rows, slice(index(-6.5, LEFT), index(-3.5, LEFT)),
                             axis=1)
    ys = BOTTOM + (np.arange(PIXELS)[rows] + 0.5) * SIZE / PIXELS
    slope, offset = np.polyfit(ys, west, 1)
    found = {"north-west": (offset + slope * top, top), "north-east": (east, top)}
    for name, (x, y) in found.items():
        ex, ey = EXPECTED[name]
        print(f"SHADOW-STUDY {name}: rendered ({x:.4f}, {y:.4f}) m, by hand ({ex}, {ey}) m, "
              f"{math.hypot(x - ex, y - ey) * 1000:.1f} mm apart")


main()
