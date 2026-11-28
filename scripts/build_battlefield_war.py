"""Build & export lightweight, matte-shaded War-Torn Human Fortress Battlefield GLB + QA render."""
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
import numpy as np
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

from build_survivor import clear_scene, export_glb, make_collection, world_bounds
from environment_apocalypse import (
    _place_piece,
    build_env_dead_tree,
    build_env_fire_barrel,
    build_env_grass_clump_tall,
    build_env_jersey_barrier,
    build_env_police_cruiser,
    build_env_rubble_crater,
    build_env_sandbag_barricade,
    build_env_street_lamp_broken,
    build_env_wrecked_car,
)
from mesh_utils import (
    add_box,
    add_cylinder,
    apply_box_uvs,
    finalize_mesh,
)
from palette import create_materials
from render_environment import _add_bounded_atmosphere_haze, _add_dusk_lights
from render_preview import aim_camera, configure_renderer, load_rgba_np, render_image, save_rgba_np


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
    meshes_meta = g.get("meshes", [])
    has_color0 = (
        len(meshes_meta) > 0
        and all(
            any("COLOR_0" in prim.get("attributes", {}) for prim in m.get("primitives", []))
            for m in meshes_meta
        )
    )
    return {
        "bytes": len(raw),
        "meshes": len(meshes_meta),
        "mesh_names": [m.get("name", "") for m in meshes_meta],
        "materials": len(g.get("materials", [])),
        "material_defs": g.get("materials", []),
        "images": len(g.get("images", [])),
        "has_color0": has_color0,
    }


def _add_barbed_coil(bm, p0, p1, radius=0.18, turns=4, mat_idx=0):
    """Build lightweight low-poly spiral barbed wire coil segments between p0 and p1."""
    v0, v1 = Vector(p0), Vector(p1)
    axis = v1 - v0
    length = axis.length
    if length < 0.05:
        return
    z_dir = axis.normalized()
    ref = Vector((0, 0, 1)) if abs(z_dir.z) < 0.8 else Vector((0, 1, 0))
    x_dir = z_dir.cross(ref).normalized()
    y_dir = z_dir.cross(x_dir).normalized()

    steps = max(8, turns * 4)
    pts = []
    for i in range(steps + 1):
        t = i / steps
        ang = t * turns * 2.0 * math.pi
        pos = v0 + axis * t + (x_dir * math.cos(ang) + y_dir * math.sin(ang)) * radius
        pts.append(tuple(pos))
    for i in range(steps):
        add_cylinder(bm, pts[i], pts[i + 1], 0.015, 0.015, segments=3, mat_idx=mat_idx)


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
    """Compact matte brown war-torn ground with subdivided AO battlegrid & zero glossy puddles."""
    bm = bmesh.new()
    m_mud = idx_map["Mat_Env_MudWet"]
    m_wood = idx_map["Mat_Env_WoodPlank"]
    m_conc = idx_map["Mat_Env_ConcreteDark"]

    # Outer horizon skirt slightly below Z = 0.0 so central battlegrid sits cleanly on top without Z-fighting
    add_box(bm, (2.0, 2.0, -0.10), (68.0, 56.0, 0.16), mat_idx=m_mud)

    # Subdivided visible battlegrid (X in [-11.5, +13.5], Y in [-7.5, +9.5]) for crisp baked contact AO
    x0, x1, nx = -11.5, 13.5, 30
    y0, y1, ny = -7.5, 9.5, 20
    grid_verts = []
    for iy in range(ny + 1):
        row = []
        wy = y0 + (y1 - y0) * (iy / ny)
        for ix in range(nx + 1):
            wx = x0 + (x1 - x0) * (ix / nx)
            # Subtle organic earth heave ONLY outside central combat corridor |Y| >= 4.0
            wz = 0.0
            if abs(wy) >= 4.0:
                edge_t = min(1.0, (abs(wy) - 4.0) / 3.5)
                wz = edge_t * 0.14 * (0.5 + 0.5 * math.sin(wx * 0.55 + wy * 0.72))
            row.append(bm.verts.new((wx, wy, wz)))
        grid_verts.append(row)

    for iy in range(ny):
        for ix in range(nx):
            v00 = grid_verts[iy][ix]
            v10 = grid_verts[iy][ix + 1]
            v11 = grid_verts[iy + 1][ix + 1]
            v01 = grid_verts[iy + 1][ix]
            f = bm.faces.new((v00, v10, v11, v01))
            f.material_index = m_mud

    # Gentle sculpted earth berms framing ONLY the visible North & South sidelines
    mud_berms = (
        (-13.5,  13.0, 14.0, 7.0, 1.25,  0.14),
        (  1.5,  13.8, 18.0, 6.8, 1.35, -0.05),
        ( 15.0,  12.8, 14.0, 7.0, 1.25, -0.16),
        (-11.0, -11.0, 15.0, 6.5, 0.90,  0.12),
        (  5.0, -11.5, 16.0, 6.5, 0.95, -0.10),
        ( -3.8,   5.4,  3.2, 2.1, 0.38,  0.22),
        (  2.0,   5.3,  2.8, 1.9, 0.34, -0.18),
        ( -2.8,  -5.6,  3.2, 2.0, 0.36, -0.20),
        (  3.2,  -5.4,  3.0, 2.0, 0.38,  0.16),
    )
    for mx, my, mw, md, mh, rz in mud_berms:
        add_box(bm, (mx, my, mh * 0.32), (mw, md, mh), rot=(0.0, 0.0, rz),
                bevel=0.35, taper_top=(0.56, 0.54), mat_idx=m_mud)

    # 4 sunken wooden duckboards along gate approach (Z <= 0.016 so unit soles never clip)
    duckboard_runs = (
        (-4.0,  2.72, 2.1,  0.04),
        (-1.2,  2.80, 2.0, -0.05),
        (-3.8, -2.76, 2.1, -0.04),
        (-1.0, -2.82, 2.0,  0.05),
    )
    for dx, dy, length, rz in duckboard_runs:
        add_box(bm, (dx, dy, 0.007), (length, 0.42, 0.014), rot=(0.015, -0.01, rz), mat_idx=m_wood)
        for sx in (-0.75, -0.25, 0.25, 0.75):
            add_box(bm, (dx + sx * (length / 2.2), dy, 0.012), (0.14, 0.48, 0.010),
                    rot=(-0.015, 0.015, rz + 0.03 * sx), mat_idx=m_wood)

    # 2 half-buried broken concrete road slabs along mud margins
    for sx, sy, sw, sd, sh, rz in (
        (-0.6,  3.95, 1.30, 0.90, 0.14,  0.32),
        ( 3.8, -4.05, 1.45, 0.86, 0.15, -0.38),
    ):
        add_box(bm, (sx, sy, 0.02), (sw, sd, sh), rot=(0.06, -0.08, rz), bevel=0.04, mat_idx=m_conc)

    obj, tris = finalize_mesh("Env_MuddyGround", bm, materials, collection=col)
    apply_box_uvs(obj, tex_scale=0.16)
    return obj, tris


