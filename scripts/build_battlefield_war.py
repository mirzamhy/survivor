"""Build & export epic War-Torn Apocalypse Fortress vs Zombie Bio-Hive Battlefield GLB + QA render."""
import json
import math
import os
import struct
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import bmesh
import bpy
from mathutils import Euler, Vector

from build_survivor import clear_scene, export_glb, make_collection, world_bounds
from environment_apocalypse import (
    _build_distant_city_skyline,
    _place_piece,
    build_env_dead_tree,
    build_env_fire_barrel,
    build_env_grass_clump_tall,
    build_env_jersey_barrier,
    build_env_police_cruiser,
    build_env_rubble_crater,
    build_env_sandbag_barricade,
    build_env_street_lamp_broken,
    build_env_supply_crate_loot,
    build_env_wrecked_car,
)
from mesh_utils import (
    add_box,
    add_cone,
    add_cylinder,
    apply_box_uvs,
    finalize_mesh,
)
from palette import create_materials
from render_environment import _add_bounded_atmosphere_haze, _add_dusk_lights
from render_preview import aim_camera, configure_renderer, load_rgba_np, render_image, save_rgba_np
import numpy as np


def _assert_pure_tris(mesh_objs):
    for m in mesh_objs:
        non_tris = sum(1 for p in m.data.polygons if len(p.vertices) != 3)
        if non_tris:
            raise RuntimeError(f"Non-triangle faces on {m.name}: {non_tris}")


def _inspect_glb(glb_path):
    with open(glb_path, "rb") as f:
        raw = f.read()
    jlen = struct.unpack("<I", raw[12:16])[0]
    g = json.loads(raw[20:20 + jlen].decode("utf-8"))
    return {
        "bytes": len(raw),
        "meshes": len(g.get("meshes", [])),
        "materials": len(g.get("materials", [])),
        "images": len(g.get("images", [])),
    }


def _add_puddle_fan(bm, px, py, pz, rx, ry, yaw, seed, mat_idx, segments=12):
    """Add an organic low-poly glossy water/mud puddle polygon built natively from triangles."""
    ca, sa = math.cos(yaw), math.sin(yaw)
    vc = bm.verts.new((px, py, pz))
    ring = []
    for i in range(segments):
        ang = (2.0 * math.pi * i) / segments
        wobble = 0.78 + 0.34 * abs(math.sin(ang * 2.5 + seed * 0.7))
        lx = math.cos(ang) * rx * wobble
        ly = math.sin(ang) * ry * wobble
        wx = px + lx * ca - ly * sa
        wy = py + lx * sa + ly * ca
        ring.append(bm.verts.new((wx, wy, pz)))
    for i in range(segments):
        f = bm.faces.new((vc, ring[i], ring[(i + 1) % segments]))
        f.material_index = mat_idx


def _add_barbed_coil(bm, p0, p1, radius=0.18, turns=5, mat_idx=0):
    """Build low-poly spiral barbed wire coil segments between p0 and p1."""
    v0, v1 = Vector(p0), Vector(p1)
    axis = v1 - v0
    length = axis.length
    if length < 0.05:
        return
    z_dir = axis.normalized()
    ref = Vector((0, 0, 1)) if abs(z_dir.z) < 0.8 else Vector((0, 1, 0))
    x_dir = z_dir.cross(ref).normalized()
    y_dir = z_dir.cross(x_dir).normalized()

    steps = max(12, turns * 6)
    pts = []
    for i in range(steps + 1):
        t = i / steps
        ang = t * turns * 2.0 * math.pi
        pos = v0 + axis * t + (x_dir * math.cos(ang) + y_dir * math.sin(ang)) * radius
        pts.append(tuple(pos))
    for i in range(steps):
        add_cylinder(bm, pts[i], pts[i + 1], 0.015, 0.015, segments=4, mat_idx=mat_idx)


def _add_czech_hedgehog(bm, cx, cy, cz=0.0, scale=0.85, yaw=0.0, mat_steel=0, mat_rust=0):
    """Three crossed rusted steel I-beams anchored in the mud as anti-tank obstacle."""
    axes = (
        Vector(( 0.85,  0.52, 0.90)),
        Vector((-0.85,  0.52, 0.90)),
        Vector(( 0.00, -0.92, 0.90)),
    )
    rot_m = Euler((0.0, 0.0, yaw), "XYZ").to_matrix()
    center = Vector((cx, cy, cz + 0.44 * scale))
    for i, a in enumerate(axes):
        d = (rot_m @ a).normalized() * (0.72 * scale)
        p0 = tuple(center - d)
        p1 = tuple(center + d)
        add_cylinder(bm, p0, p1, 0.065 * scale, 0.055 * scale, segments=4, mat_idx=mat_rust if i % 2 else mat_steel)


