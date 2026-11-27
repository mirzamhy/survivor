"""Batch 2: Six Rigged Faceless Horror Zombies with distinct scales (1.42m..2.26m) & unique skills."""
import math
import bmesh
from mathutils import Vector

from mesh_utils import (
    add_box,
    add_cloth_creases,
    add_cone,
    add_cylinder,
    apply_box_uvs,
    bake_character_vertex_ao,
    finalize_mesh,
    loft_rings,
    ring_ellipse,
    ring_perp,
    ring_yz,
)
from rig_controls import build_control_rig
from rig_mixamo import (
    attach_gear_to_bone,
    create_mixamo_armature,
    create_weapon_sockets,
    make_proportions,
    skin_body_to_armature,
)
from zombie_head import build_zombie_head


def _tag(verts, regions, name):
    regions.setdefault(name, []).extend(verts)


def _perp_chain_rings(pts, radii_up_side, up_hint=(0.0, 0.0, 1.0), n=6):
    vecs = [Vector(p) for p in pts]
    m = len(vecs)
    rings = []
    for k in range(m):
        if k == 0:
            tan = vecs[1] - vecs[0]
        elif k == m - 1:
            tan = vecs[-1] - vecs[-2]
        else:
            tan = vecs[k + 1] - vecs[k - 1]
        r_u, r_s = radii_up_side[k]
        rings.append(ring_perp(vecs[k], tan, up_hint=up_hint, r_up=r_u, r_side=r_s, n=n))
    return rings


def _build_zombie_hand(
    bm, mat_idx, regions, P, side, sx, skin_mat,
    glove_mat=None, stain_mat="Mat_ZBloodDried", bulk=1.0, finger_len_mul=1.0,
):
    """Build 5-finger Mixamo-weighted undead claw hand (supports oversized crusher or long spidery claws)."""
    s = P["scale"]
    b = bulk
    fl = finger_len_mul
    wri_x = P["wrist"][0]
    hand_end_x = P["hand_end"][0]
    arm_y = P["arm"][1]
    arm_z = P["arm"][2]
    palm_mat = glove_mat if glove_mat else skin_mat

    palm_specs = [
        (wri_x - 0.032 * s,      arm_y,            arm_z,            0.023 * s * b, 0.015 * s * b),
        (wri_x - 0.004 * s,      arm_y,            arm_z,            0.025 * s * b, 0.014 * s * b),
        (wri_x + 0.020 * s,      arm_y - 0.004*s,  arm_z + 0.001*s,  0.033 * s * b, 0.016 * s * b),
        (wri_x + 0.048 * s,      arm_y - 0.006*s,  arm_z + 0.002*s,  0.035 * s * b, 0.016 * s * b),
        (hand_end_x - 0.010 * s, arm_y - 0.006*s,  arm_z + 0.001*s,  0.035 * s * b, 0.015 * s * b),
        (hand_end_x + 0.004 * s, arm_y - 0.006*s,  arm_z - 0.001*s,  0.031 * s * b, 0.012 * s * b),
    ]
    palm_rings = [ring_yz(sx * px, py, pz, ry, rz, n=8, squash_top=1.08, squash_bot=0.90)
                  for (px, py, pz, ry, rz) in palm_specs]
    if sx < 0:
        palm_rings = list(reversed(palm_rings))
    v_palm = loft_rings(bm, palm_rings, close_caps=(True, True), mat_idx=mat_idx[palm_mat])
    for f in {f for v in v_palm for f in v.link_faces}:
        if abs(f.calc_center_median().x) < wri_x - 0.006 * s:
            f.material_index = mat_idx[skin_mat]
    _tag(v_palm, regions, f"hand_{side}")

    finger_specs = [
        ("index",  [(0.0084, 0.0084), (0.0072, 0.0072), (0.0056, 0.0056), (0.0036, 0.0036)]),
        ("middle", [(0.0086, 0.0086), (0.0074, 0.0074), (0.0058, 0.0058), (0.0038, 0.0038)]),
        ("ring",   [(0.0080, 0.0080), (0.0068, 0.0068), (0.0054, 0.0054), (0.0035, 0.0035)]),
        ("pinky",  [(0.0070, 0.0070), (0.0060, 0.0060), (0.0046, 0.0046), (0.0032, 0.0032)]),
    ]
    for fname, f_rad in finger_specs:
        pts = P[fname]
        base_x = pts[0][0] - 0.010 * s
        def _fx(k):
            return sx * (base_x + (pts[k][0] - base_x) * fl)
        spine = [
            (_fx(0), pts[0][1], pts[0][2]),
            (_fx(1), pts[1][1], pts[1][2] - 0.002 * s),
            (_fx(2), pts[2][1], pts[2][2] - 0.006 * s * fl),
            (_fx(3), pts[3][1], pts[3][2] - 0.011 * s * fl),
        ]
        scaled_rad = [(ru * s * b, rs * s * b) for (ru, rs) in f_rad]
        v_fin = loft_rings(bm, _perp_chain_rings(spine, scaled_rad, n=5),
                           close_caps=(True, True), mat_idx=mat_idx[skin_mat])
        for f in {f for v in v_fin for f in v.link_faces}:
            cx = abs(f.calc_center_median().x)
            if glove_mat and cx < pts[1][0]:
                f.material_index = mat_idx[glove_mat]
            elif cx > pts[2][0]:
                f.material_index = mat_idx[stain_mat]
        _tag(v_fin, regions, f"{fname}_{side}")

    t_pts = P["thumb"]
    t_spine = [
        (sx * (wri_x + 0.008 * s), arm_y - 0.005 * s, arm_z - 0.002 * s),
        (sx * t_pts[0][0], t_pts[0][1], t_pts[0][2]),
        (sx * t_pts[1][0], t_pts[1][1], t_pts[1][2]),
        (sx * t_pts[2][0], t_pts[2][1], t_pts[2][2]),
        (sx * t_pts[3][0], t_pts[3][1], t_pts[3][2] - 0.003 * s * fl),
    ]
    t_radii = [
        (0.0130 * s * b, 0.0150 * s * b),
        (0.0112 * s * b, 0.0125 * s * b),
        (0.0092 * s * b, 0.0098 * s * b),
        (0.0074 * s * b, 0.0078 * s * b),
        (0.0046 * s * b, 0.0050 * s * b),
    ]
    v_th = loft_rings(bm, _perp_chain_rings(t_spine, t_radii, n=6),
                      close_caps=(True, True), mat_idx=mat_idx[skin_mat])
    for f in {f for v in v_th for f in v.link_faces}:
        cy = f.calc_center_median().y
        if glove_mat and cy > t_pts[1][1] + 0.004 * s:
            f.material_index = mat_idx[glove_mat]
        elif cy < t_pts[2][1]:
            f.material_index = mat_idx[stain_mat]
    for v in v_th:
        if abs(v.co.x) < t_pts[0][0] - 0.004 * s:
            _tag([v], regions, f"hand_{side}")
        else:
            _tag([v], regions, f"thumb_{side}")


