"""Modular Zombie Apocalypse Environment Kit (14 pure-tri low-poly assets + assembled Battleground Diorama).

All modular builders ground cleanly at Z = 0.0 in Blender meters (1 BU = 1m):
  - Cracked Ground & Road : env_ground_cracked_earth, env_road_cracked_asphalt, env_rubble_crater
  - Ruined Buildings/Walls: env_building_ruined_corner, env_building_ruined_store, env_wall_ruined_brick
  - Overgrown Foliage     : env_grass_clump_tall, env_overgrown_bush, env_dead_tree
  - Street Props & Cover  : env_wrecked_car, env_jersey_barrier, env_sandbag_barricade,
                            env_street_lamp_broken, env_fire_barrel
"""
import math
import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

from mesh_utils import (
    add_box,
    add_cone,
    add_cylinder,
    apply_box_uvs,
    finalize_mesh,
    loft_rings,
    ring_ellipse,
)


def _add_grass_blade(bm, x, y, z, height=0.36, width=0.045, yaw=0.0, lean=0.14, mat_idx=0):
    """Build a crisp 2-segment tapered low-poly grass blade rising from (x, y, z)."""
    ca, sa = math.cos(yaw), math.sin(yaw)
    hw = width * 0.5
    mw = width * 0.30
    pts0 = (
        Vector((x - sa * hw, y + ca * hw, z)),
        Vector((x + sa * hw, y - ca * hw, z)),
    )
    mid_off = lean * 0.35
    pts1 = (
        Vector((x + ca * mid_off - sa * mw, y + sa * mid_off + ca * mw, z + height * 0.55)),
        Vector((x + ca * mid_off + sa * mw, y + sa * mid_off - ca * mw, z + height * 0.55)),
    )
    tip = Vector((x + ca * lean, y + sa * lean, z + height))

    v0a = bm.verts.new(pts0[0])
    v0b = bm.verts.new(pts0[1])
    v1a = bm.verts.new(pts1[0])
    v1b = bm.verts.new(pts1[1])
    vt = bm.verts.new(tip)
    for tri in ((v0a, v0b, v1b), (v0a, v1b, v1a), (v1a, v1b, vt)):
        try:
            f = bm.faces.new(tri)
            f.material_index = mat_idx
        except ValueError:
            pass


def _add_grass_patch(bm, cx, cy, cz, count=10, spread=0.28, h_min=0.16, h_max=0.42,
                     idx_dry=0, idx_lush=0, seed=1):
    """Scatter low-poly grass blades radially around (cx, cy, cz)."""
    for i in range(count):
        h1 = ((i * 73 + seed * 37) % 97) / 97.0
        h2 = ((i * 41 + seed * 19) % 89) / 89.0
        h3 = ((i * 29 + seed * 53) % 79) / 79.0
        ang = 2.0 * math.pi * ((i / max(1, count)) + 0.17 * h1)
        r = spread * (0.18 + 0.82 * h2)
        gx = cx + math.cos(ang) * r
        gy = cy + math.sin(ang) * r
        gh = h_min + (h_max - h_min) * h3
        gw = 0.032 + 0.025 * h1
        mat_i = idx_dry if (i % 3 == 0) else idx_lush
        _add_grass_blade(bm, gx, gy, cz, height=gh, width=gw, yaw=ang, lean=gh * 0.34, mat_idx=mat_i)


def _add_stone_chunk(bm, center, radius, sx=1.0, sy=0.82, sz=0.58, yaw=0.0, tilt=0.15, mat_idx=0):
    """Create a jagged faceted rubble/stone chunk around `center`."""
    add_box(
        bm,
        center=center,
        size=(radius * 2.0 * sx, radius * 2.0 * sy, radius * 1.4 * sz),
        rot=(tilt, tilt * 0.6, yaw),
        bevel=radius * 0.22,
        taper_top=(0.74, 0.70),
        mat_idx=mat_idx,
    )


def _add_broken_glass_window(bm, center, width, height, depth=0.08, along_x=True,
                             materials_map=None, frame_mat=0, glass_mat=0, board_mat=0,
                             boarded=True, seed=1):
    """Recessed ruined window opening with frame, jagged glass shards, and optional diagonal boards."""
    cx, cy, cz = center
    rot_z = 0.0 if along_x else math.pi * 0.5
    # Window sill & lintel
    add_box(bm, (cx, cy, cz - height * 0.5 - 0.04), (width + 0.16, depth + 0.10, 0.08),
            rot=(0.0, 0.0, rot_z), mat_idx=frame_mat)
    add_box(bm, (cx, cy, cz + height * 0.5 + 0.04), (width + 0.16, depth + 0.10, 0.08),
            rot=(0.0, 0.0, rot_z), mat_idx=frame_mat)
    # Dark interior backing recess
    add_box(bm, (cx, cy, cz), (width * 0.94, depth * 0.35, height * 0.94),
            rot=(0.0, 0.0, rot_z), mat_idx=frame_mat)

    # Jagged broken glass shards sticking out from bottom/top/sides
    shard_offsets = (-0.34, -0.10, 0.18, 0.36)
    for k, frac in enumerate(shard_offsets):
        sh = height * (0.22 + 0.14 * ((k + seed) % 3))
        dx = frac * width if along_x else 0.0
        dy = 0.0 if along_x else frac * width
        sz_off = -height * 0.5 + sh * 0.5 if k % 2 == 0 else height * 0.5 - sh * 0.45
        add_box(
            bm,
            (cx + dx, cy + dy, cz + sz_off),
            (width * 0.16, 0.018, sh),
            rot=(0.0, 0.12 * (1 if k % 2 == 0 else -1), rot_z),
            taper_top=(0.25, 0.8),
            mat_idx=glass_mat,
        )

    if boarded:
        n_boards = 2 if width < 1.2 else 3
        for b in range(n_boards):
            bz = cz + (-0.28 + 0.28 * b) * height
            tilt_y = 0.12 * (1 if (b + seed) % 2 == 0 else -1)
            px = width * 1.12
            if along_x:
                add_box(bm, (cx, cy - depth * 0.55, bz), (px, 0.045, 0.14),
                        rot=(0.0, tilt_y, 0.0), mat_idx=board_mat)
            else:
                add_box(bm, (cx - depth * 0.55, cy, bz), (px, 0.045, 0.14),
                        rot=(0.0, tilt_y, math.pi * 0.5), mat_idx=board_mat)


# ---------------------------------------------------------------------------
# 1. CRACKED GROUND & RUINED ROAD (3 Tiles)
# ---------------------------------------------------------------------------
def build_env_ground_cracked_earth(materials, idx_map, collection=None, name="Env_Ground_CrackedEarth"):
    """4.0m x 4.0m parched cracked-earth tile with tilted 3D soil plates, fissure gaps, stones & weeds."""
    bm = bmesh.new()
    m_soil = idx_map["Mat_Env_SoilCracked"]
    m_dark = idx_map["Mat_Env_ConcreteDark"]
    m_dry = idx_map["Mat_Env_GrassDry"]
    m_lush = idx_map["Mat_Env_GrassLush"]

    # Subsurface dark trench floor so gaps between cracked plates show deep 3D fissures
    add_box(bm, (0.0, 0.0, -0.055), (4.0, 4.0, 0.09), mat_idx=m_dark)

    # 4x4 grid of irregular cracked earth plates with physical crack gaps & slight tilt
    step = 0.98
    for ix in range(4):
        for iy in range(4):
            cx = -1.47 + ix * step
            cy = -1.47 + iy * step
            h_seed = ((ix * 13 + iy * 29) % 17) / 17.0
            rx = 0.90 - 0.06 * ((ix + iy) % 2)
            ry = 0.90 - 0.06 * ((ix * 2 + iy) % 2)
            pz = -0.004 + 0.008 * h_seed
            tx = (h_seed - 0.5) * 0.055
            ty = (((ix * 7 + iy * 11) % 13) / 13.0 - 0.5) * 0.055
            add_box(
                bm,
                (cx, cy, pz),
                (rx, ry, 0.042),
                rot=(tx, ty, 0.03 * (h_seed - 0.5)),
                bevel=0.014,
                taper_top=(0.94, 0.94),
                mat_idx=m_soil,
            )

    # Scattered cracked rocks + dry weeds emerging out of fissures
    stones = [(-1.05, 0.52, 0.11), (0.48, -1.02, 0.13), (1.12, 0.98, 0.09), (-0.48, -0.50, 0.08)]
    for k, (sx, sy, sr) in enumerate(stones):
        _add_stone_chunk(bm, (sx, sy, sr * 0.42), sr, yaw=k * 0.8, mat_idx=m_dark)

    crack_weeds = [(-0.98, -0.02), (0.02, 0.98), (0.98, -0.96), (-0.02, -0.98), (0.96, 0.02)]
    for k, (wx, wy) in enumerate(crack_weeds):
        _add_grass_patch(bm, wx, wy, -0.01, count=6, spread=0.18, h_min=0.14, h_max=0.34,
                         idx_dry=m_dry, idx_lush=m_lush, seed=k + 3)

    obj, tris = finalize_mesh(name, bm, materials, collection=collection)
    apply_box_uvs(obj, tex_scale=0.45)
    return obj, tris


