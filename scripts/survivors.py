"""Batch 1: Five Playable Survivors (Jake, Maya, Rico, Lena, Tom) with signature gear & universal weapons."""
import math
import bpy
import bmesh
from mathutils import Vector

from head_sculpt import build_character_head
from mesh_utils import (
    add_box,
    add_cloth_creases,
    add_cylinder,
    finalize_mesh,
    loft_rings,
    ring_ellipse,
    ring_perp,
    ring_yz,
)
from rig_mixamo import (
    attach_gear_to_bone,
    create_mixamo_armature,
    create_weapon_sockets,
    hold,
    make_proportions,
    skin_body_to_armature,
)
from rig_controls import build_control_rig
from weapons import (
    ALL_WEAPON_BUILDERS,
    build_weapon_knife,
    build_weapon_pistol,
)

WEAPON_BUILDERS_MAP = {wid: fn for wid, fn, _ in ALL_WEAPON_BUILDERS}


def _tag(verts, regions, name):
    regions.setdefault(name, []).extend(verts)


def _perp_chain_rings(pts, radii_up_side, up_hint=(0.0, 0.0, 1.0), n=6):
    """Build a list of cross-section rings perpendicular to the polyline `pts`."""
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


def _build_sculpted_hand(bm, mat_idx, regions, P, side, sx, skin_mat, glove_mat):
    """Build anatomical low-poly hand: arched palm, thenar pad, perpendicular-ring thumb & fingers."""
    s = P["scale"]
    wri_x = P["wrist"][0]
    hand_end_x = P["hand_end"][0]
    arm_y = P["arm"][1]
    arm_z = P["arm"][2]

    # 1. Sculpted 6-ring wrist-to-knuckle palm loft (n=8, overlaps 3 cm inside forearm cuff)
    palm_specs = [
        (wri_x - 0.032 * s, arm_y,            arm_z,            0.023 * s, 0.015 * s),  # inside cuff
        (wri_x - 0.004 * s, arm_y,            arm_z,            0.025 * s, 0.014 * s),  # wrist crease
        (wri_x + 0.020 * s, arm_y - 0.004*s,  arm_z + 0.001*s,  0.033 * s, 0.016 * s),  # mid metacarpal arch
        (wri_x + 0.048 * s, arm_y - 0.006*s,  arm_z + 0.002*s,  0.035 * s, 0.016 * s),  # palm pad
        (hand_end_x - 0.010*s, arm_y - 0.006*s, arm_z + 0.001*s, 0.035 * s, 0.015 * s), # knuckle ridge
        (hand_end_x + 0.004*s, arm_y - 0.006*s, arm_z - 0.001*s, 0.031 * s, 0.012 * s), # distal web
    ]
    palm_rings = [ring_yz(sx * px, py, pz, ry, rz, n=8, squash_top=1.08, squash_bot=0.90)
                  for (px, py, pz, ry, rz) in palm_specs]
    if sx < 0:
        palm_rings = list(reversed(palm_rings))
    v_palm = loft_rings(bm, palm_rings, close_caps=(True, True), mat_idx=mat_idx[glove_mat])
    for f in {f for v in v_palm for f in v.link_faces}:
        if abs(f.calc_center_median().x) < wri_x - 0.006 * s:
            f.material_index = mat_idx[skin_mat]
    _tag(v_palm, regions, f"hand_{side}")

    # 2. Five individual low-poly fingers (Index, Middle, Ring, Pinky via ring_perp)
    finger_specs = [
        ("index",  [(0.0086, 0.0086), (0.0076, 0.0076), (0.0066, 0.0066), (0.0054, 0.0054)]),
        ("middle", [(0.0088, 0.0088), (0.0078, 0.0078), (0.0068, 0.0068), (0.0055, 0.0055)]),
        ("ring",   [(0.0082, 0.0082), (0.0072, 0.0072), (0.0063, 0.0063), (0.0051, 0.0051)]),
        ("pinky",  [(0.0072, 0.0072), (0.0063, 0.0063), (0.0054, 0.0054), (0.0044, 0.0044)]),
    ]
    for fname, f_rad in finger_specs:
        pts = P[fname]
        spine = [
            (sx * (pts[0][0] - 0.010 * s), pts[0][1], pts[0][2]),
            (sx * pts[1][0], pts[1][1], pts[1][2] - 0.001 * s),
            (sx * pts[2][0], pts[2][1], pts[2][2] - 0.002 * s),
            (sx * pts[3][0], pts[3][1], pts[3][2] - 0.003 * s),
        ]
        scaled_rad = [(ru * s, rs * s) for (ru, rs) in f_rad]
        v_fin = loft_rings(bm, _perp_chain_rings(spine, scaled_rad, n=5),
                           close_caps=(True, True), mat_idx=mat_idx[skin_mat])
        if glove_mat != skin_mat:
            for f in {f for v in v_fin for f in v.link_faces}:
                if abs(f.calc_center_median().x) < pts[1][0]:
                    f.material_index = mat_idx[glove_mat]
        _tag(v_fin, regions, f"{fname}_{side}")

    # 4. Compact Opposable Thumb + Fleshy Thenar Pad via ring_perp (zero paper-ribbon flattening!)
    t_pts = P["thumb"]
    t_spine = [
        (sx * (wri_x + 0.008 * s), arm_y - 0.005 * s, arm_z - 0.002 * s),  # inside palm thenar base
        (sx * t_pts[0][0], t_pts[0][1], t_pts[0][2]),                      # CMC joint
        (sx * t_pts[1][0], t_pts[1][1], t_pts[1][2]),                      # MCP knuckle
        (sx * t_pts[2][0], t_pts[2][1], t_pts[2][2]),                      # IP joint
        (sx * t_pts[3][0], t_pts[3][1], t_pts[3][2]),                      # Tip
    ]
    t_radii = [
        (0.0135 * s, 0.0155 * s),
        (0.0115 * s, 0.0130 * s),
        (0.0096 * s, 0.0102 * s),
        (0.0080 * s, 0.0084 * s),
        (0.0062 * s, 0.0066 * s),
    ]
    v_th = loft_rings(bm, _perp_chain_rings(t_spine, t_radii, n=6),
                      close_caps=(True, True), mat_idx=mat_idx[skin_mat])
    if glove_mat != skin_mat:
        for f in {f for v in v_th for f in v.link_faces}:
            if f.calc_center_median().y > t_pts[1][1] + 0.004 * s:
                f.material_index = mat_idx[glove_mat]
    # Base ring blends with palm/hand, distal rings drive via thumb bone chain
    for v in v_th:
        if abs(v.co.x) < t_pts[0][0] - 0.004 * s:
            _tag([v], regions, f"hand_{side}")
        else:
            _tag([v], regions, f"thumb_{side}")


def _char_label(base, gender):
    return f"{base}_{'Female' if gender == 'female' else 'Male'}"


