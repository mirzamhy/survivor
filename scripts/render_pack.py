"""Batch 1 visual QA renderer: 17-weapon armory sheet, hand/mechanics QA, 5 survivor sheets & lineup."""
import math
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import bpy
import bmesh
import numpy as np
from mathutils import Euler, Vector

from build_survivor import clear_scene, world_bounds
from mesh_utils import add_box, add_cone, add_cylinder, finalize_mesh
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
    apply_zombie_death_pose,
    apply_zombie_detonate_pose,
    apply_zombie_echo_click_pose,
    apply_zombie_idle_pose,
    apply_zombie_lunge_pose,
    apply_zombie_rafflesia_pose,
    apply_zombie_run_pose,
    apply_zombie_shamble_pose,
    apply_zombie_shriek_pose,
    apply_zombie_signature_pose,
    apply_zombie_slam_pose,
    apply_zombie_spit_pose,
    apply_zombie_swipe_pose,
    pose_hand_grip,
    reset_pose,
    snap_feet_to_floor,
    solve_gun_first_weapon_ik,
)
from mutant_vfx import spawn_mutant_vfx
from rig_creature import apply_creature_pose
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
from weapon_vfx import ALL_VFX_BUILDERS, spawn_weapon_vfx
from weapons import ALL_WEAPON_BUILDERS
from zombies import ZOMBIE_BUILDERS, ZOMBIE_SKILL_MAP
from zombies_mutants import MUTANT_BUILDERS, MUTANT_META


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


def _spawn_skill_preview_vfx(slug, arm_obj, materials, idx_map, col):
    """Build lightweight low-poly skill VFX accents strictly for QA sheet visual readability."""
    bpy.context.view_layer.update()
    bm = bmesh.new()
    pb = arm_obj.pose.bones
    head_p = (arm_obj.matrix_world @ pb["mixamorig:Head"].matrix).to_translation()
    chest_p = (arm_obj.matrix_world @ pb["mixamorig:Spine1"].matrix).to_translation()
    rhand_p = (arm_obj.matrix_world @ pb["mixamorig:RightHand"].matrix).to_translation()

    if slug == "banshee_screamer":
        # Expanding tilted sonic shockwave rings above/in front of upturned screaming head
        for k, (dist, rad) in enumerate(((0.16, 0.22), (0.34, 0.36), (0.54, 0.50))):
            c = head_p + Vector((0.0, -dist * 0.55, dist * 0.85))
            for i in range(8):
                a0 = (2.0 * math.pi * i) / 8.0
                a1 = (2.0 * math.pi * ((i + 1) % 8)) / 8.0
                p0 = (c.x + rad * math.cos(a0), c.y + rad * 0.5 * math.sin(a0), c.z + rad * 0.85 * math.sin(a0))
                p1 = (c.x + rad * math.cos(a1), c.y + rad * 0.5 * math.sin(a1), c.z + rad * 0.85 * math.sin(a1))
                add_cylinder(bm, p0, p1, 0.010, 0.010, segments=5, mat_idx=idx_map["Mat_ZSonicWave"])
    elif slug == "spitter_hazmat":
        # Glowing acid vomit jet arcing forward along -Y from mouth + droplets
        m_p = head_p + Vector((0.0, -0.10, 0.02))
        for k in range(6):
            t = k / 5.0
            pt = m_p + Vector((0.02 * math.sin(k * 2.1), -0.14 - 0.72 * t, -0.35 * (t ** 1.6)))
            sz = 0.022 + 0.018 * math.sin(k * 1.4)
            add_box(bm, center=tuple(pt), size=(sz, sz * 2.4, sz),
                    rot=(0.3 * t, 0.4 * k, 0.2), bevel=sz * 0.22, mat_idx=idx_map["Mat_ZAcidGlow"])
    elif slug == "bloater_boomer":
        # Volatile gas burst shards & toxic smoke cloud erupting outward from chest/gut
        for i in range(8):
            ang = (2.0 * math.pi * i) / 8.0
            rad = 0.34 + 0.14 * (i % 2)
            pt = chest_p + Vector((rad * math.cos(ang), rad * 0.85 * math.sin(ang) - 0.05, 0.18 * ((i % 3) - 1)))
            sz = 0.048 + 0.016 * (i % 2)
            add_box(bm, center=tuple(pt), size=(sz, sz, sz), rot=(i * 0.5, i * 0.3, 0.4),
                    bevel=sz * 0.24, mat_idx=idx_map["Mat_ZBoilGlow" if i % 2 == 0 else "Mat_ZAcidGlow"])
    elif slug == "juggernaut_brute":
        # Ground shockwave ring of radial stone spikes around slamming giant fist
        cx, cy = rhand_p.x, rhand_p.y
        for i in range(8):
            ang = (2.0 * math.pi * i) / 8.0
            ca, sa = math.cos(ang), math.sin(ang)
            b0 = (cx + 0.16 * ca, cy + 0.16 * sa, 0.00)
            tip = (cx + 0.42 * ca, cy + 0.42 * sa, 0.16 + 0.08 * (i % 2))
            add_cone(bm, b0, tip, 0.055, segments=5, mat_idx=idx_map["Mat_WorkGrey"])
    elif slug == "crawler_stalker":
        # Fast diagonal feral claw slash arcs in front of pouncing hands
        for dz in (-0.06, 0.0, 0.06):
            p0 = rhand_p + Vector((-0.08, -0.10, 0.10 + dz))
            p1 = rhand_p + Vector((0.28, -0.16, -0.08 + dz))
            add_cylinder(bm, tuple(p0), tuple(p1), 0.008, 0.003, segments=5, mat_idx=idx_map["Mat_VfxBloodFresh"])
    elif slug == "walker_shambler":
        # Blood mist streaks erupting at grabbing bite distance
        for i in range(5):
            pt = head_p + Vector(((i - 2) * 0.045, -0.22 - 0.04 * (i % 2), -0.05 + 0.04 * (i % 3)))
            add_box(bm, center=tuple(pt), size=(0.022, 0.042, 0.020), rot=(0.3, i * 0.5, 0.2),
                    mat_idx=idx_map["Mat_VfxBloodFresh"])

    if len(bm.verts) > 0:
        finalize_mesh(f"{slug}_SkillVFX", bm, materials, collection=col)
    else:
        bm.free()