def build_human_fortress_base(materials, idx_map, col):
    """Streamlined Apocalypse Scrap-Metal Fortress + Blast Gate + Watchtower (no hidden rear clutter)."""
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

    # 1. Angled Scrap-Metal Palisade Perimeter Wings (visible North & South flanks)
    wall_segments = (
        (-5.65,  2.55, 2.35, 3.15, -14.0),
        (-6.35,  4.45, 2.25, 3.25, -34.0),
        (-7.95,  5.55, 2.40, 3.00, -70.0),
        (-5.65, -2.55, 2.35, 3.15,  14.0),
        (-6.35, -4.45, 2.25, 3.25,  34.0),
        (-7.95, -5.55, 2.40, 3.00,  70.0),
    )
    for idx, (wx, wy, wlen, wh, rz_deg) in enumerate(wall_segments):
        rz = math.radians(rz_deg)
        add_box(bm, (wx, wy, wh * 0.5), (0.34, wlen, wh), rot=(0.0, 0.0, rz), bevel=0.03, mat_idx=m_steel)
        add_box(bm, (wx, wy, 0.22), (0.58, wlen * 0.96, 0.44), rot=(0.0, 0.0, rz), bevel=0.04, mat_idx=m_conc)
        for k in (-0.36, 0.36):
            rx = wx - math.sin(rz) * (wlen * k)
            ry = wy + math.cos(rz) * (wlen * k)
            add_box(bm, (rx + 0.14 * math.cos(rz), ry + 0.14 * math.sin(rz), wh * 0.52),
                    (0.18, 0.16, wh * 1.02), rot=(0.0, 0.0, rz), mat_idx=m_rust if idx % 2 else m_metal)
        add_box(bm, (wx + 0.19 * math.cos(rz), wy + 0.19 * math.sin(rz), wh * 0.46),
                (0.06, wlen * 0.55, 0.72), rot=(0.06, 0.0, rz), mat_idx=m_rust)
        if abs(wy) < 3.5:
            add_box(bm, (wx + 0.21 * math.cos(rz), wy + 0.21 * math.sin(rz), 1.55),
                    (0.05, wlen * 0.48, 0.24), rot=(0.0, 0.0, rz), mat_idx=m_haz)
        add_box(bm, (wx, wy, wh + 0.14), (0.48, wlen * 0.92, 0.28), rot=(0.0, 0.0, rz), bevel=0.05, mat_idx=m_bag)
        p_start = (wx + 0.22 * math.cos(rz) - math.sin(rz) * wlen * 0.45,
                   wy + 0.22 * math.sin(rz) + math.cos(rz) * wlen * 0.45, wh + 0.42)
        p_end = (wx + 0.22 * math.cos(rz) + math.sin(rz) * wlen * 0.45,
                 wy + 0.22 * math.sin(rz) - math.cos(rz) * wlen * 0.45, wh + 0.42)
        _add_barbed_coil(bm, p_start, p_end, radius=0.18, turns=4, mat_idx=m_wire)
        bx = wx - 0.85 * math.cos(rz)
        by = wy - 0.85 * math.sin(rz)
        add_cylinder(bm, (bx, by, 0.0), (wx - 0.15 * math.cos(rz), wy - 0.15 * math.sin(rz), wh * 0.72),
                     0.09, 0.08, segments=6, mat_idx=m_wood)

    # 2. Central Armored Steel Blast Gate Towers & Overhead Gantry (X = -5.35, Y = +/-1.48)
    for side in (-1.0, 1.0):
        gy = side * 1.48
        add_box(bm, (-5.38, gy, 1.65), (0.72, 0.68, 3.30), bevel=0.04, taper_top=(0.90, 0.90), mat_idx=m_conc)
        add_box(bm, (-5.34, gy, 1.55), (0.78, 0.56, 2.40), bevel=0.02, mat_idx=m_steel)
        add_box(bm, (-4.98, gy, 1.40), (0.08, 0.46, 0.34), mat_idx=m_haz)
        add_box(bm, (-5.38, gy, 3.44), (0.28, 0.28, 0.28), bevel=0.04, mat_idx=m_blue)
        for sb_k in range(3):
            add_box(bm, (-4.98, gy + side * 0.42 + (sb_k - 1) * 0.18, 0.22 + sb_k * 0.20),
                    (0.54, 0.42, 0.22), rot=(0.0, 0.0, side * 0.35), bevel=0.04, mat_idx=m_bag)

    add_box(bm, (-5.38, 0.0, 3.12), (0.78, 3.65, 0.52), bevel=0.04, mat_idx=m_steel)
    add_box(bm, (-5.00, 0.0, 3.12), (0.08, 2.60, 0.24), mat_idx=m_haz)
    _add_barbed_coil(bm, (-5.20, -1.75, 3.56), (-5.20, 1.75, 3.56), radius=0.20, turns=5, mat_idx=m_wire)
    for side in (-1.0, 1.0):
        add_box(bm, (-5.58, side * 1.24, 1.15), (0.78, 0.12, 2.25), rot=(0.0, 0.0, side * 0.38), bevel=0.02, mat_idx=m_rust)

    # 3. Elevated Guard Watchtower ("Menara Jaga") at X = -6.60, Y = +3.30
    wt_x, wt_y = -6.60, 3.30
    wt_r = 1.02
    wt_h = 3.45
    corners = ((-1, -1), (1, -1), (1, 1), (-1, 1))
    for cx, cy in corners:
        lx0, ly0 = wt_x + cx * (wt_r + 0.16), wt_y + cy * (wt_r + 0.16)
        lx1, ly1 = wt_x + cx * wt_r, wt_y + cy * wt_r
        add_cylinder(bm, (lx0, ly0, 0.0), (lx1, ly1, wt_h), 0.13, 0.10, segments=6, mat_idx=m_wood)
        add_cylinder(bm, (lx1, ly1, wt_h), (lx1, ly1, wt_h + 1.95), 0.08, 0.07, segments=6, mat_idx=m_wood)

    for c_i in range(4):
        c0 = corners[c_i]
        c1 = corners[(c_i + 1) % 4]
        p00 = (wt_x + c0[0] * (wt_r + 0.14), wt_y + c0[1] * (wt_r + 0.14), 0.35)
        p01 = (wt_x + c1[0] * (wt_r + 0.05), wt_y + c1[1] * (wt_r + 0.05), wt_h * 0.52)
        p10 = (wt_x + c1[0] * (wt_r + 0.14), wt_y + c1[1] * (wt_r + 0.14), 0.35)
        p11 = (wt_x + c0[0] * (wt_r + 0.05), wt_y + c0[1] * (wt_r + 0.05), wt_h * 0.52)
        add_cylinder(bm, p00, p01, 0.05, 0.05, segments=4, mat_idx=m_wood)
        add_cylinder(bm, p10, p11, 0.05, 0.05, segments=4, mat_idx=m_wood)

    add_box(bm, (wt_x, wt_y, wt_h), (2.48, 2.48, 0.20), bevel=0.03, mat_idx=m_wood)
    for wall_pos, wall_sz in (
        ((wt_x + 1.12, wt_y, wt_h + 0.45), (0.20, 2.35, 0.72)),
        ((wt_x - 1.12, wt_y, wt_h + 0.45), (0.20, 2.35, 0.72)),
        ((wt_x, wt_y - 1.12, wt_h + 0.45), (2.35, 0.20, 0.72)),
        ((wt_x, wt_y + 1.12, wt_h + 0.45), (2.35, 0.20, 0.72)),
    ):
        add_box(bm, wall_pos, wall_sz, bevel=0.02, mat_idx=m_steel)
    add_box(bm, (wt_x + 1.12, wt_y, wt_h + 0.90), (0.28, 2.10, 0.24), bevel=0.04, mat_idx=m_bag)

    add_box(bm, (wt_x, wt_y, wt_h + 2.02), (2.68, 2.68, 0.18), rot=(0.0, -0.14, 0.0), bevel=0.03, mat_idx=m_rust)
    for sy_off in (-0.58, 0.58):
        add_cylinder(bm, (wt_x + 1.05, wt_y + sy_off, wt_h + 1.65), (wt_x + 1.48, wt_y + sy_off - 0.10, wt_h + 1.50),
                     0.14, 0.20, segments=6, mat_idx=m_metal)
        add_box(bm, (wt_x + 1.48, wt_y + sy_off - 0.10, wt_h + 1.50), (0.05, 0.26, 0.26), mat_idx=m_fire)
    add_cylinder(bm, (wt_x - 0.35, wt_y, wt_h + 2.05), (wt_x - 0.35, wt_y, wt_h + 4.10), 0.055, 0.03, segments=6, mat_idx=m_metal)
    add_box(bm, (wt_x - 0.35, wt_y, wt_h + 4.18), (0.22, 0.22, 0.26), bevel=0.03, mat_idx=m_ember)

    # 4. 2 Front Anti-Tank Czech Hedgehogs flanking approach
    for hx, hy, sc, yaw in (
        (-4.35,  2.95, 0.86,  0.42),
        (-4.35, -2.95, 0.86, -0.48),
    ):
        _add_czech_hedgehog(bm, hx, hy, cz=0.0, scale=sc, yaw=yaw, mat_steel=m_steel, mat_rust=m_rust)

    obj, tris = finalize_mesh("Env_HumanFortress", bm, materials, collection=col)
    apply_box_uvs(obj, tex_scale=0.52)
    return obj, tris