def _add_jagged_rip_cuff(bm, center_xy_or_yz, r1, r2, pos, axis, mat_idx, amp=0.018, n=8):
    """Build a crisp zig-zag torn cloth cuff collar (`axis='Z'` for legs/hem, `'X'` for sleeves)."""
    ring_a = []
    ring_b = []
    for i in range(n):
        ang = (2.0 * math.pi * i) / n
        zag = amp if (i % 2 == 0) else -amp
        if axis == "Z":
            cx, cy = center_xy_or_yz
            px = cx + r1 * math.cos(ang)
            py = cy + r2 * math.sin(ang)
            ring_a.append((px, py, pos + amp * 1.4))
            ring_b.append((px * 1.01, py * 1.01, pos + zag))
        else:
            cy, cz = center_xy_or_yz
            py = cy + r1 * math.cos(ang)
            pz = cz + r2 * math.sin(ang)
            sx = 1.0 if pos >= 0 else -1.0
            ring_a.append((pos - sx * amp * 1.4, py, pz))
            ring_b.append((pos + sx * zag, py * 1.01, pz * 1.01))
    if axis == "X" and pos < 0:
        ring_a, ring_b = list(reversed(ring_a)), list(reversed(ring_b))
    return loft_rings(bm, [ring_a, ring_b], close_caps=(True, True), mat_idx=mat_idx)


def _add_tattered_strips(bm, mat_idx, regions, s, z_top, rx, ry, strip_mat, count=6, drop=0.14, tag="hips_soft"):
    """Add ragged hanging cloth strips around a torn hem without boxy slabs."""
    verts = []
    for i in range(count):
        ang = math.radians(-165 + i * (330.0 / max(1, count - 1)))
        ca, sa = math.cos(ang), math.sin(ang)
        len_i = drop * (0.75 + 0.45 * ((i * 3) % 3) / 2.0) * s
        px = (rx + 0.008 * s) * ca
        py = 0.006 * s + (ry + 0.008 * s) * sa
        pz = z_top - 0.38 * len_i
        verts.extend(add_box(
            bm,
            center=(px, py, pz),
            size=(0.036 * s, 0.010 * s, len_i),
            rot=(-0.10 * sa, 0.10 * ca, ang + math.pi * 0.5),
            taper_top=(1.15, 1.0),
            mat_idx=mat_idx[strip_mat],
        ))
    _tag(verts, regions, tag)
    return verts


def _paint_torso_stains(v_torso, mat_idx, s, pattern):
    """Flush face-painted blood, torn overalls, or toxic burns directly on torso triangles (zero slabs)."""
    faces = {f for v in v_torso for f in v.link_faces}
    for f in faces:
        c = f.calc_center_median()
        if c.y > -0.025 * s:
            continue
        if pattern == "blood_chest":
            if 1.15 * s < c.z < 1.38 * s and -0.08 * s < c.x < 0.02 * s:
                f.material_index = mat_idx["Mat_ZBloodDried"]
            elif 1.02 * s < c.z <= 1.15 * s and -0.05 * s < c.x < 0.01 * s:
                f.material_index = mat_idx["Mat_ZFlesh"]
        elif pattern == "banshee_blood":
            if 1.12 * s < c.z < 1.40 * s and -0.02 * s < c.x < 0.06 * s:
                f.material_index = mat_idx["Mat_ZBloodDried"]
        elif pattern == "toxic_burn":
            if 1.10 * s < c.z < 1.34 * s and -0.06 * s < c.x < 0.07 * s:
                f.material_index = mat_idx["Mat_ZSkinDark"] if c.x > 0.0 else mat_idx["Mat_ZSkinToxic"]
        elif pattern == "bloater_belly":
            if 0.94 * s < c.z < 1.24 * s and abs(c.x) < 0.16 * s:
                f.material_index = mat_idx["Mat_ZVeinDark"] if (c.x < 0.0 and c.z > 1.08 * s) else mat_idx["Mat_ZSkinBruised"]
            elif c.z >= 1.24 * s and abs(c.x) < 0.09 * s:
                f.material_index = mat_idx["Mat_ZSkinBruised"]
        elif pattern == "juggernaut_rips":
            if 1.10 * s < c.z < 1.32 * s and -0.10 * s < c.x < 0.02 * s:
                f.material_index = mat_idx["Mat_ZSkinBruised"] if c.z > 1.20 * s else mat_idx["Mat_ZBloodDried"]