def build_muddy_battlefield_terrain(materials, idx_map, col):
    """160m x 160m wet muddy brown earth with glossy rainwater puddles, duckboards & shell mounds."""
    bm = bmesh.new()
    m_mud = idx_map["Mat_Env_MudWet"]
    m_soil = idx_map["Mat_Env_SoilCracked"]
    m_puddle = idx_map["Mat_Env_MudPuddle"]
    m_wood = idx_map["Mat_Env_WoodPlank"]
    m_conc = idx_map["Mat_Env_ConcreteDark"]

    # Flat walkable wet muddy base flush at Z = 0.0 across central battle zone
    add_box(bm, (0.0, 0.0, -0.06), (160.0, 160.0, 0.12), mat_idx=m_mud)

    # Outer mud berms & bombed earth ridges strictly outside Y in [-4.5, +4.5]
    outer_berms = (
        (-28.0,  16.0, 18.0, 9.0, 1.8,  0.18),
        (  0.0,  17.5, 24.0, 7.5, 1.4, -0.06),
        ( 29.0,  16.2, 18.0, 9.0, 1.9, -0.22),
        (-34.0, -18.5, 16.0, 9.5, 1.3,  0.28),
        ( 34.0, -18.5, 16.0, 9.5, 1.3, -0.26),
        (  0.0, -34.0, 38.0, 11.0, 1.5, 0.02),
    )
    for bx, by, bw, bd, bh, rz in outer_berms:
        add_box(bm, (bx, by, bh * 0.36 - 0.02), (bw, bd, bh), rot=(0.0, 0.0, rz),
                bevel=0.45, taper_top=(0.60, 0.56), mat_idx=m_mud)

    # Low muddy mounds flanking the battlefield margins (outside walking corridor)
    mud_mounds = (
        (-4.0,  5.6, 3.2, 2.2, 0.42, 0.25),
        ( 1.2,  5.2, 2.8, 1.9, 0.36, -0.18),
        ( 5.0,  5.6, 3.0, 2.1, 0.45, 0.12),
        (-3.6, -5.8, 3.4, 2.2, 0.38, -0.22),
        ( 2.8, -5.5, 3.1, 2.0, 0.40, 0.20),
    )
    for mx, my, mw, md, mh, rz in mud_mounds:
        add_box(bm, (mx, my, mh * 0.32), (mw, md, mh), rot=(0.0, 0.0, rz),
                bevel=0.35, taper_top=(0.55, 0.52), mat_idx=m_mud)

    # 14 glossy muddy rainwater puddles reflecting dusk light & fire/siren glow
    puddle_specs = (
        (-4.1,  0.85, 1.05, 0.55,  0.18, 11),
        (-3.6, -1.45, 1.25, 0.62, -0.24, 17),
        (-2.2,  0.15, 1.40, 0.72,  0.32, 23),
        (-1.4, -2.05, 1.15, 0.58, -0.12, 31),
        (-0.3,  1.65, 1.35, 0.64,  0.40, 41),
        ( 0.4, -0.45, 1.50, 0.75, -0.18, 53),
        ( 1.8,  1.25, 1.22, 0.58,  0.22, 61),
        ( 2.3, -1.75, 1.30, 0.62, -0.28, 71),
        ( 3.7,  0.35, 1.18, 0.60,  0.15, 83),
        ( 4.3, -1.10, 1.10, 0.52, -0.35, 89),
        (-2.5,  4.90, 0.88, 0.76,  0.10, 97),
        ( 2.6,  5.10, 0.92, 0.80, -0.15, 103),
        (-1.2, -5.40, 0.90, 0.75,  0.25, 109),
        ( 3.4, -5.20, 0.95, 0.78, -0.20, 113),
    )
    for px, py, rx, ry, yaw, seed in puddle_specs:
        _add_puddle_fan(bm, px, py, 0.005, rx, ry, yaw, seed, m_puddle, segments=12)

    # Sunken wooden duckboards along mud edges (keep Z flush <= 0.025 so legs never clip)
    duckboard_runs = (
        (-4.2,  2.78, 2.2,  0.04),
        (-1.4,  2.85, 2.0, -0.06),
        ( 1.5,  2.82, 2.1,  0.05),
        (-4.0, -2.82, 2.2, -0.05),
        (-1.1, -2.88, 2.0,  0.04),
        ( 1.8, -2.84, 2.1, -0.03),
    )
    for dx, dy, length, rz in duckboard_runs:
        add_box(bm, (dx, dy, 0.009), (length, 0.42, 0.018), rot=(0.02, -0.015, rz), mat_idx=m_wood)
        for sx in (-0.75, -0.25, 0.25, 0.75):
            add_box(bm, (dx + sx * (length / 2.2), dy, 0.016), (0.14, 0.48, 0.014),
                    rot=(-0.02, 0.02, rz + 0.03 * sx), mat_idx=m_wood)

    # Concrete broken road chunks half-buried in the brown mud
    slabs = (
        (-0.8,  3.95, 1.35, 0.95, 0.14, 0.35),
        ( 3.9, -4.15, 1.50, 0.88, 0.16, -0.42),
        (-7.4,  4.85, 1.70, 1.10, 0.18, 0.15),
    )
    for sx, sy, sw, sd, sh, rz in slabs:
        add_box(bm, (sx, sy, 0.02), (sw, sd, sh), rot=(0.06, -0.08, rz), bevel=0.04, mat_idx=m_conc)

    obj, tris = finalize_mesh("Env_MuddyBattlefield", bm, materials, collection=col)
    apply_box_uvs(obj, tex_scale=0.16)
    return obj, tris