def _build_war_ruin_piece(materials, idx_map, col, name, loc, rot_z_deg=0.0, height=7.0, variant=0):
    """Artillery-shelled abandoned building ruin visible behind combat corridor."""
    bm = bmesh.new()
    m_conc = idx_map["Mat_Env_ConcreteCracked"]
    m_dark = idx_map["Mat_Env_ConcreteDark"]
    m_brick = idx_map["Mat_Env_BrickRuined"]
    m_plaster = idx_map["Mat_Env_PlasterDamaged"]
    m_rust = idx_map["Mat_Env_RustHeavy"]
    m_glass = idx_map["Mat_Env_GlassBroken"]

    w, d = 5.4, 3.8
    add_box(bm, (0.0, 0.0, 0.22), (w + 0.55, d + 0.45, 0.44), bevel=0.08, mat_idx=m_dark)
    add_box(bm, (0.0, d * 0.42, height * 0.46), (w, 0.36, height * 0.92), bevel=0.04, mat_idx=m_brick if variant % 2 == 0 else m_conc)
    add_box(bm, (-w * 0.45, 0.0, height * 0.42), (0.38, d, height * 0.84), bevel=0.04, mat_idx=m_plaster)
    add_box(bm, ( w * 0.45, 0.0, height * 0.34), (0.38, d, height * 0.68), bevel=0.04, mat_idx=m_conc)

    col_heights = (height * 0.88, height * 0.74, height * 0.96, height * 0.62)
    col_xy = ((-w * 0.46, -d * 0.44), (w * 0.46, -d * 0.44), (-w * 0.46, d * 0.44), (w * 0.46, d * 0.44))
    for (cx, cy), ch in zip(col_xy, col_heights):
        add_box(bm, (cx, cy, ch * 0.5), (0.44, 0.44, ch), bevel=0.03, mat_idx=m_dark)
        for rk in range(2):
            add_cylinder(bm, (cx + (rk - 0.5) * 0.10, cy, ch - 0.05),
                         (cx + (rk - 0.5) * 0.18, cy + (0.10 if rk else -0.10), ch + 0.55),
                         0.022, 0.015, segments=4, mat_idx=m_rust)

    add_box(bm, (-0.35, 0.10, height * 0.46), (w * 0.86, d * 0.82, 0.26),
            rot=(0.24 if variant % 2 == 0 else -0.20, 0.16, 0.04), bevel=0.04, mat_idx=m_conc)
    add_box(bm, (-0.95, -d * 0.42, height * 0.72), (w * 0.54, 0.32, 0.52),
            rot=(0.05, -0.06, 0.0), bevel=0.03, mat_idx=m_dark)
    for wx in (-1.35, 0.0, 1.35):
        add_box(bm, (wx, d * 0.40, height * 0.34), (0.95, 0.22, 1.35), mat_idx=m_glass)
        add_box(bm, (wx, d * 0.38, height * 0.65), (0.95, 0.22, 1.15), mat_idx=m_glass)
    add_box(bm, (0.55, -d * 0.35, 0.42), (2.4, 1.35, 0.82), rot=(0.10, -0.12, 0.25), bevel=0.10, taper_top=(0.58, 0.55), mat_idx=m_brick)

    obj, _ = finalize_mesh(name, bm, materials, collection=col)
    obj.location = Vector(loc)
    obj.rotation_euler = Euler((0.0, 0.0, math.radians(rot_z_deg)), "XYZ")
    apply_box_uvs(obj, tex_scale=0.38)
    return obj