def _build_zombie_base(
    bm, mat_idx, regions, P,
    shirt_mat, sleeve_mat, pants_mat, skin_mat,
    glove_mat=None, stain_mat="Mat_ZBloodDried",
    boot_mat="Mat_Boots", sole_mat="Mat_BootSole",
    body_type="gaunt",
    bare_arm_L=False, bare_arm_R=False,
    torn_pant_L=False, torn_pant_R=False,
    arm_bulk_L=1.0, arm_bulk_R=1.0,
    hand_bulk_L=1.0, hand_bulk_R=1.0,
    finger_len_mul=1.0,
    torso_stain=None,
):
    """Build parametric horror zombie torso, 3-loop joints, asymmetric limbs & jagged tears."""
    s = P["scale"]
    sh_s = P["shoulder_scale"]
    fem = P["female"]
    is_stalk = (body_type == "stalker")
    is_bloat = (body_type == "bloater")
    is_jug = (body_type == "juggernaut")
    is_gaunt = (body_type == "gaunt")
    is_haz = (body_type == "hazmat")

    if fem:
        pelvis_rx, waist_rx, mid_rx, chest_rx, top_rx = (
            0.156 * s, 0.096 * s, 0.120 * s, 0.144 * s, 0.134 * sh_s * s
        )
        r_pelvis = ring_ellipse(0.0, 0.006 * s, 0.900 * s, pelvis_rx, 0.108 * s, n=12, squash_front=0.92, squash_back=1.22)
        r_waist  = ring_ellipse(0.0, 0.006 * s, 1.045 * s, waist_rx,  0.074 * s, n=12, squash_front=0.90, squash_back=1.08)
        r_under  = ring_ellipse(0.0, 0.008 * s, 1.205 * s, mid_rx,    0.086 * s, n=12, squash_front=0.96, squash_back=1.06)
        r_bust   = ring_ellipse(0.0, 0.006 * s, 1.300 * s, chest_rx,  0.110 * s, n=12, squash_front=1.15, squash_back=1.06)
        r_upper  = ring_ellipse(0.0, 0.010 * s, 1.380 * s, chest_rx * 0.97, 0.092 * s, n=12, squash_front=1.02, squash_back=1.06)
        r_shldr  = ring_ellipse(0.0, 0.012 * s, 1.452 * s, top_rx,    0.080 * s, n=12, squash_front=0.88, squash_back=1.04)
        r_neck   = ring_ellipse(0.0, 0.014 * s, 1.482 * s, 0.055 * s, 0.053 * s, n=12)
        for ring, proj, stern in ((r_bust, 0.012 * s, 0.010 * s), (r_upper, 0.006 * s, 0.005 * s)):
            ring[8]  = (ring[8][0],  ring[8][1]  - proj,  ring[8][2])
            ring[10] = (ring[10][0], ring[10][1] - proj,  ring[10][2])
            ring[9]  = (ring[9][0],  ring[9][1]  + stern, ring[9][2])
        shirt_rings = [r_pelvis, r_waist, r_under, r_bust, r_upper, r_shldr, r_neck]
    elif is_bloat:
        # Grotesquely distended swollen belly & hunched bloated upper back built into torso mesh
        pelvis_rx, waist_rx, mid_rx, chest_rx, top_rx = (
            0.205 * s, 0.232 * s, 0.240 * s, 0.218 * s, 0.190 * s
        )
        shirt_rings = [
            ring_ellipse(0.0,  0.002 * s, 0.905 * s, pelvis_rx, 0.150 * s, n=12, squash_front=1.28, squash_back=1.08),
            ring_ellipse(0.0, -0.010 * s, 1.040 * s, waist_rx,  0.175 * s, n=12, squash_front=1.52, squash_back=1.06),
            ring_ellipse(0.0, -0.006 * s, 1.185 * s, mid_rx,    0.165 * s, n=12, squash_front=1.36, squash_back=1.18),
            ring_ellipse(0.0,  0.008 * s, 1.330 * s, chest_rx,  0.145 * s, n=12, squash_front=1.06, squash_back=1.28),
            ring_ellipse(0.0,  0.016 * s, 1.456 * s, top_rx,    0.122 * s, n=12, squash_front=0.92, squash_back=1.22),
            ring_ellipse(0.0,  0.016 * s, 1.484 * s, 0.088 * s, 0.080 * s, n=12),
        ]
    elif is_jug:
        pelvis_rx, waist_rx, mid_rx, chest_rx, top_rx = (
            0.188 * s, 0.184 * s, 0.216 * s, 0.246 * s, 0.228 * s
        )
        shirt_rings = [
            ring_ellipse(0.0, 0.004 * s, 0.910 * s, pelvis_rx, 0.132 * s, n=12, squash_front=1.05, squash_back=1.08),
            ring_ellipse(0.0, 0.004 * s, 1.035 * s, waist_rx,  0.132 * s, n=12, squash_front=1.08, squash_back=1.06),
            ring_ellipse(0.0, 0.008 * s, 1.185 * s, mid_rx,    0.148 * s, n=12, squash_front=1.08, squash_back=1.18),
            ring_ellipse(0.0, 0.014 * s, 1.335 * s, chest_rx,  0.158 * s, n=12, squash_front=1.06, squash_back=1.26),
            ring_ellipse(0.0, 0.018 * s, 1.458 * s, top_rx,    0.132 * s, n=12, squash_front=0.92, squash_back=1.24),
            ring_ellipse(0.0, 0.016 * s, 1.484 * s, 0.094 * s, 0.086 * s, n=12),
        ]
    else:
        w_mul = 0.78 if is_stalk else (0.90 if is_gaunt else (1.06 if is_haz else 1.0))
        pelvis_rx = 0.152 * w_mul * s
        waist_rx  = 0.138 * w_mul * s
        mid_rx    = 0.160 * w_mul * s
        chest_rx  = 0.184 * (0.86 if is_stalk else (0.96 if is_gaunt else w_mul)) * s
        top_rx    = 0.166 * sh_s * s
        shirt_rings = [
            ring_ellipse(0.0, 0.004 * s, 0.910 * s, pelvis_rx, 0.100 * w_mul * s, n=12, squash_front=0.94, squash_back=1.05),
            ring_ellipse(0.0, 0.006 * s, 1.030 * s, waist_rx,  0.090 * w_mul * s, n=12, squash_front=0.88, squash_back=1.06),
            ring_ellipse(0.0, 0.010 * s, 1.180 * s, mid_rx,    0.104 * w_mul * s, n=12, squash_front=0.94, squash_back=1.08),
            ring_ellipse(0.0, 0.012 * s, 1.325 * s, chest_rx,  0.116 * w_mul * s, n=12, squash_front=0.96, squash_back=1.10),
            ring_ellipse(0.0, 0.014 * s, 1.455 * s, top_rx,    0.098 * w_mul * s, n=12, squash_front=0.92, squash_back=1.08),
            ring_ellipse(0.0, 0.015 * s, 1.482 * s, 0.070 * s, 0.064 * s,         n=12),
        ]

    v_torso = loft_rings(bm, shirt_rings, close_caps=(True, True), mat_idx=mat_idx[shirt_mat])
    add_cloth_creases(bm, [v for v in v_torso if 0.96 * s < v.co.z < 1.44 * s], strength=0.0032 * s, seed=71)
    _tag(v_torso, regions, "torso")

    for f in {f for v in v_torso for f in v.link_faces}:
        cen = f.calc_center_median()
        if cen.z > 1.425 * s and abs(cen.x) < 0.048 * s and cen.y < -0.042 * s:
            f.material_index = mat_idx[skin_mat]
    if torso_stain:
        _paint_torso_stains(v_torso, mat_idx, s, torso_stain)

    # Arms + 3-loop shoulder/elbow topology + asymmetric limb bulk + 5-finger claws
    sh_x = P["arm"][0]
    arm_x0 = sh_x - 0.048 * s
    arm_x1 = sh_x + 0.038 * s
    elb_x = P["elbow"][0]
    wri_x = P["wrist"][0]
    cuff_x = wri_x - 0.018 * s
    arm_y = P["arm"][1]
    arm_z = P["arm"][2]

    base_arm = 1.12 if is_bloat else (1.08 if is_haz else (0.74 if is_stalk else (0.86 if is_gaunt else 1.0)))
    r_arm_0 = (0.043 if fem else 0.060 * base_arm) * s
    r_elb_0 = (0.035 if fem else 0.048 * base_arm) * s
    r_wri_0 = (0.025 if fem else 0.036 * base_arm) * s

    for side, sx, bare_fore, a_bulk, h_bulk in (
        ("L",  1.0, bare_arm_L, arm_bulk_L, hand_bulk_L),
        ("R", -1.0, bare_arm_R, arm_bulk_R, hand_bulk_R),
    ):
        r_arm = r_arm_0 * a_bulk
        r_elb = r_elb_0 * a_bulk
        r_wri = r_wri_0 * a_bulk
        fa_mul = 0.80 if (bare_fore and a_bulk <= 1.05) else 1.0
        sleeve_specs = [
            (arm_x0,                       arm_y,            arm_z - 0.004 * s, r_arm * 1.05, r_arm * 1.08),
            (sh_x,                         arm_y,            arm_z,             r_arm * 1.04, r_arm * 1.06),
            (arm_x1,                       arm_y + 0.002*s,  arm_z,             r_arm * 0.98, r_arm * 0.98),
            (elb_x - 0.028 * s,            P["elbow"][1],    arm_z,             r_elb * 1.02, r_elb * 1.02),
            (elb_x,                        P["elbow"][1],    arm_z,             r_elb * (0.90 if bare_fore else 1.0), r_elb * (0.90 if bare_fore else 1.0)),
            (elb_x + 0.028 * s,            P["elbow"][1],    arm_z,             r_elb * 0.96 * fa_mul, r_elb * 0.96 * fa_mul),
            (0.50 * elb_x + 0.50 * cuff_x, arm_y + 0.003*s,  arm_z,             r_elb * 0.86 * fa_mul, r_elb * 0.80 * fa_mul),
            (0.25 * elb_x + 0.75 * cuff_x, arm_y + 0.001*s,  arm_z,             r_wri * 0.88 * fa_mul, r_wri * 0.78 * fa_mul),
            (cuff_x,                       arm_y,            arm_z,             r_wri * 0.74 * fa_mul, r_wri * 0.60 * fa_mul),
        ]
        rings = [ring_yz(sx * ax, cy, cz, ry, rz, n=8) for (ax, cy, cz, ry, rz) in sleeve_specs]
        if sx < 0:
            rings = list(reversed(rings))
        v_slv = loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_idx[sleeve_mat])
        _tag(v_slv, regions, f"arm_{side}")

        if bare_fore:
            rip_x = arm_x1 if is_stalk or is_jug else (elb_x - 0.015 * s)
            for f in {f for v in v_slv for f in v.link_faces}:
                ax = abs(f.calc_center_median().x)
                if ax > wri_x - 0.055 * s:
                    f.material_index = mat_idx[stain_mat]
                elif ax > rip_x:
                    f.material_index = mat_idx[skin_mat]
            if not is_jug or side == "L":
                _tag(_add_jagged_rip_cuff(
                    bm, (arm_y, arm_z), r_arm * 1.04 if rip_x < elb_x - 0.05 * s else r_elb * 1.06,
                    r_arm * 1.04 if rip_x < elb_x - 0.05 * s else r_elb * 1.06,
                    sx * rip_x, "X", mat_idx[sleeve_mat], amp=0.016 * s,
                ), regions, f"arm_{side}")

        gmat = glove_mat[side] if isinstance(glove_mat, dict) else glove_mat
        _build_zombie_hand(
            bm, mat_idx, regions, P, side, sx, skin_mat,
            glove_mat=gmat, stain_mat=stain_mat, bulk=h_bulk, finger_len_mul=finger_len_mul,
        )

    # Pelvis & Legs (NO flat rectangular shin plaques!)
    hx = P["hip"][0]
    leg_scale = 1.24 if is_jug else (1.16 if is_bloat else (1.06 if is_haz else (0.78 if is_stalk else (0.90 if is_gaunt else 1.0))))
    pelvis_rings = [
        ring_ellipse(0.0, 0.004 * s, 0.785 * s, 0.148 * leg_scale * s, (0.106 if fem else 0.098 * leg_scale) * s, n=10, squash_back=1.18 if fem else 1.02),
        ring_ellipse(0.0, 0.006 * s, 0.870 * s, pelvis_rx + 0.006 * s, (0.112 if fem else 0.106 * leg_scale) * s, n=10, squash_back=1.22 if fem else 1.04),
        ring_ellipse(0.0, 0.004 * s, 0.945 * s, pelvis_rx * 0.90,      (0.090 if fem else 0.098 * leg_scale) * s, n=10),
    ]
    _tag(loft_rings(bm, pelvis_rings, close_caps=(True, True), mat_idx=mat_idx[pants_mat]), regions, "hips_soft")

    r_th = (0.075 if fem else 0.088 * leg_scale) * s
    r_kn = (0.053 if fem else 0.070 * leg_scale) * s
    r_ankle = (0.043 if fem else 0.054 * leg_scale) * s
    kn_z = P["knee"][2]

    for side, sx, bare_shin in (("L", 1.0, torn_pant_L), ("R", -1.0, torn_pant_R)):
        sh_mul = 0.80 if bare_shin else 1.0
        leg_rings = [
            ring_ellipse(sx * hx,        0.016 * s, 0.185 * s,        r_ankle * sh_mul,     r_ankle * 1.12 * sh_mul, n=8),
            ring_ellipse(sx * hx,        0.010 * s, 0.305 * s,        r_kn * 0.90 * sh_mul, r_kn * 1.00 * sh_mul,    n=8),
            ring_ellipse(sx * hx,       -0.002 * s, kn_z - 0.036 * s, r_kn * 0.96 * sh_mul, r_kn * 1.02 * sh_mul,    n=8),
            ring_ellipse(sx * hx,       -0.004 * s, kn_z,             r_kn,                 r_kn * 1.06,             n=8),
            ring_ellipse(sx * hx,       -0.003 * s, kn_z + 0.036 * s, r_kn * 1.05,          r_kn * 1.12,             n=8),
            ring_ellipse(sx * hx,       -0.002 * s, 0.680 * s,        r_th * 0.92,          r_th,                    n=8),
            ring_ellipse(sx * hx * 0.94, 0.002 * s, 0.865 * s,        r_th * 1.02,          r_th * 1.06,             n=8),
            ring_ellipse(sx * hx * 0.90, 0.004 * s, 0.925 * s,        r_th * 0.94,          r_th * 1.02,             n=8),
        ]
        v_leg = loft_rings(bm, leg_rings, close_caps=(True, True), mat_idx=mat_idx[pants_mat])
        add_cloth_creases(bm, [v for v in v_leg if 0.25 * s < v.co.z < 0.88 * s and abs(v.co.z - kn_z) > 0.05 * s],
                          strength=0.0024 * s, seed=53)
        _tag(v_leg, regions, f"leg_{side}")

        if bare_shin:
            rip_z = kn_z - 0.01 * s
            for f in {f for v in v_leg for f in v.link_faces}:
                c = f.calc_center_median()
                if c.z < rip_z:
                    if c.z > rip_z - 0.065 * s and c.y < -0.01 * s and (c.x * sx) > (hx - 0.015 * s):
                        f.material_index = mat_idx["Mat_ZBloodDried"]
                    else:
                        f.material_index = mat_idx[skin_mat]
            _tag(_add_jagged_rip_cuff(
                bm, (sx * hx, 0.0), r_kn * 1.08, r_kn * 1.14,
                rip_z, "Z", mat_idx[pants_mat], amp=0.020 * s,
            ), regions, f"leg_{side}")

        bw = (0.044 if fem else 0.052 * (1.20 if is_jug else (1.12 if is_bloat else (0.82 if is_stalk else 1.0)))) * s
        shaft = [
            ring_ellipse(sx * hx, 0.018 * s, 0.065 * s, bw,        bw * 1.24, n=8),
            ring_ellipse(sx * hx, 0.018 * s, 0.145 * s, bw * 1.06, bw * 1.24, n=8),
            ring_ellipse(sx * hx, 0.016 * s, 0.210 * s, bw * 1.12, bw * 1.26, n=8),
        ]
        _tag(loft_rings(bm, shaft, close_caps=(True, True), mat_idx=mat_idx[boot_mat]), regions, f"boot_shaft_{side}")
        _tag(add_box(
            bm, center=(sx * hx, -0.044 * s, 0.052 * s),
            size=(bw * 1.85, (0.194 if fem else 0.215) * s, (0.056 if fem else 0.064) * s),
            bevel=0.007 * s, taper_top=(0.84, 0.88), mat_idx=mat_idx[boot_mat],
        ), regions, f"foot_{side}")
        _tag(add_box(
            bm, center=(sx * hx, -0.078 * s, 0.011 * s),
            size=(bw * 1.98, (0.138 if fem else 0.156) * s, (0.022 if fem else 0.026) * s),
            mat_idx=mat_idx[sole_mat],
        ), regions, f"foot_{side}")
        _tag(add_box(
            bm, center=(sx * hx, 0.034 * s, 0.018 * s),
            size=(bw * 1.94, (0.060 if fem else 0.070) * s, 0.036 * s),
            mat_idx=mat_idx[sole_mat],
        ), regions, f"foot_{side}")

    return {
        "s": s,
        "sh_s": sh_s,
        "fem": fem,
        "pelvis_rx": pelvis_rx,
        "waist_rx": waist_rx,
        "mid_rx": mid_rx,
        "chest_rx": chest_rx,
        "top_rx": top_rx,
        "r_arm": r_arm_0,
        "r_th": r_th,
        "hx": hx,
    }