def build_human_fortress_base(materials, idx_map, col):
    """Heavy Apocalypse Scrap-Metal Fortress + Blast Gate + Watchtower + Hedgehogs on West side."""
    bm = bmesh.new()
    m_steel = idx_map["Mat_Env_FortressSteel"]
    m_rust = idx_map["Mat_Env_RustHeavy"]
    m_wood = idx_map["Mat_Env_WoodPlank"]
    m_bag = idx_map["Mat_Env_Sandbag"]
    m_wire = idx_map["Mat_Env_BarbedWire"]
    m_haz = idx_map["Mat_Env_HazardYellow"]
    m_blue = idx_map["Mat_Env_BeaconBlue"]
    m_ember = idx_map["Mat_Env_EmberGlow"]
    m_fire = idx_map["Mat_Env_FireCore"]
    m_conc = idx_map["Mat_Env_ConcreteDark"]
    m_metal = idx_map["Mat_Env_MetalScrap"]
    m_cloth = idx_map["Mat_Env_MedCanvas"]

    # 1. Angled Scrap-Metal Palisade Perimeter Walls (North Wing Y=+1.4..+5.5 & South Wing Y=-1.4..-5.5)
    wall_segments = (
        # (center_x, center_y, len_y, height, rot_z_deg)
        (-5.85,  2.55, 2.35, 3.15, -14.0),
        (-6.55,  4.50, 2.25, 3.25, -34.0),
        (-8.20,  5.65, 2.60, 3.05, -72.0),
        (-5.85, -2.55, 2.35, 3.15,  14.0),
        (-6.55, -4.50, 2.25, 3.25,  34.0),
        (-8.20, -5.65, 2.60, 3.05,  72.0),
        (-9.60,  0.00, 9.20, 3.00,   0.0),  # Rear enclosing bunker wall
    )
    for idx, (wx, wy, wlen, wh, rz_deg) in enumerate(wall_segments):
        rz = math.radians(rz_deg)
        # Main corrugated steel wall slab
        add_box(bm, (wx, wy, wh * 0.5), (0.34, wlen, wh), rot=(0.0, 0.0, rz), bevel=0.03, mat_idx=m_steel)
        # Heavy concrete footing blocks & rusted I-beam vertical ribs
        add_box(bm, (wx, wy, 0.22), (0.58, wlen * 0.96, 0.44), rot=(0.0, 0.0, rz), bevel=0.04, mat_idx=m_conc)
        for k in (-0.36, 0.36):
            rx = wx - math.sin(rz) * (wlen * k)
            ry = wy + math.cos(rz) * (wlen * k)
            add_box(bm, (rx + 0.14 * math.cos(rz), ry + 0.14 * math.sin(rz), wh * 0.52),
                    (0.18, 0.16, wh * 1.02), rot=(0.0, 0.0, rz), mat_idx=m_rust if idx % 2 else m_metal)
        # Welded angled armor plate patches + hazard warning band
        add_box(bm, (wx + 0.19 * math.cos(rz), wy + 0.19 * math.sin(rz), wh * 0.46),
                (0.06, wlen * 0.55, 0.72), rot=(0.06, 0.0, rz), mat_idx=m_rust)
        if abs(wy) < 3.5 and wx > -9.0:
            add_box(bm, (wx + 0.21 * math.cos(rz), wy + 0.21 * math.sin(rz), 1.55),
                    (0.05, wlen * 0.48, 0.24), rot=(0.0, 0.0, rz), mat_idx=m_haz)
        # Stacked top sandbag rampart & razor barbed-wire coils
        if wx > -9.0:
            add_box(bm, (wx, wy, wh + 0.14), (0.48, wlen * 0.92, 0.28), rot=(0.0, 0.0, rz), bevel=0.05, mat_idx=m_bag)
            p_start = (wx + 0.22 * math.cos(rz) - math.sin(rz) * wlen * 0.45,
                       wy + 0.22 * math.sin(rz) + math.cos(rz) * wlen * 0.45, wh + 0.42)
            p_end = (wx + 0.22 * math.cos(rz) + math.sin(rz) * wlen * 0.45,
                     wy + 0.22 * math.sin(rz) - math.cos(rz) * wlen * 0.45, wh + 0.42)
            _add_barbed_coil(bm, p_start, p_end, radius=0.18, turns=5, mat_idx=m_wire)
            # Angled rear timber strut braces
            bx = wx - 0.85 * math.cos(rz)
            by = wy - 0.85 * math.sin(rz)
            add_cylinder(bm, (bx, by, 0.0), (wx - 0.15 * math.cos(rz), wy - 0.15 * math.sin(rz), wh * 0.72),
                         0.09, 0.08, segments=6, mat_idx=m_wood)

    # 2. Central Armored Steel Blast Gate Towers & Overhead Gantry (X = -5.6, Y = +/-1.42)
    for side in (-1.0, 1.0):
        gy = side * 1.48
        add_box(bm, (-5.58, gy, 1.65), (0.72, 0.68, 3.30), bevel=0.04, taper_top=(0.90, 0.90), mat_idx=m_conc)
        add_box(bm, (-5.54, gy, 1.55), (0.78, 0.56, 2.40), bevel=0.02, mat_idx=m_steel)
        add_box(bm, (-5.18, gy, 1.40), (0.08, 0.46, 0.34), mat_idx=m_haz)
        # Beacons atop gate pylons
        add_box(bm, (-5.58, gy, 3.44), (0.28, 0.28, 0.28), bevel=0.04, mat_idx=m_blue)
        # Sandbag pillbox buttresses flanking the gate
        for sb_k in range(3):
            add_box(bm, (-5.18, gy + side * 0.42 + (sb_k - 1) * 0.18, 0.22 + sb_k * 0.20),
                    (0.54, 0.42, 0.22), rot=(0.0, 0.0, side * 0.35), bevel=0.04, mat_idx=m_bag)

    # Overhead heavy reinforced steel gate lintel beam + floodlights + barbed wire crown
    add_box(bm, (-5.58, 0.0, 3.12), (0.78, 3.65, 0.52), bevel=0.04, mat_idx=m_steel)
    add_box(bm, (-5.20, 0.0, 3.12), (0.08, 2.60, 0.24), mat_idx=m_haz)
    _add_barbed_coil(bm, (-5.40, -1.75, 3.56), (-5.40, 1.75, 3.56), radius=0.20, turns=7, mat_idx=m_wire)
    # Angled half-open armored blast gate doors framing the entrance
    for side in (-1.0, 1.0):
        add_box(bm, (-5.78, side * 1.24, 1.15), (0.78, 0.12, 2.25), rot=(0.0, 0.0, side * 0.38), bevel=0.02, mat_idx=m_rust)

    # 3. Elevated Guard Watchtower ("Menara Jaga") at X = -6.8, Y = +3.5 (Z = 0 -> 7.8m)
    wt_x, wt_y = -6.85, 3.55
    wt_r = 1.02
    wt_h = 3.45
    corners = ((-1, -1), (1, -1), (1, 1), (-1, 1))
    for cx, cy in corners:
        lx0, ly0 = wt_x + cx * (wt_r + 0.16), wt_y + cy * (wt_r + 0.16)
        lx1, ly1 = wt_x + cx * wt_r, wt_y + cy * wt_r
        add_cylinder(bm, (lx0, ly0, 0.0), (lx1, ly1, wt_h), 0.13, 0.10, segments=6, mat_idx=m_wood)
        # Upper roof posts
        add_cylinder(bm, (lx1, ly1, wt_h), (lx1, ly1, wt_h + 1.95), 0.08, 0.07, segments=6, mat_idx=m_wood)

    # Diagonal X-bracing between watchtower stilts
    for c_i in range(4):
        c0 = corners[c_i]
        c1 = corners[(c_i + 1) % 4]
        p00 = (wt_x + c0[0] * (wt_r + 0.14), wt_y + c0[1] * (wt_r + 0.14), 0.35)
        p01 = (wt_x + c1[0] * (wt_r + 0.05), wt_y + c1[1] * (wt_r + 0.05), wt_h * 0.52)
        p10 = (wt_x + c1[0] * (wt_r + 0.14), wt_y + c1[1] * (wt_r + 0.14), 0.35)
        p11 = (wt_x + c0[0] * (wt_r + 0.05), wt_y + c0[1] * (wt_r + 0.05), wt_h * 0.52)
        add_cylinder(bm, p00, p01, 0.05, 0.05, segments=5, mat_idx=m_wood)
        add_cylinder(bm, p10, p11, 0.05, 0.05, segments=5, mat_idx=m_wood)

    # Elevated firing platform deck + sandbag parapet + scrap steel armor railing
    add_box(bm, (wt_x, wt_y, wt_h), (2.48, 2.48, 0.20), bevel=0.03, mat_idx=m_wood)
    for wall_pos, wall_sz in (
        ((wt_x + 1.12, wt_y, wt_h + 0.45), (0.20, 2.35, 0.72)),
        ((wt_x - 1.12, wt_y, wt_h + 0.45), (0.20, 2.35, 0.72)),
        ((wt_x, wt_y - 1.12, wt_h + 0.45), (2.35, 0.20, 0.72)),
        ((wt_x, wt_y + 1.12, wt_h + 0.45), (2.35, 0.20, 0.72)),
    ):
        add_box(bm, wall_pos, wall_sz, bevel=0.02, mat_idx=m_steel)
    add_box(bm, (wt_x + 1.12, wt_y, wt_h + 0.90), (0.28, 2.10, 0.24), bevel=0.04, mat_idx=m_bag)

    # Sloped corrugated steel watchtower roof + tattered banner + radar/radio mast + searchlights
    add_box(bm, (wt_x, wt_y, wt_h + 2.02), (2.68, 2.68, 0.18), rot=(0.0, -0.14, 0.0), bevel=0.03, mat_idx=m_rust)
    add_box(bm, (wt_x + 1.24, wt_y - 0.55, wt_h + 0.20), (0.04, 0.78, 0.65), rot=(0.12, 0.08, 0.0), mat_idx=m_cloth)
    # Searchlight projector cans aimed across the muddy battlefield
    for sy_off in (-0.58, 0.58):
        add_cylinder(bm, (wt_x + 1.05, wt_y + sy_off, wt_h + 1.65), (wt_x + 1.48, wt_y + sy_off - 0.10, wt_h + 1.50),
                     0.14, 0.20, segments=8, mat_idx=m_metal)
        add_box(bm, (wt_x + 1.48, wt_y + sy_off - 0.10, wt_h + 1.50), (0.05, 0.26, 0.26), mat_idx=m_fire)
    # Mast spire atop roof
    add_cylinder(bm, (wt_x - 0.35, wt_y, wt_h + 2.05), (wt_x - 0.35, wt_y, wt_h + 4.30), 0.055, 0.03, segments=6, mat_idx=m_metal)
    add_box(bm, (wt_x - 0.35, wt_y, wt_h + 4.38), (0.22, 0.22, 0.26), bevel=0.03, mat_idx=m_ember)

    # 4. Interior Fortress Command Bunker Shelter (X = -8.4, Y = -2.2)
    add_box(bm, (-8.3, -2.2, 1.30), (2.2, 3.0, 2.60), bevel=0.05, mat_idx=m_conc)
    add_box(bm, (-8.3, -2.2, 2.72), (2.6, 3.3, 0.24), rot=(0.0, -0.06, 0.0), bevel=0.03, mat_idx=m_steel)
    add_box(bm, (-7.18, -2.2, 2.05), (0.10, 1.40, 0.36), mat_idx=m_ember)

    # 5. Four Anti-Tank Czech Hedgehogs embedded along approaches
    for hx, hy, sc, yaw in (
        (-4.65,  3.35, 0.88, 0.4),
        (-4.65, -3.35, 0.88, -0.5),
        (-1.85, -3.75, 0.82, 0.8),
        ( 1.55,  3.85, 0.84, -0.3),
    ):
        _add_czech_hedgehog(bm, hx, hy, cz=0.0, scale=sc, yaw=yaw, mat_steel=m_steel, mat_rust=m_rust)

    obj, tris = finalize_mesh("Env_HumanFortress", bm, materials, collection=col)
    apply_box_uvs(obj, tex_scale=0.52)
    return obj, tris


