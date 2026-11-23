"""Procedural faceted low-poly body, clothing, and facial geometry for the Survivor.

Coordinate system (Blender standard):
  +Z = Up (0.00 = boot soles, 1.80 = beanie top)
  -Y = Forward (character faces -Y)
  +X = Character Left
  -X = Character Right
"""
import math
import bmesh
from mathutils import Vector

from head_sculpt import build_sculpted_head_and_beanie
from mesh_utils import (
    add_box,
    add_cloth_creases,
    add_cylinder,
    loft_rings,
    ring_ellipse,
    ring_yz,
    finalize_mesh,
)


# Shared anatomical & joint proportions (in meters) used by both mesh & Mixamo rig.
PROPORTIONS = {
    "height": 1.80,
    "hips": (0.0, 0.00, 0.94),
    "spine": (0.0, 0.005, 1.04),
    "spine1": (0.0, 0.010, 1.18),
    "spine2": (0.0, 0.012, 1.33),
    "neck": (0.0, 0.012, 1.48),
    "head": (0.0, 0.005, 1.565),
    "head_top": (0.0, 0.005, 1.80),
    # Left side (+X); right side mirrors X -> -X
    "shoulder_in": (0.045, 0.012, 1.415),
    "arm": (0.185, 0.015, 1.425),
    "elbow": (0.450, 0.022, 1.425),
    "wrist": (0.715, 0.015, 1.425),
    "hand_end": (0.805, 0.012, 1.425),
    "thumb": [
        (0.742, -0.022, 1.415),
        (0.768, -0.048, 1.404),
        (0.790, -0.068, 1.394),
        (0.808, -0.084, 1.386),
    ],
    "index": [
        (0.798, -0.020, 1.426),
        (0.826, -0.020, 1.424),
        (0.850, -0.020, 1.421),
        (0.872, -0.020, 1.418),
    ],
    "middle": [
        (0.802, 0.008, 1.428),
        (0.832, 0.008, 1.426),
        (0.858, 0.008, 1.423),
        (0.882, 0.008, 1.420),
    ],
    "hip": (0.102, 0.00, 0.91),
    "knee": (0.105, -0.006, 0.50),
    "ankle": (0.105, 0.018, 0.095),
    "ball": (0.105, -0.072, 0.028),
    "toe": (0.105, -0.148, 0.025),
}


def _tag(verts, regions, name):
    """Store BMVert references in region buckets (converted to indices at end)."""
    bucket = regions.setdefault(name, [])
    bucket.extend(verts)