def _finalize_zombie(name, bm, materials, regions, P, col_char, col_rig):
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    region_indices = {k: {v.index for v in vlist if v.is_valid} for k, vlist in regions.items()}

    body_obj, body_tris = finalize_mesh(f"{name}_Body", bm, materials, collection=col_char)
    apply_box_uvs(body_obj, tex_scale=2.6)
    bake_character_vertex_ao(body_obj, style="zombie")
    arm_obj, specs = create_mixamo_armature(collection=col_rig, proportions=P)
    arm_obj.name = f"{name}_Armature"
    skin_body_to_armature(body_obj, arm_obj, specs, region_indices)
    build_control_rig(arm_obj, P)
    create_weapon_sockets(arm_obj, P, col_rig)
    return body_obj, body_tris, arm_obj


# ---------------------------------------------------------------------------
# 1. CRAWLER STALKER (1.42 m) - Small Wiry Predator, Long Bony Claws, Skill: Pounce
# ---------------------------------------------------------------------------
def build_zombie_crawler_stalker(materials, idx_map, col_char, col_gear, col_rig):
    P = make_proportions(height=1.42, female=False, shoulder_scale=0.88)
    bm = bmesh.new()
    regions = {}

    build_zombie_head(
        bm, idx_map, regions, P, gender="male",
        skin_mat="Mat_ZSkinPale", hair_mat="Mat_HairBlack",
        headgear="stalker_rags", jaw_open=0.022, gaunt=0.96,
        asym_wound="cheek_l_blood", blood_chin=True,
    )
    T = _build_zombie_base(
        bm, idx_map, regions, P,
        shirt_mat="Mat_ZShroudDark", sleeve_mat="Mat_ZShroudDark",
        pants_mat="Mat_ZClothDirty", skin_mat="Mat_ZSkinPale",
        stain_mat="Mat_ZBloodDried", boot_mat="Mat_Bandage",
        body_type="stalker", bare_arm_L=True, bare_arm_R=True,
        torn_pant_L=True, torn_pant_R=True, finger_len_mul=1.25,
    )
    s = T["s"]
    _add_tattered_strips(bm, idx_map, regions, s, 0.905 * s, T["pelvis_rx"] * 1.05, 0.095 * s,
                         "Mat_ZShroudDark", count=6, drop=0.14, tag="hips_soft")

    body_obj, body_tris, arm_obj = _finalize_zombie("Zombie_Crawler_Stalker", bm, materials, regions, P, col_char, col_rig)
    return body_obj, body_tris, arm_obj, []