def build_zombie_hive_base(materials, idx_map, col):
    """Corrupted Bio-Hive Spire + Shattered Bunker Shell + Rib Arches + Glowing Bio-Core on East side."""
    bm = bmesh.new()
    m_flesh = idx_map["Mat_Env_HiveFlesh"]
    m_glow = idx_map["Mat_Env_HiveGlow"]
    m_conc = idx_map["Mat_Env_ConcreteDark"]
    m_brick = idx_map["Mat_Env_BrickRuined"]
    m_rust = idx_map["Mat_Env_RustHeavy"]

    # 1. Ruptured Concrete Bunker Shell swallowed by the Bio-Hive
    bunker_walls = (
        ((7.8,  2.55, 1.35), (2.6, 0.55, 2.70), ( 0.08, -0.06,  0.32)),
        ((7.8, -2.55, 1.35), (2.6, 0.55, 2.70), (-0.08,  0.06, -0.32)),
        ((8.9,  0.00, 1.65), (0.85, 4.40, 3.30), ( 0.00,  0.08,  0.00)),
        ((7.6,  1.80, 2.75), (2.8, 2.20, 0.36), ( 0.24, -0.18,  0.15)),
        ((7.6, -1.80, 2.75), (2.8, 2.20, 0.36), (-0.22, -0.16, -0.15)),
    )
    for i, (pos, sz, rot) in enumerate(bunker_walls):
        add_box(bm, pos, sz, rot=rot, bevel=0.06, taper_top=(0.86, 0.88), mat_idx=m_conc if i < 3 else m_brick)

    # Exposed jagged steel rebar jutting from broken bunker slabs
    for ry in (-2.2, -1.2, 1.1, 2.3):
        add_cylinder(bm, (6.55, ry, 2.45), (5.85, ry * 0.92, 2.85), 0.035, 0.025, segments=5, mat_idx=m_rust)

    # 2. Towering Corrupted Bio-Hive Spire (X = +7.5, Y = 0, Z = 0 -> 5.4m)
    spires = (
        ((7.55,  0.00, 0.0), (7.75,  0.05, 5.45), 1.45, 0.32),
        ((7.20,  1.45, 0.0), (7.60,  1.15, 3.95), 0.92, 0.22),
        ((7.20, -1.45, 0.0), (7.60, -1.15, 4.10), 0.96, 0.24),
        ((6.65,  2.15, 0.0), (6.30,  1.85, 2.75), 0.68, 0.16),
        ((6.65, -2.15, 0.0), (6.30, -1.85, 2.85), 0.70, 0.16),
    )
    for p0, p1, r0, r1 in spires:
        add_cylinder(bm, p0, p1, r0, r1, segments=8, mat_idx=m_flesh)
        add_cone(bm, p1, (p1[0] - 0.15, p1[1], p1[2] + 0.75), r1, segments=7, mat_idx=m_flesh)

    # 3. 5 Curved Chitin Rib Arches cradling the front glowing Bio-Core Heart
    for k in range(5):
        ang = -0.85 + k * 0.425
        y_off = math.sin(ang) * 2.15
        x_base = 6.95 - math.cos(ang) * 0.55
        p_mid = (x_base - 0.75, y_off * 0.82, 2.05)
        p_tip = (6.35, y_off * 0.28, 3.10 - abs(k - 2) * 0.22)
        add_cylinder(bm, (x_base, y_off, 0.0), p_mid, 0.26, 0.20, segments=6, mat_idx=m_flesh)
        add_cylinder(bm, p_mid, p_tip, 0.20, 0.08, segments=6, mat_idx=m_flesh)

    # Faceted glowing Bio-Core Heart Crystal floating inside rib cage (X = +6.45, Z = 1.90)
    add_box(bm, (6.42, 0.0, 1.90), (0.88, 0.88, 1.15), rot=(0.45, 0.35, 0.78),
            bevel=0.14, mat_idx=m_glow)

    # 4. Pulsing Toxic Egg-Sacs & Creeping Organic Tendril Roots (reaching X = +5.3)
    sacs = (
        (5.95,  1.25, 0.34, 0.42),
        (5.85, -1.35, 0.36, 0.45),
        (5.65,  0.38, 0.28, 0.35),
        (5.60, -0.52, 0.30, 0.36),
        (6.45,  2.55, 0.42, 0.48),
        (6.45, -2.55, 0.40, 0.46),
    )
    for sx, sy, sz, rad in sacs:
        add_box(bm, (sx, sy, sz), (rad * 1.35, rad * 1.25, rad * 1.45),
                rot=(0.2, -0.15, sx), bevel=rad * 0.35, mat_idx=m_glow if rad < 0.38 else m_flesh)

    for ty_end in (-2.5, -1.6, -0.7, 0.7, 1.6, 2.5):
        add_cylinder(bm, (6.60, ty_end * 0.65, 0.08), (5.25, ty_end, 0.02),
                     0.20, 0.05, segments=6, mat_idx=m_flesh)

    obj, tris = finalize_mesh("Env_ZombieBioHive", bm, materials, collection=col)
    apply_box_uvs(obj, tex_scale=0.55)
    return obj, tris