def build_env_road_cracked_asphalt(materials, idx_map, collection=None, name="Env_Road_CrackedAsphalt"):
    """6.0m x 6.0m ruined city avenue: cracked asphalt slabs, potholes, broken yellow line, curbs & drain."""
    bm = bmesh.new()
    m_asph = idx_map["Mat_Env_AsphaltCracked"]
    m_soil = idx_map["Mat_Env_SoilCracked"]
    m_conc = idx_map["Mat_Env_ConcreteCracked"]
    m_dark = idx_map["Mat_Env_ConcreteDark"]
    m_line = idx_map["Mat_Env_RoadStripe"]
    m_metal = idx_map["Mat_Env_MetalScrap"]
    m_dry = idx_map["Mat_Env_GrassDry"]
    m_lush = idx_map["Mat_Env_GrassLush"]

    # Sub-road cracked earth bed (shows inside potholes & slab seams)
    add_box(bm, (0.0, 0.0, -0.045), (6.0, 6.0, 0.07), mat_idx=m_soil)

    # Central walkable asphalt avenue (X in [-3, 3], Y in [-2.35, 2.35]), flush at Z=0.0 with pothole depressions
    add_box(bm, (0.0, 0.0, -0.016), (6.0, 4.72, 0.032), mat_idx=m_asph)

    # Recessed 3D pothole earth patches & broken asphalt rim lips (kept away from central combat lane Y=0)
    for px, py, sx, sy in ((-0.85, -1.55, 0.95, 0.62), (1.05, 1.52, 1.05, 0.68)):
        add_box(bm, (px, py, 0.002), (sx, sy, 0.010), bevel=0.02, mat_idx=m_soil)
        _add_stone_chunk(bm, (px - sx * 0.35, py + 0.12, 0.024), 0.10, yaw=px, mat_idx=m_dark)
        _add_stone_chunk(bm, (px + sx * 0.28, py - 0.10, 0.022), 0.08, yaw=py, mat_idx=m_conc)

    # Faded yellow dashed center road stripes
    for sx in (-2.05, 0.05, 2.10):
        add_box(bm, (sx, 0.02, 0.004), (1.15, 0.12, 0.008),
                rot=(0.0, 0.0, 0.015 * sx), mat_idx=m_line)

    # Raised cracked concrete curbs & segmented sidewalks along +Y and -Y edges
    for side in (-1.0, 1.0):
        for kx in (-2.25, -0.75, 0.75, 2.25):
            drop = 0.012 if (kx == 0.75 and side > 0) else 0.0
            add_box(
                bm,
                (kx, side * 2.66, 0.040 - drop),
                (1.45, 0.64, 0.10),
                rot=(side * 0.015, 0.01 * kx, 0.0),
                bevel=0.012,
                mat_idx=m_conc,
            )
        # Weeds sprouting from the asphalt-curb expansion seam
        _add_grass_patch(bm, -1.50, side * 2.32, 0.005, count=7, spread=0.22,
                         h_min=0.14, h_max=0.36, idx_dry=m_dry, idx_lush=m_lush, seed=int(side + 5))
        _add_grass_patch(bm, 1.48, side * 2.34, 0.005, count=6, spread=0.20,
                         h_min=0.14, h_max=0.32, idx_dry=m_dry, idx_lush=m_lush, seed=int(side + 11))

    # Storm drain grate recessed at front-right curb
    add_box(bm, (-0.75, -2.26, 0.012), (0.68, 0.36, 0.025), mat_idx=m_dark)
    for gx in (-0.98, -0.84, -0.70, -0.56):
        add_box(bm, (gx, -2.26, 0.024), (0.045, 0.28, 0.012), mat_idx=m_metal)

    obj, tris = finalize_mesh(name, bm, materials, collection=collection)
    apply_box_uvs(obj, tex_scale=0.36)
    return obj, tris


def build_env_rubble_crater(materials, idx_map, collection=None, name="Env_Rubble_Crater"):
    """3.2m x 3.2m impact rubble mound: cracked earth rim, shattered concrete slabs, bricks, bent rebar & weeds."""
    bm = bmesh.new()
    m_soil = idx_map["Mat_Env_SoilCracked"]
    m_conc = idx_map["Mat_Env_ConcreteCracked"]
    m_dark = idx_map["Mat_Env_ConcreteDark"]
    m_brick = idx_map["Mat_Env_BrickRuined"]
    m_rust = idx_map["Mat_Env_RustHeavy"]
    m_dry = idx_map["Mat_Env_GrassDry"]
    m_lush = idx_map["Mat_Env_GrassLush"]

    # Base dirt berm & crater ring chunks
    add_box(bm, (0.0, 0.0, 0.03), (2.9, 2.7, 0.08), bevel=0.12, taper_top=(0.82, 0.82), mat_idx=m_soil)
    for k in range(8):
        ang = (2.0 * math.pi * k) / 8.0
        r = 0.85 + 0.18 * (k % 2)
        _add_stone_chunk(
            bm,
            (math.cos(ang) * r, math.sin(ang) * r, 0.14 + 0.04 * (k % 3)),
            radius=0.34 + 0.06 * (k % 2),
            sx=1.35, sy=0.95, sz=0.48,
            yaw=ang + 0.5, tilt=0.22 * (1 if k % 2 == 0 else -1),
            mat_idx=m_conc if k % 2 == 0 else m_dark,
        )

    # Stacked central concrete slab shards & scattered red bricks
    add_box(bm, (-0.18, 0.12, 0.28), (1.10, 0.72, 0.18), rot=(0.24, -0.32, 0.45), bevel=0.02, mat_idx=m_conc)
    add_box(bm, (0.28, -0.18, 0.24), (0.88, 0.60, 0.15), rot=(-0.20, 0.36, -0.30), bevel=0.02, mat_idx=m_dark)
    for bi, (bx, by, bz, byaw) in enumerate((
        (-0.55, -0.38, 0.14, 0.3), (0.58, 0.42, 0.12, -0.6), (-0.10, -0.62, 0.10, 1.1),
        (0.15, 0.55, 0.16, 0.7), (-0.72, 0.22, 0.10, -0.9),
    )):
        add_box(bm, (bx, by, bz), (0.24, 0.12, 0.08), rot=(0.1, 0.2 * (bi % 2), byaw), mat_idx=m_brick)

    # Protruding bent iron rebar rods from broken slabs
    for p0, p1 in (
        ((-0.25, 0.15, 0.28), (-0.52, 0.36, 0.72)),
        ((0.20, -0.10, 0.24), (0.48, -0.35, 0.64)),
        ((0.05, 0.25, 0.28), (0.24, 0.58, 0.58)),
    ):
        add_cylinder(bm, p0, p1, 0.015, 0.013, segments=5, mat_idx=m_rust)

    _add_grass_patch(bm, -0.92, -0.82, 0.06, count=8, spread=0.28, idx_dry=m_dry, idx_lush=m_lush, seed=21)
    _add_grass_patch(bm, 0.88, 0.75, 0.06, count=7, spread=0.25, idx_dry=m_dry, idx_lush=m_lush, seed=25)

    obj, tris = finalize_mesh(name, bm, materials, collection=collection)
    apply_box_uvs(obj, tex_scale=0.65)
    return obj, tris


# ---------------------------------------------------------------------------
# 2. RUINED BUILDINGS & BROKEN WALLS (3 Structures)
# ---------------------------------------------------------------------------
def build_env_building_ruined_corner(materials, idx_map, collection=None, name="Env_Building_RuinedCorner"):
    """5.2m x 4.8m x 6.4m 2-story ruined brick/concrete building with blown upper corner, rebar, boarded windows & vines."""
    bm = bmesh.new()
    m_brick = idx_map["Mat_Env_BrickRuined"]
    m_conc = idx_map["Mat_Env_ConcreteCracked"]
    m_dark = idx_map["Mat_Env_ConcreteDark"]
    m_wood = idx_map["Mat_Env_WoodPlank"]
    m_glass = idx_map["Mat_Env_GlassBroken"]
    m_rust = idx_map["Mat_Env_RustHeavy"]
    m_lush = idx_map["Mat_Env_GrassLush"]
    m_dry = idx_map["Mat_Env_GrassDry"]

    # Ground plinth foundation (Z=0..0.24) + interior dark floor slab
    add_box(bm, (0.0, 0.0, 0.12), (5.20, 4.80, 0.24), bevel=0.015, mat_idx=m_dark)

    # Corner structural concrete pillars
    for px, py, ph in (
        (-2.35, -2.15, 6.15), (2.35, -2.15, 3.85),
        (-2.35,  2.15, 6.15), (2.35,  2.15, 5.20),
    ):
        add_box(bm, (px, py, ph * 0.5), (0.42, 0.42, ph), bevel=0.012, mat_idx=m_conc)

    # First-floor ruined brick walls (Z=0.24..3.15)
    # Front wall (-Y): left solid pier, central doorway gap (Z=0.24..2.35), right window wall
    add_box(bm, (-1.40, -2.15, 1.70), (1.72, 0.28, 2.92), mat_idx=m_brick)
    add_box(bm, ( 0.00, -2.15, 2.75), (1.20, 0.28, 0.82), mat_idx=m_brick)  # header above doorway
    add_box(bm, ( 1.40, -2.15, 0.72), (1.72, 0.28, 0.96), mat_idx=m_brick)  # below right window
    add_box(bm, ( 1.40, -2.15, 2.78), (1.72, 0.28, 0.74), mat_idx=m_brick)  # above right window
    add_box(bm, ( 0.72, -2.15, 1.78), (0.36, 0.28, 1.26), mat_idx=m_brick)
    add_box(bm, ( 2.08, -2.15, 1.78), (0.36, 0.28, 1.26), mat_idx=m_brick)

    # Left (-X) & Back (+Y) lower & second floor masonry walls
    add_box(bm, (-2.35, 0.0, 3.15), (0.28, 4.10, 5.82), mat_idx=m_brick)
    add_box(bm, ( 0.00, 2.15, 2.85), (4.45, 0.28, 5.22), mat_idx=m_brick)
    # Right (+X) lower wall + partial jagged collapsed upper wall
    add_box(bm, ( 2.35, 0.0, 1.70), (0.28, 4.10, 2.92), mat_idx=m_brick)
    add_box(bm, ( 2.35, 1.10, 4.05), (0.28, 1.95, 1.85), mat_idx=m_brick)

    # Second floor concrete belt course & broken floor slab at Z=3.15 (with collapsed front-right bay)
    add_box(bm, (0.0, 0.0, 3.16), (4.96, 4.56, 0.20), mat_idx=m_dark)
    add_box(bm, (-1.10, 0.40, 3.22), (2.75, 3.70, 0.16), mat_idx=m_conc)

    # Upper story (-Y front wall left half standing up to Z=6.15, jagged collapse on right half)
    add_box(bm, (-1.20, -2.15, 3.62), (2.10, 0.28, 0.76), mat_idx=m_brick)
    add_box(bm, (-1.20, -2.15, 5.65), (2.10, 0.28, 0.92), mat_idx=m_brick)
    add_box(bm, (-2.00, -2.15, 4.62), (0.50, 0.28, 1.24), mat_idx=m_brick)
    add_box(bm, (-0.42, -2.15, 4.62), (0.52, 0.28, 1.24), mat_idx=m_brick)
    # Stepped ruined brick teeth at collapsed corner edge
    for kx, ky, kh in ((-0.05, -2.15, 4.15), (0.45, -2.15, 3.75), (2.35, -0.25, 3.60), (0.95, 2.15, 5.50)):
        add_box(bm, (kx, ky, kh * 0.5 + 1.55), (0.44, 0.30, kh - 3.0), rot=(0.0, 0.05, 0.0), mat_idx=m_brick)

    # Partial collapsed concrete roof overhang + bent rebar embedded cleanly in broken slab edges
    add_box(bm, (-1.25, 0.25, 6.18), (2.65, 4.35, 0.22), rot=(0.04, -0.06, 0.0), mat_idx=m_dark)
    for rx, ry in ((-0.08, -1.55), (-0.02, -0.45), (-0.02, 0.75)):
        add_cylinder(bm, (rx, ry, 6.20), (rx + 0.42, ry - 0.10, 6.32), 0.016, 0.012, segments=5, mat_idx=m_rust)
    for rx, ry in ((0.22, -1.35), (0.24, -0.55), (0.22, 0.45)):
        add_cylinder(bm, (rx, ry, 3.22), (rx + 0.44, ry - 0.16, 3.06), 0.015, 0.012, segments=5, mat_idx=m_rust)

    # Windows with shattered glass & barricade boards
    _add_broken_glass_window(bm, (1.40, -2.15, 1.78), 1.05, 1.18, depth=0.30, along_x=True,
                             frame_mat=m_dark, glass_mat=m_glass, board_mat=m_wood, boarded=True, seed=1)
    _add_broken_glass_window(bm, (-1.20, -2.15, 4.62), 1.05, 1.18, depth=0.30, along_x=True,
                             frame_mat=m_dark, glass_mat=m_glass, board_mat=m_wood, boarded=True, seed=2)
    _add_broken_glass_window(bm, (-2.35, -0.45, 1.78), 1.15, 1.18, depth=0.30, along_x=False,
                             frame_mat=m_dark, glass_mat=m_glass, board_mat=m_wood, boarded=True, seed=3)

    # Exterior rusted drainage pipe & AC box
    add_cylinder(bm, (-2.55, -1.45, 0.24), (-2.55, -1.45, 5.75), 0.065, 0.065, segments=6, mat_idx=m_rust)
    add_box(bm, (-2.68, 0.95, 2.35), (0.42, 0.68, 0.50), rot=(0.06, -0.05, 0.0), mat_idx=m_rust)

    # Base rubble pile, spilled wood boards & climbing ivy/weeds
    for rx, ry, rr in ((-1.75, -2.42, 0.22), (0.65, -2.38, 0.18), (2.48, -1.85, 0.26), (1.95, -2.42, 0.20)):
        _add_stone_chunk(bm, (rx, ry, rr * 0.42), rr, yaw=rx * 1.3, mat_idx=m_conc if rr > 0.21 else m_brick)
    add_box(bm, (-0.10, -2.55, 0.06), (0.95, 0.16, 0.045), rot=(0.05, 0.0, 0.35), mat_idx=m_wood)
    _add_grass_patch(bm, -2.25, -2.45, 0.02, count=10, spread=0.32, h_min=0.18, h_max=0.48,
                     idx_dry=m_dry, idx_lush=m_lush, seed=7)
    _add_grass_patch(bm, 2.45, -2.25, 0.02, count=8, spread=0.28, h_min=0.16, h_max=0.40,
                     idx_dry=m_dry, idx_lush=m_lush, seed=13)
    # Climbing wall moss/vine clusters
    for vx, vy, vz in ((-2.48, -1.95, 1.45), (-2.48, -1.80, 2.55), (-2.15, -2.30, 3.25)):
        add_box(bm, (vx, vy, vz), (0.28, 0.42, 0.68), rot=(0.1, 0.2, 0.3), bevel=0.05, mat_idx=m_lush)

    obj, tris = finalize_mesh(name, bm, materials, collection=collection)
    apply_box_uvs(obj, tex_scale=0.52)
    return obj, tris