# ---------------------------------------------------------------------------
# 2. WALKER SHAMBLER (1.78 m) - Classic Faceless Undead, Torn Office Tie, Skill: Grapple Bite
# ---------------------------------------------------------------------------
def build_zombie_walker_shambler(materials, idx_map, col_char, col_gear, col_rig):
    P = make_proportions(height=1.78, female=False)
    bm = bmesh.new()
    regions = {}

    build_zombie_head(
        bm, idx_map, regions, P, gender="male",
        skin_mat="Mat_ZSkinGreen", hair_mat="Mat_HairBlack",
        headgear="messy_patchy", jaw_open=0.017, gaunt=0.88,
        asym_wound="cheek_r", blood_chin=True,
    )
    T = _build_zombie_base(
        bm, idx_map, regions, P,
        shirt_mat="Mat_ZShirtTorn", sleeve_mat="Mat_ZShirtTorn",
        pants_mat="Mat_ZClothDirty", skin_mat="Mat_ZSkinGreen",
        body_type="gaunt", bare_arm_R=True, torn_pant_L=True, torso_stain="blood_chest",
    )
    s = T["s"]

    _tag(_add_jagged_rip_cuff(bm, (0.0, 0.004 * s), T["pelvis_rx"] * 1.04, 0.104 * s,
                              0.905 * s, "Z", idx_map["Mat_ZShirtTorn"], amp=0.024 * s, n=12),
         regions, "torso")
    _tag(add_box(bm, center=(0.016 * s, -0.104 * s, 1.385 * s), size=(0.030 * s, 0.012 * s, 0.135 * s),
                 rot=(-0.10, 0.0, 0.18), taper_top=(0.75, 0.8), mat_idx=idx_map["Mat_ZTieDark"]),
         regions, "torso")
    _tag(add_box(bm, center=(0.032 * s, -0.112 * s, 1.245 * s), size=(0.040 * s, 0.012 * s, 0.160 * s),
                 rot=(-0.12, 0.0, -0.22), taper_top=(0.65, 0.9), mat_idx=idx_map["Mat_ZTieDark"]),
         regions, "torso")
    _tag(loft_rings(bm, [
        ring_ellipse(0.0, 0.004 * s, 0.920 * s, T["pelvis_rx"] + 0.010 * s, 0.106 * s, n=10),
        ring_ellipse(0.0, 0.004 * s, 0.962 * s, T["pelvis_rx"] + 0.010 * s, 0.106 * s, n=10),
    ], close_caps=(True, True), mat_idx=idx_map["Mat_BeltLeather"]), regions, "hips_rigid")

    body_obj, body_tris, arm_obj = _finalize_zombie("Zombie_Walker_Shambler", bm, materials, regions, P, col_char, col_rig)
    return body_obj, body_tris, arm_obj, []