def _build_base_torso_and_arms(
    bm, mat_idx, regions, P,
    shirt_mat, sleeve_mat, pants_mat, skin_mat, glove_mat="Mat_BeltLeather",
    boot_mat="Mat_Boots", sole_mat="Mat_BootSole",
    plaid_mat=None, forearm_skin_L=False, forearm_bandage_L=False,
):
    """Build shared parametric torso, 3-loop joints, sculpted hands, pants, and boots.

    Returns torso/limb scale dictionary T so role outfits & gear fit both genders cleanly.
    """
    s = P["scale"]
    sh_s = P["shoulder_scale"]
    fem = P["female"]
    tx = (0.78 if fem else 1.0) * s
    ty = (0.84 if fem else 1.0) * s

    # Torso loft (Z = 0.90*s .. 1.482*s): male athletic V-taper vs sculpted female hourglass w/ integrated bust
    if fem:
        pelvis_rx = 0.158 * s
        waist_rx = 0.098 * s
        mid_rx = 0.122 * s
        chest_rx = 0.144 * s
        top_rx = 0.136 * sh_s * s
        r_pelvis = ring_ellipse(0.0, 0.006 * s, 0.900 * s, pelvis_rx, 0.110 * s, n=12, squash_front=0.92, squash_back=1.24)
        r_waist  = ring_ellipse(0.0, 0.006 * s, 1.045 * s, waist_rx,  0.076 * s, n=12, squash_front=0.90, squash_back=1.08)
        r_under  = ring_ellipse(0.0, 0.008 * s, 1.205 * s, mid_rx,    0.088 * s, n=12, squash_front=0.98, squash_back=1.06)
        r_bust   = ring_ellipse(0.0, 0.006 * s, 1.300 * s, chest_rx,  0.112 * s, n=12, squash_front=1.16, squash_back=1.06)
        r_upper  = ring_ellipse(0.0, 0.010 * s, 1.380 * s, chest_rx * 0.97, 0.094 * s, n=12, squash_front=1.02, squash_back=1.06)
        r_shldr  = ring_ellipse(0.0, 0.012 * s, 1.452 * s, top_rx,    0.080 * s, n=12, squash_front=0.88, squash_back=1.04)
        r_neck   = ring_ellipse(0.0, 0.014 * s, 1.482 * s, 0.056 * s, 0.054 * s, n=12)
        # Subtle integrated sternum valley & twin bust projection (ring_ellipse n=12: 9=-Y center, 8/10=±30° bust)
        for ring, proj, stern in ((r_bust, 0.013 * s, 0.010 * s), (r_upper, 0.006 * s, 0.005 * s)):
            ring[8]  = (ring[8][0],  ring[8][1]  - proj,  ring[8][2])
            ring[10] = (ring[10][0], ring[10][1] - proj,  ring[10][2])
            ring[9]  = (ring[9][0],  ring[9][1]  + stern, ring[9][2])
        shirt_rings = [r_pelvis, r_waist, r_under, r_bust, r_upper, r_shldr, r_neck]
    else:
        pelvis_rx = 0.156 * s
        waist_rx = 0.150 * s
        mid_rx = 0.165 * s
        chest_rx = 0.186 * s
        top_rx = 0.166 * sh_s * s
        shirt_rings = [
            ring_ellipse(0.0, 0.004 * s, 0.910 * s, pelvis_rx, 0.104 * ty, n=12, squash_front=0.95, squash_back=1.05),
            ring_ellipse(0.0, 0.006 * s, 1.030 * s, waist_rx,  0.102 * ty, n=12, squash_front=0.95, squash_back=1.05),
            ring_ellipse(0.0, 0.010 * s, 1.180 * s, mid_rx,    0.112 * ty, n=12, squash_front=0.96, squash_back=1.06),
            ring_ellipse(0.0, 0.012 * s, 1.325 * s, chest_rx,  0.122 * ty, n=12, squash_front=0.96, squash_back=1.06),
            ring_ellipse(0.0, 0.014 * s, 1.455 * s, top_rx,    0.102 * ty, n=12, squash_front=0.92, squash_back=1.05),
            ring_ellipse(0.0, 0.015 * s, 1.482 * s, 0.074 * s, 0.068 * ty, n=12),
        ]
    v_torso = loft_rings(bm, shirt_rings, close_caps=(True, True), mat_idx=mat_idx[shirt_mat])
    _tag(v_torso, regions, "torso")

    # Flush V-neck skin zone + optional plaid pattern
    torso_faces = {f for v in v_torso for f in v.link_faces}
    for f in torso_faces:
        cen = f.calc_center_median()
        if cen.z > 1.425 * s and abs(cen.x) < 0.044 * s and cen.y < -0.045 * s:
            f.material_index = mat_idx[skin_mat]
        elif plaid_mat is not None and 0.94 * s < cen.z < 1.44 * s:
            iz = int(cen.z / (0.095 * s))
            ix = int((cen.x + 0.30) / (0.065 * s))
            if (iz + ix) % 2 == 0:
                f.material_index = mat_idx[plaid_mat[0]]
            elif iz % 3 == 0:
                f.material_index = mat_idx[plaid_mat[1]]

    # Arms + 3-loop shoulder/elbow topology + sculpted hands
    sh_x = P["arm"][0]
    arm_x0 = sh_x - 0.048 * s
    arm_x1 = sh_x + 0.038 * s
    elb_x = P["elbow"][0]
    wri_x = P["wrist"][0]
    cuff_x = wri_x - 0.018 * s
    arm_y = P["arm"][1]
    arm_z = P["arm"][2]
    r_arm = (0.043 if fem else 0.064) * s
    r_elb = (0.036 if fem else 0.054) * s
    r_wri = (0.025 if fem else 0.039) * s

    for side, sx in (("L", 1.0), ("R", -1.0)):
        # 9-ring sleeve with deltoid shoulder overlap + 3-loop elbow + multi-ring forearm twist zone
        sleeve_specs = [
            (arm_x0,                         arm_y,            arm_z - 0.004 * s, r_arm * 1.05, r_arm * 1.08),  # torso overlap
            (sh_x,                           arm_y,            arm_z,             r_arm * 1.04, r_arm * 1.06),  # shoulder pivot
            (arm_x1,                         arm_y + 0.002*s,  arm_z,             r_arm * 0.98, r_arm * 0.98),  # upper bicep
            (elb_x - 0.028 * s,              P["elbow"][1],    arm_z,             r_elb * 1.04, r_elb * 1.04),  # elbow loop -1
            (elb_x,                          P["elbow"][1],    arm_z,             r_elb,        r_elb),         # elbow center
            (elb_x + 0.028 * s,              P["elbow"][1],    arm_z,             r_elb * 0.98, r_elb * 0.98),  # elbow loop +1
            (0.50 * elb_x + 0.50 * cuff_x,   arm_y + 0.003*s,  arm_z,             r_elb * 0.86, r_elb * 0.80),  # mid forearm
            (0.25 * elb_x + 0.75 * cuff_x,   arm_y + 0.001*s,  arm_z,             r_wri * 0.88, r_wri * 0.76),  # lower twist ring
            (cuff_x,                         arm_y,            arm_z,             r_wri * 0.72, r_wri * 0.56),  # tapered wrist cuff
        ]
        rings = [ring_yz(sx * ax, cy, cz, ry, rz, n=8) for (ax, cy, cz, ry, rz) in sleeve_specs]
        if sx < 0:
            rings = list(reversed(rings))
        v_slv = loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_idx[sleeve_mat])
        _tag(v_slv, regions, f"arm_{side}")

        slv_faces = {f for v in v_slv for f in v.link_faces}
        for f in slv_faces:
            cen = f.calc_center_median()
            if forearm_skin_L and abs(cen.x) > elb_x - 0.01 * s:
                f.material_index = mat_idx[skin_mat]
            elif plaid_mat is not None:
                ib = int(abs(cen.x) / (0.075 * s))
                if ib % 2 == 0:
                    f.material_index = mat_idx[plaid_mat[0]]

        if forearm_bandage_L and side == "L":
            band = [
                ring_yz((elb_x + 0.08 * s), arm_y + 0.002 * s, arm_z, r_elb * 0.96, r_elb * 0.96, n=8),
                ring_yz((cuff_x - 0.02 * s), arm_y, arm_z, r_wri * 1.05, r_wri * 0.98, n=8),
            ]
            _tag(loft_rings(bm, band, close_caps=(True, True), mat_idx=mat_idx["Mat_Bandage"]), regions, "arm_L")

        # Continuous wrist-to-palm + sculpted fingers & thumb
        _build_sculpted_hand(bm, mat_idx, regions, P, side, sx, skin_mat, glove_mat)

    # Pelvis & Legs with 3-loop knee joint topology
    hx = P["hip"][0]
    pelvis_rings = [
        ring_ellipse(0.0, 0.004 * s, 0.785 * s, (0.148 if fem else 0.148) * s, (0.106 if fem else 0.098) * s, n=10, squash_back=1.18 if fem else 1.02),
        ring_ellipse(0.0, 0.006 * s, 0.870 * s, pelvis_rx + (0.008 if fem else 0.004) * s, (0.112 if fem else 0.104) * s, n=10, squash_back=1.24 if fem else 1.04),
        ring_ellipse(0.0, 0.004 * s, 0.945 * s, (0.132 if fem else 0.144) * s, (0.090 if fem else 0.096) * s, n=10),
    ]
    _tag(loft_rings(bm, pelvis_rings, close_caps=(True, True), mat_idx=mat_idx[pants_mat]), regions, "hips_soft")

    r_th = (0.076 if fem else 0.090) * s
    r_kn = (0.054 if fem else 0.074) * s
    r_ankle = (0.044 if fem else 0.058) * s
    kn_z = P["knee"][2]
    for side, sx in (("L", 1.0), ("R", -1.0)):
        leg_rings = [
            ring_ellipse(sx * hx,        0.016 * s, 0.185 * s,       r_ankle,      r_ankle * 1.12, n=8),
            ring_ellipse(sx * hx,        0.010 * s, 0.305 * s,       r_kn * 0.92,  r_kn * 1.02,  n=8),
            ring_ellipse(sx * hx,       -0.002 * s, kn_z - 0.036 * s, r_kn * 0.98, r_kn * 1.04,  n=8),
            ring_ellipse(sx * hx,       -0.004 * s, kn_z,            r_kn,         r_kn * 1.06,  n=8),
            ring_ellipse(sx * hx,       -0.003 * s, kn_z + 0.036 * s, r_kn * 1.05, r_kn * 1.12,  n=8),
            ring_ellipse(sx * hx,       -0.002 * s, 0.680 * s,       r_th * 0.92,  r_th,         n=8),
            ring_ellipse(sx * hx * 0.94, 0.002 * s, 0.865 * s,       r_th * 1.04 if fem else r_th, r_th * (1.10 if fem else 1.06), n=8),
            ring_ellipse(sx * hx * 0.90, 0.004 * s, 0.925 * s,       r_th * 0.94,  r_th * 1.02,  n=8),
        ]
        v_leg = loft_rings(bm, leg_rings, close_caps=(True, True), mat_idx=mat_idx[pants_mat])
        add_cloth_creases(bm, [v for v in v_leg if 0.25 * s < v.co.z < 0.88 * s and abs(v.co.z - kn_z) > 0.05 * s],
                          strength=0.0022 * s, seed=29)
        _tag(v_leg, regions, f"leg_{side}")

        # Combat / work boot seated at Z = 0.00 (sleeker tapered profile on female)
        bw = (0.045 if fem else 0.056) * s
        shaft = [
            ring_ellipse(sx * hx, 0.018 * s, 0.065 * s, bw,        bw * 1.24, n=8),
            ring_ellipse(sx * hx, 0.018 * s, 0.145 * s, bw * 1.06, bw * 1.24, n=8),
            ring_ellipse(sx * hx, 0.016 * s, 0.220 * s, bw * 1.12, bw * 1.26, n=8),
        ]
        _tag(loft_rings(bm, shaft, close_caps=(True, True), mat_idx=mat_idx[boot_mat]), regions, f"boot_shaft_{side}")
        _tag(add_box(
            bm, center=(sx * hx, -0.044 * s, 0.052 * s),
            size=((0.082 if fem else 0.102) * s, (0.194 if fem else 0.215) * s, (0.056 if fem else 0.064) * s),
            bevel=0.007 * s, taper_top=(0.82 if fem else 0.86, 0.86 if fem else 0.90),
            mat_idx=mat_idx[boot_mat],
        ), regions, f"foot_{side}")
        _tag(add_box(
            bm, center=(sx * hx, -0.078 * s, 0.011 * s),
            size=((0.088 if fem else 0.110) * s, (0.138 if fem else 0.156) * s, (0.022 if fem else 0.026) * s),
            mat_idx=mat_idx[sole_mat],
        ), regions, f"foot_{side}")
        _tag(add_box(
            bm, center=(sx * hx, 0.034 * s, (0.019 if fem else 0.017) * s),
            size=((0.084 if fem else 0.108) * s, (0.060 if fem else 0.070) * s, (0.038 if fem else 0.034) * s),
            mat_idx=mat_idx[sole_mat],
        ), regions, f"foot_{side}")

    return {
        "s": s,
        "sh_s": sh_s,
        "fem": fem,
        "tx": tx,
        "ty": ty,
        "pelvis_rx": pelvis_rx,
        "waist_rx": waist_rx,
        "mid_rx": mid_rx,
        "chest_rx": chest_rx,
        "top_rx": top_rx,
        "r_arm": r_arm,
        "r_th": r_th,
        "hx": hx,
    }