def _merge_objects_into_single_mesh(name, src_objs, materials, col):
    """Merge transformed piece objects into 1 draw-call mesh while preserving Box UVs & material indices."""
    bpy.context.view_layer.update()
    bm = bmesh.new()
    uv_dst = bm.loops.layers.uv.new("UVMap")

    for o in src_objs:
        me = o.data
        mat_xform = o.matrix_world.copy()
        bm_tmp = bmesh.new()
        bm_tmp.from_mesh(me)
        bmesh.ops.transform(bm_tmp, matrix=mat_xform, verts=bm_tmp.verts)
        uv_tmp = bm_tmp.loops.layers.uv.active
        v_map = {}
        for v in bm_tmp.verts:
            v_map[v.index] = bm.verts.new(v.co)
        for f in bm_tmp.faces:
            try:
                nf = bm.faces.new([v_map[v.index] for v in f.verts])
                nf.material_index = f.material_index
                if uv_tmp is not None:
                    for ls, ld in zip(f.loops, nf.loops):
                        ld[uv_dst].uv = ls[uv_tmp].uv
            except ValueError:
                pass
        bm_tmp.free()

    for o in src_objs:
        me = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        bpy.data.meshes.remove(me)

    return finalize_mesh(name, bm, materials, collection=col)


def _hemisphere_samples(count=24):
    """Deterministic golden-spiral cosine-biased unit sample vectors over +Z hemisphere."""
    samples = []
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(count):
        t = (i + 0.5) / count
        z = 0.14 + 0.84 * t
        r = math.sqrt(max(0.0, 1.0 - z * z))
        phi = golden_angle * i
        samples.append(Vector((r * math.cos(phi), r * math.sin(phi), z)).normalized())
    return samples