# ---------------------------------------------------------------------------
# 3. BANSHEE SCREAMER (1.66 m) - Female Horror, Unhinged Jaw, Dark Tears, Skill: Sonic Shriek
# ---------------------------------------------------------------------------
def build_zombie_banshee_screamer(materials, idx_map, col_char, col_gear, col_rig):
    P = make_proportions(height=1.66, female=True)
    bm = bmesh.new()
    regions = {}

    build_zombie_head(
        bm, idx_map, regions, P, gender="female",
        skin_mat="Mat_ZSkinPale", hair_mat="Mat_HairBlack",
        headgear="ragged_female", jaw_open=0.026, gaunt=0.86,
        asym_wound="cheek_l_blood", blood_chin=True, dark_tears=True,
    )
    T = _build_zombie_base(
        bm, idx_map, regions, P,
        shirt_mat="Mat_ZNurseDress", sleeve_mat="Mat_ZCardigan",
        pants_mat="Mat_ZShroudDark", skin_mat="Mat_ZSkinPale",
        boot_mat="Mat_WorkGrey", body_type="female",
        bare_arm_L=True, torn_pant_R=True, finger_len_mul=1.14, torso_stain="banshee_blood",
    )
    s = T["s"]

    # Tattered cardigan contouring female hourglass + long ragged shroud skirt tatters
    c_levels = [
        (0.895 * s, T["pelvis_rx"] + 0.016 * s, 0.122 * s, 0.068 * s, 0.012 * s),
        (1.045 * s, T["waist_rx"] + 0.016 * s,  0.092 * s, 0.052 * s, 0.012 * s),
        (1.205 * s, T["mid_rx"] + 0.018 * s,    0.102 * s, 0.064 * s, 0.012 * s),
        (1.300 * s, T["chest_rx"] + 0.020 * s,  0.128 * s, 0.076 * s, 0.012 * s),
        (1.380 * s, T["chest_rx"] + 0.014 * s,  0.110 * s, 0.070 * s, 0.012 * s),
        (1.452 * s, T["top_rx"] + 0.014 * s,    0.094 * s, 0.058 * s, 0.012 * s),
    ]
    n_arc = 7
    c_rings = []
    for (cz, rx, ry, gx, th) in c_levels:
        ga = math.asin(min(0.85, gx / rx))
        a0, a1 = -0.5 * math.pi + ga, 1.5 * math.pi - ga
        op, ip = [], []
        for i in range(n_arc):
            ang = a0 + (i / (n_arc - 1)) * (a1 - a0)
            ca, sa = math.cos(ang), math.sin(ang)
            sf = 1.18 if sa < 0 else 1.13
            op.append((rx * ca, 0.006 * s + ry * sa * sf, cz))
            ip.append(((rx - th) * ca, 0.006 * s + (ry - th) * sa * sf, cz))
        c_rings.append(op + list(reversed(ip)))
    v_card = loft_rings(bm, c_rings, close_caps=(True, True), mat_idx=idx_map["Mat_ZCardigan"])
    add_cloth_creases(bm, v_card, strength=0.0026 * s, seed=41)
    _tag(v_card, regions, "torso")
    _add_tattered_strips(bm, idx_map, regions, s, 0.915 * s, T["pelvis_rx"] + 0.018 * s, 0.122 * s,
                         "Mat_ZCardigan", count=7, drop=0.19, tag="hips_soft")

    body_obj, body_tris, arm_obj = _finalize_zombie("Zombie_Banshee_Screamer", bm, materials, regions, P, col_char, col_rig)
    return body_obj, body_tris, arm_obj, []