def _finalize_character(name, bm, materials, regions, P, collection_char, collection_rig):
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    region_indices = {k: {v.index for v in vlist if v.is_valid} for k, vlist in regions.items()}

    body_obj, body_tris = finalize_mesh(f"{name}_Body", bm, materials, collection=collection_char)
    arm_obj, specs = create_mixamo_armature(collection=collection_rig, proportions=P)
    arm_obj.name = f"{name}_Armature"
    skin_body_to_armature(body_obj, arm_obj, specs, region_indices)
    build_control_rig(arm_obj, P)
    create_weapon_sockets(arm_obj, P, collection_rig)
    return body_obj, body_tris, arm_obj


def equip_weapon(arm_obj, weapon_id, materials, idx_map, collection=None, clear_existing=True):
    """Equip any of the 17 canonical weapons onto any survivor's `RightHand`/`LeftHand` sockets."""
    if clear_existing:
        for child in list(arm_obj.children):
            if child.type == "MESH" and "_Weapon_" in child.name:
                bpy.data.objects.remove(child, do_unlink=True)

    prefix = arm_obj.name[:-9] if arm_obj.name.endswith("_Armature") else arm_obj.name
    col = collection or (arm_obj.users_collection[0] if arm_obj.users_collection else bpy.context.scene.collection)

    if weapon_id in ("compound_bow", "bow", "arrow"):
        bow_obj, bow_t = WEAPON_BUILDERS_MAP["compound_bow"](
            materials, idx_map, collection=col, name=f"{prefix}_Weapon_Bow"
        )
        hold(bow_obj, arm_obj, "mixamorig:LeftHand", grip_world=tuple(arm_obj["left_grip_rest"]), hand="Left")
        arr_obj, arr_t = WEAPON_BUILDERS_MAP["arrow"](
            materials, idx_map, collection=col, name=f"{prefix}_Weapon_Arrow"
        )
        hold(arr_obj, arm_obj, "mixamorig:RightHand", grip_world=tuple(arm_obj["arrow_grip_rest"]), hand="Right")
        arm_obj["weapon_id"] = "arrow"
        arm_obj["weapon_hold_hand"] = "Right"
        return [(bow_obj, bow_t), (arr_obj, arr_t)]

    builder = WEAPON_BUILDERS_MAP.get(weapon_id)
    if builder is None:
        raise ValueError(f"Unknown weapon_id: {weapon_id!r}")
    wep_obj, wep_t = builder(materials, idx_map, collection=col, name=f"{prefix}_Weapon_{weapon_id}")
    hold(wep_obj, arm_obj, "mixamorig:RightHand", grip_world=tuple(arm_obj["right_grip_rest"]), hand="Right")
    arm_obj["weapon_id"] = weapon_id
    arm_obj["weapon_hold_hand"] = "Right"
    return [(wep_obj, wep_t)]