def _bake_scene_vertex_ao(objs):
    """Bake real BVH raycast contact AO, crevices & mud/soot grounding into 'Col' vertex colors."""
    bpy.context.view_layer.update()
    bm_all = bmesh.new()
    for obj in objs:
        bm_tmp = bmesh.new()
        bm_tmp.from_mesh(obj.data)
        bmesh.ops.transform(bm_tmp, matrix=obj.matrix_world, verts=bm_tmp.verts)
        v_map = {v.index: bm_all.verts.new(v.co) for v in bm_tmp.verts}
        for f in bm_tmp.faces:
            try:
                bm_all.faces.new([v_map[v.index] for v in f.verts])
            except ValueError:
                pass
        bm_tmp.free()

    bmesh.ops.recalc_face_normals(bm_all, faces=list(bm_all.faces))
    bvh = BVHTree.FromBMesh(bm_all)
    bm_all.free()

    samples = _hemisphere_samples(24)
    max_dist = 2.6

    for obj in objs:
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.normal_update()

        mat_names = [
            (slot.material.name if slot.material else "")
            for slot in obj.material_slots
        ]
        is_ground = obj.name == "Env_MuddyGround"
        cache = {}
        loop_colors = [None] * len(mesh.loops)
        m_world = obj.matrix_world

        for f in bm.faces:
            mname = mat_names[f.material_index] if f.material_index < len(mat_names) else ""
            skip_ao = any(k in mname for k in ("Glow", "Fire", "Ember", "Beacon", "Glass"))
            fn = f.normal
            if fn.length < 1e-6:
                fn = Vector((0.0, 0.0, 1.0))
            else:
                fn = fn.normalized()
            f_center = m_world @ f.calc_center_median()

            # Orthonormal basis around face normal
            ref = Vector((0.0, 0.0, 1.0)) if abs(fn.z) < 0.85 else Vector((0.0, 1.0, 0.0))
            t1 = fn.cross(ref).normalized()
            t2 = fn.cross(t1).normalized()

            for loop in f.loops:
                if skip_ao:
                    loop_colors[loop.index] = (1.0, 1.0, 1.0, 1.0)
                    continue

                v_w = m_world @ loop.vert.co
                key = (
                    loop.vert.index,
                    int(round(fn.x * 4)),
                    int(round(fn.y * 4)),
                    int(round(fn.z * 4)),
                )
                cached = cache.get(key)
                if cached is None:
                    to_ctr = (f_center - v_w)
                    if to_ctr.length > 1e-5:
                        to_ctr.normalize()
                    origin = v_w + fn * 0.032 + to_ctr * 0.025
                    occ = 0.0
                    for s in samples:
                        r_dir = (t1 * s.x + t2 * s.y + fn * s.z).normalized()
                        hit_loc, _, _, hit_dist = bvh.ray_cast(origin, r_dir, max_dist)
                        if hit_loc is not None and hit_dist > 0.015:
                            occ += (1.0 - hit_dist / max_dist) ** 1.15
                    occ_frac = occ / len(samples)
                    ao = max(0.42, min(1.0, 1.0 - 0.58 * min(1.0, occ_frac * 1.65)))
                    r = g = b = ao

                    if is_ground:
                        # Subtle darker churned mud combat corridor + smooth dusk edge vignette
                        if -6.0 <= v_w.x <= 10.0 and abs(v_w.y) <= 2.5:
                            lane_t = 1.0 - abs(v_w.y) / 2.5
                            r *= 1.0 - 0.12 * lane_t
                            g *= 1.0 - 0.14 * lane_t
                            b *= 1.0 - 0.16 * lane_t
                        rad = math.hypot(v_w.x - 1.0, v_w.y)
                        if rad > 15.0:
                            vig = min(1.0, (rad - 15.0) / 16.0)
                            r *= 1.0 - 0.34 * vig
                            g *= 1.0 - 0.36 * vig
                            b *= 1.0 - 0.38 * vig
                    else:
                        # Root vertical structures into brown mud/soot near ground Z = 0..0.78m
                        if 0.0 <= v_w.z < 0.78:
                            gf = ((1.0 - v_w.z / 0.78) ** 1.5) * 0.38
                            r = r * (1.0 - gf) + 0.56 * gf
                            g = g * (1.0 - gf) + 0.48 * gf
                            b = b * (1.0 - gf) + 0.42 * gf
                        # Subtle cool shade on downward/shaded faces
                        if fn.z < -0.1:
                            b = min(1.0, b * 1.06)

                    cached = (max(0.0, min(1.0, r)), max(0.0, min(1.0, g)), max(0.0, min(1.0, b)), 1.0)
                    cache[key] = cached
                loop_colors[loop.index] = cached

        bm.free()
        col_attr = mesh.color_attributes.get("Col")
        if col_attr is None:
            col_attr = mesh.color_attributes.new(name="Col", type="BYTE_COLOR", domain="CORNER")
        col_data = col_attr.data
        for idx, c in enumerate(loop_colors):
            col_data[idx].color = c


