"""Visual QA renders for the 14 modular Apocalypse Environment models and assembled Street Diorama."""
import math
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import bpy
import numpy as np
from mathutils import Vector

from build_survivor import clear_scene, world_bounds
from environment_apocalypse import ALL_ENV_BUILDERS, build_apocalypse_street_scene
from palette import create_materials
from render_pack import _stitch_grid
from render_preview import (
    add_ground_disc,
    aim_camera,
    configure_renderer,
    load_rgba_np,
    render_image,
    save_rgba_np,
)


def _add_dusk_lights(center=(0.0, 0.0, 1.0), scale=1.0, bg_rgb=(0.12, 0.13, 0.16)):
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("DuskWorld")
    scene.world.use_nodes = True
    nt = scene.world.node_tree
    bg = nt.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (*bg_rgb, 1.0)
        bg.inputs["Strength"].default_value = 0.90

    # Warm sun key + cool sky fill + subtle rim
    sun_data = bpy.data.lights.new(name="SunKey", type="SUN")
    sun_data.energy = 3.2
    sun_data.color = (1.0, 0.91, 0.78)
    sun = bpy.data.objects.new(name="SunKey", object_data=sun_data)
    scene.collection.objects.link(sun)
    aim_camera(sun, (center[0] - 12 * scale, center[1] - 14 * scale, center[2] + 18 * scale), center)

    fill_data = bpy.data.lights.new(name="CoolFill", type="AREA")
    fill_data.energy = 420.0 * (scale ** 1.4)
    fill_data.size = 6.0 * scale
    fill_data.color = (0.72, 0.84, 1.0)
    fill = bpy.data.objects.new(name="CoolFill", object_data=fill_data)
    scene.collection.objects.link(fill)
    aim_camera(fill, (center[0] + 9 * scale, center[1] - 10 * scale, center[2] + 7 * scale), center)

    rim_data = bpy.data.lights.new(name="BackRim", type="AREA")
    rim_data.energy = 340.0 * (scale ** 1.4)
    rim_data.size = 6.0 * scale
    rim_data.color = (0.88, 0.92, 1.0)
    rim = bpy.data.objects.new(name="BackRim", object_data=rim_data)
    scene.collection.objects.link(rim)
    aim_camera(rim, (center[0], center[1] + 12 * scale, center[2] + 9 * scale), center)


def render_modular_kit_sheet(out_path, tile_size=460):
    tmp_dir = os.path.join(PROJECT_DIR, "renders", "_tmp_env_kit")
    os.makedirs(tmp_dir, exist_ok=True)
    tiles = []

    for slug, builder_fn, _ in ALL_ENV_BUILDERS:
        clear_scene()
        scene = bpy.context.scene
        configure_renderer(scene)

        materials, idx_map = create_materials(with_env_textures=True)
        obj, _ = builder_fn(materials, idx_map)
        mins, maxs = world_bounds([obj])
        c = [(mins[i] + maxs[i]) * 0.5 for i in range(3)]
        span = max(maxs[0] - mins[0], maxs[1] - mins[1], maxs[2] - mins[2], 0.8)

        _add_dusk_lights(center=c, scale=max(0.6, span / 3.0), bg_rgb=(0.14, 0.15, 0.18))
        add_ground_disc(radius=max(1.2, span * 0.72))

        cam_data = bpy.data.cameras.new("EnvTileCam")
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = span * 1.32
        cam_data.clip_start = 0.05
        cam_data.clip_end = 80.0
        cam = bpy.data.objects.new("EnvTileCam", cam_data)
        scene.collection.objects.link(cam)
        scene.camera = cam

        dist = span * 2.4
        # Elevated 3/4 view showing front + side + cracks on top
        cam_loc = (c[0] - dist * 0.78, c[1] - dist * 0.96, c[2] + dist * 0.68)
        aim_camera(cam, cam_loc, c)
        p = os.path.join(tmp_dir, f"env_{slug}.png")
        render_image(scene, p, tile_size, tile_size)
        tiles.append(load_rgba_np(p))

    sheet = _stitch_grid(tiles, cols=5, bg_rgb=(0.06, 0.07, 0.09), gap=4)
    save_rgba_np(sheet, out_path)
    for fn in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, fn))
    os.rmdir(tmp_dir)
    print(f"Saved {len(tiles)}-asset modular kit sheet: {out_path}")


def render_diorama_sheet(out_path):
    tmp_dir = os.path.join(PROJECT_DIR, "renders", "_tmp_diorama")
    os.makedirs(tmp_dir, exist_ok=True)
    clear_scene()
    scene = bpy.context.scene
    configure_renderer(scene)
    materials, idx_map = create_materials(with_env_textures=True)
    build_apocalypse_street_scene(materials, idx_map)

    _add_dusk_lights(center=(0.0, 2.0, 1.5), scale=3.2, bg_rgb=(0.10, 0.12, 0.15))

    # Warm orange point lights above both fire barrels
    for lname, lx, ly in (("FirePt_W", -4.4, 3.65), ("FirePt_E", 4.6, 3.75)):
        pl_data = bpy.data.lights.new(name=lname, type="POINT")
        pl_data.energy = 280.0
        pl_data.color = (1.0, 0.45, 0.12)
        pl_data.shadow_soft_size = 0.25
        pl = bpy.data.objects.new(name=lname, object_data=pl_data)
        pl.location = (lx, ly, 1.45)
        scene.collection.objects.link(pl)

    cam_data = bpy.data.cameras.new("DioramaCam")
    cam_data.type = "PERSP"
    cam_data.lens = 28.0
    cam_data.clip_start = 0.1
    cam_data.clip_end = 150.0
    cam = bpy.data.objects.new("DioramaCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    views = [
        ("wide",  (-3.5, -14.8, 7.6), (0.0,  3.2, 1.4), 1600, 740),
        ("close", (-7.8,  -3.6, 2.3), (3.8,  4.2, 1.5), 1600, 740),
    ]
    panels = []
    for tag, loc, tgt, w, h in views:
        aim_camera(cam, loc, tgt)
        p = os.path.join(tmp_dir, f"diorama_{tag}.png")
        render_image(scene, p, w, h)
        panels.append(load_rgba_np(p))

    gap = 6
    h0, w0, _ = panels[0].shape
    out_arr = np.zeros((h0 * 2 + gap, w0, 4), dtype=np.float32)
    out_arr[:, :, :3] = 0.05
    out_arr[:, :, 3] = 1.0
    # Top row in Blender numpy (row 0 = bottom) -> place wide view at top!
    out_arr[h0 + gap:, :, :] = panels[0]
    out_arr[:h0, :, :] = panels[1]
    save_rgba_np(out_arr, out_path)

    for fn in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, fn))
    os.rmdir(tmp_dir)
    print(f"Saved Apocalypse Street Diorama sheet: {out_path}")


def main():
    os.makedirs(os.path.join(PROJECT_DIR, "renders"), exist_ok=True)
    render_modular_kit_sheet(os.path.join(PROJECT_DIR, "renders", "env_modular_kit_sheet.png"))
    render_diorama_sheet(os.path.join(PROJECT_DIR, "renders", "env_apocalypse_street_scene.png"))


if __name__ == "__main__":
    main()