def _build_neck_and_shirt(bm, mat_idx, regions):
    """Build inner henley shirt torso with flush V-neck skin zone (neck is integrated in head_sculpt)."""
    # Inner shirt torso (V-neck chest down to belt)
    shirt_rings = [
        ring_ellipse(0.0, 0.004, 0.910, 0.156, 0.108, n=10, squash_front=0.95, squash_back=1.05),
        ring_ellipse(0.0, 0.006, 1.030, 0.150, 0.105, n=10, squash_front=0.95, squash_back=1.05),
        ring_ellipse(0.0, 0.010, 1.180, 0.165, 0.114, n=10, squash_front=0.95, squash_back=1.06),
        ring_ellipse(0.0, 0.012, 1.330, 0.184, 0.122, n=10, squash_front=0.96, squash_back=1.06),
        ring_ellipse(0.0, 0.014, 1.455, 0.164, 0.106, n=10, squash_front=0.92, squash_back=1.05),
        ring_ellipse(0.0, 0.015, 1.482, 0.082, 0.072, n=10),
    ]
    v_shirt = loft_rings(bm, shirt_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_Shirt"])
    _tag(v_shirt, regions, "torso")

    # Assign Mat_Skin directly to upper-front center shirt faces for flush V-neck skin (zero floating box)
    shirt_faces = {f for v in v_shirt for f in v.link_faces}
    for f in shirt_faces:
        cen = f.calc_center_median()
        if cen.z > 1.415 and abs(cen.x) < 0.048 and cen.y < -0.050:
            f.material_index = mat_idx["Mat_Skin"]

    # Subtle survival dog-tag pendant on upper henley shirt
    v_tag = add_box(
        bm,
        center=(0.012, -0.114, 1.356),
        size=(0.018, 0.006, 0.026),
        rot=(-0.12, 0.0, 0.14),
        bevel=0.0,
        mat_idx=mat_idx["Mat_MetalDark"],
    )
    _tag(v_tag, regions, "torso")


def _build_open_jacket(bm, mat_idx, regions):
    """Build manifold thick-walled open field parka, collar, lapels, pockets, and sleeves."""
    # Build a C-shaped cross-section loop (outer + inner shell) from left front edge (+X, -Y)
    # around the back (+Y) to right front edge (-X, -Y), then back inside so it's watertight.
    levels = [
        # (cz, rx, ry, gap_half_x, thick)
        (0.895, 0.180, 0.128, 0.066, 0.014),  # bottom hem
        (1.030, 0.170, 0.122, 0.060, 0.014),  # waist
        (1.180, 0.184, 0.132, 0.062, 0.015),  # mid-ribs
        (1.330, 0.204, 0.140, 0.070, 0.015),  # chest
        (1.455, 0.188, 0.122, 0.076, 0.014),  # shoulders
    ]

    # Outer angles from front-left (+65 deg from -Y) around back to front-right (-65 deg from -Y)
    # In XY where -Y is angle -pi/2:
    # Front-left edge is near (-pi/2 + gap_angle), back is +pi/2, front-right is (3*pi/2 - gap_angle)
    n_arc = 9  # 9 points along outer arc + 9 points along inner arc = 18-point closed ring
    rings = []
    for (cz, rx, ry, gap_x, thick) in levels:
        gap_ang = math.asin(min(0.85, gap_x / rx))
        a_start = -0.5 * math.pi + gap_ang
        a_end = 1.5 * math.pi - gap_ang

        outer_pts = []
        inner_pts = []
        for i in range(n_arc):
            t = i / (n_arc - 1)
            ang = a_start + t * (a_end - a_start)
            ca, sa = math.cos(ang), math.sin(ang)
            ox = rx * ca
            oy = 0.012 + ry * sa * (1.06 if sa > 0 else 0.96)
            ix = (rx - thick) * ca
            iy = 0.012 + (ry - thick) * sa * (1.06 if sa > 0 else 0.96)
            outer_pts.append((ox, oy, cz))
            inner_pts.append((ix, iy, cz))

        ring = outer_pts + list(reversed(inner_pts))
        rings.append(ring)

    v_jacket = loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_idx["Mat_Jacket"])
    # Subtle symmetric facet creases on mid-jacket rings (preserve top/bottom hem alignment)
    mid_jacket_verts = [v for v in v_jacket if 0.96 < v.co.z < 1.40]
    add_cloth_creases(bm, mid_jacket_verts, strength=0.0028, seed=11)
    _tag(v_jacket, regions, "torso")

    # Jacket lapels + turned-up collar + chest flap pockets + hem trim
    for sx in (1.0, -1.0):
        # Folded front lapel
        v_lapel = add_box(
            bm,
            center=(sx * 0.072, -0.106, 1.385),
            size=(0.042, 0.022, 0.135),
            rot=(0.12, sx * -0.18, sx * 0.25),
            bevel=0.0,
            mat_idx=mat_idx["Mat_JacketTrim"],
        )
        _tag(v_lapel, regions, "torso")

        # Turned-up collar wing
        v_collar_side = add_box(
            bm,
            center=(sx * 0.068, -0.010, 1.495),
            size=(0.024, 0.110, 0.065),
            rot=(0.0, sx * 0.22, sx * -0.18),
            bevel=0.0,
            mat_idx=mat_idx["Mat_JacketTrim"],
        )
        _tag(v_collar_side, regions, "torso")

        # Chest flap pocket
        v_cpocket = add_box(
            bm,
            center=(sx * 0.118, -0.105, 1.295),
            size=(0.064, 0.022, 0.072),
            rot=(0.05, 0.0, sx * -0.26),
            bevel=0.0,
            mat_idx=mat_idx["Mat_JacketTrim"],
        )
        _tag(v_cpocket, regions, "torso")

        # Lower front parka pocket
        v_lpocket = add_box(
            bm,
            center=(sx * 0.122, -0.092, 0.995),
            size=(0.072, 0.026, 0.085),
            rot=(0.0, 0.0, sx * -0.28),
            bevel=0.0,
            mat_idx=mat_idx["Mat_JacketTrim"],
        )
        _tag(v_lpocket, regions, "torso")

        # Shoulder epaulet tab
        v_ep = add_box(
            bm,
            center=(sx * 0.130, 0.015, 1.472),
            size=(0.082, 0.042, 0.016),
            rot=(0.0, sx * 0.14, 0.0),
            bevel=0.0,
            mat_idx=mat_idx["Mat_JacketTrim"],
        )
        _tag(v_ep, regions, "torso")

    # Back high collar connecting left and right wings
    v_collar_back = add_box(
        bm,
        center=(0.0, 0.078, 1.498),
        size=(0.145, 0.028, 0.068),
        rot=(-0.18, 0.0, 0.0),
        bevel=0.0,
        mat_idx=mat_idx["Mat_JacketTrim"],
    )
    _tag(v_collar_back, regions, "torso")