def build_env_building_ruined_store(materials, idx_map, collection=None, name="Env_Building_RuinedStore"):
    """5.6m x 4.4m x 4.2m abandoned corner shop: plaster/brick facade, rusted corrugated awning, boarded windows & roof vent."""
    bm = bmesh.new()
    m_plast = idx_map["Mat_Env_PlasterDamaged"]
    m_brick = idx_map["Mat_Env_BrickRuined"]
    m_dark = idx_map["Mat_Env_ConcreteDark"]
    m_rust = idx_map["Mat_Env_RustHeavy"]
    m_wood = idx_map["Mat_Env_WoodPlank"]
    m_glass = idx_map["Mat_Env_GlassBroken"]
    m_dry = idx_map["Mat_Env_GrassDry"]
    m_lush = idx_map["Mat_Env_GrassLush"]

    # Foundation pad & brick lower wainscot (Z=0..0.95)
    add_box(bm, (0.0, 0.0, 0.10), (5.60, 4.40, 0.20), mat_idx=m_dark)
    add_box(bm, (0.0, 0.0, 0.56), (5.42, 4.22, 0.72), mat_idx=m_brick)

    # Main plaster storefront shell with open door bay at right-front
    add_box(bm, (-0.58, -1.96, 2.25), (4.10, 0.26, 2.68), mat_idx=m_plast)  # left-center front
    add_box(bm, ( 2.38, -1.96, 2.25), (0.58, 0.26, 2.68), mat_idx=m_plast)  # right corner pier
    add_box(bm, ( 1.72, -1.96, 3.12), (0.88, 0.26, 0.96), mat_idx=m_plast)  # header above shop door
    add_box(bm, (-2.58,  0.00, 2.25), (0.26, 4.18, 2.68), mat_idx=m_plast)
    add_box(bm, ( 2.58,  0.00, 2.25), (0.26, 4.18, 2.68), mat_idx=m_plast)
    add_box(bm, ( 0.00,  1.96, 2.25), (5.40, 0.26, 2.68), mat_idx=m_plast)

    # Damaged roof deck + broken parapet wall + rusted rooftop HVAC unit & crooked sign frame
    add_box(bm, (0.0, 0.0, 3.66), (5.48, 4.28, 0.18), mat_idx=m_dark)
    add_box(bm, (-1.15, -2.00, 3.94), (3.10, 0.22, 0.38), mat_idx=m_brick)
    add_box(bm, ( 1.80, -2.00, 3.84), (1.60, 0.22, 0.20), rot=(0.0, 0.06, 0.0), mat_idx=m_brick)
    add_box(bm, (-2.62,  0.30, 3.92), (0.22, 3.45, 0.36), mat_idx=m_brick)
    add_box(bm, (-1.20,  0.55, 4.02), (1.15, 0.92, 0.56), mat_idx=m_rust)

    # Slanted corrugated rusted shop awning (-Y front, Z=2.58)
    add_box(bm, (0.0, -2.52, 2.56), (5.25, 0.98, 0.07), rot=(0.24, -0.03, 0.0), mat_idx=m_rust)
    for ax in (-2.20, -0.60, 1.00, 2.35):
        add_cylinder(bm, (ax, -2.08, 2.75), (ax, -2.92, 2.46), 0.025, 0.022, segments=5, mat_idx=m_dark)

    # Wide storefront boarded windows & crooked overhead sign
    _add_broken_glass_window(bm, (-1.65, -1.96, 1.72), 1.45, 1.25, depth=0.30, along_x=True,
                             frame_mat=m_dark, glass_mat=m_glass, board_mat=m_wood, boarded=True, seed=4)
    _add_broken_glass_window(bm, ( 0.10, -1.96, 1.72), 1.35, 1.25, depth=0.30, along_x=True,
                             frame_mat=m_dark, glass_mat=m_glass, board_mat=m_wood, boarded=True, seed=5)
    add_box(bm, (-0.35, -2.14, 3.42), (2.70, 0.09, 0.52), rot=(0.0, 0.07, 0.0), mat_idx=m_wood)

    # Front curb rubble & weeds
    for sx, sy, sr in ((-2.45, -2.35, 0.20), (1.15, -2.28, 0.16), (2.55, -2.22, 0.18)):
        _add_stone_chunk(bm, (sx, sy, sr * 0.42), sr, mat_idx=m_brick)
    _add_grass_patch(bm, -2.10, -2.30, 0.02, count=9, spread=0.30, h_min=0.16, h_max=0.42,
                     idx_dry=m_dry, idx_lush=m_lush, seed=19)
    _add_grass_patch(bm, 2.40, -2.25, 0.02, count=7, spread=0.24, h_min=0.14, h_max=0.36,
                     idx_dry=m_dry, idx_lush=m_lush, seed=29)

    obj, tris = finalize_mesh(name, bm, materials, collection=collection)
    apply_box_uvs(obj, tex_scale=0.52)
    return obj, tris


def build_env_wall_ruined_brick(materials, idx_map, collection=None, name="Env_Wall_RuinedBrick"):
    """4.2m x 0.55m x 2.6m breached brick perimeter wall with concrete pilasters, stepped breach, rebar & weeds."""
    bm = bmesh.new()
    m_brick = idx_map["Mat_Env_BrickRuined"]
    m_conc = idx_map["Mat_Env_ConcreteCracked"]
    m_dark = idx_map["Mat_Env_ConcreteDark"]
    m_rust = idx_map["Mat_Env_RustHeavy"]
    m_dry = idx_map["Mat_Env_GrassDry"]
    m_lush = idx_map["Mat_Env_GrassLush"]

    # Ground strip & end pilasters
    add_box(bm, (0.0, 0.0, 0.08), (4.20, 0.54, 0.16), mat_idx=m_dark)
    add_box(bm, (-1.92, 0.0, 1.32), (0.38, 0.50, 2.48), mat_idx=m_conc)
    add_box(bm, ( 1.92, 0.0, 1.18), (0.38, 0.50, 2.20), mat_idx=m_conc)
    add_box(bm, (-1.92, 0.0, 2.58), (0.46, 0.56, 0.12), mat_idx=m_dark)

    # Breached brick segments leaving rugged V-gap around X=0.15
    add_box(bm, (-1.22, 0.0, 1.24), (1.06, 0.34, 2.18), mat_idx=m_brick)
    add_box(bm, (-0.52, 0.0, 0.90), (0.42, 0.34, 1.48), mat_idx=m_brick)
    add_box(bm, ( 0.15, 0.0, 0.42), (0.98, 0.34, 0.52), mat_idx=m_brick)  # low breach sill
    add_box(bm, ( 0.88, 0.0, 0.84), (0.52, 0.34, 1.36), mat_idx=m_brick)
    add_box(bm, ( 1.42, 0.0, 1.12), (0.64, 0.34, 1.92), mat_idx=m_brick)

    # Exposed horizontal rebar in breach & fallen brick pile around base
    add_cylinder(bm, (-0.50, 0.0, 1.15), (-0.18, 0.06, 1.10), 0.014, 0.012, segments=5, mat_idx=m_rust)
    add_cylinder(bm, (0.68, 0.0, 1.05), (0.32, -0.05, 0.98), 0.014, 0.012, segments=5, mat_idx=m_rust)
    for bx, by, br in ((-0.25, -0.40, 0.15), (0.28, 0.38, 0.16), (-0.78, 0.34, 0.12), (0.82, -0.36, 0.14)):
        _add_stone_chunk(bm, (bx, by, br * 0.40), br, yaw=bx * 1.4, mat_idx=m_brick)

    _add_grass_patch(bm, -0.90, -0.36, 0.02, count=8, spread=0.25, h_min=0.16, h_max=0.40,
                     idx_dry=m_dry, idx_lush=m_lush, seed=31)
    _add_grass_patch(bm, 0.15, 0.36, 0.02, count=7, spread=0.22, h_min=0.14, h_max=0.36,
                     idx_dry=m_dry, idx_lush=m_lush, seed=37)

    obj, tris = finalize_mesh(name, bm, materials, collection=collection)
    apply_box_uvs(obj, tex_scale=0.58)
    return obj, tris