def build_war_ruin_shell(materials, idx_map, col, name, loc, rot_z_deg=0.0, height=7.2, variant=0):
    """Artillery-shelled abandoned building ruin with collapsed floor slabs, broken glass & bent steel rebar."""
    bm = bmesh.new()
    m_conc = idx_map["Mat_Env_ConcreteCracked"]
    m_dark = idx_map["Mat_Env_ConcreteDark"]
    m_brick = idx_map["Mat_Env_BrickRuined"]
    m_plaster = idx_map["Mat_Env_PlasterDamaged"]
    m_rust = idx_map["Mat_Env_RustHeavy"]
    m_glass = idx_map["Mat_Env_GlassBroken"]

    w, d = 5.4, 3.8
    # Ground rubble foundation skirt
    add_box(bm, (0.0, 0.0, 0.22), (w + 0.55, d + 0.45, 0.44), bevel=0.08, mat_idx=m_dark)

    # Rear intact wall + ragged left/right side walls (front face blasted open so battle interior reads!)
    add_box(bm, (0.0, d * 0.42, height * 0.46), (w, 0.36, height * 0.92), bevel=0.04, mat_idx=m_brick if variant % 2 == 0 else m_conc)
    add_box(bm, (-w * 0.45, 0.0, height * 0.42), (0.38, d, height * 0.84), bevel=0.04, mat_idx=m_plaster)
    add_box(bm, ( w * 0.45, 0.0, height * 0.34), (0.38, d, height * 0.68), bevel=0.04, mat_idx=m_conc)

    # 4 corner concrete pillars + exposed steel rebar tufts at snapped column tops
    col_heights = (height * 0.88, height * 0.74, height * 0.96, height * 0.62)
    col_xy = ((-w * 0.46, -d * 0.44), (w * 0.46, -d * 0.44), (-w * 0.46, d * 0.44), (w * 0.46, d * 0.44))
    for (cx, cy), ch in zip(col_xy, col_heights):
        add_box(bm, (cx, cy, ch * 0.5), (0.44, 0.44, ch), bevel=0.03, mat_idx=m_dark)
        for rk in range(3):
            add_cylinder(bm, (cx + (rk - 1) * 0.08, cy, ch - 0.05),
                         (cx + (rk - 1) * 0.16, cy + (0.12 if rk % 2 else -0.10), ch + 0.58),
                         0.022, 0.015, segments=4, mat_idx=m_rust)

    # Half-collapsed intermediate 2nd floor concrete slab resting diagonally into rubble
    add_box(bm, (-0.35, 0.10, height * 0.46), (w * 0.86, d * 0.82, 0.26),
            rot=(0.24 if variant % 2 == 0 else -0.20, 0.16, 0.04), bevel=0.04, mat_idx=m_conc)
    # Jagged roof parapet cornice fragment + dark ruined window sashes
    add_box(bm, (-0.95, -d * 0.42, height * 0.72), (w * 0.54, 0.32, 0.52),
            rot=(0.05, -0.06, 0.0), bevel=0.03, mat_idx=m_dark)
    for wx in (-1.35, 0.0, 1.35):
        add_box(bm, (wx, d * 0.40, height * 0.34), (0.95, 0.22, 1.35), mat_idx=m_glass)
        add_box(bm, (wx, d * 0.38, height * 0.65), (0.95, 0.22, 1.15), mat_idx=m_glass)

    # Front bombed brick pile & fallen beam
    add_box(bm, (0.55, -d * 0.35, 0.42), (2.4, 1.35, 0.82), rot=(0.10, -0.12, 0.25), bevel=0.10, taper_top=(0.58, 0.55), mat_idx=m_brick)

    obj, tris = finalize_mesh(name, bm, materials, collection=col)
    obj.location = Vector(loc)
    obj.rotation_euler = Euler((0.0, 0.0, math.radians(rot_z_deg)), "XYZ")
    apply_box_uvs(obj, tex_scale=0.38)
    return obj, tris