def render_zombie_mechanics_qa(out_path, tile_size=560):
    """6-panel (3x2) Unique Zombie Skills QA across all 6 archetypes & distinct horror skills."""
    tmp_dir = os.path.join(PROJECT_DIR, "renders", "_tmp_zombie_qa")
    os.makedirs(tmp_dir, exist_ok=True)
    builder_map = dict(ZOMBIE_BUILDERS)
    tiles = []

    combos = [
        ("1_stalker_pounce.png",   "crawler_stalker",  apply_zombie_lunge_pose,    {"stage": "lunge"},  (-2.2, -1.6, 1.05), (0.0, -0.10, 0.72), 1.80),
        ("2_shambler_bite.png",    "walker_shambler",  apply_zombie_bite_pose,     {"stage": "bite"},   (-2.0, -1.9, 1.15), (0.0, -0.08, 0.88), 2.05),
        ("3_banshee_shriek.png",   "banshee_screamer", apply_zombie_shriek_pose,   {"stage": "peak"},   ( 1.6, -2.3, 1.35), (0.0, -0.05, 1.04), 2.38),
        ("4_spitter_acid.png",     "spitter_hazmat",   apply_zombie_spit_pose,     {"stage": "spit"},   ( 2.3, -1.7, 1.15), (0.0, -0.24, 0.86), 2.25),
        ("5_boomer_detonate.png",  "bloater_boomer",   apply_zombie_detonate_pose, {"stage": "burst"},  ( 1.6, -2.4, 1.20), (0.0,  0.00, 0.96), 2.30),
        ("6_juggernaut_slam.png",  "juggernaut_brute", apply_zombie_slam_pose,     {"stage": "impact"}, (-1.8, -2.5, 1.25), (0.0, -0.10, 0.86), 2.40),
    ]
    for fname, slug, fn, kwargs, cam_pos, tgt, oscale in combos:
        clear_scene()
        scene = bpy.context.scene
        configure_renderer(scene)
        add_studio_lights(bg_color=(0.11, 0.12, 0.14))
        add_ground_disc(radius=2.4)
        materials, idx_map = create_materials()
        body_z, _, arm_z, _ = builder_map[slug](materials, idx_map, scene.collection, scene.collection, scene.collection)

        fn(arm_z, body_z, **kwargs)
        _spawn_skill_preview_vfx(slug, arm_z, materials, idx_map, scene.collection)
        bpy.ops.object.mode_set(mode="OBJECT")

        cd = bpy.data.cameras.new("ZCam")
        cd.type = "ORTHO"
        cd.ortho_scale = oscale
        cd.clip_start = 0.02
        cd.clip_end = 50.0
        cam = bpy.data.objects.new("ZCam", cd)
        scene.collection.objects.link(cam)
        scene.camera = cam
        aim_camera(cam, cam_pos, tgt)

        p = os.path.join(tmp_dir, fname)
        render_image(scene, p, tile_size, tile_size)
        tiles.append(load_rgba_np(p))

    sheet = _stitch_grid(tiles, cols=3, bg_rgb=(0.06, 0.06, 0.08), gap=4)
    save_rgba_np(sheet, out_path)
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    print(f"Saved zombie unique skills QA sheet: {out_path}")