# ---------------------------------------------------------------------------
# 3. OVERGROWN GRASS, SHRUBS & DEAD TREE (3 Foliage Assets)
# ---------------------------------------------------------------------------
def build_env_grass_clump_tall(materials, idx_map, collection=None, name="Env_Grass_ClumpTall"):
    """1.4m x 1.4m x 0.65m lush + dry overgrown apocalypse grass & weed tuft."""
    bm = bmesh.new()
    m_soil = idx_map["Mat_Env_SoilCracked"]
    m_dry = idx_map["Mat_Env_GrassDry"]
    m_lush = idx_map["Mat_Env_GrassLush"]

    add_box(bm, (0.0, 0.0, 0.018), (0.72, 0.68, 0.036), bevel=0.04, taper_top=(0.75, 0.75), mat_idx=m_soil)
    _add_grass_patch(bm, 0.0, 0.0, 0.015, count=26, spread=0.46, h_min=0.24, h_max=0.64,
                     idx_dry=m_dry, idx_lush=m_lush, seed=41)

    obj, tris = finalize_mesh(name, bm, materials, collection=collection)
    apply_box_uvs(obj, tex_scale=0.85)
    return obj, tris


def build_env_overgrown_bush(materials, idx_map, collection=None, name="Env_Overgrown_Bush"):
    """1.8m x 1.6m x 1.15m wild tangled apocalypse briar shrub with woody stems & faceted foliage canopy."""
    bm = bmesh.new()
    m_wood = idx_map["Mat_Env_WoodPlank"]
    m_lush = idx_map["Mat_Env_GrassLush"]
    m_dry = idx_map["Mat_Env_GrassDry"]
    m_soil = idx_map["Mat_Env_SoilCracked"]

    add_box(bm, (0.0, 0.0, 0.025), (0.85, 0.80, 0.05), bevel=0.04, taper_top=(0.78, 0.78), mat_idx=m_soil)
    # Crooked woody briar stems fanning from root core
    for p1 in ((-0.38, -0.22, 0.52), (0.42, -0.18, 0.56), (-0.12, 0.36, 0.48), (0.18, 0.30, 0.60)):
        add_cylinder(bm, (0.0, 0.0, 0.02), p1, 0.042, 0.018, segments=5, mat_idx=m_wood)

    # Faceted low-poly foliage clusters (lush + dry tips)
    blobs = (
        ((0.00,  0.00, 0.55), (0.95, 0.88, 0.74), 0.14, m_lush),
        ((-0.44, -0.16, 0.42), (0.64, 0.58, 0.52), 0.10, m_lush),
        (( 0.46,  0.14, 0.46), (0.66, 0.60, 0.54), 0.10, m_dry),
        ((-0.14,  0.40, 0.40), (0.58, 0.56, 0.48), 0.09, m_lush),
        (( 0.14, -0.38, 0.38), (0.56, 0.52, 0.46), 0.09, m_dry),
        (( 0.05,  0.04, 0.86), (0.58, 0.54, 0.44), 0.08, m_lush),
    )
    for k, (ctr, sz, bev, mat_i) in enumerate(blobs):
        add_box(bm, ctr, sz, rot=(0.18 * (k % 2), -0.15, k * 0.65),
                bevel=bev, taper_top=(0.82, 0.82), mat_idx=mat_i)

    _add_grass_patch(bm, 0.0, 0.0, 0.02, count=14, spread=0.68, h_min=0.18, h_max=0.45,
                     idx_dry=m_dry, idx_lush=m_lush, seed=55)

    obj, tris = finalize_mesh(name, bm, materials, collection=collection)
    apply_box_uvs(obj, tex_scale=0.80)
    return obj, tris


def build_env_dead_tree(materials, idx_map, collection=None, name="Env_Dead_Tree"):
    """3.2m x 3.0m x 5.4m gnarled leafless dead tree with root buttresses, twisted trunk & skeletal limbs."""
    bm = bmesh.new()
    m_bark = idx_map["Mat_Env_WoodPlank"]
    m_soil = idx_map["Mat_Env_SoilCracked"]
    m_dry = idx_map["Mat_Env_GrassDry"]
    m_lush = idx_map["Mat_Env_GrassLush"]

    add_box(bm, (0.0, 0.0, 0.04), (1.35, 1.25, 0.08), bevel=0.06, taper_top=(0.75, 0.75), mat_idx=m_soil)
    # 5 flaring root buttresses gripping ground
    for k in range(5):
        ang = (2.0 * math.pi * k) / 5.0 + 0.2
        add_cylinder(
            bm,
            (math.cos(ang) * 0.16, math.sin(ang) * 0.16, 0.52),
            (math.cos(ang) * 0.78, math.sin(ang) * 0.78, 0.01),
            0.13, 0.038, segments=5, mat_idx=m_bark,
        )

    # Segmented twisted main trunk up to fork at Z=2.65
    p0 = (0.00, 0.00, 0.02)
    p1 = (-0.08, 0.05, 1.35)
    p2 = (0.06, -0.04, 2.65)
    add_cylinder(bm, p0, p1, 0.28, 0.22, segments=6, mat_idx=m_bark)
    add_cylinder(bm, p1, p2, 0.22, 0.17, segments=6, mat_idx=m_bark)

    # Skeletal primary & secondary forked branches
    branches = [
        (p2, (-0.75, -0.35, 3.95), 0.14, 0.075),
        ((-0.75, -0.35, 3.95), (-1.42, -0.62, 5.15), 0.075, 0.022),
        ((-0.75, -0.35, 3.95), (-0.88,  0.32, 4.95), 0.065, 0.018),
        (p2, ( 0.85,  0.22, 4.05), 0.13, 0.068),
        (( 0.85,  0.22, 4.05), ( 1.48,  0.48, 5.35), 0.068, 0.020),
        (( 0.85,  0.22, 4.05), ( 1.05, -0.58, 4.82), 0.058, 0.018),
        (p2, (-0.12,  0.65, 3.85), 0.11, 0.055),
        ((-0.12,  0.65, 3.85), (-0.28,  1.22, 4.98), 0.055, 0.016),
        (p1, ( 0.55, -0.45, 2.35), 0.085, 0.028),
    ]
    for b0, b1, r0, r1 in branches:
        add_cylinder(bm, b0, b1, r0, r1, segments=5, mat_idx=m_bark)

    _add_grass_patch(bm, 0.0, 0.0, 0.03, count=12, spread=0.72, h_min=0.16, h_max=0.40,
                     idx_dry=m_dry, idx_lush=m_lush, seed=61)

    obj, tris = finalize_mesh(name, bm, materials, collection=collection)
    apply_box_uvs(obj, tex_scale=0.68)
    return obj, tris


# ---------------------------------------------------------------------------
# 4. STREET PROPS & TACTICAL COVER (5 Props)
# ---------------------------------------------------------------------------
def build_env_wrecked_car(materials, idx_map, collection=None, name="Env_Wrecked_Car"):
    """4.3m x 1.85m x 1.42m abandoned rusted sedan: dented chassis, popped hood, shattered windows & 4 wheels."""
    bm = bmesh.new()
    m_paint = idx_map["Mat_Env_CarPaintFaded"]
    m_rust = idx_map["Mat_Env_RustHeavy"]
    m_metal = idx_map["Mat_Env_MetalScrap"]
    m_glass = idx_map["Mat_Env_GlassBroken"]
    m_tire = idx_map["Mat_BootSole"]

    # Grounded tire radius 0.34 -> wheel centers Z=0.33, chassis floor Z=0.36
    # Underbody chassis rails & engine bay floor
    add_box(bm, (0.0, 0.0, 0.36), (3.95, 1.56, 0.14), mat_idx=m_metal)
    # Main lower sedan body (rear trunk to front fender, along X: -2.02..+2.02)
    add_box(bm, (0.00, 0.0, 0.62), (4.04, 1.72, 0.44), bevel=0.04, taper_top=(0.96, 0.94), mat_idx=m_paint)
    # Rusting doors & front grille / headlights
    add_box(bm, (-0.10, -0.87, 0.62), (1.85, 0.04, 0.36), mat_idx=m_rust)
    add_box(bm, ( 0.05,  0.87, 0.62), (1.75, 0.04, 0.36), mat_idx=m_rust)
    add_box(bm, ( 2.02,  0.00, 0.62), (0.06, 1.24, 0.24), mat_idx=m_metal)
    # Popped engine hood ajar at windshield hinge (x=0.86..1.90) & exposed engine block
    add_box(bm, (1.36, 0.0, 0.93), (1.04, 1.54, 0.05), rot=(0.0, -0.18, 0.0), mat_idx=m_rust)
    add_box(bm, (1.38, 0.0, 0.72), (0.62, 0.72, 0.24), mat_idx=m_metal)

    # Cabin roof & A/B/C pillars
    add_box(bm, (-0.38, 0.0, 1.32), (1.68, 1.46, 0.09), rot=(0.02, -0.02, 0.0), bevel=0.02, mat_idx=m_paint)
    for px, py, ry in ((0.42, -0.68, -0.38), (0.42, 0.68, -0.38), (-1.15, -0.68, 0.35), (-1.15, 0.68, 0.35), (-0.35, -0.68, 0.0), (-0.35, 0.68, 0.0)):
        add_box(bm, (px, py, 1.07), (0.09, 0.08, 0.52), rot=(0.0, ry, 0.0), mat_idx=m_paint)

    # Shattered windshield corner shards
    add_box(bm, (0.46, -0.44, 0.96), (0.03, 0.42, 0.24), rot=(0.0, -0.38, 0.0), taper_top=(0.5, 0.3), mat_idx=m_glass)
    add_box(bm, (0.46,  0.48, 1.14), (0.03, 0.36, 0.18), rot=(0.0, -0.38, 0.0), taper_top=(0.5, 0.4), mat_idx=m_glass)

    # Crooked front & rear bumpers + rusted exhaust pipe
    add_box(bm, ( 2.08, 0.0, 0.44), (0.14, 1.76, 0.16), rot=(0.06, 0.0, -0.04), mat_idx=m_metal)
    add_box(bm, (-2.08, 0.0, 0.42), (0.14, 1.74, 0.15), rot=(-0.05, 0.0, 0.03), mat_idx=m_metal)

    # 4 Wheels (front-right wheel tilted/deflated)
    for wx, wy, tilted in ((1.28, -0.82, 0.12), (1.28, 0.82, 0.0), (-1.28, -0.82, 0.0), (-1.28, 0.82, 0.0)):
        r = 0.33
        off = 0.08 * math.sin(tilted) if tilted else 0.0
        add_cylinder(bm, (wx, wy - 0.12, r), (wx, wy + 0.12, r + off), r, r, segments=10, mat_idx=m_tire)
        add_cylinder(bm, (wx, wy - 0.13, r), (wx, wy + 0.13, r + off), 0.16, 0.16, segments=8, mat_idx=m_rust)

    obj, tris = finalize_mesh(name, bm, materials, collection=collection)
    apply_box_uvs(obj, tex_scale=0.85)
    return obj, tris


