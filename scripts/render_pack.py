"""Batch 1 visual QA renderer: 17-weapon armory sheet, hand/mechanics QA, 5 survivor sheets & lineup."""
import math
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import bpy
import numpy as np
from mathutils import Euler, Vector

from build_survivor import clear_scene, world_bounds
from palette import create_materials
from render_preview import (
    add_ground_disc,
    add_studio_lights,
    aim_camera,
    configure_renderer,
    load_rgba_np,
    render_image,
    save_rgba_np,
)
from rig_mechanics import (
    _make_rifle_world_matrix,
    _rot_bone,
    apply_aim_ads_pose,
    apply_bow_draw_pose,
    apply_crouch_aim_pose,
    apply_head_look_at,
    apply_hit_react_pose,
    apply_melee_swing_pose,
    apply_reload_pose,
    apply_run_pose,
    apply_strafe_pose,
    apply_survivor_pose,
    apply_walk_pose,
    apply_zombie_bite_pose,
    apply_zombie_lunge_pose,
    apply_zombie_shamble_pose,
    pose_hand_grip,
    reset_pose,
    snap_feet_to_floor,
    solve_gun_first_weapon_ik,
)
from survivors import (
    ROLE_POSE_MAP,
    SURVIVOR_BUILDERS,
    SURVIVOR_PAIRS,
    build_jake,
    build_lena,
    build_maya,
    build_rico,
    build_tom,
    equip_weapon,
)
from weapons import ALL_WEAPON_BUILDERS


def _body_name_for(slug):
    return "_".join(p.capitalize() for p in slug.split("_")) + "_Body"


def _stitch_grid(tiles, cols=6, bg_rgb=(0.08, 0.09, 0.11), gap=4):
    h, w, _ = tiles[0].shape
    rows = math.ceil(len(tiles) / cols)
    total_w = cols * w + (cols - 1) * gap
    total_h = rows * h + (rows - 1) * gap
    sheet = np.zeros((total_h, total_w, 4), dtype=np.float32)
    sheet[:, :, :3] = bg_rgb
    sheet[:, :, 3] = 1.0
    for idx, t in enumerate(tiles):
        r = idx // cols
        c = idx % cols
        # Note: Blender image pixels row 0 is bottom -> top row is rows - 1 - r
        y0 = (rows - 1 - r) * (h + gap)
        x0 = c * (w + gap)
        sheet[y0:y0 + h, x0:x0 + w, :] = t
    return sheet


def _stitch_horizontal(tiles, bg_rgb=(0.06, 0.06, 0.08), gap=4):
    return _stitch_grid(tiles, cols=len(tiles), bg_rgb=bg_rgb, gap=gap)


def render_weapons_sheet(out_path, tile_size=460):
    tmp_dir = os.path.join(PROJECT_DIR, "renders", "_tmp_weapons")
    os.makedirs(tmp_dir, exist_ok=True)
    tiles = []

    for wid, builder, _ in ALL_WEAPON_BUILDERS:
        clear_scene()
        scene = bpy.context.scene
        configure_renderer(scene)
        add_studio_lights(bg_color=(0.16, 0.17, 0.19))

        materials, idx_map = create_materials()
        obj, _ = builder(materials, idx_map)
        mins, maxs = world_bounds([obj])
        c = [(mins[i] + maxs[i]) * 0.5 for i in range(3)]
        span = max(maxs[2] - mins[2], maxs[1] - mins[1], 0.18) * 1.25

        cam_data = bpy.data.cameras.new("WepCam")
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = span
        cam_data.clip_start = 0.02
        cam_data.clip_end = 20.0
        cam = bpy.data.objects.new("WepCam", cam_data)
        scene.collection.objects.link(cam)
        scene.camera = cam

        aim_camera(cam, (2.2, 0.65, c[2] + 0.30), c)
        p = os.path.join(tmp_dir, f"wep_{wid}.png")
        render_image(scene, p, tile_size, tile_size)
        tiles.append(load_rgba_np(p))

    sheet = _stitch_grid(tiles, cols=6, bg_rgb=(0.06, 0.06, 0.08), gap=4)
    save_rgba_np(sheet, out_path)
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    print(f"Saved {len(tiles)}-weapon armory sheet: {out_path}")