# ---------------------------------------------------------------------------
# 1. JAKE (Male 1.80 m / Female 1.70 m) - Olive Military, Plate Carrier, 3 Mag Pouches, Radio, Dog Tags, Backpack, M4 + Pistol
# ---------------------------------------------------------------------------
def build_jake(materials, idx_map, col_char, col_gear, col_rig, gender="male"):
    is_fem = (gender == "female")
    P = make_proportions(height=1.70 if is_fem else 1.80, female=is_fem)
    label = _char_label("Jake", gender)
    bm = bmesh.new()
    regions = {}

    build_character_head(
        bm, idx_map, regions, P, gender=gender,
        skin_mat="Mat_SkinWarm", hair_mat="Mat_HairBrown",
        lip_mat="Mat_LipWarm" if is_fem else "Mat_Lip",
        headgear="cap", beard="none" if is_fem else "full",
        ponytail=is_fem, ponytail_tie="Mat_OliveDark",
        face_hair="bangs_side" if is_fem else "none",
    )
    T = _build_base_torso_and_arms(
        bm, idx_map, regions, P,
        shirt_mat="Mat_OliveMil", sleeve_mat="Mat_OliveMil",
        pants_mat="Mat_OliveDark", skin_mat="Mat_SkinWarm",
        glove_mat="Mat_LeatherDark", forearm_skin_L=True,
    )
    s, ty, hx = T["s"], T["ty"], T["hx"]
    wx = 0.78 if is_fem else 1.0

    # Plate carrier vest: compact contoured chest rig on female to clearly reveal slender hourglass waist
    if is_fem:
        _tag(add_box(bm, center=(0.0, -0.124 * s, 1.310 * s), size=(0.188 * s, 0.034 * s, 0.188 * s),
                     rot=(-0.10, 0.0, 0.0), taper_top=(0.86, 1.0), mat_idx=idx_map["Mat_CoyoteTan"]), regions, "torso")
        _tag(add_box(bm, center=(0.0, 0.112 * s, 1.295 * s), size=(0.188 * s, 0.032 * s, 0.220 * s),
                     taper_top=(0.88, 1.0), mat_idx=idx_map["Mat_CoyoteTan"]), regions, "torso")
        for sx in (1.0, -1.0):
            _tag(add_box(bm, center=(sx * 0.074 * s, 0.002 * s, 1.442 * s), size=(0.042 * s, 0.196 * s, 0.026 * s),
                         mat_idx=idx_map["Mat_CoyoteTan"]), regions, "torso")
        for mx in (-0.054, 0.0, 0.054):
            _tag(add_box(bm, center=(mx * s, -0.118 * s, 1.195 * s), size=(0.044 * s, 0.026 * s, 0.088 * s),
                         rot=(-0.12, 0.0, 0.0), mat_idx=idx_map["Mat_OliveDark"]), regions, "torso")
        _tag(add_box(bm, center=(0.082 * s, -0.128 * s, 1.375 * s), size=(0.036 * s, 0.024 * s, 0.074 * s),
                     mat_idx=idx_map["Mat_GunPolymer"]), regions, "torso")
        _tag(add_cylinder(bm, (0.090 * s, -0.128 * s, 1.412 * s), (0.098 * s, -0.124 * s, 1.545 * s),
                          0.004 * s, 0.003 * s, segments=5, mat_idx=idx_map["Mat_GunMetal"]), regions, "torso")
        _tag(add_box(bm, center=(0.010 * s, -0.102 * s, 1.405 * s), size=(0.020 * s, 0.006 * s, 0.028 * s),
                     rot=(-0.10, 0.0, 0.12), mat_idx=idx_map["Mat_GunSteel"]), regions, "torso")
    else:
        _tag(add_box(bm, center=(0.0, -0.120 * ty, 1.245 * s), size=(0.255 * wx * s, 0.042 * ty, 0.295 * s),
                     taper_top=(0.86, 1.0), mat_idx=idx_map["Mat_CoyoteTan"]), regions, "torso")
        _tag(add_box(bm, center=(0.0, 0.128 * ty, 1.245 * s), size=(0.250 * wx * s, 0.036 * ty, 0.295 * s),
                     taper_top=(0.88, 1.0), mat_idx=idx_map["Mat_CoyoteTan"]), regions, "torso")
        for sx in (1.0, -1.0):
            _tag(add_box(bm, center=(sx * 0.105 * wx * s, 0.005 * ty, 1.440 * s), size=(0.056 * wx * s, 0.220 * ty, 0.032 * s),
                         mat_idx=idx_map["Mat_CoyoteTan"]), regions, "torso")
        for mx in (-0.075, 0.0, 0.075):
            _tag(add_box(bm, center=(mx * wx * s, -0.148 * ty, 1.155 * s), size=(0.058 * wx * s, 0.034 * ty, 0.110 * s),
                         mat_idx=idx_map["Mat_OliveDark"]), regions, "torso")
        _tag(add_box(bm, center=(0.112 * wx * s, -0.144 * ty, 1.355 * s), size=(0.044 * s, 0.032 * s, 0.088 * s),
                     mat_idx=idx_map["Mat_GunPolymer"]), regions, "torso")
        _tag(add_cylinder(bm, (0.122 * wx * s, -0.144 * ty, 1.398 * s), (0.132 * wx * s, -0.140 * ty, 1.545 * s),
                          0.004 * s, 0.003 * s, segments=5, mat_idx=idx_map["Mat_GunMetal"]), regions, "torso")
        _tag(add_box(bm, center=(0.012 * s, -0.116 * ty, 1.395 * s), size=(0.022 * s, 0.006 * s, 0.032 * s),
                     rot=(-0.10, 0.0, 0.12), mat_idx=idx_map["Mat_GunSteel"]), regions, "torso")

    # Tactical belt & cargo pockets (snug hip contour on female)
    belt_rx = (0.142 if is_fem else 0.170) * s
    belt_ry = (0.098 if is_fem else 0.116) * s
    belt = [ring_ellipse(0.0, 0.004 * s, 0.915 * s, belt_rx, belt_ry, n=10),
            ring_ellipse(0.0, 0.004 * s, 0.970 * s, belt_rx, belt_ry, n=10)]
    _tag(loft_rings(bm, belt, close_caps=(True, True), mat_idx=idx_map["Mat_BeltLeather"]), regions, "hips_rigid")
    th_x = hx + T["r_th"] * 0.90
    for sx in (1.0, -1.0):
        _tag(add_box(bm, center=(sx * th_x, 0.005 * s, 0.695 * s), size=(0.034 * s, 0.095 * s, 0.140 * s),
                     mat_idx=idx_map["Mat_OliveMil"]), regions, f"thigh_rigid_{'L' if sx > 0 else 'R'}")
    # Thigh pistol holster & leg strap on right thigh (-X)
    _tag(add_box(bm, center=(-(th_x + 0.004 * s), -0.014 * s, 0.775 * s), size=(0.040 * s, 0.064 * s, 0.115 * s),
                 mat_idx=idx_map["Mat_LeatherDark"]), regions, "thigh_rigid_R")
    _tag(loft_rings(bm, [
        ring_ellipse(-hx, 0.0, 0.760 * s, T["r_th"] * 0.98, T["r_th"] * 1.05, n=8),
        ring_ellipse(-hx, 0.0, 0.790 * s, T["r_th"] * 0.98, T["r_th"] * 1.05, n=8),
    ], close_caps=(True, True), mat_idx=idx_map["Mat_BeltLeather"]), regions, "thigh_rigid_R")

    body_obj, body_tris, arm_obj = _finalize_character(label, bm, materials, regions, P, col_char, col_rig)
    gear_items = []

    # Backpack with sleeping roll (attached to Spine2)
    bm_bp = bmesh.new()
    bp_y = 0.185 * s if is_fem else 0.228 * s
    add_box(bm_bp, center=(0.0, bp_y, 1.245 * s), size=(0.245 * wx * s, 0.135 * ty, 0.375 * s),
            bevel=0.014 * s, taper_top=(0.90, 0.92), mat_idx=idx_map["Mat_OliveMil"])
    add_cylinder(bm_bp, (-0.140 * wx * s, bp_y + 0.007 * s, 1.465 * s), (0.140 * wx * s, bp_y + 0.007 * s, 1.465 * s),
                 0.044 * s, 0.044 * s, segments=6, mat_idx=idx_map["Mat_CoyoteTan"])
    bp_obj, bp_t = finalize_mesh(f"{label}_Backpack", bm_bp, materials, collection=col_gear)
    attach_gear_to_bone(bp_obj, arm_obj, "mixamorig:Spine2")
    gear_items.append((bp_obj, bp_t))

    # M4 Carbine in RightHand via unified WeaponSocket
    gear_items.extend(equip_weapon(arm_obj, "m4", materials, idx_map, collection=col_gear, clear_existing=False))

    # Backup Glock 17 holstered on right thigh (-X)
    pistol_obj, pis_t = build_weapon_pistol(materials, idx_map, collection=col_gear, name=f"{label}_Holster_Pistol")
    hold(pistol_obj, arm_obj, "mixamorig:RightUpLeg",
         grip_world=(-(th_x + 0.006 * s), -0.015 * s, 0.785 * s),
         base_rot=(math.pi, 0.0, 0.0), extra_rot=(0.0, -0.12, 0.0))
    gear_items.append((pistol_obj, pis_t))

    return body_obj, body_tris, arm_obj, gear_items