def build_env_jersey_barrier(materials, idx_map, collection=None, name="Env_Jersey_Barrier"):
    """2.2m x 0.65m x 0.92m cracked highway Jersey barrier with hazard stripes, chipped corner & rebar."""
    bm = bmesh.new()
    m_conc = idx_map["Mat_Env_ConcreteCracked"]
    m_dark = idx_map["Mat_Env_ConcreteDark"]
    m_haz = idx_map["Mat_Env_HazardYellow"]
    m_rust = idx_map["Mat_Env_RustHeavy"]
    m_dry = idx_map["Mat_Env_GrassDry"]
    m_lush = idx_map["Mat_Env_GrassLush"]

    # Stepped concrete Jersey profile extruded along X (length 2.15m)
    add_box(bm, (0.0, 0.0, 0.14), (2.15, 0.62, 0.28), bevel=0.015, taper_top=(0.98, 0.72), mat_idx=m_conc)
    add_box(bm, (0.0, 0.0, 0.56), (2.10, 0.38, 0.58), bevel=0.012, taper_top=(0.99, 0.60), mat_idx=m_conc)
    # Chipped upper end recess & faded yellow hazard stripe panels
    add_box(bm, (-0.72, 0.0, 0.76), (0.48, 0.28, 0.14), mat_idx=m_haz)
    add_box(bm, ( 0.68, 0.0, 0.76), (0.46, 0.28, 0.14), mat_idx=m_haz)
    add_cylinder(bm, (0.98, -0.05, 0.72), (1.18, -0.02, 0.78), 0.014, 0.011, segments=5, mat_idx=m_rust)
    add_cylinder(bm, (0.98,  0.05, 0.62), (1.14,  0.08, 0.64), 0.014, 0.011, segments=5, mat_idx=m_rust)
    _add_stone_chunk(bm, (0.92, -0.38, 0.08), 0.14, mat_idx=m_dark)
    _add_grass_patch(bm, -0.78, -0.38, 0.01, count=6, spread=0.18, h_min=0.12, h_max=0.30,
                     idx_dry=m_dry, idx_lush=m_lush, seed=71)

    obj, tris = finalize_mesh(name, bm, materials, collection=collection)
    apply_box_uvs(obj, tex_scale=0.95)
    return obj, tris


def build_env_sandbag_barricade(materials, idx_map, collection=None, name="Env_Sandbag_Barricade"):
    """2.6m x 0.95m x 1.05m curved 3-tier sandbag checkpoint with timber stakes & rusted scrap armor plate."""
    bm = bmesh.new()
    m_bag = idx_map["Mat_Env_Sandbag"]
    m_wood = idx_map["Mat_Env_WoodPlank"]
    m_rust = idx_map["Mat_Env_RustHeavy"]
    m_metal = idx_map["Mat_Env_MetalScrap"]

    # 3 staggered courses of plump faceted sandbags along a subtle defense arc
    rows = [
        (0.11, 5, 0.0),
        (0.32, 4, 0.08),
        (0.52, 4, -0.06),
        (0.72, 3, 0.05),
    ]
    for tier_idx, (bz, count, y_off) in enumerate(rows):
        span = 0.50
        x0 = -0.5 * (count - 1) * span
        for i in range(count):
            bx = x0 + i * span
            arc_y = 0.09 * (bx * bx) + y_off * 0.25
            add_box(
                bm,
                (bx, arc_y, bz),
                (0.49, 0.34, 0.21),
                rot=(0.04 * (i % 2), 0.03 * (tier_idx - 1), -0.18 * bx),
                bevel=0.05,
                taper_top=(0.90, 0.86),
                mat_idx=m_bag,
            )

    # Vertical wooden stabilization stakes & bolted rusted steel shield plate
    for sx in (-1.05, 0.0, 1.05):
        sy = 0.09 * (sx * sx) + 0.24
        add_cylinder(bm, (sx, sy, 0.0), (sx, sy, 0.98), 0.042, 0.036, segments=6, mat_idx=m_wood)

    add_box(bm, (0.62, -0.22, 0.54), (1.05, 0.04, 0.88), rot=(0.14, 0.02, -0.18), mat_idx=m_rust)
    add_box(bm, (0.62, -0.25, 0.88), (0.98, 0.05, 0.10), rot=(0.14, 0.02, -0.18), mat_idx=m_metal)

    obj, tris = finalize_mesh(name, bm, materials, collection=collection)
    apply_box_uvs(obj, tex_scale=1.10)
    return obj, tris


def build_env_street_lamp_broken(materials, idx_map, collection=None, name="Env_StreetLamp_Broken"):
    """1.4m x 0.5m x 5.6m bent iron street lamp on cracked concrete plinth with hanging luminaire & stop sign."""
    bm = bmesh.new()
    m_conc = idx_map["Mat_Env_ConcreteCracked"]
    m_metal = idx_map["Mat_Env_MetalScrap"]
    m_rust = idx_map["Mat_Env_RustHeavy"]
    m_glass = idx_map["Mat_Env_GlassBroken"]

    add_box(bm, (0.0, 0.0, 0.16), (0.52, 0.52, 0.32), bevel=0.02, taper_top=(0.86, 0.86), mat_idx=m_conc)
    # Lower pole straight to kink at Z=2.35, then bent ~16 deg sideways toward +X
    kink = (0.0, 0.0, 2.35)
    top = (0.48, 0.0, 5.10)
    arm_tip = (1.32, 0.0, 5.25)
    add_cylinder(bm, (0.0, 0.0, 0.30), kink, 0.085, 0.068, segments=8, mat_idx=m_metal)
    add_cylinder(bm, kink, top, 0.068, 0.050, segments=8, mat_idx=m_metal)
    add_cylinder(bm, (0.44, 0.0, 4.92), arm_tip, 0.042, 0.032, segments=6, mat_idx=m_rust)

    # Hanging broken lamp head dangling down from arm tip + snapped wire loop
    add_box(bm, (1.36, 0.0, 5.02), (0.34, 0.24, 0.14), rot=(0.0, 0.58, 0.0), bevel=0.02, mat_idx=m_rust)
    add_box(bm, (1.42, 0.0, 4.92), (0.24, 0.18, 0.08), rot=(0.0, 0.58, 0.0), mat_idx=m_glass)
    add_cylinder(bm, (0.88, 0.0, 5.08), (1.10, -0.05, 4.45), 0.008, 0.006, segments=4, mat_idx=m_metal)

    # Tilted octagonal warning/stop sign halfway up lower post
    add_cylinder(bm, (0.0, -0.09, 2.05), (0.0, -0.12, 2.05), 0.28, 0.28, segments=8, mat_idx=idx_map["Mat_Env_BarrelRed"])

    obj, tris = finalize_mesh(name, bm, materials, collection=collection)
    apply_box_uvs(obj, tex_scale=0.95)
    return obj, tris


def build_env_fire_barrel(materials, idx_map, collection=None, name="Env_FireBarrel"):
    """0.85m x 0.85m x 1.15m rusted red oil drum with cutout vents, glowing embers, flames & stacked wood."""
    bm = bmesh.new()
    m_barrel = idx_map["Mat_Env_BarrelRed"]
    m_rust = idx_map["Mat_Env_RustHeavy"]
    m_ember = idx_map["Mat_Env_EmberGlow"]
    m_fire = idx_map["Mat_Env_FireCore"]
    m_wood = idx_map["Mat_Env_WoodPlank"]
    m_brick = idx_map["Mat_Env_BrickRuined"]

    # Main 55-gal steel oil drum (radius 0.29m, height 0.90m)
    add_cylinder(bm, (0.0, 0.0, 0.0), (0.0, 0.0, 0.90), 0.29, 0.29, segments=12, mat_idx=m_barrel)
    # Rolled steel ribs along drum height
    for rz in (0.03, 0.32, 0.60, 0.88):
        add_cylinder(bm, (0.0, 0.0, rz - 0.02), (0.0, 0.0, rz + 0.02), 0.305, 0.305, segments=12, mat_idx=m_rust)

    # Charred ember bed inside drum top & low-poly flickering flame cones
    add_cylinder(bm, (0.0, 0.0, 0.72), (0.0, 0.0, 0.88), 0.24, 0.23, segments=8, mat_idx=m_ember)
    add_cone(bm, ( 0.00,  0.00, 0.86), ( 0.04, -0.02, 1.24), 0.14, segments=5, mat_idx=m_fire)
    add_cone(bm, (-0.09,  0.06, 0.86), (-0.12,  0.09, 1.14), 0.09, segments=5, mat_idx=m_ember)
    add_cone(bm, ( 0.10, -0.05, 0.86), ( 0.14, -0.08, 1.12), 0.08, segments=5, mat_idx=m_ember)

    # Stacked firewood logs & bricks beside drum
    add_cylinder(bm, (0.34, -0.18, 0.055), (0.52, 0.24, 0.055), 0.055, 0.050, segments=6, mat_idx=m_wood)
    add_cylinder(bm, (0.40, -0.22, 0.135), (0.58, 0.16, 0.085), 0.050, 0.046, segments=6, mat_idx=m_wood)
    add_box(bm, (-0.36, -0.12, 0.04), (0.22, 0.11, 0.08), rot=(0.0, 0.0, 0.5), mat_idx=m_brick)

    obj, tris = finalize_mesh(name, bm, materials, collection=collection)
    apply_box_uvs(obj, tex_scale=1.20)
    return obj, tris