def _build_arms_and_hands(bm, mat_idx, regions):
    """Build T-pose jacket sleeves, forearm bandage, fingerless gloves, and fingers."""
    for side, sx in (("L", 1.0), ("R", -1.0)):
        # Jacket sleeve from shoulder overlap (|X|=0.14) to wrist cuff (|X|=0.705)
        # Note: shoulder overlaps torso slightly so bending never leaves gaps
        sleeve_specs = [
            (0.145, 0.014, 1.418, 0.072, 0.076),
            (0.215, 0.015, 1.425, 0.066, 0.068),
            (0.340, 0.018, 1.425, 0.060, 0.060),
            (0.450, 0.022, 1.425, 0.056, 0.056),  # elbow
            (0.585, 0.018, 1.425, 0.050, 0.050),
            (0.695, 0.015, 1.425, 0.044, 0.044),  # cuff
        ]
        sleeve_rings = [
            ring_yz(sx * ax, cy, cz, ry, rz, n=8)
            for (ax, cy, cz, ry, rz) in sleeve_specs
        ]
        if sx < 0:
            sleeve_rings = list(reversed(sleeve_rings))
        v_sleeve = loft_rings(bm, sleeve_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_Jacket"])
        _tag(v_sleeve, regions, f"arm_{side}")

        # Rolled cuff ring
        cuff_rings = [
            ring_yz(sx * 0.685, 0.015, 1.425, 0.048, 0.048, n=8),
            ring_yz(sx * 0.708, 0.015, 1.425, 0.048, 0.048, n=8),
        ]
        if sx < 0:
            cuff_rings = list(reversed(cuff_rings))
        v_cuff = loft_rings(bm, cuff_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_JacketTrim"])
        _tag(v_cuff, regions, f"arm_{side}")

        # Exposed wrist skin between cuff and glove
        wrist_rings = [
            ring_yz(sx * 0.695, 0.015, 1.425, 0.036, 0.030, n=8),
            ring_yz(sx * 0.735, 0.015, 1.425, 0.035, 0.026, n=8),
        ]
        if sx < 0:
            wrist_rings = list(reversed(wrist_rings))
        v_wrist = loft_rings(bm, wrist_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_Skin"])
        _tag(v_wrist, regions, f"arm_{side}")

        # Asymmetric bandage wrap on LEFT forearm (+X)
        if side == "L":
            band_rings = [
                ring_yz(0.555, 0.018, 1.425, 0.056, 0.056, n=8),
                ring_yz(0.655, 0.016, 1.425, 0.051, 0.051, n=8),
            ]
            v_band = loft_rings(bm, band_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_Bandage"])
            _tag(v_band, regions, "arm_L")

        # Fingerless tactical glove palm (from wrist 0.725 to knuckles 0.805)
        v_palm = add_box(
            bm,
            center=(sx * 0.766, 0.008, 1.425),
            size=(0.082, 0.072, 0.032),
            bevel=0.005,
            mat_idx=mat_idx["Mat_BeltLeather"],
        )
        _tag(v_palm, regions, f"hand_{side}")

        # Articulated low-poly fingers (exposed skin tips)
        # Thumb
        t_pts = PROPORTIONS["thumb"]
        for seg in range(3):
            p0 = (sx * t_pts[seg][0], t_pts[seg][1], t_pts[seg][2])
            p1 = (sx * t_pts[seg + 1][0], t_pts[seg + 1][1], t_pts[seg + 1][2])
            r0 = 0.0115 - seg * 0.0015
            r1 = 0.0100 - seg * 0.0015
            mat_seg = mat_idx["Mat_BeltLeather"] if seg == 0 else mat_idx["Mat_Skin"]
            vt = add_cylinder(bm, p0, p1, r0, r1, segments=6, mat_idx=mat_seg)
            _tag(vt, regions, f"thumb_{side}_{seg + 1}")

        # Index finger
        i_pts = PROPORTIONS["index"]
        for seg in range(3):
            p0 = (sx * i_pts[seg][0], i_pts[seg][1], i_pts[seg][2])
            p1 = (sx * i_pts[seg + 1][0], i_pts[seg + 1][1], i_pts[seg + 1][2])
            r0 = 0.0105 - seg * 0.0012
            r1 = 0.0093 - seg * 0.0012
            mat_seg = mat_idx["Mat_BeltLeather"] if seg == 0 else mat_idx["Mat_Skin"]
            vi = add_cylinder(bm, p0, p1, r0, r1, segments=6, mat_idx=mat_seg)
            _tag(vi, regions, f"index_{side}_{seg + 1}")

        # Middle + ring/pinky grouped finger block aligned with middle bone
        m_pts = PROPORTIONS["middle"]
        for seg in range(3):
            p0 = (sx * m_pts[seg][0], m_pts[seg][1] + 0.012, m_pts[seg][2])
            p1 = (sx * m_pts[seg + 1][0], m_pts[seg + 1][1] + 0.012, m_pts[seg + 1][2])
            mid_x = 0.5 * (p0[0] + p1[0])
            mid_y = 0.5 * (p0[1] + p1[1])
            mid_z = 0.5 * (p0[2] + p1[2])
            seg_len = abs(p1[0] - p0[0]) + 0.004
            mat_seg = mat_idx["Mat_BeltLeather"] if seg == 0 else mat_idx["Mat_Skin"]
            vm = add_box(
                bm,
                center=(mid_x, mid_y, mid_z),
                size=(seg_len, 0.044 - seg * 0.004, 0.019 - seg * 0.002),
                bevel=0.0,
                mat_idx=mat_seg,
            )
            _tag(vm, regions, f"middle_{side}_{seg + 1}")


def _build_belt_and_pouches(bm, mat_idx, regions):
    """Build leather survival belt, front buckle, and hip pouches (rigidly on Hips)."""
    belt_rings = [
        ring_ellipse(0.0, 0.004, 0.915, 0.172, 0.120, n=10),
        ring_ellipse(0.0, 0.004, 0.970, 0.172, 0.120, n=10),
    ]
    v_belt = loft_rings(bm, belt_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_BeltLeather"])
    _tag(v_belt, regions, "hips_rigid")

    # Metallic front buckle
    v_buckle = add_box(
        bm,
        center=(0.0, -0.120, 0.942),
        size=(0.056, 0.022, 0.052),
        bevel=0.0,
        mat_idx=mat_idx["Mat_MetalDark"],
    )
    _tag(v_buckle, regions, "hips_rigid")

    # Left hip utility pouch (+X)
    v_pouch_l = add_box(
        bm,
        center=(0.184, 0.015, 0.905),
        size=(0.052, 0.095, 0.115),
        rot=(0.0, 0.08, 0.0),
        bevel=0.0,
        mat_idx=mat_idx["Mat_BeltLeather"],
    )
    _tag(v_pouch_l, regions, "hips_rigid")

    # Right hip small ammo/tool pouch (-X)
    v_pouch_r = add_box(
        bm,
        center=(-0.178, -0.020, 0.915),
        size=(0.044, 0.068, 0.092),
        rot=(0.0, -0.08, 0.0),
        bevel=0.0,
        mat_idx=mat_idx["Mat_BeltLeather"],
    )
    _tag(v_pouch_r, regions, "hips_rigid")

    # Rear cargo trouser pockets for stronger back silhouette
    for sx in (1.0, -1.0):
        v_rpocket = add_box(
            bm,
            center=(sx * 0.080, 0.102, 0.855),
            size=(0.082, 0.020, 0.086),
            rot=(-0.10, 0.0, sx * 0.12),
            bevel=0.0,
            mat_idx=mat_idx["Mat_JacketTrim"],
        )
        _tag(v_rpocket, regions, "hips_rigid")


def _build_legs_and_boots(bm, mat_idx, regions):
    """Build pelvis, baggy cargo pants, cargo pockets, asymmetric knee pad, and combat boots."""
    # Pelvis block connecting both legs smoothly into waist (tucked slightly inside shirt/belt)
    pelvis_rings = [
        ring_ellipse(0.0, 0.002, 0.785, 0.148, 0.100, n=10),
        ring_ellipse(0.0, 0.004, 0.875, 0.156, 0.106, n=10),
        ring_ellipse(0.0, 0.004, 0.945, 0.144, 0.098, n=10),
    ]
    v_pelvis = loft_rings(bm, pelvis_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_Pants"])
    _tag(v_pelvis, regions, "hips_soft")

    for side, sx in (("L", 1.0), ("R", -1.0)):
        # Cargo pant leg from hip overlap (0.91) down to boot cuff (0.19)
        leg_rings = [
            ring_ellipse(sx * 0.105,  0.016, 0.185, 0.062, 0.068, n=8),  # tucked into boot
            ring_ellipse(sx * 0.105,  0.010, 0.305, 0.072, 0.078, n=8),  # calf
            ring_ellipse(sx * 0.105, -0.004, 0.495, 0.074, 0.080, n=8),  # knee
            ring_ellipse(sx * 0.104, -0.002, 0.680, 0.086, 0.094, n=8),  # mid thigh
            ring_ellipse(sx * 0.098,  0.002, 0.865, 0.094, 0.102, n=8),  # upper thigh
            ring_ellipse(sx * 0.092,  0.004, 0.925, 0.088, 0.098, n=8),  # pelvis overlap
        ]
        v_leg = loft_rings(bm, leg_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_Pants"])
        mid_leg_verts = [v for v in v_leg if 0.25 < v.co.z < 0.88]
        add_cloth_creases(bm, mid_leg_verts, strength=0.0025, seed=23)
        _tag(v_leg, regions, f"leg_{side}")

        # Bulky outer-thigh cargo pocket
        v_pocket = add_box(
            bm,
            center=(sx * 0.186, 0.005, 0.695),
            size=(0.036, 0.098, 0.145),
            rot=(0.0, sx * 0.06, 0.0),
            bevel=0.0,
            mat_idx=mat_idx["Mat_JacketTrim"],
        )
        _tag(v_pocket, regions, f"thigh_rigid_{side}")

        # Asymmetric details: Right knee tactical knee pad (-X), Left shin cloth strap (+X)
        if side == "R":
            v_pad = add_box(
                bm,
                center=(-0.105, -0.086, 0.498),
                size=(0.108, 0.032, 0.118),
                bevel=0.0,
                taper_top=(0.88, 0.9),
                mat_idx=mat_idx["Mat_KneePad"],
            )
            v_strap = loft_rings(
                bm,
                [
                    ring_ellipse(-0.105, -0.002, 0.478, 0.078, 0.084, n=8),
                    ring_ellipse(-0.105, -0.002, 0.516, 0.078, 0.084, n=8),
                ],
                close_caps=(True, True),
                mat_idx=mat_idx["Mat_KneePad"],
            )
            _tag(v_pad + v_strap, regions, "shin_rigid_R")
        else:
            v_legwrap = loft_rings(
                bm,
                [
                    ring_ellipse(0.105, 0.010, 0.275, 0.075, 0.081, n=8),
                    ring_ellipse(0.105, 0.010, 0.355, 0.077, 0.083, n=8),
                ],
                close_caps=(True, True),
                mat_idx=mat_idx["Mat_Bandage"],
            )
            _tag(v_legwrap, regions, "shin_rigid_L")

        # Combat Boots (Z = 0.00 to 0.23)
        # Boot shaft (0.08 to 0.225)
        boot_shaft_rings = [
            ring_ellipse(sx * 0.105,  0.018, 0.065, 0.058, 0.074, n=8),
            ring_ellipse(sx * 0.105,  0.018, 0.145, 0.064, 0.074, n=8),
            ring_ellipse(sx * 0.105,  0.016, 0.225, 0.068, 0.076, n=8),
        ]
        v_shaft = loft_rings(bm, boot_shaft_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_Boots"])
        _tag(v_shaft, regions, f"boot_shaft_{side}")

        # Foot upper (instep + toe box)
        v_foot = add_box(
            bm,
            center=(sx * 0.105, -0.048, 0.056),
            size=(0.108, 0.225, 0.068),
            bevel=0.010,
            taper_top=(0.86, 0.90),
            mat_idx=mat_idx["Mat_Boots"],
        )
        _tag(v_foot, regions, f"foot_{side}")

        # Combat boot sole split into distinct heel + forefoot tread resting on Z = 0.00
        v_sole_fore = add_box(
            bm,
            center=(sx * 0.105, -0.086, 0.013),
            size=(0.116, 0.164, 0.026),
            bevel=0.0,
            mat_idx=mat_idx["Mat_BootSole"],
        )
        v_sole_heel = add_box(
            bm,
            center=(sx * 0.105, 0.036, 0.017),
            size=(0.114, 0.072, 0.034),
            bevel=0.0,
            mat_idx=mat_idx["Mat_BootSole"],
        )
        _tag(v_sole_fore + v_sole_heel, regions, f"foot_{side}")

        # Ankle cuff strap around boot shaft
        v_boot_strap = loft_rings(
            bm,
            [
                ring_ellipse(sx * 0.105, 0.016, 0.200, 0.071, 0.079, n=8),
                ring_ellipse(sx * 0.105, 0.016, 0.222, 0.071, 0.079, n=8),
            ],
            close_caps=(True, True),
            mat_idx=mat_idx["Mat_BeltLeather"],
        )
        _tag(v_boot_strap, regions, f"boot_shaft_{side}")

        # Front lace tongue accent
        v_laces = add_box(
            bm,
            center=(sx * 0.105, -0.052, 0.145),
            size=(0.048, 0.022, 0.115),
            rot=(-0.18, 0.0, 0.0),
            bevel=0.0,
            mat_idx=mat_idx["Mat_BootSole"],
        )
        _tag(v_laces, regions, f"boot_shaft_{side}")


def build_survivor_body(materials, idx_map, collection=None):
    """Build the complete Survivor_Body mesh and return (obj, tri_count, region_indices)."""
    bm = bmesh.new()
    regions = {}

    build_sculpted_head_and_beanie(bm, idx_map, regions)
    _build_neck_and_shirt(bm, idx_map, regions)
    _build_open_jacket(bm, idx_map, regions)
    _build_arms_and_hands(bm, idx_map, regions)
    _build_belt_and_pouches(bm, idx_map, regions)
    _build_legs_and_boots(bm, idx_map, regions)

    # Convert BMVert references to final integer vertex indices
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    region_indices = {}
    for k, vlist in regions.items():
        region_indices[k] = {v.index for v in vlist if v.is_valid}

    obj, tris = finalize_mesh("Survivor_Body", bm, materials, collection=collection)
    return obj, tris, region_indices