# ---------------------------------------------------------------------------
# 4. SPITTER HAZMAT (1.76 m) - Swollen Throat Bile Sac, Torn Suit, Skill: Acid Spit
# ---------------------------------------------------------------------------
def build_zombie_spitter_hazmat(materials, idx_map, col_char, col_gear, col_rig):
    P = make_proportions(height=1.76, female=False, shoulder_scale=1.02)
    bm = bmesh.new()
    regions = {}

    build_zombie_head(
        bm, idx_map, regions, P, gender="male",
        skin_mat="Mat_ZSkinToxic", hair_mat="Mat_HairBlack",
        headgear="hazmat_torn", jaw_open=0.020, gaunt=0.72,
        asym_wound="toxic_boils", blood_chin=False, neck_sac=True,
    )
    T = _build_zombie_base(
        bm, idx_map, regions, P,
        shirt_mat="Mat_ZHazmatYellow", sleeve_mat="Mat_ZHazmatYellow",
        pants_mat="Mat_ZHazmatYellow", skin_mat="Mat_ZSkinToxic",
        glove_mat={"L": "Mat_ZHazmatTrim", "R": None},
        stain_mat="Mat_ZAcidGlow", boot_mat="Mat_ZHazmatTrim",
        body_type="hazmat", bare_arm_R=True, torn_pant_L=True, torso_stain="toxic_burn",
    )
    s = T["s"]

    _tag(loft_rings(bm, [
        ring_ellipse(0.0, 0.008 * s, 1.472 * s, 0.090 * s, 0.082 * s, n=10),
        ring_ellipse(0.0, 0.010 * s, 1.504 * s, 0.084 * s, 0.078 * s, n=10),
    ], close_caps=(True, True), mat_idx=idx_map["Mat_ZHazmatTrim"]), regions, "torso")
    for sx in (1.0, -1.0):
        _tag(add_box(bm, center=(sx * 0.088 * s, 0.008 * s, 1.464 * s), size=(0.068 * s, 0.026 * s, 0.016 * s),
                     rot=(0.0, sx * 0.16, 0.0), mat_idx=idx_map["Mat_ZHazmatTrim"]), regions, "torso")
    # Small organic acid blisters around torn chest opening (NO flat rib plaque)
    for px, pz, pr in ((-0.026, 1.280, 0.016), (0.030, 1.235, 0.020), (-0.012, 1.195, 0.015), (0.044, 1.295, 0.013)):
        _tag(add_box(
            bm, center=(px * s, -0.118 * s, pz * s),
            size=(pr * s, pr * 0.85 * s, pr * s),
            rot=(0.35, 0.45, 0.2), bevel=pr * 0.24 * s, mat_idx=idx_map["Mat_ZAcidGlow"],
        ), regions, "torso")
    # Dangling broken black respirator on chest
    _tag(add_cylinder(bm, (0.045 * s, -0.095 * s, 1.465 * s), (0.086 * s, -0.136 * s, 1.345 * s),
                      0.008 * s, 0.008 * s, segments=5, mat_idx=idx_map["Mat_ZHazmatTrim"]), regions, "torso")
    _tag(add_box(bm, center=(0.092 * s, -0.145 * s, 1.325 * s), size=(0.064 * s, 0.056 * s, 0.068 * s),
                 rot=(0.30, 0.18, -0.20), taper_top=(0.82, 0.86), mat_idx=idx_map["Mat_ZHazmatTrim"]), regions, "torso")
    _tag(add_cylinder(bm, (0.092 * s, -0.158 * s, 1.315 * s), (0.092 * s, -0.184 * s, 1.298 * s),
                      0.022 * s, 0.020 * s, segments=6, mat_idx=idx_map["Mat_GunMetal"]), regions, "torso")
    _tag(loft_rings(bm, [
        ring_ellipse(0.0, 0.006 * s, 0.922 * s, T["pelvis_rx"] + 0.010 * s, 0.112 * s, n=10),
        ring_ellipse(0.0, 0.006 * s, 0.958 * s, T["pelvis_rx"] + 0.010 * s, 0.112 * s, n=10),
    ], close_caps=(True, True), mat_idx=idx_map["Mat_ZHazmatTrim"]), regions, "hips_rigid")

    body_obj, body_tris, arm_obj = _finalize_zombie("Zombie_Spitter_Hazmat", bm, materials, regions, P, col_char, col_rig)
    gear_items = []

    bm_tk = bmesh.new()
    add_box(bm_tk, center=(0.0, 0.175 * s, 1.270 * s), size=(0.205 * s, 0.048 * s, 0.285 * s),
            mat_idx=idx_map["Mat_ZHazmatTrim"])
    for sx in (1.0, -1.0):
        add_cylinder(bm_tk, (sx * 0.054 * s, 0.228 * s, 1.130 * s), (sx * 0.054 * s, 0.228 * s, 1.430 * s),
                     0.044 * s, 0.044 * s, segments=8, mat_idx=idx_map["Mat_ZHazmatYellow"])
        add_cylinder(bm_tk, (sx * 0.054 * s, 0.228 * s, 1.430 * s), (sx * 0.054 * s, 0.228 * s, 1.462 * s),
                     0.036 * s, 0.016 * s, segments=8, mat_idx=idx_map["Mat_GunSteel"])
    add_box(bm_tk, center=(-0.054 * s, 0.268 * s, 1.295 * s), size=(0.022 * s, 0.018 * s, 0.135 * s),
            rot=(0.0, 0.18, 0.0), mat_idx=idx_map["Mat_ZAcidGlow"])
    tk_obj, tk_t = finalize_mesh("Zombie_Spitter_Hazmat_AirTank", bm_tk, materials, collection=col_gear)
    apply_box_uvs(tk_obj, tex_scale=3.2)
    bake_character_vertex_ao(tk_obj, style="zombie")
    attach_gear_to_bone(tk_obj, arm_obj, "mixamorig:Spine2")
    gear_items.append((tk_obj, tk_t))

    return body_obj, body_tris, arm_obj, gear_items


# ---------------------------------------------------------------------------
# 5. BLOATER BOOMER (1.88 m) - Swollen Volatile Pustule Belly, Skill: Volatile Detonate
# ---------------------------------------------------------------------------
def build_zombie_bloater_boomer(materials, idx_map, col_char, col_gear, col_rig):
    P = make_proportions(height=1.88, female=False, shoulder_scale=1.14)
    bm = bmesh.new()
    regions = {}

    build_zombie_head(
        bm, idx_map, regions, P, gender="male",
        skin_mat="Mat_ZSkinBruised", hair_mat="Mat_HairBlack",
        headgear="boomer_bloated", jaw_open=0.018, gaunt=0.18,
        head_scale_xy=1.18, blood_chin=True, boomer_blisters=True,
    )
    T = _build_zombie_base(
        bm, idx_map, regions, P,
        shirt_mat="Mat_ZShirtTorn", sleeve_mat="Mat_ZShirtTorn",
        pants_mat="Mat_DenimBlue", skin_mat="Mat_ZSkinBruised",
        stain_mat="Mat_ZBoilDark", body_type="bloater",
        bare_arm_L=True, bare_arm_R=True, torn_pant_L=True,
        arm_bulk_L=1.10, arm_bulk_R=1.10, torso_stain="bloater_belly",
    )
    s = T["s"]

    # Snapped overall straps resting cleanly high on shoulders (clear of bloated lower gut)
    _tag(add_box(bm, center=(0.105 * s, -0.118 * s, 1.405 * s), size=(0.036 * s, 0.016 * s, 0.095 * s),
                 rot=(-0.18, 0.0, -0.10), mat_idx=idx_map["Mat_DenimBlue"]), regions, "torso")
    _tag(add_box(bm, center=(-0.105 * s, -0.122 * s, 1.390 * s), size=(0.036 * s, 0.016 * s, 0.115 * s),
                 rot=(-0.18, 0.0, 0.14), mat_idx=idx_map["Mat_DenimBlue"]), regions, "torso")
    # Clustered glowing volatile gas pustules erupting organically from distended gut & hunchback
    boils = (
        ((-0.072, -0.256, 1.075), 0.044, "Mat_ZBoilDark"),
        ((-0.055, -0.270, 1.090), 0.030, "Mat_ZBoilGlow"),
        (( 0.068, -0.246, 1.135), 0.040, "Mat_ZBoilDark"),
        (( 0.082, -0.260, 1.150), 0.028, "Mat_ZBoilGlow"),
        (( 0.010, -0.268, 1.020), 0.036, "Mat_ZBoilGlow"),
        ((-0.118, -0.205, 1.185), 0.034, "Mat_ZBoilDark"),
        (( 0.135, -0.175, 1.230), 0.032, "Mat_ZBoilGlow"),
        (( 0.092,  0.178, 1.385), 0.042, "Mat_ZBoilDark"),
        (( 0.105,  0.192, 1.398), 0.028, "Mat_ZBoilGlow"),
        ((-0.075,  0.172, 1.320), 0.034, "Mat_ZBoilGlow"),
    )
    for pos, rad, bmat in boils:
        _tag(add_box(
            bm,
            center=(pos[0] * s, pos[1] * s, pos[2] * s),
            size=(rad * s, rad * s, rad * s),
            rot=(0.4, 0.3, 0.25),
            bevel=rad * 0.26 * s,
            mat_idx=idx_map[bmat],
        ), regions, "torso")

    body_obj, body_tris, arm_obj = _finalize_zombie("Zombie_Bloater_Boomer", bm, materials, regions, P, col_char, col_rig)
    return body_obj, body_tris, arm_obj, []