def _prune_unused_materials(objs):
    """Strip unused material slots from meshes & remove unreferenced materials/images before export."""
    for obj in objs:
        mesh = obj.data
        used_idx = sorted({p.material_index for p in mesh.polygons})
        old_mats = [slot.material for slot in obj.material_slots]
        remap = {}
        kept_mats = []
        for old_i in used_idx:
            if 0 <= old_i < len(old_mats) and old_mats[old_i] is not None:
                remap[old_i] = len(kept_mats)
                kept_mats.append(old_mats[old_i])
        new_indices = [remap.get(p.material_index, 0) for p in mesh.polygons]
        mesh.materials.clear()
        for m in kept_mats:
            mesh.materials.append(m)
        mesh.polygons.foreach_set("material_index", new_indices)
        mesh.update()

    # Remove unreferenced materials and images so GLB packs ONLY active textures
    for mat in list(bpy.data.materials):
        if mat.users == 0:
            bpy.data.materials.remove(mat)
    for img in list(bpy.data.images):
        if img.users == 0:
            bpy.data.images.remove(img)


def build_war_battlefield_scene(materials, idx_map, collection=None):
    """Assemble lightweight, matte 4-mesh War-Torn Human Fortress Battlefield Diorama."""
    col = collection if collection is not None else bpy.context.scene.collection

    # 1. Ground mesh
    ground_obj, _ = build_muddy_battlefield_terrain(materials, idx_map, col)

    # 2. Human Fortress mesh
    fortress_obj, _ = build_human_fortress_base(materials, idx_map, col)

    # 3. Only 2 visible bombed ruins behind combat corridor -> merged into Env_VisibleRuins
    ruin_pieces = [
        _build_war_ruin_piece(materials, idx_map, col, "Tmp_Ruin_WC", (-1.8, 7.8, 0.0), rot_z_deg=-4.0, height=6.8, variant=1),
        _build_war_ruin_piece(materials, idx_map, col, "Tmp_Ruin_EC", ( 4.6, 8.2, 0.0), rot_z_deg= 5.0, height=7.3, variant=2),
    ]
    ruins_obj, _ = _merge_objects_into_single_mesh("Env_VisibleRuins", ruin_pieces, materials, col)

    # 4. Only visible midground war props -> merged into Env_WarProps
    prop_specs = (
        (build_env_wrecked_car,        "Tmp_WreckedCar_N",   (-1.1,  4.2, 0.0), -18.0, 1.0),
        (build_env_police_cruiser,     "Tmp_PoliceCruiser",  ( 3.3,  4.3, 0.0), 160.0, 1.0),
        (build_env_fire_barrel,        "Tmp_FireBarrel_N",   (-4.65, 2.35, 0.0), 15.0, 1.0),
        (build_env_fire_barrel,        "Tmp_FireBarrel_S",   (-4.65,-2.35, 0.0),-25.0, 1.0),
        (build_env_sandbag_barricade,  "Tmp_MidSandbag_N",   (-0.3,  3.4, 0.0), -10.0, 1.0),
        (build_env_jersey_barrier,     "Tmp_Barrier_SW",     (-2.3, -3.7, 0.0),  10.0, 1.0),
        (build_env_jersey_barrier,     "Tmp_Barrier_SE",     ( 2.8, -3.8, 0.0), -14.0, 1.0),
        (build_env_rubble_crater,      "Tmp_Crater_N",       (-2.1,  5.1, 0.0),  20.0, 0.90),
        (build_env_rubble_crater,      "Tmp_Crater_S",       ( 2.5, -4.9, 0.0), -25.0, 0.88),
        (build_env_street_lamp_broken, "Tmp_Lamp_E",         ( 5.4,  3.9, 0.0), 170.0, 1.0),
        (build_env_dead_tree,          "Tmp_DeadTree_C",     ( 1.2,  6.3, 0.0), 105.0, 0.92),
        (build_env_grass_clump_tall,   "Tmp_DeadGrass_0",    (-3.2,  3.6, 0.0),  40.0, 0.95),
        (build_env_grass_clump_tall,   "Tmp_DeadGrass_1",    ( 1.0,  3.7, 0.0), 145.0, 0.95),
        (build_env_grass_clump_tall,   "Tmp_DeadGrass_2",    ( 4.4,  3.5, 0.0), 210.0, 0.95),
    )
    prop_pieces = []
    for fn, pname, ploc, prz, psc in prop_specs:
        pobj, _ = _place_piece(fn, materials, idx_map, col, pname, loc=ploc, rot_z_deg=prz, scale=psc)
        prop_pieces.append(pobj)
    props_obj, _ = _merge_objects_into_single_mesh("Env_WarProps", prop_pieces, materials, col)

    placed = [ground_obj, fortress_obj, ruins_obj, props_obj]
    _bake_scene_vertex_ao(placed)
    _prune_unused_materials(placed)

    total_tris = sum(sum(1 for _ in o.data.polygons) for o in placed)
    return placed, total_tris