# ---------------------------------------------------------------------------
# 2. MAYA (Female 1.68 m / Male 1.79 m) - Dark Blue Scrubs, Field Jacket, Red Cross Armband, Forearm Bandage, Stethoscope, Pistol
# ---------------------------------------------------------------------------
def build_maya(materials, idx_map, col_char, col_gear, col_rig, gender="female"):
    is_fem = (gender == "female")
    P = make_proportions(height=1.68 if is_fem else 1.79, female=is_fem)
    label = _char_label("Maya", gender)
    bm = bmesh.new()
    regions = {}

    build_character_head(
        bm, idx_map, regions, P, gender=gender,
        skin_mat="Mat_SkinLight", hair_mat="Mat_HairBlack",
        lip_mat="Mat_LipWarm" if is_fem else "Mat_Lip",
        headgear="ponytail" if is_fem else "short_hair",
        beard="none" if is_fem else "stubble",
        ponytail_tie="Mat_ScrubBlue",
        face_hair="bangs_side" if is_fem else "none",
    )
    T = _build_base_torso_and_arms(
        bm, idx_map, regions, P,
        shirt_mat="Mat_ScrubBlue", sleeve_mat="Mat_FieldJacket",
        pants_mat="Mat_ScrubDark", skin_mat="Mat_SkinLight",
        glove_mat="Mat_SkinLight", forearm_bandage_L=True,
    )
    s, ty = T["s"], T["ty"]

    # Cinched open hourglass field jacket around female bust & narrow waist (sa < 0 is front -Y!)
    n_arc = 7
    if is_fem:
        j_levels = [
            (0.900 * s, T["pelvis_rx"] + 0.012 * s, 0.118 * s, 0.068 * s, 0.012 * s),
            (1.045 * s, T["waist_rx"] + 0.012 * s,  0.088 * s, 0.050 * s, 0.012 * s),
            (1.205 * s, T["mid_rx"] + 0.014 * s,    0.098 * s, 0.062 * s, 0.013 * s),
            (1.300 * s, T["chest_rx"] + 0.014 * s,  0.122 * s, 0.074 * s, 0.013 * s),
            (1.380 * s, T["chest_rx"] + 0.008 * s,  0.104 * s, 0.068 * s, 0.012 * s),
            (1.452 * s, T["top_rx"] + 0.010 * s,    0.090 * s, 0.058 * s, 0.012 * s),
        ]
    else:
        j_levels = [
            (0.920 * s, T["pelvis_rx"] + 0.014 * s, 0.122 * ty, 0.054 * s, 0.013 * s),
            (1.060 * s, T["waist_rx"] + 0.018 * s,  0.116 * ty, 0.048 * s, 0.013 * s),
            (1.220 * s, T["mid_rx"] + 0.018 * s,    0.128 * ty, 0.052 * s, 0.014 * s),
            (1.360 * s, T["chest_rx"] + 0.016 * s,  0.132 * ty, 0.058 * s, 0.014 * s),
            (1.458 * s, T["top_rx"] + 0.010 * s,    0.114 * ty, 0.064 * s, 0.013 * s),
        ]
    j_rings = []
    for (cz, rx, ry, gx, th) in j_levels:
        ga = math.asin(min(0.85, gx / rx))
        a0, a1 = -0.5 * math.pi + ga, 1.5 * math.pi - ga
        op, ip = [], []
        for i in range(n_arc):
            ang = a0 + (i / (n_arc - 1)) * (a1 - a0)
            ca, sa = math.cos(ang), math.sin(ang)
            sf = (1.16 if sa < 0 else 1.14) if is_fem else 1.02
            op.append((rx * ca, 0.006 * s + ry * sa * sf, cz))
            ip.append(((rx - th) * ca, 0.006 * s + (ry - th) * sa * sf, cz))
        j_rings.append(op + list(reversed(ip)))
    _tag(loft_rings(bm, j_rings, close_caps=(True, True), mat_idx=idx_map["Mat_FieldJacket"]), regions, "torso")
    _tag(add_box(bm, center=(0.0, 0.068 * ty, 1.485 * s),
                 size=(0.124 * (0.92 if is_fem else 1.0) * s, 0.032 * s, 0.052 * s),
                 mat_idx=idx_map["Mat_FieldJacket"]), regions, "torso")

    # White + Red Cross armband on right upper arm (-X) fitted to T["r_arm"]
    ax_in = -(P["arm"][0] + 0.075 * s)
    ax_out = -(P["arm"][0] + 0.145 * s)
    rb = T["r_arm"] * 1.05
    arm_band = [
        ring_yz(ax_in, P["arm"][1], P["arm"][2], rb, rb, n=8),
        ring_yz(ax_out, P["arm"][1], P["arm"][2], rb * 0.97, rb * 0.97, n=8),
    ]
    _tag(loft_rings(bm, list(reversed(arm_band)), close_caps=(True, True), mat_idx=idx_map["Mat_MedWhite"]), regions, "arm_R")
    _tag(add_box(bm, center=(0.5 * (ax_in + ax_out), P["arm"][1] - (rb + 0.002 * s), P["arm"][2]),
                 size=(0.044 * s, 0.010 * s, 0.018 * s), mat_idx=idx_map["Mat_MedRed"]), regions, "arm_R")
    _tag(add_box(bm, center=(0.5 * (ax_in + ax_out), P["arm"][1] - (rb + 0.002 * s), P["arm"][2]),
                 size=(0.018 * s, 0.010 * s, 0.044 * s), mat_idx=idx_map["Mat_MedRed"]), regions, "arm_R")

    # Stethoscope draped clearly outside collar & upper chest
    st_y = -0.122 * ty
    for sx in (1.0, -1.0):
        _tag(add_cylinder(
            bm,
            (sx * 0.054 * s, -0.005 * s, 1.495 * s),
            (sx * 0.046 * s, st_y, 1.385 * s),
            0.007 * s, 0.007 * s, segments=5, mat_idx=idx_map["Mat_GunPolymer"],
        ), regions, "torso")
    _tag(add_cylinder(
        bm, (0.046 * s, st_y, 1.385 * s), (0.042 * s, st_y - 0.004 * s, 1.320 * s),
        0.006 * s, 0.006 * s, segments=5, mat_idx=idx_map["Mat_GunPolymer"],
    ), regions, "torso")
    _tag(add_cylinder(
        bm, (0.042 * s, st_y - 0.002 * s, 1.318 * s), (0.042 * s, st_y - 0.014 * s, 1.315 * s),
        0.018 * s, 0.018 * s, segments=8, mat_idx=idx_map["Mat_GunSteel"],
    ), regions, "torso")

    body_obj, body_tris, arm_obj = _finalize_character(label, bm, materials, regions, P, col_char, col_rig)
    gear_items = []

    # Medic backpack with white + red cross on Spine2
    bm_mp = bmesh.new()
    add_box(bm_mp, center=(0.0, 0.195 * ty, 1.245 * s), size=(0.240 * s, 0.135 * ty, 0.340 * s),
            bevel=0.012 * s, mat_idx=idx_map["Mat_ScrubBlue"])
    add_box(bm_mp, center=(0.0, 0.266 * ty, 1.265 * s), size=(0.110 * s, 0.014 * ty, 0.110 * s),
            mat_idx=idx_map["Mat_MedWhite"])
    add_box(bm_mp, center=(0.0, 0.275 * ty, 1.265 * s), size=(0.072 * s, 0.008 * ty, 0.024 * s),
            mat_idx=idx_map["Mat_MedRed"])
    add_box(bm_mp, center=(0.0, 0.275 * ty, 1.265 * s), size=(0.024 * s, 0.008 * ty, 0.072 * s),
            mat_idx=idx_map["Mat_MedRed"])
    mp_obj, mp_t = finalize_mesh(f"{label}_MedicPack", bm_mp, materials, collection=col_gear)
    attach_gear_to_bone(mp_obj, arm_obj, "mixamorig:Spine2")
    gear_items.append((mp_obj, mp_t))

    # Glock 17 in RightHand via unified WeaponSocket
    gear_items.extend(equip_weapon(arm_obj, "pistol", materials, idx_map, collection=col_gear, clear_existing=False))

    return body_obj, body_tris, arm_obj, gear_items