def render_gender_pair_sheet(role, out_path, tile_size=520):
    """4-panel Male vs Female comparison sheet: (1) Male posed 3/4, (2) Female posed 3/4,
    (3) Male head/chest close-up, (4) Female head/chest close-up.
    """
    tmp_dir = os.path.join(PROJECT_DIR, "renders", f"_tmp_pair_{role}")
    os.makedirs(tmp_dir, exist_ok=True)
    pose_style = ROLE_POSE_MAP[role]
    builder_map = dict(SURVIVOR_BUILDERS)
    tiles_full = []
    tiles_head = []

    for gender in ("male", "female"):
        slug = f"{role}_{gender}"
        clear_scene()
        scene = bpy.context.scene
        configure_renderer(scene)
        add_studio_lights(bg_color=(0.14, 0.15, 0.17))
        add_ground_disc(radius=1.8)
        materials, idx_map = create_materials()
        body_obj, _, arm_obj, _ = builder_map[slug](
            materials, idx_map, scene.collection, scene.collection, scene.collection
        )

        cd = bpy.data.cameras.new("PairCam")
        cd.type = "ORTHO"
        cd.clip_start = 0.02
        cd.clip_end = 50.0
        cam = bpy.data.objects.new("PairCam", cd)
        scene.collection.objects.link(cam)
        scene.camera = cam

        # Head/upper torso close-up in clean rest stance first
        mins, maxs = world_bounds([body_obj])
        h = maxs[2] - mins[2]
        cd.ortho_scale = h * 0.42
        aim_camera(cam, (-1.8, -2.6, h * 0.88), (0.0, 0.0, h * 0.78))
        p_head = os.path.join(tmp_dir, f"{gender}_head.png")
        render_image(scene, p_head, tile_size, tile_size)
        tiles_head.append(load_rgba_np(p_head))

        # Full body in signature combat/weapon pose
        wid = arm_obj.get("weapon_id")
        rg = tuple(arm_obj["right_grip_rest"]) if "right_grip_rest" in arm_obj else None
        apply_survivor_pose(arm_obj, body_obj, style=pose_style, weapon_id=wid, right_grip_rest=rg)
        cd.ortho_scale = 2.02
        aim_camera(cam, (-2.3, -2.5, 1.12), (0.0, -0.05, 0.90))
        p_full = os.path.join(tmp_dir, f"{gender}_full.png")
        render_image(scene, p_full, tile_size, tile_size)
        tiles_full.append(load_rgba_np(p_full))

    sheet = _stitch_horizontal(tiles_full + tiles_head, bg_rgb=(0.06, 0.06, 0.08), gap=4)
    save_rgba_np(sheet, out_path)
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    print(f"Saved gender pair comparison sheet: {out_path}")