def _build_wet_road_puddles(materials, idx_map, col):
    """Add irregular flat mirror-gloss rainwater puddles nestled along road cracks & gutters."""
    bm = bmesh.new()
    m_puddle = idx_map["Mat_Env_PuddleWet"]

    puddle_specs = (
        (-12.2, -1.12, 1.35, 0.54,  0.08, 11),
        ( -6.2,  1.34, 1.45, 0.52, -0.06, 23),
        ( -5.8, -1.16, 1.48, 0.56,  0.12, 41),
        ( -0.4,  1.12, 1.32, 0.50, -0.05, 53),
        (  0.4, -1.18, 1.42, 0.52,  0.10, 67),
        (  5.7,  1.36, 1.40, 0.52, -0.10, 79),
        (  6.4, -1.10, 1.35, 0.50,  0.08, 89),
        ( 11.9,  1.22, 1.44, 0.54, -0.08, 97),
    )

    n_pts = 12
    for px, py, rx, ry, yaw, seed in puddle_specs:
        cy, sy = math.cos(yaw), math.sin(yaw)
        bot_ring = []
        top_ring = []
        for i in range(n_pts):
            t = (2.0 * math.pi * i) / n_pts
            wob = 1.0 + 0.22 * math.sin(2.0 * t + seed) + 0.14 * math.cos(3.0 * t - seed * 1.7)
            lx = rx * wob * math.cos(t)
            ly = ry * wob * math.sin(t)
            wx = px + lx * cy - ly * sy
            wy = py + lx * sy + ly * cy
            bot_ring.append((wx, wy, 0.001))
            top_ring.append((
                px + (lx * 0.94) * cy - (ly * 0.94) * sy,
                py + (lx * 0.94) * sy + (ly * 0.94) * cy,
                0.0055,
            ))
        loft_rings(bm, [bot_ring, top_ring], close_caps=(False, True), mat_idx=m_puddle)

    obj, tris = finalize_mesh("Env_WetPuddles", bm, materials, collection=col)
    apply_box_uvs(obj, tex_scale=0.50)
    return obj, tris


def _build_foundation_and_street_clutter(materials, idx_map, col):
    """Root buildings into the earth with rubble foundations, add broken steel fences & street crates."""
    bm = bmesh.new()
    m_soil = idx_map["Mat_Env_SoilCracked"]
    m_conc = idx_map["Mat_Env_ConcreteCracked"]
    m_dark = idx_map["Mat_Env_ConcreteDark"]
    m_brick = idx_map["Mat_Env_BrickRuined"]
    m_metal = idx_map["Mat_Env_MetalScrap"]
    m_rust = idx_map["Mat_Env_RustHeavy"]
    m_wood = idx_map["Mat_Env_WoodPlank"]
    m_dry = idx_map["Mat_Env_GrassDry"]
    m_lush = idx_map["Mat_Env_GrassLush"]

    # Foundation dirt/rubble collars rooting first-row buildings & walls into ground
    skirts = (
        (-11.8, 7.75, 5.4, 4.3, 0.24,  4.0),
        ( -4.6, 7.95, 5.8, 4.0, 0.22, -2.0),
        (  0.6, 5.60, 4.2, 1.4, 0.20,  2.0),
        (  5.2, 8.15, 5.8, 4.0, 0.22,  3.0),
        ( 12.2, 7.85, 5.4, 4.3, 0.24, -6.0),
        (-16.5, 6.20, 4.2, 1.5, 0.20, 18.0),
        ( 16.8, 6.40, 4.2, 1.5, 0.20,-15.0),
    )
    for k, (sx, sy, sw, sd, sh, rot_deg) in enumerate(skirts):
        rz = math.radians(rot_deg)
        add_box(bm, (sx, sy, sh * 0.35), (sw, sd, sh), rot=(0.0, 0.0, rz),
                bevel=0.14, taper_top=(0.82, 0.80), mat_idx=m_soil)
        _add_stone_chunk(bm, (sx - sw * 0.36, sy - sd * 0.44, 0.14), 0.26, yaw=k * 0.9, mat_idx=m_dark)
        _add_stone_chunk(bm, (sx + sw * 0.34, sy - sd * 0.42, 0.13), 0.22, yaw=k * 1.4, mat_idx=m_conc)
        _add_grass_patch(bm, sx - sw * 0.42, sy - sd * 0.45, 0.02, count=7, spread=0.32,
                         h_min=0.18, h_max=0.45, idx_dry=m_dry, idx_lush=m_lush, seed=k + 30)

    # Broken steel security fences bridging vacant lot gap & arena flanks (transparent silhouettes)
    fence_runs = (
        (-1.55, 6.85,  2.75, 6.95, 11),
        (-18.6, 5.30, -14.8, 5.50, 22),
        ( 14.8, 5.55,  18.8, 5.35, 33),
    )
    for x0, y0, x1, y1, fseed in fence_runs:
        span_v = Vector((x1 - x0, y1 - y0, 0.0))
        length = span_v.length
        yaw = math.atan2(span_v.y, span_v.x)
        # Concrete fence curb
        mid = Vector(((x0 + x1) * 0.5, (y0 + y1) * 0.5, 0.09))
        add_box(bm, mid, (length, 0.22, 0.22), rot=(0.0, 0.0, yaw), bevel=0.02, mat_idx=m_dark)
        n_posts = 4
        for pi in range(n_posts):
            t = pi / (n_posts - 1)
            px = x0 + (x1 - x0) * t
            py = y0 + (y1 - y0) * t
            lean_x = 0.08 * math.sin(pi * 2.1 + fseed)
            lean_y = 0.10 * math.cos(pi * 1.7 + fseed)
            h_post = 1.65 - (0.35 if pi == 2 else 0.0)
            add_cylinder(bm, (px, py, 0.16), (px + lean_x, py + lean_y, h_post),
                         0.036, 0.032, segments=6, mat_idx=m_metal if pi % 2 == 0 else m_rust)
            # Criss-cross wire-frame diamond slats (skip gap on one broken bay)
            if pi < n_posts - 1 and not (pi == 1 and fseed == 11):
                nx = x0 + (x1 - x0) * ((pi + 1) / (n_posts - 1))
                ny = y0 + (y1 - y0) * ((pi + 1) / (n_posts - 1))
                for hz in (0.65, 1.28):
                    add_cylinder(bm, (px, py, hz), (nx, ny, hz - 0.04),
                                 0.016, 0.016, segments=5, mat_idx=m_rust)
                add_cylinder(bm, (px, py, 0.24), (nx, ny, 1.32), 0.014, 0.014, segments=5, mat_idx=m_metal)
                add_cylinder(bm, (px, py, 1.32), (nx, ny, 0.24), 0.014, 0.014, segments=5, mat_idx=m_metal)

    # Supply crates, wooden pallets & scattered brick piles near barricades & shoulders
    crate_spots = (
        (-2.45,  4.45, 0.22, 0.62, 0.48, 0.44,  0.30, m_wood),
        (-2.22,  4.50, 0.58, 0.42, 0.36, 0.32, -0.22, m_rust),
        ( 5.55,  4.18, 0.20, 0.56, 0.50, 0.40,  0.48, m_wood),
        (-11.7, -4.10, 0.20, 0.60, 0.46, 0.40, -0.35, m_wood),
        ( 11.4, -4.15, 0.21, 0.64, 0.48, 0.42,  0.28, m_dark),
    )
    for cx, cy, cz, sx, sy, sz, rz, mat_i in crate_spots:
        add_box(bm, (cx, cy, cz), (sx, sy, sz), rot=(0.0, 0.0, rz), bevel=0.02, mat_idx=mat_i)
    add_box(bm, (-3.1, 4.35, 0.05), (0.95, 0.85, 0.10), rot=(0.0, 0.0, 0.18), mat_idx=m_wood)
    add_box(bm, ( 6.1, 4.30, 0.11), (0.48, 0.36, 0.22), rot=(0.12, -0.1, 0.6), mat_idx=m_brick)

    obj, tris = finalize_mesh("Env_StreetClutter", bm, materials, collection=col)
    apply_box_uvs(obj, tex_scale=0.55)
    return obj, tris