# ---------------------------------------------------------------------------
# 3. RICO (Male 1.82 m / Female 1.70 m) - Blue Denim Overalls w/ Oil Stains, Red Bandana + Goggles, Tool Belt, Pipe Wrench
# ---------------------------------------------------------------------------
def build_rico(materials, idx_map, col_char, col_gear, col_rig, gender="male"):
    is_fem = (gender == "female")
    P = make_proportions(height=1.70 if is_fem else 1.82, female=is_fem, shoulder_scale=1.00 if is_fem else 1.06)
    label = _char_label("Rico", gender)
    bm = bmesh.new()
    regions = {}

    build_character_head(
        bm, idx_map, regions, P, gender=gender,
        skin_mat="Mat_SkinTan", hair_mat="Mat_HairBlack",
        lip_mat="Mat_LipWarm" if is_fem else "Mat_Lip",
        headgear="bandana_goggles", beard="none" if is_fem else "stubble",
        ponytail=is_fem, ponytail_tie="Mat_BandanaRed",
        face_hair="bangs_side" if is_fem else "none",
    )
    T = _build_base_torso_and_arms(
        bm, idx_map, regions, P,
        shirt_mat="Mat_WorkGrey", sleeve_mat="Mat_WorkGrey",
        pants_mat="Mat_DenimBlue", skin_mat="Mat_SkinTan",
        glove_mat="Mat_LeatherDark", forearm_skin_L=True,
    )
    s, ty, hx = T["s"], T["ty"], T["hx"]
    wx = 0.78 if is_fem else 1.0

    # Fitted denim overalls: seamless hourglass conformal apron + bib hugging female waist & bust
    if is_fem:
        bib_rings = [
            ring_ellipse(0.0, 0.006 * s, 0.910 * s, T["pelvis_rx"] + 0.008 * s, 0.116 * s, n=12, squash_front=0.95, squash_back=1.24),
            ring_ellipse(0.0, 0.006 * s, 1.045 * s, T["waist_rx"] + 0.008 * s,  0.082 * s, n=12, squash_front=0.94, squash_back=1.08),
            ring_ellipse(0.0, 0.008 * s, 1.205 * s, 0.096 * s, 0.094 * s, n=12, squash_front=1.02, squash_back=0.88),
            ring_ellipse(0.0, 0.006 * s, 1.300 * s, 0.098 * s, 0.120 * s, n=12, squash_front=1.18, squash_back=0.84),
            ring_ellipse(0.0, 0.006 * s, 1.350 * s, 0.092 * s, 0.106 * s, n=12, squash_front=1.10, squash_back=0.82),
        ]
        # Keep only the upper bib front/back smooth without spilling onto bare shoulders above waist
        for r in bib_rings[2:]:
            for idx_side in (0, 1, 5, 6, 7, 11):
                # Pull upper-bib sides inward so grey tee sleeves/ribs show cleanly beside the bib
                x_v, y_v, z_v = r[idx_side]
                r[idx_side] = (x_v * 0.88, y_v, z_v)
            r[8] = (r[8][0], r[8][1] - 0.010 * s, r[8][2])
            r[10] = (r[10][0], r[10][1] - 0.010 * s, r[10][2])
        _tag(loft_rings(bm, bib_rings, close_caps=(True, True), mat_idx=idx_map["Mat_DenimBlue"]), regions, "torso")
        for sx in (1.0, -1.0):
            _tag(add_box(bm, center=(sx * 0.064 * s, -0.095 * s, 1.400 * s), size=(0.026 * s, 0.016 * s, 0.125 * s),
                         rot=(0.24, 0.0, 0.0), mat_idx=idx_map["Mat_DenimBlue"]), regions, "torso")
            _tag(add_box(bm, center=(sx * 0.064 * s, 0.082 * s, 1.390 * s), size=(0.026 * s, 0.016 * s, 0.165 * s),
                         rot=(-0.20, 0.0, 0.0), mat_idx=idx_map["Mat_DenimBlue"]), regions, "torso")
            _tag(add_box(bm, center=(sx * 0.064 * s, -0.118 * s, 1.345 * s), size=(0.030 * s, 0.010 * s, 0.020 * s),
                         mat_idx=idx_map["Mat_Brass"]), regions, "torso")
        _tag(add_box(bm, center=(-0.038 * s, -0.098 * s, 1.155 * s), size=(0.060 * s, 0.012 * s, 0.068 * s),
                     rot=(-0.18, 0.0, 0.18), mat_idx=idx_map["Mat_OilStain"]), regions, "torso")
    else:
        _tag(add_box(bm, center=(0.0, -0.116 * ty, 1.155 * s), size=(0.245 * s, 0.036 * ty, 0.340 * s),
                     mat_idx=idx_map["Mat_DenimBlue"]), regions, "torso")
        _tag(add_box(bm, center=(0.0, 0.118 * ty, 1.135 * s), size=(0.240 * s, 0.030 * ty, 0.285 * s),
                     mat_idx=idx_map["Mat_DenimBlue"]), regions, "torso")
        for sx in (1.0, -1.0):
            _tag(add_box(bm, center=(sx * 0.088 * s, -0.100 * ty, 1.385 * s), size=(0.038 * s, 0.022 * ty, 0.165 * s),
                         rot=(0.18, 0.0, 0.0), mat_idx=idx_map["Mat_DenimBlue"]), regions, "torso")
            _tag(add_box(bm, center=(sx * 0.088 * s, 0.092 * ty, 1.365 * s), size=(0.038 * s, 0.022 * ty, 0.215 * s),
                         rot=(-0.18, 0.0, 0.0), mat_idx=idx_map["Mat_DenimBlue"]), regions, "torso")
            _tag(add_box(bm, center=(sx * 0.088 * s, -0.125 * ty, 1.318 * s), size=(0.042 * s, 0.014 * ty, 0.024 * s),
                         mat_idx=idx_map["Mat_Brass"]), regions, "torso")
        _tag(add_box(bm, center=(-0.055 * s, -0.134 * ty, 1.140 * s), size=(0.082 * s, 0.008 * ty, 0.095 * s),
                     rot=(0.0, 0.0, 0.22), mat_idx=idx_map["Mat_OilStain"]), regions, "torso")
    _tag(add_box(bm, center=(hx + 0.002 * s, -T["r_th"] * 0.96, 0.720 * s), size=(0.070 * s, 0.014 * s, 0.115 * s),
                 mat_idx=idx_map["Mat_OilStain"]), regions, "leg_L")

    # Leather tool belt + hammer, screwdriver, and yellow tape measure
    belt_rx = T["pelvis_rx"] + 0.016 * s
    belt = [ring_ellipse(0.0, 0.004 * s, 0.915 * s, belt_rx, 0.118 * ty, n=10),
            ring_ellipse(0.0, 0.004 * s, 0.970 * s, belt_rx, 0.118 * ty, n=10)]
    _tag(loft_rings(bm, belt, close_caps=(True, True), mat_idx=idx_map["Mat_BeltLeather"]), regions, "hips_rigid")
    tool_x = belt_rx + 0.018 * s
    _tag(add_cylinder(bm, (tool_x, 0.01 * s, 0.94 * s), (tool_x + 0.006 * s, 0.03 * s, 0.71 * s),
                      0.012 * s, 0.011 * s, segments=6, mat_idx=idx_map["Mat_WoodBat"]), regions, "hips_rigid")
    _tag(add_box(bm, center=(tool_x, 0.01 * s, 0.945 * s), size=(0.032 * s, 0.095 * s, 0.028 * s),
                 mat_idx=idx_map["Mat_GunSteel"]), regions, "hips_rigid")
    _tag(add_box(bm, center=(-tool_x, -0.03 * s, 0.92 * s), size=(0.044 * s, 0.068 * s, 0.068 * s),
                 mat_idx=idx_map["Mat_ToolYellow"]), regions, "hips_rigid")
    _tag(add_cylinder(bm, (-tool_x, 0.055 * ty, 0.96 * s), (-tool_x, 0.055 * ty, 0.80 * s),
                      0.012 * s, 0.005 * s, segments=6, mat_idx=idx_map["Mat_BandanaRed"]), regions, "hips_rigid")

    body_obj, body_tris, arm_obj = _finalize_character(label, bm, materials, regions, P, col_char, col_rig)
    gear_items = []

    # Pipe wrench in RightHand via unified WeaponSocket
    gear_items.extend(equip_weapon(arm_obj, "pipe_wrench", materials, idx_map, collection=col_gear, clear_existing=False))

    return body_obj, body_tris, arm_obj, gear_items