def build_war_battlefield_scene(materials, idx_map, collection=None):
    """Assemble full epic 2-Base War Battlefield Diorama grounded at Z = 0.0."""
    col = collection if collection is not None else bpy.context.scene.collection
    placed = []
    total_tris = 0

    def add_mod(fn, iname, loc, rz=0.0, sc=1.0):
        nonlocal total_tris
        obj, t = _place_piece(fn, materials, idx_map, col, iname, loc=loc, rot_z_deg=rz, scale=sc)
        placed.append(obj)
        total_tris += t

    # 1. Muddy battlefield terrain + glossy wet puddles + duckboards
    m_obj, m_tris = build_muddy_battlefield_terrain(materials, idx_map, col)
    placed.append(m_obj)
    total_tris += m_tris

    # 2. West Human Scrap-Metal Fortress & East Corrupted Zombie Bio-Hive
    f_obj, f_tris = build_human_fortress_base(materials, idx_map, col)
    placed.append(f_obj)
    total_tris += f_tris

    h_obj, h_tris = build_zombie_hive_base(materials, idx_map, col)
    placed.append(h_obj)
    total_tris += h_tris

    # 3. War-Torn Abandoned Concrete & Brick Ruins in Background (+Y)
    ruin_specs = (
        ("Env_WarRuin_W",  (-11.4,  8.2, 0.0),   6.0, 7.6, 0),
        ("Env_WarRuin_WC", ( -2.8,  9.0, 0.0),  -3.0, 6.8, 1),
        ("Env_WarRuin_EC", (  3.2,  9.2, 0.0),   4.0, 7.2, 2),
        ("Env_WarRuin_E",  ( 11.8,  8.2, 0.0),  -7.0, 7.5, 3),
    )
    for rname, rloc, rrz, rh, rvar in ruin_specs:
        robj, rtris = build_war_ruin_shell(materials, idx_map, col, rname, rloc, rot_z_deg=rrz, height=rh, variant=rvar)
        placed.append(robj)
        total_tris += rtris

    # 4. War Debris, Wrecked Cars, Police Cruiser (with siren), Shell Craters, Barrels & Lamps
    add_mod(build_env_wrecked_car,        "Env_WreckedCar_N",   (-1.6,  4.4, 0.0), rz=-22.0)
    add_mod(build_env_police_cruiser,     "Env_PoliceCruiser",  ( 2.4,  4.5, 0.0), rz=158.0)
    add_mod(build_env_wrecked_car,        "Env_WreckedCar_SE",  ( 9.2, -5.8, 0.0), rz=145.0)
    add_mod(build_env_supply_crate_loot,  "Env_FortCrate_1",    (-8.0,  1.8, 0.0), rz=14.0)
    add_mod(build_env_supply_crate_loot,  "Env_FortCrate_2",    (-7.4, -0.8, 0.0), rz=-18.0)
    add_mod(build_env_sandbag_barricade,  "Env_MidSandbag_N",   (-0.6,  3.5, 0.0), rz=-12.0)
    add_mod(build_env_jersey_barrier,     "Env_Barrier_SW",     (-2.8, -3.9, 0.0), rz=8.0)
    add_mod(build_env_jersey_barrier,     "Env_Barrier_NE",     ( 3.2,  3.7, 0.0), rz=-14.0)

    # Burning Fire Barrels lighting Fortress Gate + Midfield + Hive flank
    for fname, floc, frz in (
        ("Env_FireBarrel_GateN", (-5.0,  2.4, 0.0), 15.0),
        ("Env_FireBarrel_GateS", (-5.0, -2.4, 0.0), -25.0),
        ("Env_FireBarrel_Mid",   ( 0.2,  4.1, 0.0), 40.0),
    ):
        add_mod(build_env_fire_barrel, fname, floc, rz=frz)

    add_mod(build_env_street_lamp_broken, "Env_Lamp_W", (-8.5, 3.8, 0.0), rz=-10.0)
    add_mod(build_env_street_lamp_broken, "Env_Lamp_E", ( 5.8, 3.9, 0.0), rz=170.0)

    for cname, cloc, crz, csc in (
        ("Env_Crater_N1", (-2.5,  4.9, 0.0),  20.0, 0.92),
        ("Env_Crater_N2", ( 2.6,  5.1, 0.0), -35.0, 0.95),
        ("Env_Crater_S1", (-1.2, -5.4, 0.0),  15.0, 0.88),
        ("Env_Crater_S2", ( 3.4, -5.2, 0.0), -22.0, 0.92),
    ):
        add_mod(build_env_rubble_crater, cname, cloc, rz=crz, sc=csc)

    add_mod(build_env_dead_tree, "Env_DeadTree_W",  (-13.8,  7.4, 0.0), rz=30.0)
    add_mod(build_env_dead_tree, "Env_DeadTree_C",  (  0.2,  6.8, 0.0), rz=110.0, sc=0.92)
    add_mod(build_env_dead_tree, "Env_DeadTree_E",  ( 14.0,  7.2, 0.0), rz=-45.0)
    add_mod(build_env_dead_tree, "Env_DeadTree_SE", ( 12.2, -7.2, 0.0), rz=65.0, sc=0.86)

    for k, (gx, gy, sc, rz) in enumerate((
        (-10.2, 3.6, 1.0, 20), (-3.8, 3.7, 0.9, 85), (0.8, 3.6, 0.95, 145),
        ( 4.6,  3.5, 1.0, 210), (-4.0, -3.5, 0.95, 50), (3.5, -3.6, 0.95, 165),
    )):
        add_mod(build_env_grass_clump_tall, f"Env_DeadGrass_{k}", (gx, gy, 0.0), rz=rz, sc=sc)

    # 5. Distant bombed city horizon
    s_obj, s_tris = _build_distant_city_skyline(materials, idx_map, col)
    placed.append(s_obj)
    total_tris += s_tris

    # Ensure every mesh has pure triangles
    for obj in placed:
        mesh = obj.data
        if any(len(p.vertices) != 3 for p in mesh.polygons):
            bm_t = bmesh.new()
            bm_t.from_mesh(mesh)
            bmesh.ops.triangulate(bm_t, faces=bm_t.faces)
            bm_t.to_mesh(mesh)
            bm_t.free()
            mesh.update()

    return placed, total_tris