def render_zombies_head_sheet(out_path, tile_size=540):
    """6-panel (3x2) Close-Up Portrait QA showing faceless Loomis/Asaro horror zombie faces & mutations."""
    tmp_dir = os.path.join(PROJECT_DIR, "renders", "_tmp_zheads")
    os.makedirs(tmp_dir, exist_ok=True)
    tiles = []

    for slug, builder in ZOMBIE_BUILDERS:
        clear_scene()
        scene = bpy.context.scene
        configure_renderer(scene)
        add_studio_lights(bg_color=(0.12, 0.13, 0.15))
        materials, idx_map = create_materials()
        body_z, _, _, _ = builder(materials, idx_map, scene.collection, scene.collection, scene.collection)

        mins, maxs = world_bounds([body_z])
        h = maxs[2] - mins[2]
        cam_x = -1.35 if slug == "walker_shambler" else 1.35

        cd = bpy.data.cameras.new("ZHeadCam")
        cd.type = "ORTHO"
        cd.ortho_scale = h * 0.36
        cd.clip_start = 0.02
        cd.clip_end = 50.0
        cam = bpy.data.objects.new("ZHeadCam", cd)
        scene.collection.objects.link(cam)
        scene.camera = cam
        aim_camera(cam, (cam_x, -2.75, h * 0.89), (0.0, -0.02, h * 0.83))

        p = os.path.join(tmp_dir, f"zhead_{slug}.png")
        render_image(scene, p, tile_size, tile_size)
        tiles.append(load_rgba_np(p))

    sheet = _stitch_grid(tiles, cols=3, bg_rgb=(0.06, 0.06, 0.08), gap=4)
    save_rgba_np(sheet, out_path)
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    print(f"Saved zombie heads close-up sheet: {out_path}")