# ---------------------------------------------------------------------------
# 4. LENA (Female 1.70 m / Male 1.80 m) - Uncovered Ranger Hair, Folded Green Cowl & Bracer, Terracotta Scarf, Leather Coat, Quiver + Knife, Bow + Arrow
# ---------------------------------------------------------------------------
def build_lena(materials, idx_map, col_char, col_gear, col_rig, gender="female"):
    is_fem = (gender == "female")
    P = make_proportions(height=1.70 if is_fem else 1.80, female=is_fem)
    label = _char_label("Lena", gender)
    bm = bmesh.new()
    regions = {}

    build_character_head(
        bm, idx_map, regions, P, gender=gender,
        skin_mat="Mat_SkinLight", hair_mat="Mat_HairBrown",
        lip_mat="Mat_LipWarm" if is_fem else "Mat_Lip",
        headgear="ranger_hair" if is_fem else "short_hair",
        beard="none" if is_fem else "stubble",
        ponytail_tie="Mat_HoodGreen",
        face_hair="bangs_side" if is_fem else "none",
    )
    T = _build_base_torso_and_arms(
        bm, idx_map, regions, P,
        shirt_mat="Mat_HoodGreen", sleeve_mat="Mat_HoodGreen",
        pants_mat="Mat_Pants", skin_mat="Mat_SkinLight",
        glove_mat="Mat_BeltLeather",
    )
    s, ty = T["s"], T["ty"]

    # Clean forest-green ranger jacket hem skirt blending waist into hips + leather waist belt
    hem_rings = [
        ring_ellipse(0.0, 0.006 * s, 0.905 * s, T["pelvis_rx"] + 0.020 * s, (0.128 if is_fem else 0.126 * ty / s) * s,
                     n=12, squash_front=0.96, squash_back=1.24 if is_fem else 1.06),
        ring_ellipse(0.0, 0.006 * s, 0.965 * s, (T["pelvis_rx"] * 0.60 + T["waist_rx"] * 0.40) + 0.015 * s,
                     (0.112 if is_fem else 0.118 * ty / s) * s, n=12, squash_front=0.96, squash_back=1.18 if is_fem else 1.05),
        ring_ellipse(0.0, 0.006 * s, 1.035 * s, T["waist_rx"] + 0.011 * s, (0.090 if is_fem else 0.112 * ty / s) * s,
                     n=12, squash_front=0.96, squash_back=1.08 if is_fem else 1.05),
    ]
    _tag(loft_rings(bm, hem_rings, close_caps=(True, True), mat_idx=idx_map["Mat_HoodGreen"]),
         regions, "hips_soft")
    belt_rx = (0.148 if is_fem else 0.172) * s
    belt_l = [
        ring_ellipse(0.0, 0.006 * s, 0.945 * s, belt_rx, (0.120 if is_fem else 0.125) * s,
                     n=12, squash_front=0.96, squash_back=1.20 if is_fem else 1.06),
        ring_ellipse(0.0, 0.006 * s, 0.985 * s, (0.132 if is_fem else 0.168) * s, (0.108 if is_fem else 0.122) * s,
                     n=12, squash_front=0.96, squash_back=1.15 if is_fem else 1.06),
    ]
    _tag(loft_rings(bm, belt_l, close_caps=(True, True), mat_idx=idx_map["Mat_BeltLeather"]), regions, "hips_rigid")

    # Full terracotta scarf collar clearing V-neck + 4-ring contoured ribbon tail curving smoothly over chest/bust
    scarf_rings = [
        ring_ellipse(0.0, 0.002 * s, 1.448 * s, (0.104 if is_fem else 0.122) * s, (0.094 if is_fem else 0.108) * s, n=10),
        ring_ellipse(0.0, 0.004 * s, 1.472 * s, (0.096 if is_fem else 0.112) * s, (0.090 if is_fem else 0.102) * s, n=10),
        ring_ellipse(0.0, 0.006 * s, 1.500 * s, (0.086 if is_fem else 0.100) * s, (0.084 if is_fem else 0.096) * s, n=10),
        ring_ellipse(0.0, 0.008 * s, 1.514 * s, (0.068 if is_fem else 0.082) * s, (0.068 if is_fem else 0.080) * s, n=10),
    ]
    _tag(loft_rings(bm, scarf_rings, close_caps=(True, True), mat_idx=idx_map["Mat_ScarfRust"]), regions, "torso")
    tail_cx = -0.018 * s
    tail_rings = [
        [(tail_cx + hw, cy + ht, cz), (tail_cx + hw, cy - ht, cz),
         (tail_cx - hw, cy - ht, cz), (tail_cx - hw, cy + ht, cz)]
        for cz, cy, hw, ht in (
            (1.460 * s, (-0.090 if is_fem else -0.102) * s, 0.026 * s, 0.010 * s),
            (1.385 * s, (-0.122 if is_fem else -0.128) * s, 0.025 * s, 0.009 * s),
            (1.300 * s, (-0.146 if is_fem else -0.138) * s, 0.023 * s, 0.008 * s),
            (1.225 * s, (-0.138 if is_fem else -0.134) * s, 0.016 * s, 0.006 * s),
        )
    ]
    _tag(loft_rings(bm, tail_rings, close_caps=(True, True), mat_idx=idx_map["Mat_ScarfRust"]), regions, "torso")

    # Side waist-belt survival knife sheath (right hip -X, clear of thigh)
    hip_x = -(belt_rx + 0.016 * s)
    ang_hip = 0.12
    d_blade = Vector((0.0, math.sin(ang_hip), -math.cos(ang_hip)))
    kn_grip = Vector((hip_x, -0.012 * s, 0.960 * s))
    sheath_cen = kn_grip + d_blade * (0.142 * s)
    _tag(add_box(bm, center=tuple(sheath_cen), size=(0.022 * s, 0.036 * s, 0.172 * s),
                 rot=(ang_hip, 0.0, 0.0), bevel=0.004 * s, taper_top=(1.0, 1.0),
                 mat_idx=idx_map["Mat_BeltLeather"]), regions, "hips_rigid")

    body_obj, body_tris, arm_obj = _finalize_character(label, bm, materials, regions, P, col_char, col_rig)
    gear_items = []

    kn_obj, kn_t = build_weapon_knife(materials, idx_map, collection=col_gear, name=f"{label}_Hip_Knife")
    hold(kn_obj, arm_obj, "mixamorig:Hips",
         grip_world=tuple(kn_grip),
         base_rot=(math.pi, 0.0, 0.0), extra_rot=(ang_hip, 0.0, 0.0))
    gear_items.append((kn_obj, kn_t))

    bm_q = bmesh.new()
    add_cylinder(bm_q, (-0.095 * s, 0.158 * ty, 1.06 * s), (0.075 * s, 0.158 * ty, 1.46 * s),
                 0.044 * s, 0.056 * s, segments=8, mat_idx=idx_map["Mat_BeltLeather"])
    for ox, oz in ((-0.02, 0.01), (0.0, 0.02), (0.02, 0.01), (-0.01, -0.01), (0.015, -0.015)):
        add_cylinder(bm_q, ((0.068 + ox) * s, 0.158 * ty, (1.44 + oz) * s),
                     ((0.105 + ox) * s, 0.158 * ty, (1.53 + oz) * s),
                     0.005 * s, 0.005 * s, segments=5, mat_idx=idx_map["Mat_Carbon"])
        add_box(bm_q, center=((0.102 + ox) * s, 0.158 * ty, (1.52 + oz) * s),
                size=(0.014 * s, 0.014 * s, 0.036 * s), mat_idx=idx_map["Mat_VaneRed"])
    q_obj, q_t = finalize_mesh(f"{label}_Quiver", bm_q, materials, collection=col_gear)
    attach_gear_to_bone(q_obj, arm_obj, "mixamorig:Spine2")
    gear_items.append((q_obj, q_t))

    # Compound bow + Arrow via unified WeaponSocket
    gear_items.extend(equip_weapon(arm_obj, "compound_bow", materials, idx_map, collection=col_gear, clear_existing=False))

    return body_obj, body_tris, arm_obj, gear_items