def render_war_qa_sheet(out_path):
    tmp_dir = os.path.join(PROJECT_DIR, "renders", "_tmp_war_qa")
    os.makedirs(tmp_dir, exist_ok=True)
    clear_scene()
    scene = bpy.context.scene
    configure_renderer(scene)
    materials, idx_map = create_materials(with_env_textures=True)
    build_war_battlefield_scene(materials, idx_map)

    _add_dusk_lights(center=(0.0, 2.0, 1.8), scale=3.2, bg_rgb=(0.09, 0.11, 0.15), atmospheric_sky=True)
    _add_bounded_atmosphere_haze(scene)

    for lname, lx, ly in (("FireGateN", -5.0, 2.4), ("FireGateS", -5.0, -2.4), ("FireMid", 0.2, 4.1)):
        pl_data = bpy.data.lights.new(name=lname, type="POINT")
        pl_data.energy = 420.0
        pl_data.color = (1.0, 0.45, 0.12)
        pl_data.shadow_soft_size = 0.30
        pl = bpy.data.objects.new(name=lname, object_data=pl_data)
        pl.location = (lx, ly, 1.45)
        scene.collection.objects.link(pl)

    # Toxic green glow light inside Zombie Bio-Hive
    hv_data = bpy.data.lights.new(name="HiveCorePt", type="POINT")
    hv_data.energy = 650.0
    hv_data.color = (0.55, 1.0, 0.18)
    hv_data.shadow_soft_size = 0.45
    hv = bpy.data.objects.new(name="HiveCorePt", object_data=hv_data)
    hv.location = (6.2, 0.0, 2.0)
    scene.collection.objects.link(hv)

    cam_data = bpy.data.cameras.new("WarQACam")
    cam_data.type = "PERSP"
    cam_data.lens = 25.0
    cam_data.clip_start = 0.1
    cam_data.clip_end = 260.0
    cam = bpy.data.objects.new("WarQACam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    views = [
        ("wide",     (-0.5, -16.2, 6.2), (0.0, 1.2, 1.6), 1600, 740),
        ("fortress", (-1.8,  -9.6, 3.8), (-6.2, 1.4, 2.1), 1600, 740),
    ]
    panels = []
    for tag, loc, tgt, w, h in views:
        aim_camera(cam, loc, tgt)
        p = os.path.join(tmp_dir, f"war_{tag}.png")
        render_image(scene, p, w, h)
        panels.append(load_rgba_np(p))

    gap = 6
    h0, w0, _ = panels[0].shape
    out_arr = np.zeros((h0 * 2 + gap, w0, 4), dtype=np.float32)
    out_arr[:, :, :3] = 0.05
    out_arr[:, :, 3] = 1.0
    out_arr[h0 + gap:, :, :] = panels[0]
    out_arr[:h0, :, :] = panels[1]
    save_rgba_np(out_arr, out_path)

    for fn in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, fn))
    os.rmdir(tmp_dir)
    print(f"Saved War Battlefield QA sheet: {out_path}")