def render_zombies_lineup(out_path, width=1920, height=820):
    """Studio lineup of all 6 faceless horror zombies ordered small-to-giant (1.42m .. 2.26m)."""
    clear_scene()
    scene = bpy.context.scene
    configure_renderer(scene)
    add_studio_lights(bg_color=(0.09, 0.10, 0.12))
    add_ground_disc(radius=5.6)
    materials, idx_map = create_materials()

    builder_map = dict(ZOMBIE_BUILDERS)
    ordered_specs = [
        ("crawler_stalker",  -2.60, "idle"),
        ("banshee_screamer", -1.58, "shamble"),
        ("spitter_hazmat",   -0.55, "idle"),
        ("walker_shambler",   0.48, "shamble"),
        ("bloater_boomer",    1.54, "idle"),
        ("juggernaut_brute",  2.65, "swipe"),
    ]
    for slug, xpos, pose_kind in ordered_specs:
        col = bpy.data.collections.new(f"Col_{slug}")
        scene.collection.children.link(col)
        body_z, _, arm_z, _ = builder_map[slug](materials, idx_map, col, col, col)
        if pose_kind == "swipe":
            apply_zombie_swipe_pose(arm_z, body_z, stage="windup")
            bpy.ops.object.mode_set(mode="OBJECT")
        else:
            apply_zombie_signature_pose(arm_z, body_z, pose_name=pose_kind)
        arm_z.location = Vector((xpos, 0.0, 0.0))

    cam_data = bpy.data.cameras.new("ZLineupCam")
    cam_data.type = "PERSP"
    cam_data.lens = 35.0
    cam = bpy.data.objects.new("ZLineupCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    aim_camera(cam, (-0.05, -8.85, 1.32), (0.0, 0.0, 1.05))

    render_image(scene, out_path, width, height)
    print(f"Saved 6-zombie horde lineup: {out_path}")


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


def render_vfx_sheet(out_path, tile_size=440):
    """4-column showcase of all 13 modular weapon VFX GLB assets on dark backdrop."""
    tmp_dir = os.path.join(PROJECT_DIR, "renders", "_tmp_vfx")
    os.makedirs(tmp_dir, exist_ok=True)
    tiles = []

    for vid, builder in ALL_VFX_BUILDERS:
        clear_scene()
        scene = bpy.context.scene
        configure_renderer(scene)
        add_studio_lights(bg_color=(0.06, 0.07, 0.09))

        materials, idx_map = create_materials()
        obj, _ = builder(materials, idx_map)
        mins, maxs = world_bounds([obj])
        c = [(mins[i] + maxs[i]) * 0.5 for i in range(3)]
        span = max(maxs[0] - mins[0], maxs[1] - mins[1], maxs[2] - mins[2], 0.14) * 1.45

        cam_data = bpy.data.cameras.new("VfxCam")
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = span
        cam_data.clip_start = 0.01
        cam_data.clip_end = 20.0
        cam = bpy.data.objects.new("VfxCam", cam_data)
        scene.collection.objects.link(cam)
        scene.camera = cam

        aim_camera(cam, (c[0] + 1.4, c[1] + 0.55, c[2] + 0.45), c)
        p = os.path.join(tmp_dir, f"vfx_{vid}.png")
        render_image(scene, p, tile_size, tile_size)
        tiles.append(load_rgba_np(p))

    sheet = _stitch_grid(tiles, cols=4, bg_rgb=(0.04, 0.05, 0.07), gap=4)
    save_rgba_np(sheet, out_path)
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    print(f"Saved {len(tiles)}-effect weapon VFX sheet: {out_path}")


def render_weapon_vfx_action_qa(out_path, tile_size=560):
    """6-panel (3x2) Live Weapon VFX Combat Showcase: Rifle, Pistol, Shotgun, Sniper, Bow, Melee."""
    tmp_dir = os.path.join(PROJECT_DIR, "renders", "_tmp_vfx_qa")
    os.makedirs(tmp_dir, exist_ok=True)
    builder_map = dict(SURVIVOR_BUILDERS)
    tiles = []

    combos = [
        ("jake_male",   "m4",            (-2.15, -2.35, 1.15), (0.0, -0.35, 0.96), "recoil"),
        ("maya_female", "pistol",        (-1.85, -2.25, 1.15), (0.0, -0.30, 0.94), "recoil"),
        ("tom_female",  "double_barrel", (-2.15, -2.35, 1.15), (0.0, -0.38, 0.96), "recoil"),
        ("lena_female", "sniper",        (-2.25, -2.35, 1.15), (0.0, -0.38, 0.96), "recoil"),
        ("lena_male",   "compound_bow",  (-2.20, -2.40, 1.18), (0.0, -0.20, 0.95), "bow"),
        ("rico_female", "pipe_wrench",   (-2.00, -2.25, 1.18), (0.0, -0.15, 0.95), "melee"),
    ]
    for idx, (slug, wid, cam_loc, tgt, mode) in enumerate(combos):
        clear_scene()
        scene = bpy.context.scene
        configure_renderer(scene)
        add_studio_lights(bg_color=(0.07, 0.08, 0.10))
        add_ground_disc(radius=2.2)
        materials, idx_map = create_materials()

        body_obj, _, arm_obj, _ = builder_map[slug](materials, idx_map, scene.collection, scene.collection, scene.collection)
        equip_weapon(arm_obj, wid, materials, idx_map, collection=scene.collection, clear_existing=True)

        if mode == "bow":
            apply_bow_draw_pose(arm_obj, body_obj, right_grip_rest=tuple(arm_obj["arrow_grip_rest"]),
                                draw_factor=1.0, release_follow=True)
        elif mode == "melee":
            apply_melee_swing_pose(arm_obj, body_obj, stage="impact")
        else:
            apply_aim_ads_pose(arm_obj, body_obj, weapon_id=wid,
                               right_grip_rest=tuple(arm_obj["right_grip_rest"]),
                               recoil_pitch_deg=6.0, kick_m=0.025, mode="aim")

        bpy.context.view_layer.update()
        spawn_weapon_vfx(arm_obj, wid, materials, idx_map, scene.collection, add_light=True)
        bpy.ops.object.mode_set(mode="OBJECT")

        cd = bpy.data.cameras.new("VfxQaCam")
        cd.type = "ORTHO"
        cd.ortho_scale = 2.15
        cd.clip_start = 0.02
        cd.clip_end = 50.0
        cam = bpy.data.objects.new("VfxQaCam", cd)
        scene.collection.objects.link(cam)
        scene.camera = cam
        aim_camera(cam, cam_loc, tgt)

        p = os.path.join(tmp_dir, f"{idx}_{slug}_{wid}.png")
        render_image(scene, p, tile_size, tile_size)
        tiles.append(load_rgba_np(p))

    sheet = _stitch_grid(tiles, cols=3, bg_rgb=(0.04, 0.05, 0.07), gap=4)
    save_rgba_np(sheet, out_path)
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    print(f"Saved live weapon VFX action QA sheet: {out_path}")


def render_mutant_showcase(slug, out_path, tile_size=560):
    """6-panel (3x2) Single-Mutant Turnaround, Bilateral Head Close-Ups & Unique Skill Action QA."""
    tmp_dir = os.path.join(PROJECT_DIR, "renders", f"_tmp_mut_{slug}")
    os.makedirs(tmp_dir, exist_ok=True)
    builder = dict(MUTANT_BUILDERS)[slug]
    tiles = []

    clear_scene()
    scene = bpy.context.scene
    configure_renderer(scene)
    add_studio_lights(bg_color=(0.11, 0.12, 0.14))
    add_ground_disc(radius=2.5)
    materials, idx_map = create_materials()
    body_m, _, arm_m, _ = builder(materials, idx_map, scene.collection, scene.collection, scene.collection)

    cd = bpy.data.cameras.new("MutCam")
    cd.type = "ORTHO"
    cd.clip_start = 0.02
    cd.clip_end = 50.0
    cam = bpy.data.objects.new("MutCam", cd)
    scene.collection.objects.link(cam)
    scene.camera = cam

    skill_mode = MUTANT_META[slug]["skill_pose"]
    is_creature = (arm_m.get("rig_type") == "creature")

    if is_creature:
        meta = MUTANT_META[slug]
        b_ortho = meta.get("body_ortho", 2.48)
        b_tgt_z = meta.get("body_tgt_z", 0.68)
        h_ortho = meta.get("head_ortho", 0.96)
        h_cam_y = meta.get("head_cam_y", -2.50)
        idle_stg = meta.get("idle_stage", "idle")
        head_stg = meta.get("head_stage", "lunge_bite")
        skill_stg = meta.get("skill_stage", "vine_thrash")
        vfx_mat = idx_map[meta.get("vfx_mat", "Mat_ZHeartGlow")]

        apply_creature_pose(arm_m, body_m, slug, stage=idle_stg, phase=0.05)
        bpy.ops.object.mode_set(mode="OBJECT")
        cd.ortho_scale = b_ortho
        for tag, loc, tgt in (
            ("1_front",      ( 0.00, -3.60, b_tgt_z + 0.24), (0.0, 0.0, b_tgt_z)),
            ("2_front_34",   ( 2.25, -2.75, b_tgt_z + 0.36), (0.0, 0.0, b_tgt_z)),
            ("3_back_34",    (-2.25,  2.75, b_tgt_z + 0.36), (0.0, 0.0, b_tgt_z)),
        ):
            aim_camera(cam, loc, tgt)
            p = os.path.join(tmp_dir, f"{tag}.png")
            render_image(scene, p, tile_size, tile_size)
            tiles.append(load_rgba_np(p))

        apply_creature_pose(arm_m, body_m, slug, stage=head_stg, phase=0.0)
        bpy.ops.object.mode_set(mode="OBJECT")
        head_pos = (arm_m.matrix_world @ arm_m.pose.bones["Head"].matrix).to_translation()
        h_z_off = meta.get("head_z_off", 0.0)
        cd.ortho_scale = h_ortho
        for tag, loc, tgt in (
            ("4_head_front", (head_pos.x, head_pos.y + h_cam_y, head_pos.z + 0.06 + h_z_off), (head_pos.x, head_pos.y - 0.05, head_pos.z + h_z_off)),
            ("5_head_34",    (head_pos.x + 1.50, head_pos.y + h_cam_y * 0.85, head_pos.z + 0.08 + h_z_off), (head_pos.x, head_pos.y - 0.05, head_pos.z + h_z_off)),
        ):
            aim_camera(cam, loc, tgt)
            p = os.path.join(tmp_dir, f"{tag}.png")
            render_image(scene, p, tile_size, tile_size)
            tiles.append(load_rgba_np(p))

        apply_creature_pose(arm_m, body_m, slug, stage=skill_stg, phase=0.25)
        bpy.ops.object.mode_set(mode="OBJECT")
        spawn_mutant_vfx(arm_m, slug, materials, idx_map, scene.collection, add_light=True)

        cd.ortho_scale = b_ortho * 1.14
        aim_camera(cam, (2.35, -2.25, b_tgt_z + 0.42), (0.0, -0.15, b_tgt_z))
        p6 = os.path.join(tmp_dir, "6_skill.png")
        render_image(scene, p6, tile_size, tile_size)
        tiles.append(load_rgba_np(p6))
    else:
        if skill_mode == "rafflesia_lash":
            apply_zombie_rafflesia_pose(arm_m, body_m, stage="stalk")
        else:
            apply_zombie_echo_click_pose(arm_m, body_m, stage="listen")
        bpy.ops.object.mode_set(mode="OBJECT")
        cd.ortho_scale = 2.55 if skill_mode == "rafflesia_lash" else 2.35
        for tag, loc, tgt in (
            ("1_front",      ( 0.00, -3.20, 1.05), (0.0, 0.0, 0.98)),
            ("2_front_34",   ( 1.85, -2.50, 1.15), (0.0, 0.0, 0.98)),
            ("3_back_34",    (-1.85,  2.50, 1.15), (0.0, 0.0, 0.98)),
        ):
            aim_camera(cam, loc, tgt)
            p = os.path.join(tmp_dir, f"{tag}.png")
            render_image(scene, p, tile_size, tile_size)
            tiles.append(load_rgba_np(p))

        reset_pose(arm_m.pose.bones)
        bpy.context.view_layer.update()
        if skill_mode == "rafflesia_lash":
            cd.ortho_scale = 0.98
            head_views = (
                ("4_head_front", (0.00, -2.75, 1.68), (0.0, -0.04, 1.62)),
                ("5_head_34",    (1.55, -2.55, 1.64), (0.0, -0.04, 1.60)),
            )
        else:
            cd.ortho_scale = 0.78
            head_views = (
                ("4_head_l", ( 1.35, -2.75, 1.66), (0.0, -0.02, 1.58)),
                ("5_head_r", (-1.35, -2.75, 1.66), (0.0, -0.02, 1.58)),
            )
        for tag, loc, tgt in head_views:
            aim_camera(cam, loc, tgt)
            p = os.path.join(tmp_dir, f"{tag}.png")
            render_image(scene, p, tile_size, tile_size)
            tiles.append(load_rgba_np(p))

        if skill_mode == "rafflesia_lash":
            apply_zombie_rafflesia_pose(arm_m, body_m, stage="lash")
        else:
            apply_zombie_echo_click_pose(arm_m, body_m, stage="dash")
        bpy.ops.object.mode_set(mode="OBJECT")
        bm_sp = bmesh.new()
        head_p = (arm_m.matrix_world @ arm_m.pose.bones["mixamorig:Head"].matrix).to_translation()
        mote_mat = idx_map["Mat_ZHeartGlow" if skill_mode == "rafflesia_lash" else "Mat_ZSporeMote"]
        for i in range(8):
            ang = (2.0 * math.pi * i) / 8.0
            rad = 0.24 + 0.14 * (i % 2)
            pt = head_p + Vector((rad * math.cos(ang), -0.14 + rad * 0.6 * math.sin(ang), 0.14 * ((i % 3) - 1)))
            add_box(bm_sp, center=tuple(pt), size=(0.024, 0.024, 0.024), rot=(i * 0.4, i * 0.5, 0.2),
                    bevel=0.005, mat_idx=mote_mat)
        finalize_mesh(f"{slug}_SporePreview", bm_sp, materials, collection=scene.collection)

        cd.ortho_scale = 2.55 if skill_mode == "rafflesia_lash" else 2.35
        aim_camera(cam, (2.10, -1.90, 1.18), (0.0, -0.06, 0.94))
        p6 = os.path.join(tmp_dir, "6_skill.png")
        render_image(scene, p6, tile_size, tile_size)
        tiles.append(load_rgba_np(p6))

    sheet = _stitch_grid(tiles, cols=3, bg_rgb=(0.06, 0.06, 0.08), gap=4)
    save_rgba_np(sheet, out_path)
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    print(f"Saved mutant showcase sheet: {out_path}")


def render_mutant_combat_vfx_qa(out_path, tile_size=640):
    """4-panel (2x2) Dramatic Combat Action VFX Showcase for all 4 Creature Mutants."""
    tmp_dir = os.path.join(PROJECT_DIR, "renders", "_tmp_mut_vfx")
    os.makedirs(tmp_dir, exist_ok=True)
    builder_map = dict(MUTANT_BUILDERS)
    tiles = []

    for slug in ("rafflesia", "scythe_stalker", "thorn_shroud", "arachnid_maw", "bile_juggernaut"):
        clear_scene()
        scene = bpy.context.scene
        configure_renderer(scene)
        add_studio_lights(bg_color=(0.06, 0.07, 0.09))
        add_ground_disc(radius=2.5)
        materials, idx_map = create_materials()

        body_m, _, arm_m, _ = builder_map[slug](materials, idx_map, scene.collection, scene.collection, scene.collection)
        meta = MUTANT_META[slug]
        apply_creature_pose(arm_m, body_m, slug, stage=meta["skill_stage"], phase=0.25)
        bpy.ops.object.mode_set(mode="OBJECT")
        spawn_mutant_vfx(arm_m, slug, materials, idx_map, scene.collection, add_light=True)

        cd = bpy.data.cameras.new("MutVfxCam")
        cd.type = "ORTHO"
        cd.ortho_scale = meta["body_ortho"] * 1.15
        cd.clip_start = 0.02
        cd.clip_end = 50.0
        cam = bpy.data.objects.new("MutVfxCam", cd)
        scene.collection.objects.link(cam)
        scene.camera = cam
        tgt_z = meta["body_tgt_z"]
        aim_camera(cam, (2.25, -2.25, tgt_z + 0.42), (0.0, -0.22, tgt_z))
        p = os.path.join(tmp_dir, f"vfx_{slug}.png")
        render_image(scene, p, tile_size, tile_size)
        tiles.append(load_rgba_np(p))

    # Tile 6: Full 5-Mutant Scale & Silhouette Lineup Comparison!
    clear_scene()
    scene = bpy.context.scene
    configure_renderer(scene)
    add_studio_lights(bg_color=(0.08, 0.09, 0.11))
    add_ground_disc(radius=4.8)
    materials, idx_map = create_materials()
    for s_id, xp in (
        ("arachnid_maw",    -2.90),
        ("rafflesia",       -1.35),
        ("scythe_stalker",   0.15),
        ("thorn_shroud",     1.45),
        ("bile_juggernaut",  2.95),
    ):
        bm_o, _, am_o, _ = builder_map[s_id](materials, idx_map, scene.collection, scene.collection, scene.collection)
        apply_creature_pose(am_o, bm_o, s_id, stage="idle", phase=0.05)
        am_o.location = Vector((xp, 0.0, 0.0))
    cd = bpy.data.cameras.new("LineupMutCam")
    cd.type = "ORTHO"
    cd.ortho_scale = 7.20
    cd.clip_start = 0.02
    cd.clip_end = 60.0
    cam = bpy.data.objects.new("LineupMutCam", cd)
    scene.collection.objects.link(cam)
    scene.camera = cam
    aim_camera(cam, (0.05, -7.80, 1.55), (0.05, 0.0, 1.10))
    p_lin = os.path.join(tmp_dir, "6_lineup.png")
    render_image(scene, p_lin, tile_size, tile_size)
    tiles.append(load_rgba_np(p_lin))

    sheet = _stitch_grid(tiles, cols=3, bg_rgb=(0.04, 0.05, 0.07), gap=4)
    save_rgba_np(sheet, out_path)
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    print(f"Saved mutant combat VFX showcase: {out_path}")


def main():
    vfx_only = "--vfx-only" in sys.argv
    zombies_only = "--zombies-only" in sys.argv
    mutant_only = "--mutant-only" in sys.argv
    mutant_vfx_qa = "--mutant-vfx-qa" in sys.argv
    renders_dir = os.path.join(PROJECT_DIR, "renders")
    os.makedirs(renders_dir, exist_ok=True)

    if mutant_vfx_qa:
        render_mutant_combat_vfx_qa(os.path.join(renders_dir, "mutant_combat_vfx_qa.png"))
        return

    if mutant_only:
        idx = sys.argv.index("--mutant-only")
        only_slug = sys.argv[idx + 1] if (idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("-")) else None
        targets = [s for s, _ in MUTANT_BUILDERS if (only_slug is None or s == only_slug)]
        for s in targets:
            out_png = os.path.join(renders_dir, MUTANT_META[s]["render_name"])
            render_mutant_showcase(s, out_png)
        if only_slug is None:
            render_mutant_combat_vfx_qa(os.path.join(renders_dir, "mutant_combat_vfx_qa.png"))
        return

    if zombies_only:
        render_zombies_head_sheet(os.path.join(renders_dir, "zombies_head_sheet.png"))
        render_zombies_lineup(os.path.join(renders_dir, "zombies_lineup.png"))
        render_zombie_mechanics_qa(os.path.join(renders_dir, "zombie_mechanics_qa.png"))
        return

    render_vfx_sheet(os.path.join(renders_dir, "weapon_vfx_sheet.png"))
    render_weapon_vfx_action_qa(os.path.join(renders_dir, "weapon_vfx_action_qa.png"))
    if vfx_only:
        return

    render_weapons_sheet(os.path.join(renders_dir, "weapons_sheet.png"))
    render_hand_mechanics_qa(os.path.join(renders_dir, "hand_mechanics_qa.png"))
    render_locomotion_combat_qa(os.path.join(renders_dir, "locomotion_combat_qa.png"))
    render_zombies_head_sheet(os.path.join(renders_dir, "zombies_head_sheet.png"))
    render_zombies_lineup(os.path.join(renders_dir, "zombies_lineup.png"))
    render_zombie_mechanics_qa(os.path.join(renders_dir, "zombie_mechanics_qa.png"))
    for role in ("jake", "maya", "rico", "lena", "tom"):
        render_gender_pair_sheet(role, os.path.join(renders_dir, f"pair_{role}.png"))
    render_survivors_lineup(os.path.join(renders_dir, "survivors_lineup.png"))
    render_universal_weapons_qa(os.path.join(renders_dir, "universal_weapons_qa.png"))


if __name__ == "__main__":
    main()