def _build_distant_city_skyline(materials, idx_map, col):
    """Build 360-degree ruined skyscraper ring, collapsed concrete highway overpass & red-beacon radio tower."""
    bm = bmesh.new()
    m_conc = idx_map["Mat_Env_ConcreteCracked"]
    m_dark = idx_map["Mat_Env_ConcreteDark"]
    m_brick = idx_map["Mat_Env_BrickRuined"]
    m_plaster = idx_map["Mat_Env_PlasterDamaged"]
    m_glass = idx_map["Mat_Env_GlassBroken"]
    m_metal = idx_map["Mat_Env_MetalScrap"]
    m_rust = idx_map["Mat_Env_RustHeavy"]
    m_wood = idx_map["Mat_Env_WoodPlank"]
    m_beacon = idx_map["Mat_Env_BeaconRed"]

    # 1. Collapsed Concrete Highway Overpass in North Mid-Background (Y ~ +20.5m)
    oy = 20.5
    # Heavy battered concrete piers along west and east intact spans
    for px in (-21.0, -13.0, -5.5, 6.2, 14.0, 22.0):
        for py_off in (-1.35, 1.35):
            add_box(bm, (px, oy + py_off, 3.4), (1.05, 0.95, 6.8),
                    taper_top=(0.86, 0.86), mat_idx=m_dark)
        add_box(bm, (px, oy, 6.85), (1.35, 4.30, 0.85), bevel=0.06, mat_idx=m_conc)

    # Intact/broken elevated west deck (X = -26..-3.4) & east deck (X = +4.2..+26)
    add_box(bm, (-14.7, oy, 7.62), (22.6, 4.70, 0.72), bevel=0.05, mat_idx=m_conc)
    add_box(bm, (-14.7, oy - 2.18, 8.28), (22.4, 0.32, 0.68), bevel=0.03, mat_idx=m_dark)
    add_box(bm, (-14.7, oy + 2.18, 8.28), (22.4, 0.32, 0.68), bevel=0.03, mat_idx=m_dark)

    add_box(bm, (15.1, oy, 7.62), (21.8, 4.70, 0.72), bevel=0.05, mat_idx=m_conc)
    add_box(bm, (15.1, oy - 2.18, 8.28), (21.6, 0.32, 0.68), bevel=0.03, mat_idx=m_dark)
    add_box(bm, (15.1, oy + 2.18, 8.28), (21.6, 0.32, 0.68), bevel=0.03, mat_idx=m_dark)

    # Tilted collapsed center span hanging from east edge & resting on rubble mound
    add_box(bm, (0.4, oy - 0.1, 3.6), (8.2, 4.50, 0.68), rot=(0.14, 0.56, 0.04), bevel=0.06, mat_idx=m_dark)
    add_box(bm, (-1.8, oy + 0.2, 0.7), (5.2, 3.60, 0.80), rot=(-0.10, -0.25, 0.20), bevel=0.08, mat_idx=m_conc)
    for rz_off in (-1.4, -0.4, 0.7, 1.6):
        add_cylinder(bm, (-3.5, oy + rz_off, 7.55), (-1.9, oy + rz_off, 7.20), 0.04, 0.03, segments=5, mat_idx=m_rust)
        add_cylinder(bm, ( 4.3, oy + rz_off, 7.58), ( 2.8, oy + rz_off, 7.35), 0.04, 0.03, segments=5, mat_idx=m_rust)

    # 2. Leaning Steel Radio / Cell Lattice Tower at (16.2, 22.0) silhouetted against open sky gap
    tx, ty = 16.2, 22.0
    tilt_x, tilt_y = 0.045, 0.025
    add_box(bm, (tx, ty, 0.35), (3.4, 3.4, 0.70), bevel=0.08, mat_idx=m_dark)
    levels = ((0.65, 1.35), (6.0, 1.00), (12.0, 0.68), (17.5, 0.42), (20.8, 0.24))
    corners = ((-1, -1), (1, -1), (1, 1), (-1, 1))
    for li in range(len(levels) - 1):
        z0, w0 = levels[li]
        z1, w1 = levels[li + 1]
        pts0 = [(tx + cx * w0 + z0 * tilt_x, ty + cy * w0 + z0 * tilt_y, z0) for cx, cy in corners]
        pts1 = [(tx + cx * w1 + z1 * tilt_x, ty + cy * w1 + z1 * tilt_y, z1) for cx, cy in corners]
        for ci in range(4):
            ni = (ci + 1) % 4
            add_cylinder(bm, pts0[ci], pts1[ci], 0.095, 0.08, segments=5, mat_idx=m_metal)
            add_cylinder(bm, pts1[ci], pts1[ni], 0.055, 0.055, segments=5, mat_idx=m_rust if li % 2 == 0 else m_metal)
            add_cylinder(bm, pts0[ci], pts1[ni], 0.042, 0.042, segments=4, mat_idx=m_metal)
    top_x = tx + 20.8 * tilt_x
    top_y = ty + 20.8 * tilt_y
    # Crossarms + glowing red beacon crystal
    add_box(bm, (top_x, top_y, 18.2), (2.4, 0.16, 0.16), rot=(0.0, 0.0, 0.3), mat_idx=m_metal)
    add_cylinder(bm, (top_x, top_y, 20.8), (top_x + 0.08, top_y + 0.04, 22.3), 0.09, 0.04, segments=6, mat_idx=m_metal)
    add_box(bm, (top_x + 0.08, top_y + 0.04, 22.45), (0.38, 0.38, 0.42), bevel=0.06, mat_idx=m_beacon)

    # 3. 360-Degree Ruined Skyscrapers, Smokestacks & Rooftop Water Towers (sky gap behind radio tower!)
    skyscrapers = (
        # North skyline backdrop (X, Y, W, D, H, yaw, body_mat, has_water_tower)
        (-42.0, 42.0, 9.5, 8.5, 24.0,  0.12, m_dark,    False),
        (-30.5, 45.0, 10.5, 8.8, 30.0, -0.06, m_plaster, True),
        (-21.5, 38.0, 8.2, 7.6, 18.0,  0.08, m_brick,   False),
        (-13.2, 46.0, 9.6, 8.6, 32.0, -0.04, m_dark,    False),
        ( -4.2, 43.0, 8.5, 7.8, 22.0,  0.05, m_plaster, False),
        (  5.2, 48.0, 10.8, 9.0, 33.0, 0.02, m_dark,    False),
        ( 26.8, 44.0, 9.4, 8.2, 28.0,  0.06, m_brick,   True),
        ( 37.0, 40.0, 8.8, 7.8, 24.0, -0.10, m_dark,    False),
        ( 46.0, 42.0, 9.5, 8.4, 26.0,  0.14, m_plaster, False),
        # Far east/west street corridor framing buildings
        (-31.0, 12.0, 8.2, 8.6, 15.5,  0.04, m_brick,   False),
        (-34.5, -5.5, 8.5, 9.0, 13.0, -0.08, m_dark,    False),
        ( 31.0, 11.5, 8.4, 8.5, 16.5, -0.05, m_plaster, False),
        ( 34.5, -6.0, 8.8, 8.8, 13.5,  0.09, m_brick,   False),
        # Distant south outer perimeter (well outside r=36m camera zone)
        (-34.0,-34.0, 8.8, 8.0, 14.0,  0.22, m_dark,    False),
        (-16.0,-46.0, 9.5, 8.2, 16.0, -0.10, m_plaster, False),
        (  4.0,-50.0, 10.0, 8.5, 15.0, 0.06, m_dark,    False),
        ( 22.0,-44.0, 9.0, 8.0, 14.5,  0.18, m_brick,   False),
        ( 36.0,-30.0, 8.5, 8.2, 13.5, -0.15, m_dark,    False),
    )

    for idx, (bx, by, bw, bd, bh, yaw, bmat, water_tower) in enumerate(skyscrapers):
        # Main stepped skyscraper shell with jagged/broken upper setback
        add_box(bm, (bx, by, bh * 0.42), (bw, bd, bh * 0.84),
                rot=(0.0, 0.0, yaw), mat_idx=bmat)
        # Broken upper crown (offset & shorter to create ragged bombed roofline)
        crown_h = bh * (0.24 + 0.05 * (idx % 3))
        crown_tilt = 0.04 if idx % 2 == 0 else -0.04
        add_box(bm, (bx + bw * 0.12 * (1 if idx % 2 == 0 else -1), by, bh * 0.82 + crown_h * 0.40),
                (bw * 0.68, bd * 0.72, crown_h),
                rot=(crown_tilt, -crown_tilt * 0.8, yaw), mat_idx=m_plaster if bmat == m_dark else m_dark)

        # Dark shattered window floor bands along facade facing street
        n_floors = max(3, int(bh // 4.2))
        for fl in range(1, n_floors):
            fz = fl * 3.8
            if fz < bh * 0.80:
                add_box(bm, (bx, by, fz), (bw + 0.16, bd + 0.16, 1.35),
                        rot=(0.0, 0.0, yaw), mat_idx=m_glass if (fl + idx) % 3 != 0 else m_dark)

        # Optional rooftop water tower
        if water_tower:
            wz_base = bh * 0.84
            add_cylinder(bm, (bx - 1.2, by - 0.8, wz_base), (bx - 1.2, by - 0.8, wz_base + 2.4), 0.14, 0.10, segments=4, mat_idx=m_metal)
            add_cylinder(bm, (bx + 0.2, by - 0.8, wz_base), (bx + 0.2, by - 0.8, wz_base + 2.4), 0.14, 0.10, segments=4, mat_idx=m_metal)
            add_cylinder(bm, (bx - 0.5, by + 0.2, wz_base), (bx - 0.5, by + 0.2, wz_base + 2.4), 0.14, 0.10, segments=4, mat_idx=m_metal)
            add_cylinder(bm, (bx - 0.5, by - 0.4, wz_base + 2.4), (bx - 0.5, by - 0.4, wz_base + 4.9), 1.35, 1.25, segments=8, mat_idx=m_wood)
            add_cone(bm, (bx - 0.5, by - 0.4, wz_base + 4.9), (bx - 0.5, by - 0.4, wz_base + 5.8), 1.45, segments=8, mat_idx=m_rust)

    # Twin ruined industrial factory smokestacks in far north corners
    for sx, sy, sh in ((-35.5, 48.0, 31.0), (35.5, 48.0, 29.0)):
        add_cylinder(bm, (sx, sy, 0.0), (sx + 0.35, sy - 0.2, sh), 2.1, 1.05, segments=10, mat_idx=m_brick)
        add_box(bm, (sx + 0.35, sy - 0.2, sh - 0.4), (2.5, 2.5, 0.7), rot=(0.12, -0.08, 0.4), mat_idx=m_dark)

    obj, tris = finalize_mesh("Env_DistantSkyline", bm, materials, collection=col)
    apply_box_uvs(obj, tex_scale=0.32)
    return obj, tris


ALL_ENV_BUILDERS = [
    ("ground_cracked_earth", build_env_ground_cracked_earth, "ground"),
    ("road_cracked_asphalt", build_env_road_cracked_asphalt, "ground"),
    ("rubble_crater",        build_env_rubble_crater,        "ground"),
    ("building_ruined_corner", build_env_building_ruined_corner, "building"),
    ("building_ruined_store",  build_env_building_ruined_store,  "building"),
    ("wall_ruined_brick",      build_env_wall_ruined_brick,      "building"),
    ("grass_clump_tall",       build_env_grass_clump_tall,       "foliage"),
    ("overgrown_bush",         build_env_overgrown_bush,         "foliage"),
    ("dead_tree",              build_env_dead_tree,              "foliage"),
    ("wrecked_car",            build_env_wrecked_car,            "prop"),
    ("jersey_barrier",         build_env_jersey_barrier,         "prop"),
    ("sandbag_barricade",      build_env_sandbag_barricade,      "prop"),
    ("street_lamp_broken",     build_env_street_lamp_broken,     "prop"),
    ("fire_barrel",            build_env_fire_barrel,            "prop"),
]


# ---------------------------------------------------------------------------
# 5. ASSEMBLED APOCALYPSE STREET BATTLEGROUND DIORAMA (38m x 26m)
# ---------------------------------------------------------------------------
def _place_piece(builder_fn, materials, idx_map, col, inst_name, loc=(0, 0, 0), rot_z_deg=0.0, scale=1.0, uv_scale=None):
    obj, tris = builder_fn(materials, idx_map, collection=col, name=inst_name)
    obj.location = Vector(loc)
    obj.rotation_euler = Euler((0.0, 0.0, math.radians(rot_z_deg)), "XYZ")
    obj.scale = Vector((scale, scale, scale))
    if uv_scale is not None:
        apply_box_uvs(obj, tex_scale=uv_scale)
    return obj, tris


def build_apocalypse_street_scene(materials, idx_map, collection=None):
    """Assemble a cohesive 38m x 26m post-apocalyptic city street diorama aligned for Battle Viewer.

    Blender +Y maps to Three.js -Z (background skyline); Blender -Y maps to Three.js +Z (open camera side).
    Central road X in [-18, +18], Y in [-3.0, +3.0] sits flush at Z = 0.0 so combat units walk & fight cleanly.
    """
    col = collection if collection is not None else bpy.context.scene.collection
    placed = []
    total_tris = 0

    def add(fn, iname, loc, rz=0.0, sc=1.0, uvs=None):
        nonlocal total_tris
        obj, t = _place_piece(fn, materials, idx_map, col, iname, loc=loc, rot_z_deg=rz, scale=sc, uv_scale=uvs)
        placed.append(obj)
        total_tris += t

    # 1. Endless 160m x 160m Wasteland Earth Skirt + Continuing Side Street + Shoulder Strips
    bm_base = bmesh.new()
    m_soil = idx_map["Mat_Env_SoilCracked"]
    m_dark = idx_map["Mat_Env_ConcreteDark"]
    m_asph = idx_map["Mat_Env_AsphaltCracked"]
    m_conc = idx_map["Mat_Env_ConcreteCracked"]
    m_line = idx_map["Mat_Env_RoadStripe"]

    # Seamless outer cracked-earth terrain extending far into fog (top at Z = -0.018)
    add_box(bm_base, (0.0, 0.0, -0.078), (160.0, 160.0, 0.12), mat_idx=m_soil)
    # Raised inner shoulder strips flush under the ruins & props (top at Z = -0.010)
    add_box(bm_base, (0.0,  8.8, -0.050), (42.0, 12.2, 0.08), mat_idx=m_soil)
    add_box(bm_base, (0.0, -8.8, -0.050), (42.0, 12.2, 0.08), mat_idx=m_soil)
    # Outer low-poly wasteland berms/rubble hills outside the combat corridor
    outer_berms = (
        (-28.0,  15.5, 16.0,  8.5, 1.5,  0.22),
        (  0.0,  16.5, 22.0,  6.5, 1.2, -0.05),
        ( 29.0,  16.0, 17.0,  8.5, 1.7, -0.25),
        (-36.0, -18.0, 14.0,  9.0, 1.1,  0.30),
        ( 36.0, -18.0, 14.0,  9.0, 1.2, -0.28),
        (  0.0, -32.0, 34.0, 10.0, 1.4,  0.02),
    )
    for bx, by, bw, bd, bh, rz in outer_berms:
        add_box(bm_base, (bx, by, bh * 0.35 - 0.02), (bw, bd, bh), rot=(0.0, 0.0, rz),
                bevel=0.45, taper_top=(0.62, 0.58), mat_idx=m_soil)

    # Continuing cracked asphalt avenue extending West (-68..-18) and East (+18..+68) into horizon fog
    for dir_x in (-1.0, 1.0):
        ax = dir_x * 43.0
        add_box(bm_base, (ax, 0.0, -0.018), (50.0, 4.72, 0.032), mat_idx=m_asph)
        add_box(bm_base, (ax,  2.66, 0.036), (50.0, 0.64, 0.095), mat_idx=m_conc)
        add_box(bm_base, (ax, -2.66, 0.036), (50.0, 0.64, 0.095), mat_idx=m_conc)
        for dx in range(21, 67, 4):
            add_box(bm_base, (dir_x * dx, 0.02, 0.002), (1.35, 0.12, 0.006), mat_idx=m_line)

    base_obj, base_tris = finalize_mesh("Env_BaseEarth", bm_base, materials, collection=col)
    apply_box_uvs(base_obj, tex_scale=0.18)
    placed.append(base_obj)
    total_tris += base_tris

    # Scattered cracked earth plates along north & south shoulder strips
    for ix, ex in enumerate((-15.0, -9.5, -4.0, 2.0, 8.0, 14.0)):
        add(build_env_ground_cracked_earth, f"Env_Earth_N_{ix}", (ex, 5.2, -0.008), rz=(ix % 4) * 90.0, sc=1.05)
        add(build_env_ground_cracked_earth, f"Env_Earth_S_{ix}", (ex, -5.2, -0.008), rz=((ix + 2) % 4) * 90.0, sc=1.05)

    # 2. Central 6-tile cracked asphalt avenue along X in [-18, +18], Y in [-3, +3]
    for i, rx in enumerate((-15.0, -9.0, -3.0, 3.0, 9.0, 15.0)):
        add(build_env_road_cracked_asphalt, f"Env_Road_{i}", (rx, 0.0, 0.0), rz=180.0 if (i % 2 == 1) else 0.0)

    # 3. North/Background City Ruins Skyline (+Y = Blender background -> Three.js -Z)
    add(build_env_building_ruined_corner, "Env_Bldg_Corner_W",  (-11.8, 7.8, 0.0), rz=4.0)
    add(build_env_building_ruined_store,  "Env_Bldg_Store_WC",  (-4.6,  8.0, 0.0), rz=-2.0)
    add(build_env_wall_ruined_brick,      "Env_Wall_Breach_C",  ( 0.6,  5.6, 0.0), rz=2.0)
    add(build_env_building_ruined_store,  "Env_Bldg_Store_EC",  ( 5.2,  8.2, 0.0), rz=3.0)
    add(build_env_building_ruined_corner, "Env_Bldg_Corner_E",  (12.2,  7.9, 0.0), rz=-6.0)
    add(build_env_wall_ruined_brick,      "Env_Wall_Far_W",     (-16.5, 6.2, 0.0), rz=18.0)
    add(build_env_wall_ruined_brick,      "Env_Wall_Far_E",     (16.8,  6.4, 0.0), rz=-15.0)

    # 4. Background Street Props, Cars, Fire Barrels, Checkpoints & Lamps
    add(build_env_wrecked_car,        "Env_Car_W",          (-7.8,  4.0, 0.0), rz=-16.0)
    add(build_env_wrecked_car,        "Env_Car_E",          ( 8.6,  4.3, 0.0), rz=168.0)
    add(build_env_sandbag_barricade,  "Env_Sandbags_N",     (-1.4,  3.85, 0.0), rz=-6.0)
    add(build_env_jersey_barrier,     "Env_Barrier_N1",     (-11.4, 3.35, 0.0), rz=4.0)
    add(build_env_jersey_barrier,     "Env_Barrier_N2",     ( 3.8,  3.45, 0.0), rz=-5.0)
    add(build_env_street_lamp_broken, "Env_Lamp_W",         (-9.2,  3.05, 0.0), rz=-8.0)
    add(build_env_street_lamp_broken, "Env_Lamp_E",         ( 6.8,  3.10, 0.0), rz=174.0)
    add(build_env_fire_barrel,        "Env_FireBarrel_W",   (-4.4,  3.65, 0.0), rz=25.0)
    add(build_env_fire_barrel,        "Env_FireBarrel_E",   ( 4.6,  3.75, 0.0), rz=-40.0)
    add(build_env_rubble_crater,      "Env_Rubble_N1",      (-8.2,  5.6, 0.0), rz=30.0, sc=0.88)
    add(build_env_rubble_crater,      "Env_Rubble_N2",      ( 9.4,  5.8, 0.0), rz=-45.0, sc=0.92)

    # 5. Dead Trees & Overgrown Grass / Shrubs Along Ruin Margins
    add(build_env_dead_tree, "Env_DeadTree_W", (-15.2, 8.2, 0.0), rz=25.0)
    add(build_env_dead_tree, "Env_DeadTree_E", ( 15.4, 8.6, 0.0), rz=-40.0)
    add(build_env_dead_tree, "Env_DeadTree_C", (  0.8, 10.6, 0.0), rz=110.0, sc=0.90)

    for k, (bx, by, sc, rz) in enumerate((
        (-13.8, 4.4, 1.10, 15), (-7.0, 5.2, 0.95, 70), (-1.8, 5.2, 1.05, 130),
        ( 2.8,  5.0, 0.90, 40), ( 7.6, 5.4, 1.15, 200), (13.6, 4.5, 1.00, 310),
    )):
        add(build_env_overgrown_bush, f"Env_Bush_N_{k}", (bx, by, 0.0), rz=rz, sc=sc)

    for k, (gx, gy, sc, rz) in enumerate((
        (-14.2, 3.1, 1.1, 20), (-10.4, 3.2, 0.95, 85), (-5.8, 3.2, 1.05, 140),
        (-2.8,  3.3, 1.0, 210), ( 0.4, 3.4, 1.15, 45), ( 3.0, 3.2, 0.95, 175),
        ( 6.0,  3.3, 1.05, 95), (10.2, 3.2, 1.10, 260), (14.4, 3.1, 1.05, 15),
    )):
        add(build_env_grass_clump_tall, f"Env_Grass_N_{k}", (gx, gy, 0.0), rz=rz, sc=sc)

    # 6. South/Foreground Shoulder (low props/grass/rubble + flank barriers so default camera stays 100% clear)
    add(build_env_jersey_barrier, "Env_Barrier_S1", (-10.8, -3.55, 0.0), rz=-3.0)
    add(build_env_jersey_barrier, "Env_Barrier_S2", ( 10.8, -3.55, 0.0), rz=5.0)
    add(build_env_rubble_crater,  "Env_Rubble_S1",  (-12.6, -5.8,  0.0), rz=15.0, sc=0.82)
    add(build_env_rubble_crater,  "Env_Rubble_S2",  ( 12.6, -5.6,  0.0), rz=-25.0, sc=0.82)
    add(build_env_wrecked_car,    "Env_Car_FlankS", (-14.8, -6.2,  0.0), rz=22.0)
    add(build_env_dead_tree,      "Env_Tree_FlankS",( 15.8, -6.8,  0.0), rz=65.0, sc=0.88)

    for k, (gx, gy, sc, rz) in enumerate((
        (-13.5, -3.15, 1.0, 40), (-8.5, -3.20, 0.95, 120), (-3.5, -3.25, 0.90, 220),
        ( 3.2,  -3.25, 0.92, 75), ( 8.4, -3.20, 1.00, 190), (13.4, -3.15, 1.05, 300),
    )):
        add(build_env_grass_clump_tall, f"Env_Grass_S_{k}", (gx, gy, 0.0), rz=rz, sc=sc)

    # 7. Wet Road Puddles, Building Foundation Grounding/Fences & 360° Ruined City Skyline
    for extra_fn in (
        _build_wet_road_puddles,
        _build_foundation_and_street_clutter,
        _build_distant_city_skyline,
    ):
        e_obj, e_tris = extra_fn(materials, idx_map, col)
        placed.append(e_obj)
        total_tris += e_tris

    return placed, total_tris