# ---------------------------------------------------------------------------
# 5. TOM (Male 1.81 m / Female 1.70 m) - Cowboy Hat, Red Plaid Flannel, Shearling Vest, Reading Glasses, Shell Belt, Shotgun
# ---------------------------------------------------------------------------
def build_tom(materials, idx_map, col_char, col_gear, col_rig, gender="male"):
    is_fem = (gender == "female")
    P = make_proportions(height=1.70 if is_fem else 1.81, female=is_fem)
    label = _char_label("Tom", gender)
    bm = bmesh.new()
    regions = {}

    build_character_head(
        bm, idx_map, regions, P, gender=gender,
        skin_mat="Mat_SkinMed", hair_mat="Mat_HairGrey",
        lip_mat="Mat_LipWarm" if is_fem else "Mat_Lip",
        headgear="cowboy", beard="none" if is_fem else "mustache",
        ponytail=False,
        face_hair="long_shoulder" if is_fem else "none",
    )
    T = _build_base_torso_and_arms(
        bm, idx_map, regions, P,
        shirt_mat="Mat_FlannelRed", sleeve_mat="Mat_FlannelRed",
        pants_mat="Mat_Pants", skin_mat="Mat_SkinMed",
        glove_mat="Mat_SkinMed",
        plaid_mat=("Mat_FlannelDark", "Mat_FlannelCheck"),
    )
    s, ty = T["s"], T["ty"]
    wx = 0.80 if is_fem else 1.0

    # Leather vest cinched tightly to female hourglass (sa < 0 is front -Y so bust opens cleanly!)
    n_arc = 7
    if is_fem:
        v_levels = [
            (0.945 * s, T["pelvis_rx"] + 0.012 * s, 0.120 * s, 0.070 * s, 0.012 * s),
            (1.055 * s, T["waist_rx"] + 0.014 * s,  0.090 * s, 0.054 * s, 0.012 * s),
            (1.205 * s, T["mid_rx"] + 0.016 * s,    0.102 * s, 0.066 * s, 0.013 * s),
            (1.300 * s, T["chest_rx"] + 0.016 * s,  0.126 * s, 0.080 * s, 0.013 * s),
            (1.380 * s, T["chest_rx"] + 0.010 * s,  0.108 * s, 0.074 * s, 0.012 * s),
            (1.450 * s, T["top_rx"] + 0.012 * s,    0.094 * s, 0.062 * s, 0.012 * s),
        ]
    else:
        v_levels = [
            (0.955 * s, T["pelvis_rx"] + 0.018 * s, 0.132 * ty, 0.056 * s, 0.014 * s),
            (1.080 * s, T["waist_rx"] + 0.020 * s,  0.128 * ty, 0.052 * s, 0.014 * s),
            (1.220 * s, T["mid_rx"] + 0.020 * s,    0.140 * ty, 0.056 * s, 0.015 * s),
            (1.360 * s, T["chest_rx"] + 0.018 * s,  0.142 * ty, 0.062 * s, 0.015 * s),
            (1.452 * s, T["top_rx"] + 0.014 * s,    0.122 * ty, 0.068 * s, 0.014 * s),
        ]
    v_rings = []
    for (cz, rx, ry, gx, th) in v_levels:
        ga = math.asin(min(0.85, gx / rx))
        a0, a1 = -0.5 * math.pi + ga, 1.5 * math.pi - ga
        op, ip = [], []
        for i in range(n_arc):
            ang = a0 + (i / (n_arc - 1)) * (a1 - a0)
            ca, sa = math.cos(ang), math.sin(ang)
            sf = (1.16 if sa < 0 else 1.14) if is_fem else (1.06 if sa > 0 else 0.98)
            op.append((rx * ca, 0.008 * s + ry * sa * sf, cz))
            ip.append(((rx - th) * ca, 0.008 * s + (ry - th) * sa * sf, cz))
        v_rings.append(op + list(reversed(ip)))
    _tag(loft_rings(bm, v_rings, close_caps=(True, True), mat_idx=idx_map["Mat_VestLeather"]), regions, "torso")

    lap_x = 0.076 * s if is_fem else 0.064 * s
    lap_y = -0.114 * s if is_fem else -0.108 * ty
    for sx in (1.0, -1.0):
        _tag(add_box(bm, center=(sx * lap_x, lap_y, 1.385 * s),
                     size=(0.032 * s if is_fem else 0.036 * s, 0.016 * s, 0.120 * s),
                     rot=(0.10, sx * -0.16, sx * 0.20), mat_idx=idx_map["Mat_Shearling"]), regions, "torso")
    _tag(add_box(bm, center=(0.0, 0.078 * ty, 1.468 * s),
                 size=(0.145 * wx * s, 0.034 * ty, 0.058 * s),
                 mat_idx=idx_map["Mat_Shearling"]), regions, "torso")

    # Left vest pocket + reading glasses peeking out
    px_v = 0.105 * s if is_fem else 0.108 * s
    py_v = -0.118 * s if is_fem else -0.120 * ty
    _tag(add_box(bm, center=(px_v, py_v, 1.285 * s),
                 size=(0.048 * s, 0.016 * s, 0.058 * s),
                 rot=(0.04, 0.0, -0.24), mat_idx=idx_map["Mat_VestLeather"]), regions, "torso")
    _tag(add_box(bm, center=(px_v, py_v - 0.006 * s, 1.320 * s),
                 size=(0.042 * s, 0.008 * s, 0.016 * s),
                 rot=(0.0, 0.0, -0.24), mat_idx=idx_map["Mat_Brass"]), regions, "torso")

    # Shotgun shell belt around hips (snug contour on female)
    belt_rx = (0.144 if is_fem else 0.170) * s
    belt_ry = (0.102 if is_fem else 0.118) * s
    belt = [ring_ellipse(0.0, 0.004 * s, 0.915 * s, belt_rx, belt_ry, n=10),
            ring_ellipse(0.0, 0.004 * s, 0.970 * s, belt_rx, belt_ry, n=10)]
    _tag(loft_rings(bm, belt, close_caps=(True, True), mat_idx=idx_map["Mat_BeltLeather"]), regions, "hips_rigid")
    for ang_deg in (-60, -40, -20, 20, 40, 60):
        ang = math.radians(-90 + ang_deg)
        sx_p = (belt_rx + 0.005 * s) * math.cos(ang)
        sy_p = (belt_ry + 0.004 * s) * math.sin(ang)
        _tag(add_cylinder(bm, (sx_p, sy_p, 0.918 * s), (sx_p, sy_p, 0.960 * s),
                          0.009 * s, 0.009 * s, segments=6, mat_idx=idx_map["Mat_ShellRed"]), regions, "hips_rigid")
        _tag(add_cylinder(bm, (sx_p, sy_p, 0.960 * s), (sx_p, sy_p, 0.972 * s),
                          0.0095 * s, 0.0095 * s, segments=6, mat_idx=idx_map["Mat_Brass"]), regions, "hips_rigid")

    body_obj, body_tris, arm_obj = _finalize_character(label, bm, materials, regions, P, col_char, col_rig)
    gear_items = []

    # Double-barrel shotgun in RightHand via unified WeaponSocket
    gear_items.extend(equip_weapon(arm_obj, "double_barrel", materials, idx_map, collection=col_gear, clear_existing=False))

    return body_obj, body_tris, arm_obj, gear_items


ROLE_POSE_MAP = {
    "jake": "rifle",
    "maya": "pistol",
    "rico": "wrench",
    "lena": "bow",
    "tom":  "rifle",
}

SURVIVOR_PAIRS = [
    ("jake", build_jake),
    ("maya", build_maya),
    ("rico", build_rico),
    ("lena", build_lena),
    ("tom",  build_tom),
]

SURVIVOR_BUILDERS = [
    ("jake_male",   lambda *a: build_jake(*a, gender="male")),
    ("jake_female", lambda *a: build_jake(*a, gender="female")),
    ("maya_male",   lambda *a: build_maya(*a, gender="male")),
    ("maya_female", lambda *a: build_maya(*a, gender="female")),
    ("rico_male",   lambda *a: build_rico(*a, gender="male")),
    ("rico_female", lambda *a: build_rico(*a, gender="female")),
    ("lena_male",   lambda *a: build_lena(*a, gender="male")),
    ("lena_female", lambda *a: build_lena(*a, gender="female")),
    ("tom_male",    lambda *a: build_tom(*a, gender="male")),
    ("tom_female",  lambda *a: build_tom(*a, gender="female")),
]