def render_war_qa_sheet(out_path):
    tmp_dir = os.path.join(PROJECT_DIR, "renders", "_tmp_war_qa")
    os.makedirs(tmp_dir, exist_ok=True)
    clear_scene()
    scene = bpy.context.scene
    configure_renderer(scene)
    materials, idx_map = create_materials(with_env_textures=True, env_vertex_ao=True)
    build_war_battlefield_scene(materials, idx_map)

    _add_dusk_lights(center=(0.0, 1.5, 1.6), scale=2.8, bg_rgb=(0.08, 0.10, 0.14), atmospheric_sky=True)
    _add_bounded_atmosphere_haze(scene)

    for lname, lx, ly in (("FireGateN", -4.65, 2.35), ("FireGateS", -4.65, -2.35)):
        pl_data = bpy.data.lights.new(name=lname, type="POINT")
        pl_data.energy = 380.0
        pl_data.color = (1.0, 0.48, 0.14)
        pl_data.shadow_soft_size = 0.30
        pl = bpy.data.objects.new(name=lname, object_data=pl_data)
        pl.location = (lx, ly, 1.45)
        scene.collection.objects.link(pl)

    cam_data = bpy.data.cameras.new("WarQACam")
    cam_data.type = "PERSP"
    cam_data.lens = 26.0
    cam_data.clip_start = 0.1
    cam_data.clip_end = 220.0
    cam = bpy.data.objects.new("WarQACam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    views = [
        ("wide",          (-1.0, -15.5, 6.4), (-0.4, 1.0, 1.4), 1400, 620),
        ("fortress",      (-2.2,  -9.8, 4.0), (-5.2, 1.2, 1.9), 1400, 620),
        ("over_fortress", (-11.2, -7.2, 7.2), ( 1.6, 0.5, 1.0), 1400, 620),
    ]
    panels = []
    for tag, loc, tgt, w, h in views:
        aim_camera(cam, loc, tgt)
        p = os.path.join(tmp_dir, f"war_{tag}.png")
        render_image(scene, p, w, h)
        panels.append(load_rgba_np(p))

    gap = 6
    h0, w0, _ = panels[0].shape
    out_arr = np.zeros((h0 * 3 + gap * 2, w0, 4), dtype=np.float32)
    out_arr[:, :, :3] = 0.05
    out_arr[:, :, 3] = 1.0
    out_arr[:h0, :, :] = panels[0]
    out_arr[h0 + gap:h0 * 2 + gap, :, :] = panels[1]
    out_arr[(h0 + gap) * 2:, :, :] = panels[2]
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
    print("BUILDING LIGHTWEIGHT MATTE HUMAN FORTRESS BATTLEFIELD (NO ZOMBIE BASE)")
    clear_scene()
    col = make_collection("WarBattlefield")
    materials, idx_map = create_materials(with_env_textures=True, env_vertex_ao=True)
    objs, total_tris = build_war_battlefield_scene(materials, idx_map, collection=col)
    _assert_pure_tris(objs)

    mins, maxs = world_bounds(objs)
    blend_path = os.path.join(env_dir, "battlefield_fortress_war.blend")
    glb_path = os.path.join(env_dir, "battlefield_fortress_war.glb")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    export_glb(glb_path, selected_only=False, export_animations=False)
    info = _inspect_glb(glb_path)
    print(
        f"  WAR BATTLEFIELD : {len(objs)} meshes ({info['mesh_names']}) | {total_tris} tris | "
        f"span {maxs[0]-mins[0]:.1f}x{maxs[1]-mins[1]:.1f}x{maxs[2]-mins[2]:.1f}m | "
        f"mats={info['materials']} | imgs={info['images']} | color0={info['has_color0']} | "
        f"{info['bytes'] / (1024*1024):.2f} MB"
    )
    if len(objs) != 4:
        raise RuntimeError(f"Expected 4 meshes, got {len(objs)}")
    if total_tris > 14000:
        raise RuntimeError(f"Expected <= 14000 tris, got {total_tris}")
    if info["bytes"] >= 4.0 * 1024 * 1024:
        raise RuntimeError(f"Expected GLB < 4.0 MB, got {info['bytes'] / (1024*1024):.2f} MB")
    if info["images"] < 10:
        raise RuntimeError(f"Expected >= 10 PBR images, got {info['images']}")
    if not info["has_color0"]:
        raise RuntimeError("Missing baked COLOR_0 vertex AO attribute in exported GLB")

    render_war_qa_sheet(os.path.join(PROJECT_DIR, "renders", "battlefield_fortress_war_qa.png"))
    print("=" * 74)
    print("WAR BATTLEFIELD BUILD COMPLETE")


if __name__ == "__main__":
    main()