def render_survivor_sheet(slug, blend_path, out_path, tile_size=560):
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene
    configure_renderer(scene)
    add_studio_lights(bg_color=(0.15, 0.16, 0.18))
    add_ground_disc(radius=1.8)

    cam_data = bpy.data.cameras.new("SurvCam")
    cam_data.type = "ORTHO"
    cam_data.clip_start = 0.05
    cam_data.clip_end = 50.0
    cam = bpy.data.objects.new("SurvCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    body = bpy.data.objects[_body_name_for(slug)]
    mins, maxs = world_bounds([body])
    h = maxs[2] - mins[2]
    cz = 0.5 * h

    views = [
        ("front", ( 0.0, -4.8, cz),          (0.0, 0.02, cz),          h * 1.15),
        ("34",    (-3.0, -3.6, cz + 0.32),   (0.0, 0.02, cz),          h * 1.15),
        ("back",  ( 0.0,  4.8, cz),          (0.0, 0.02, cz),          h * 1.15),
        ("head",  (-1.8, -2.8, h * 0.96),    (0.0, -0.01, h * 0.89),   h * 0.28),
    ]
    tmp_dir = os.path.join(PROJECT_DIR, "renders", f"_tmp_{name}")
    os.makedirs(tmp_dir, exist_ok=True)
    tiles = []
    for vname, loc, tgt, ortho_s in views:
        cam_data.ortho_scale = ortho_s
        aim_camera(cam, loc, tgt)
        p = os.path.join(tmp_dir, f"{vname}.png")
        render_image(scene, p, tile_size, tile_size)
        tiles.append(load_rgba_np(p))

    sheet = _stitch_horizontal(tiles, bg_rgb=(0.06, 0.06, 0.08), gap=4)
    save_rgba_np(sheet, out_path)
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    print(f"Saved survivor sheet: {out_path}")


def render_hand_mechanics_qa(out_path, tile_size=600):
    """4-panel Hand Micro-Mechanics QA: (1) 5-finger relaxed cascade, (2) M4 trigger-off & supinated handguard,
    (3) M4 tactical reload mag-pinch, (4) Maya 5-finger thumbs-forward pistol grip.
    """
    tmp_dir = os.path.join(PROJECT_DIR, "renders", "_tmp_qa")
    os.makedirs(tmp_dir, exist_ok=True)
    tiles = []

    def make_cam(scene, ortho=True, val=0.30):
        cd = bpy.data.cameras.new("QACam")
        cd.type = "ORTHO" if ortho else "PERSP"
        if ortho:
            cd.ortho_scale = val
        else:
            cd.lens = val
        cd.clip_start = 0.02
        cd.clip_end = 50.0
        c = bpy.data.objects.new("QACam", cd)
        scene.collection.objects.link(c)
        scene.camera = c
        return c

    # Panel 1: Jake 5-finger sculpted Left Hand close-up (top-front angled so all 5 digits read clearly)
    clear_scene()
    scene = bpy.context.scene
    configure_renderer(scene)
    add_studio_lights(bg_color=(0.14, 0.15, 0.17))
    materials, idx_map = create_materials()
    body_j, _, arm_j, _ = build_jake(materials, idx_map, scene.collection, scene.collection, scene.collection)
    bpy.context.view_layer.objects.active = arm_j
    bpy.ops.object.mode_set(mode="POSE")
    pose_hand_grip(arm_j.pose.bones, "Left", "relaxed")
    bpy.ops.object.mode_set(mode="OBJECT")
    cam = make_cam(scene, ortho=True, val=0.22)
    aim_camera(cam, (0.76, -0.35, 1.72), (0.75, 0.0, 1.42))
    p1 = os.path.join(tmp_dir, "1_hand_5finger.png")
    render_image(scene, p1, tile_size, tile_size)
    tiles.append(load_rgba_np(p1))

    # Panel 2: Jake M4 Trigger Discipline (trigger_off straight index) + Left 5-finger supinated handguard support
    rg = tuple(arm_j["right_grip_rest"])
    apply_aim_ads_pose(arm_j, body_j, weapon_id="m4", right_grip_rest=rg, mode="aim", trigger_discipline=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    aim_camera(cam, (-0.52, -0.78, 1.48), (-0.06, -0.35, 1.36))
    cam.data.ortho_scale = 0.48
    p2 = os.path.join(tmp_dir, "2_m4_trigger_discipline.png")
    render_image(scene, p2, tile_size, tile_size)
    tiles.append(load_rgba_np(p2))

    # Panel 3: Jake M4 Reload Mag-Pinch close-up (canted rifle, trigger_off, left mag_pinch under magwell)
    apply_reload_pose(arm_j, body_j, stage="mag_pinch", weapon_id="m4", right_grip_rest=rg)
    bpy.ops.object.mode_set(mode="OBJECT")
    aim_camera(cam, (0.62, -0.82, 1.32), (-0.05, -0.32, 1.32))
    cam.data.ortho_scale = 0.56
    p3 = os.path.join(tmp_dir, "3_reload_mag_pinch.png")
    render_image(scene, p3, tile_size, tile_size)
    tiles.append(load_rgba_np(p3))

    # Panel 4: Maya 5-finger Two-Handed Thumbs-Forward Pistol Grip Close-Up
    clear_scene()
    scene = bpy.context.scene
    configure_renderer(scene)
    add_studio_lights(bg_color=(0.14, 0.15, 0.17))
    add_ground_disc(radius=2.0)
    materials, idx_map = create_materials()
    body_m, _, arm_m, _ = build_maya(materials, idx_map, scene.collection, scene.collection, scene.collection)
    apply_aim_ads_pose(arm_m, body_m, weapon_id="pistol",
                       right_grip_rest=tuple(arm_m["right_grip_rest"]), mode="aim")
    bpy.ops.object.mode_set(mode="OBJECT")
    cam = make_cam(scene, ortho=True, val=0.52)
    aim_camera(cam, (0.72, -1.05, 1.40), (0.02, -0.38, 1.27))
    p4 = os.path.join(tmp_dir, "4_maya_pistol_5finger.png")
    render_image(scene, p4, tile_size, tile_size)
    tiles.append(load_rgba_np(p4))

    sheet = _stitch_horizontal(tiles, bg_rgb=(0.06, 0.06, 0.08), gap=4)
    save_rgba_np(sheet, out_path)
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    print(f"Saved hand & mechanics QA sheet: {out_path}")


def render_locomotion_combat_qa(out_path, tile_size=540):
    """6-panel (3x2) Combat & Locomotion QA: Walk, Run, Strafe Split, Crouch Aim, Reload Tactical, Melee Swing."""
    tmp_dir = os.path.join(PROJECT_DIR, "renders", "_tmp_loco")
    os.makedirs(tmp_dir, exist_ok=True)
    tiles = []

    def setup_char(builder_fn):
        clear_scene()
        scene = bpy.context.scene
        configure_renderer(scene)
        add_studio_lights(bg_color=(0.14, 0.15, 0.17))
        add_ground_disc(radius=2.2)
        materials, idx_map = create_materials()
        body_obj, _, arm_obj, _ = builder_fn(materials, idx_map, scene.collection, scene.collection, scene.collection)
        cd = bpy.data.cameras.new("LocoCam")
        cd.type = "ORTHO"
        cd.ortho_scale = 2.05
        cd.clip_start = 0.02
        cd.clip_end = 50.0
        cam = bpy.data.objects.new("LocoCam", cd)
        scene.collection.objects.link(cam)
        scene.camera = cam
        return scene, cam, body_obj, arm_obj

    scene, cam, body_j, arm_j = setup_char(build_jake)
    rg = tuple(arm_j["right_grip_rest"])

    # 1. Walk_Cycle (Foot-Roll IK contact)
    apply_walk_pose(arm_j, body_j, phase=0.06, weapon_id="m4", right_grip_rest=rg)
    bpy.ops.object.mode_set(mode="OBJECT")
    aim_camera(cam, (-2.5, -1.6, 1.15), (0.0, 0.0, 0.90))
    p1 = os.path.join(tmp_dir, "1_walk.png")
    render_image(scene, p1, tile_size, tile_size)
    tiles.append(load_rgba_np(p1))

    # 2. Run_Cycle
    apply_run_pose(arm_j, body_j, phase=0.14, weapon_id="m4", right_grip_rest=rg)
    bpy.ops.object.mode_set(mode="OBJECT")
    aim_camera(cam, (-2.5, -1.6, 1.15), (0.0, 0.0, 0.90))
    p2 = os.path.join(tmp_dir, "2_run.png")
    render_image(scene, p2, tile_size, tile_size)
    tiles.append(load_rgba_np(p2))

    # 3. Strafe_Right (Upper/Lower split)
    apply_strafe_pose(arm_j, body_j, phase=0.20, weapon_id="m4", right_grip_rest=rg)
    bpy.ops.object.mode_set(mode="OBJECT")
    aim_camera(cam, (-1.6, -2.5, 1.25), (-0.05, -0.05, 0.90))
    p3 = os.path.join(tmp_dir, "3_strafe.png")
    render_image(scene, p3, tile_size, tile_size)
    tiles.append(load_rgba_np(p3))

    # 4. Crouch_Aim (Low kneeling ADS, centered cleanly so both legs + weapon fit frame)
    apply_crouch_aim_pose(arm_j, body_j, weapon_id="m4", right_grip_rest=rg)
    bpy.ops.object.mode_set(mode="OBJECT")
    aim_camera(cam, (-2.5, -1.8, 1.00), (0.0, -0.05, 0.65))
    cam.data.ortho_scale = 2.05
    p4 = os.path.join(tmp_dir, "4_crouch_aim.png")
    render_image(scene, p4, tile_size, tile_size)
    tiles.append(load_rgba_np(p4))

    # 5. Reload_Tactical
    apply_reload_pose(arm_j, body_j, stage="mag_pinch", weapon_id="m4", right_grip_rest=rg)
    bpy.ops.object.mode_set(mode="OBJECT")
    aim_camera(cam, (1.6, -2.2, 1.20), (-0.02, -0.05, 0.92))
    cam.data.ortho_scale = 1.95
    p5 = os.path.join(tmp_dir, "5_reload.png")
    render_image(scene, p5, tile_size, tile_size)
    tiles.append(load_rgba_np(p5))

    # 6. Melee_Swing (Rico mid-impact pipe wrench swing)
    scene, cam, body_r, arm_r = setup_char(build_rico)
    apply_melee_swing_pose(arm_r, body_r, stage="impact")
    bpy.ops.object.mode_set(mode="OBJECT")
    aim_camera(cam, (-2.1, -2.2, 1.22), (0.0, -0.05, 0.92))
    p6 = os.path.join(tmp_dir, "6_melee_swing.png")
    render_image(scene, p6, tile_size, tile_size)
    tiles.append(load_rgba_np(p6))

    sheet = _stitch_grid(tiles, cols=3, bg_rgb=(0.06, 0.06, 0.08), gap=4)
    save_rgba_np(sheet, out_path)
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    print(f"Saved locomotion & combat QA sheet: {out_path}")


def render_zombie_mechanics_qa(out_path, tile_size=560):
    """4-panel Reaction & Zombie Mechanics QA: Hit React, Zombie Shamble, Zombie Lunge, Zombie Bite Grab."""
    tmp_dir = os.path.join(PROJECT_DIR, "renders", "_tmp_zombie_qa")
    os.makedirs(tmp_dir, exist_ok=True)
    tiles = []

    clear_scene()
    scene = bpy.context.scene
    configure_renderer(scene)
    add_studio_lights(bg_color=(0.14, 0.15, 0.17))
    add_ground_disc(radius=2.2)
    materials, idx_map = create_materials()
    body_j, _, arm_j, _ = build_jake(materials, idx_map, scene.collection, scene.collection, scene.collection)
    for obj in bpy.data.objects:
        if "Weapon" in obj.name or "Holster" in obj.name or "Backpack" in obj.name:
            obj.hide_render = True

    cd = bpy.data.cameras.new("ZCam")
    cd.type = "ORTHO"
    cd.ortho_scale = 2.05
    cd.clip_start = 0.02
    cd.clip_end = 50.0
    cam = bpy.data.objects.new("ZCam", cd)
    scene.collection.objects.link(cam)
    scene.camera = cam

    for idx, (fname, fn, kwargs, cam_pos, tgt) in enumerate([
        ("1_hit_react.png",   apply_hit_react_pose,      {"stage": "peak"}, ( 1.8, -2.2, 1.15), (0.0, 0.0, 0.90)),
        ("2_z_shamble.png",   apply_zombie_shamble_pose, {"phase": 0.22},   (-2.3, -1.7, 1.15), (0.0, 0.0, 0.88)),
        ("3_z_lunge.png",     apply_zombie_lunge_pose,   {"stage": "lunge"},(-2.6, -1.6, 1.15), (0.0, -0.15, 0.85)),
        ("4_z_bite_grab.png", apply_zombie_bite_pose,    {"stage": "bite"}, (-2.2, -1.7, 1.15), (0.0, -0.08, 0.90)),
    ]):
        fn(arm_j, body_j, **kwargs)
        bpy.ops.object.mode_set(mode="OBJECT")
        aim_camera(cam, cam_pos, tgt)
        p = os.path.join(tmp_dir, fname)
        render_image(scene, p, tile_size, tile_size)
        tiles.append(load_rgba_np(p))

    sheet = _stitch_horizontal(tiles, bg_rgb=(0.06, 0.06, 0.08), gap=4)
    save_rgba_np(sheet, out_path)
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    print(f"Saved zombie mechanics QA sheet: {out_path}")


def render_survivors_lineup(out_path, width=1920, height=1160):
    """Render 2-row studio showcase of all 10 survivors: Top Row = 5 Male, Bottom Row = 5 Female."""
    tmp_dir = os.path.join(PROJECT_DIR, "renders", "_tmp_lineup")
    os.makedirs(tmp_dir, exist_ok=True)
    builder_map = dict(SURVIVOR_BUILDERS)
    x_positions = [-2.05, -1.02, 0.00, 1.02, 2.05]
    row_imgs = []

    for gender in ("male", "female"):
        clear_scene()
        scene = bpy.context.scene
        configure_renderer(scene)
        add_studio_lights(bg_color=(0.09, 0.10, 0.12))
        add_ground_disc(radius=4.5)
        materials, idx_map = create_materials()

        for role, xpos in zip(("jake", "maya", "rico", "lena", "tom"), x_positions):
            slug = f"{role}_{gender}"
            col = bpy.data.collections.new(f"Col_{slug}")
            scene.collection.children.link(col)
            body_obj, _, arm_obj, _ = builder_map[slug](materials, idx_map, col, col, col)
            wid = arm_obj.get("weapon_id")
            rg = tuple(arm_obj["right_grip_rest"]) if "right_grip_rest" in arm_obj else None
            apply_survivor_pose(arm_obj, body_obj, style=ROLE_POSE_MAP[role], weapon_id=wid, right_grip_rest=rg)
            arm_obj.location = Vector((xpos, 0.0, 0.0))

        cam_data = bpy.data.cameras.new("LineupCam")
        cam_data.type = "PERSP"
        cam_data.lens = 36.0
        cam = bpy.data.objects.new("LineupCam", cam_data)
        scene.collection.objects.link(cam)
        scene.camera = cam

        aim_camera(cam, (-0.10, -7.85, 1.25), (0.0, 0.0, 0.92))
        rp = os.path.join(tmp_dir, f"row_{gender}.png")
        render_image(scene, rp, width, height // 2)
        row_imgs.append(load_rgba_np(rp))

    # Stack Top = Male, Bottom = Female (Blender image row 0 is bottom -> bottom goes first)
    sheet = _stitch_grid([row_imgs[0], row_imgs[1]], cols=1, bg_rgb=(0.06, 0.06, 0.08), gap=4)
    save_rgba_np(sheet, out_path)
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    print(f"Saved 10-survivor Male/Female lineup: {out_path}")


def render_universal_weapons_qa(out_path, tile_size=540):
    """6-panel (3x2) Cross-Character Weapon Compatibility QA using equip_weapon() across all weapon classes."""
    tmp_dir = os.path.join(PROJECT_DIR, "renders", "_tmp_univ")
    os.makedirs(tmp_dir, exist_ok=True)
    builder_map = dict(SURVIVOR_BUILDERS)
    tiles = []

    combos = [
        ("maya_female", "ak47",         (-2.1, -2.2, 1.15), (0.0, -0.05, 0.90), "aim"),
        ("jake_male",   "compound_bow", (-2.2, -2.4, 1.18), (0.0, -0.05, 0.92), "bow"),
        ("lena_female", "sniper",       (-2.2, -2.3, 1.15), (0.0, -0.08, 0.90), "aim"),
        ("rico_female", "revolver",     (-1.9, -2.2, 1.15), (0.0, -0.05, 0.90), "aim"),
        ("tom_female",  "lmg",          (-2.1, -2.3, 1.15), (0.0, -0.06, 0.90), "aim"),
        ("jake_female", "pipe_wrench",  (-2.0, -2.2, 1.18), (0.0, -0.05, 0.90), "melee"),
    ]
    for idx, (slug, wid, cam_loc, tgt, mode) in enumerate(combos):
        clear_scene()
        scene = bpy.context.scene
        configure_renderer(scene)
        add_studio_lights(bg_color=(0.14, 0.15, 0.17))
        add_ground_disc(radius=2.0)
        materials, idx_map = create_materials()
        body_obj, _, arm_obj, _ = builder_map[slug](materials, idx_map, scene.collection, scene.collection, scene.collection)
        equip_weapon(arm_obj, wid, materials, idx_map, collection=scene.collection, clear_existing=True)

        if mode == "bow":
            apply_bow_draw_pose(arm_obj, body_obj, right_grip_rest=tuple(arm_obj["arrow_grip_rest"]), draw_factor=1.0)
        elif mode == "melee":
            apply_melee_swing_pose(arm_obj, body_obj, stage="impact")
        else:
            apply_aim_ads_pose(arm_obj, body_obj, weapon_id=wid,
                               right_grip_rest=tuple(arm_obj["right_grip_rest"]), mode="aim")
        bpy.ops.object.mode_set(mode="OBJECT")

        cd = bpy.data.cameras.new("UCam")
        cd.type = "ORTHO"
        cd.ortho_scale = 2.02
        cd.clip_start = 0.02
        cd.clip_end = 50.0
        cam = bpy.data.objects.new("UCam", cd)
        scene.collection.objects.link(cam)
        scene.camera = cam
        aim_camera(cam, cam_loc, tgt)

        p = os.path.join(tmp_dir, f"{idx}_{slug}_{wid}.png")
        render_image(scene, p, tile_size, tile_size)
        tiles.append(load_rgba_np(p))

    sheet = _stitch_grid(tiles, cols=3, bg_rgb=(0.06, 0.06, 0.08), gap=4)
    save_rgba_np(sheet, out_path)
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    print(f"Saved universal weapons QA sheet: {out_path}")


def main():
    renders_dir = os.path.join(PROJECT_DIR, "renders")
    os.makedirs(renders_dir, exist_ok=True)

    render_weapons_sheet(os.path.join(renders_dir, "weapons_sheet.png"))
    render_hand_mechanics_qa(os.path.join(renders_dir, "hand_mechanics_qa.png"))
    render_locomotion_combat_qa(os.path.join(renders_dir, "locomotion_combat_qa.png"))
    render_zombie_mechanics_qa(os.path.join(renders_dir, "zombie_mechanics_qa.png"))
    for role in ("jake", "maya", "rico", "lena", "tom"):
        render_gender_pair_sheet(role, os.path.join(renders_dir, f"pair_{role}.png"))
    render_survivors_lineup(os.path.join(renders_dir, "survivors_lineup.png"))
    render_universal_weapons_qa(os.path.join(renders_dir, "universal_weapons_qa.png"))


if __name__ == "__main__":
    main()