def main():
    env_dir = os.path.join(PROJECT_DIR, "output", "environment")
    os.makedirs(env_dir, exist_ok=True)
    os.makedirs(os.path.join(PROJECT_DIR, "renders"), exist_ok=True)

    print("=" * 74)
    print("BUILDING WAR-TORN HUMAN FORTRESS vs ZOMBIE BIO-HIVE BATTLEFIELD")
    clear_scene()
    col = make_collection("WarBattlefield")
    materials, idx_map = create_materials(with_env_textures=True)
    objs, total_tris = build_war_battlefield_scene(materials, idx_map, collection=col)
    _assert_pure_tris(objs)

    mins, maxs = world_bounds(objs)
    blend_path = os.path.join(env_dir, "battlefield_fortress_war.blend")
    glb_path = os.path.join(env_dir, "battlefield_fortress_war.glb")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    export_glb(glb_path, selected_only=False, export_animations=False)
    info = _inspect_glb(glb_path)
    if info["images"] < 14:
        raise RuntimeError(f"battlefield_fortress_war.glb expected >= 14 PBR images, got {info['images']}")
    print(
        f"  WAR BATTLEFIELD : {len(objs)} meshes | {total_tris} tris | "
        f"span {maxs[0]-mins[0]:.1f}x{maxs[1]-mins[1]:.1f}x{maxs[2]-mins[2]:.1f}m | "
        f"imgs={info['images']} | {info['bytes'] / (1024*1024):.2f} MB"
    )

    render_war_qa_sheet(os.path.join(PROJECT_DIR, "renders", "battlefield_fortress_war_qa.png"))
    print("=" * 74)
    print("WAR BATTLEFIELD BUILD COMPLETE")


if __name__ == "__main__":
    main()