# ---------------------------------------------------------------------------
# 6. JUGGERNAUT BRUTE (2.26 m) - Giant Crusher Arm w/ Bone Spikes, Rebar, Skill: Ground Slam
# ---------------------------------------------------------------------------
def build_zombie_juggernaut_brute(materials, idx_map, col_char, col_gear, col_rig):
    P = make_proportions(height=2.26, female=False, shoulder_scale=1.34)
    bm = bmesh.new()
    regions = {}

    build_zombie_head(
        bm, idx_map, regions, P, gender="male",
        skin_mat="Mat_ZSkinBruised", hair_mat="Mat_HairBlack",
        headgear="juggernaut_scarred", jaw_open=0.020, gaunt=0.45,
        head_scale_xy=1.22, asym_wound="brow_scar", blood_chin=True,
    )
    T = _build_zombie_base(
        bm, idx_map, regions, P,
        shirt_mat="Mat_ZRiotNavy", sleeve_mat="Mat_ZRiotNavy",
        pants_mat="Mat_ZClothDirty", skin_mat="Mat_ZSkinBruised",
        boot_mat="Mat_BootSole", body_type="juggernaut",
        bare_arm_L=True, bare_arm_R=True, torn_pant_R=True,
        arm_bulk_L=1.22, arm_bulk_R=1.68, hand_bulk_L=1.20, hand_bulk_R=1.55,
        torso_stain="juggernaut_rips",
    )
    s = T["s"]
    sh_x = P["arm"][0]

    # Shredded SWAT chest armor fragments + left tactical shoulder pauldron + heavy knee guard
    _tag(add_box(bm, center=(0.042 * s, -0.155 * s, 1.320 * s), size=(0.185 * s, 0.040 * s, 0.220 * s),
                 rot=(-0.06, 0.0, 0.08), taper_top=(0.86, 1.0), mat_idx=idx_map["Mat_ZRiotArmor"]), regions, "torso")
    _tag(add_box(bm, center=(0.0, 0.165 * s, 1.290 * s), size=(0.285 * s, 0.042 * s, 0.295 * s),
                 taper_top=(0.88, 1.0), mat_idx=idx_map["Mat_ZRiotArmor"]), regions, "torso")
    _tag(add_box(bm, center=(sh_x + 0.015 * s, 0.008 * s, P["arm"][2] + 0.088 * s),
                 size=(0.175 * s, 0.185 * s, 0.068 * s), rot=(0.0, 0.28, 0.0),
                 taper_top=(0.82, 0.86), mat_idx=idx_map["Mat_ZRiotArmor"]), regions, "arm_L")
    _tag(add_box(bm, center=(-T["hx"], -0.100 * s, P["knee"][2]), size=(0.138 * s, 0.042 * s, 0.140 * s),
                 taper_top=(0.86, 0.90), mat_idx=idx_map["Mat_ZRiotArmor"]), regions, "shin_rigid_R")

    # Sculpted bone spikes erupting organically from the mutated right crusher arm (-X)
    elb_x = P["elbow"][0]
    wri_x = P["wrist"][0]
    ay, az = P["arm"][1], P["arm"][2]
    for sx_off, sp_dir, len_sp, r_sp in (
        (elb_x - 0.02 * s, ( 0.04, 0.10,  0.14), 0.115 * s, 0.024 * s),
        (elb_x + 0.06 * s, (-0.03, 0.08,  0.13), 0.095 * s, 0.020 * s),
        (0.5 * (elb_x + wri_x), (-0.02, -0.04, 0.12), 0.085 * s, 0.018 * s),
        (wri_x - 0.05 * s, (-0.04, 0.05,  0.10), 0.072 * s, 0.015 * s),
    ):
        base = (-sx_off, ay, az + 0.048 * s)
        d = Vector(sp_dir).normalized() * len_sp
        tip = (base[0] + d.x, base[1] + d.y, base[2] + d.z)
        _tag(add_cone(bm, base, tip, r_sp * 1.18, segments=6, mat_idx=idx_map["Mat_ZFlesh"]), regions, "arm_R")
        _tag(add_cone(bm, (base[0] + d.x * 0.12, base[1] + d.y * 0.12, base[2] + d.z * 0.12),
                      tip, r_sp * 0.90, segments=6, mat_idx=idx_map["Mat_ZBone"]), regions, "arm_R")

    body_obj, body_tris, arm_obj = _finalize_zombie("Zombie_Juggernaut_Brute", bm, materials, regions, P, col_char, col_rig)
    gear_items = []

    # Detachable Rebar + concrete chunk impaled into right upper back/shoulder
    bm_reb = bmesh.new()
    add_cylinder(bm_reb, (-0.135 * s, 0.075 * s, 1.320 * s), (-0.275 * s, 0.235 * s, 1.720 * s),
                 0.016 * s, 0.013 * s, segments=6, mat_idx=idx_map["Mat_ZRebar"])
    add_cylinder(bm_reb, (-0.125 * s, -0.095 * s, 1.265 * s), (-0.145 * s, 0.085 * s, 1.330 * s),
                 0.015 * s, 0.015 * s, segments=6, mat_idx=idx_map["Mat_ZFlesh"])
    add_box(bm_reb, center=(-0.265 * s, 0.225 * s, 1.690 * s), size=(0.098 * s, 0.090 * s, 0.080 * s),
            rot=(0.35, -0.42, 0.22), mat_idx=idx_map["Mat_WorkGrey"])
    reb_obj, reb_t = finalize_mesh("Zombie_Juggernaut_Brute_Rebar", bm_reb, materials, collection=col_gear)
    apply_box_uvs(reb_obj, tex_scale=3.2)
    bake_character_vertex_ao(reb_obj, style="zombie")
    attach_gear_to_bone(reb_obj, arm_obj, "mixamorig:Spine2")
    gear_items.append((reb_obj, reb_t))

    return body_obj, body_tris, arm_obj, gear_items


ZOMBIE_BUILDERS = [
    ("crawler_stalker",   build_zombie_crawler_stalker),
    ("walker_shambler",   build_zombie_walker_shambler),
    ("banshee_screamer",  build_zombie_banshee_screamer),
    ("spitter_hazmat",    build_zombie_spitter_hazmat),
    ("bloater_boomer",    build_zombie_bloater_boomer),
    ("juggernaut_brute",  build_zombie_juggernaut_brute),
]

ZOMBIE_SKILL_MAP = {
    "crawler_stalker":   "pounce",
    "walker_shambler":   "bite",
    "banshee_screamer":  "shriek",
    "spitter_hazmat":    "spit",
    "bloater_boomer":    "detonate",
    "juggernaut_brute":  "slam",
}
