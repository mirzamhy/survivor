"""One-by-one Weird Mutant Zombies with radically unique non-humanoid forms, heads & custom rigs."""
import math
import bmesh
from mathutils import Euler, Vector

from mesh_utils import (
    add_box,
    add_cone,
    add_cylinder,
    apply_box_uvs,
    finalize_mesh,
    loft_rings,
    ring_ellipse,
    ring_perp,
    ring_yz,
)
from mutant_heads import (
    _add_curved_leaf,
    _add_fungal_fan,
    _add_tapered_ribbon,
    build_head_arachnid_maw,
    build_head_bile_juggernaut,
    build_head_fungal_bloom,
    build_head_rafflesia,
    build_head_scythe_stalker,
    build_head_thorn_shroud,
)
from rig_creature import create_creature_armature, skin_creature_to_armature
from rig_mixamo import make_proportions
from zombies import (
    _add_jagged_rip_cuff,
    _build_zombie_base,
    _finalize_zombie,
    _perp_chain_rings,
    _tag,
)


# ---------------------------------------------------------------------------
# MUTANT #1: RAFFLESIA CARNIVOROUS BLOOD-FLOWER MONSTER (1.88 m)
# ---------------------------------------------------------------------------
def _add_thorny_vine(
    bm, mat_idx, spine_pts, rads, mat_vine="Mat_ZVinePale", mat_thorn="Mat_ZLeafDark",
    thorn_count=6, thorn_len=0.022, n=6, twist_total=1.8, up_hint=(0.0, 0.0, 1.0),
):
    """Loft an organic fluted/helical-twisted vine along `spine_pts` studded with sharp low-poly thorns."""
    vecs = [Vector(p) for p in spine_pts]
    m = len(vecs)
    rings = []
    frames = []
    uh = Vector(up_hint)
    for k in range(m):
        if k == 0:
            tan = vecs[1] - vecs[0]
        elif k == m - 1:
            tan = vecs[-1] - vecs[-2]
        else:
            tan = vecs[k + 1] - vecs[k - 1]
        if tan.length < 1e-6:
            tan = Vector((0.0, 0.0, 1.0))
        tan.normalize()
        u = uh - tan * uh.dot(tan)
        if u.length < 1e-6:
            fb = Vector((1.0, 0.0, 0.0)) if abs(tan.x) < 0.9 else Vector((0.0, 1.0, 0.0))
            u = fb - tan * fb.dot(tan)
        u.normalize()
        v = tan.cross(u).normalized()

        t = k / max(1, m - 1)
        twist = twist_total * t
        ct, st = math.cos(twist), math.sin(twist)
        ut = u * ct + v * st
        vt = -u * st + v * ct
        frames.append((vecs[k], tan, ut, vt))

        ru, rs = rads[k]
        pts = []
        for i in range(n):
            th = (2.0 * math.pi * i) / n
            # Subtle fluted bark/tendon ridge modulation so it reads organic
            flute = 1.0 + 0.11 * math.cos(3.0 * th)
            pts.append(tuple(vecs[k] + ut * (math.cos(th) * ru * flute) + vt * (math.sin(th) * rs * flute)))
        rings.append(pts)

    verts = loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_idx[mat_vine])

    if thorn_count > 0 and m >= 2:
        for ti in range(thorn_count):
            frac = 0.18 + 0.70 * (ti / max(1, thorn_count - 1 if thorn_count > 1 else 1))
            fidx = frac * (m - 1)
            k0 = min(m - 2, int(fidx))
            alpha = fidx - k0
            c0, t0, u0, v0 = frames[k0]
            c1, t1, u1, v1 = frames[k0 + 1]
            c_pt = c0.lerp(c1, alpha)
            tan_pt = t0.lerp(t1, alpha).normalized()
            u_pt = u0.lerp(u1, alpha).normalized()
            v_pt = v0.lerp(v1, alpha).normalized()
            r_here = 0.5 * (rads[k0][0] * (1.0 - alpha) + rads[k0 + 1][0] * alpha)
            th_ang = ti * 2.15 + twist_total * frac
            out_dir = (u_pt * math.cos(th_ang) + v_pt * math.sin(th_ang)).normalized()
            base_pt = c_pt + out_dir * (r_here * 0.78)
            tip_pt = base_pt + (out_dir * 0.85 + tan_pt * 0.45).normalized() * thorn_len
            verts.extend(add_cone(bm, tuple(base_pt), tuple(tip_pt), max(0.0022, r_here * 0.42), segments=4, mat_idx=mat_idx[mat_thorn]))
    return verts


def _build_vine_tendril_hand(bm, mat_idx, regions, P, side, sx):
    """Build knotted thorny palm & 5 thick thorny undulating tentacle-claws preserving Mixamo finger weights."""
    s = P["scale"]
    wri_x = P["wrist"][0]
    hand_end_x = P["hand_end"][0]
    arm_y = P["arm"][1]
    arm_z = P["arm"][2]

    palm_specs = [
        (wri_x - 0.030 * s,      arm_y,            arm_z,            0.025 * s, 0.017 * s),
        (wri_x - 0.004 * s,      arm_y,            arm_z,            0.027 * s, 0.016 * s),
        (wri_x + 0.020 * s,      arm_y - 0.003*s,  arm_z + 0.002*s,  0.031 * s, 0.016 * s),
        (hand_end_x - 0.010 * s, arm_y - 0.004*s,  arm_z,            0.028 * s, 0.013 * s),
        (hand_end_x + 0.006 * s, arm_y - 0.004*s,  arm_z - 0.002*s,  0.022 * s, 0.011 * s),
    ]
    palm_rings = [ring_yz(sx * px, py, pz, ry, rz, n=8) for (px, py, pz, ry, rz) in palm_specs]
    if sx < 0:
        palm_rings = list(reversed(palm_rings))
    v_palm = loft_rings(bm, palm_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_ZVinePale"])
    for f in {f for v in v_palm for f in v.link_faces}:
        if f.calc_center_median().z > arm_z + 0.005 * s:
            f.material_index = mat_idx["Mat_ZLeafDark"]
    _tag(v_palm, regions, f"hand_{side}")

    # 3 dorsal knuckle thorns protruding from back of knotted palm
    for k in range(3):
        kx = wri_x + (0.004 + 0.020 * k) * s
        _tag(add_cone(
            bm,
            (sx * kx, arm_y + (0.008 * (k - 1)) * s, arm_z + 0.010 * s),
            (sx * (kx + 0.014 * s), arm_y + (0.014 * (k - 1)) * s, arm_z + 0.032 * s),
            0.0048 * s, segments=4, mat_idx=mat_idx["Mat_ZLeafDark"],
        ), regions, f"hand_{side}")

    # 5 Thick Thorny Writhing Vine-Tentacle Claws mapped strictly onto Mixamo finger bones
    tendril_specs = (
        ("index",  2.05,  0.030, -0.044, (0.0102, 0.0086, 0.0062, 0.0034)),
        ("middle", 2.35, -0.026, -0.072, (0.0110, 0.0092, 0.0066, 0.0036)),
        ("ring",   2.15,  0.036, -0.056, (0.0100, 0.0082, 0.0060, 0.0032)),
        ("pinky",  1.85,  0.022, -0.040, (0.0086, 0.0072, 0.0052, 0.0030)),
    )
    for fname, mul, y_curl, z_drop, rads in tendril_specs:
        pts = P[fname]
        bx = pts[0][0] - 0.010 * s
        by, bz = pts[0][1], pts[0][2]
        def _pt(k, dy, dz):
            return (
                sx * (bx + (pts[k][0] - bx) * mul),
                by + dy * s,
                bz + dz * s,
            )
        spine = [
            _pt(0, 0.0, 0.0),
            _pt(1, y_curl * 0.48, z_drop * 0.20),
            _pt(2, -y_curl * 0.85, z_drop * 0.58),
            _pt(3, y_curl * 0.90, z_drop * 1.00),
        ]
        srad = [(r * s, r * s) for r in rads]
        v_t = _add_thorny_vine(
            bm, mat_idx, spine, srad,
            mat_vine="Mat_ZVinePale", mat_thorn="Mat_ZLeafDark",
            thorn_count=3, thorn_len=0.016 * s, n=5, twist_total=1.2 * sx,
        )
        for f in {f for v in v_t for f in v.link_faces}:
            if abs(f.calc_center_median().x) > bx + 0.095 * s:
                f.material_index = mat_idx["Mat_ZLeafMid"]
        _tag(v_t, regions, f"{fname}_{side}")

    # Thick barbed thumb vine-claw
    t_pts = P["thumb"]
    bx_t = wri_x + 0.008 * s
    t_spine = [
        (sx * bx_t, arm_y - 0.004 * s, arm_z - 0.002 * s),
        (sx * (bx_t + 0.032 * s), t_pts[0][1] - 0.012 * s, arm_z - 0.014 * s),
        (sx * (bx_t + 0.070 * s), t_pts[1][1] - 0.034 * s, arm_z - 0.038 * s),
        (sx * (bx_t + 0.100 * s), t_pts[2][1] - 0.020 * s, arm_z - 0.072 * s),
        (sx * (bx_t + 0.086 * s), t_pts[3][1] - 0.042 * s, arm_z - 0.100 * s),
    ]
    t_rad = [(0.0115*s, 0.0115*s), (0.0095*s, 0.0095*s), (0.0076*s, 0.0076*s), (0.0054*s, 0.0054*s), (0.0032*s, 0.0032*s)]
    v_th = _add_thorny_vine(
        bm, mat_idx, t_spine, t_rad,
        mat_vine="Mat_ZLeafMid", mat_thorn="Mat_ZLeafDark",
        thorn_count=3, thorn_len=0.016 * s, n=5, twist_total=1.0 * sx,
    )
    for v in v_th:
        if abs(v.co.x) < t_pts[0][0] - 0.004 * s:
            _tag([v], regions, f"hand_{side}")
        else:
            _tag([v], regions, f"thumb_{side}")


def build_mutant_rafflesia(materials, idx_map, col_char, col_gear, col_rig):
    """Build Quadruped 4-Legged Multi-Tentacle Carnivorous Plant-Beast with 52-bone Creature Rig."""
    bm = bmesh.new()
    regions = {}
    chain_verts = {}

    def _cadd(key, verts):
        chain_verts.setdefault(key, []).extend(verts)

    # 1. Gnarled Root-Pelvis Bridge & 14 Crooked Hanging Aerial Rootlets (Z = 0.34 .. 0.48 m)
    _cadd("pelvis", loft_rings(bm, [
        ring_ellipse(0.0, 0.020, 0.350, 0.210, 0.140, n=10),
        ring_ellipse(0.0, 0.015, 0.415, 0.225, 0.150, n=10),
        ring_ellipse(0.0, 0.010, 0.480, 0.185, 0.130, n=10),
    ], close_caps=(True, True), mat_idx=idx_map["Mat_ZBarkDark"]))

    for sx in (1.0, -1.0):
        _cadd("pelvis", _add_thorny_vine(
            bm, idx_map,
            [(0.0, -0.105, 0.41), (0.11 * sx, -0.125, 0.43), (0.19 * sx, -0.03, 0.42), (0.14 * sx, 0.11, 0.40)],
            [(0.022, 0.018), (0.024, 0.020), (0.022, 0.018), (0.016, 0.014)],
            mat_vine="Mat_ZBarkMid", mat_thorn="Mat_ZLeafDark", thorn_count=0, n=6, twist_total=1.2,
        ))

    # 14 crooked hanging aerial root tendrils underneath belly arch
    for k in range(14):
        frac = (k / 13.0) - 0.5
        px = frac * 0.34 + 0.012 * math.sin(k * 2.1)
        py = (-0.065 + 0.14 * ((k * 3) % 4) / 3.0)
        len_r = 0.12 + 0.07 * ((k * 5) % 3) / 2.0
        r_pts = [
            (px, py, 0.375),
            (px + 0.016 * math.cos(k * 1.7), py - 0.014 * math.sin(k), 0.375 - len_r * 0.45),
            (px - 0.012 * math.sin(k * 2.3), py + 0.012 * math.cos(k), 0.375 - len_r),
        ]
        _cadd("pelvis", _add_thorny_vine(
            bm, idx_map, r_pts,
            [(0.012, 0.011), (0.0075, 0.007), (0.0025, 0.0025)],
            mat_vine=("Mat_ZBarkMid" if k % 2 == 0 else "Mat_ZBarkDark"),
            mat_thorn="Mat_ZLeafDark", thorn_count=0, n=4, twist_total=0.8,
        ))

    # 2. 4 Sprawling Braided Tree-Root Legs (FL, FR, BL, BR) + Splayed 4-Claw Root-Talon Feet on Z=0
    leg_configs = (
        ("Leg_FL",  1.0, -1.0, ( 0.14, -0.05, 0.42), ( 0.46, -0.22, 0.46), ( 0.44, -0.30, 0.08), ( 0.47, -0.36, 0.025)),
        ("Leg_FR", -1.0, -1.0, (-0.14, -0.05, 0.42), (-0.46, -0.22, 0.46), (-0.44, -0.30, 0.08), (-0.47, -0.36, 0.025)),
        ("Leg_BL",  1.0,  1.0, ( 0.13,  0.08, 0.40), ( 0.38,  0.22, 0.42), ( 0.36,  0.29, 0.08), ( 0.39,  0.34, 0.025)),
        ("Leg_BR", -1.0,  1.0, (-0.13,  0.08, 0.40), (-0.38,  0.22, 0.42), (-0.36,  0.29, 0.08), (-0.39,  0.34, 0.025)),
    )
    for lname, sx, fy, hip, knee, ankle, foot_c in leg_configs:
        hv, kv, av, fv = Vector(hip), Vector(knee), Vector(ankle), Vector(foot_c)
        spine = [
            tuple(hv),
            tuple(hv.lerp(kv, 0.45) + Vector((0.0, 0.0, 0.048))),
            tuple(hv.lerp(kv, 0.84) + Vector((0.0, 0.0, 0.025))),
            tuple(kv.lerp(av, 0.16) + Vector((0.025 * sx, 0.012 * fy, 0.015))),
            tuple(kv.lerp(av, 0.54) + Vector((0.035 * sx, 0.016 * fy, 0.018))),
            tuple(av),
        ]
        _cadd(lname, loft_rings(bm, _perp_chain_rings(
            spine, [(0.072, 0.068), (0.064, 0.060), (0.068, 0.064), (0.064, 0.060), (0.054, 0.050), (0.048, 0.046)], n=7,
        ), close_caps=(True, True), mat_idx=idx_map["Mat_ZBarkDark"]))

        # 3 intertwining braided root-muscle cords wrapping hip -> knee -> ankle
        for c_i, phase in enumerate((0.0, 2.09, 4.18)):
            c_pts = []
            c_rads = []
            for st in range(6):
                t = st / 5.0
                if t < 0.5:
                    p = hv.lerp(kv, t * 2.0) + Vector((0.0, 0.0, 0.045 * math.sin(t * 2.0 * math.pi)))
                else:
                    p = kv.lerp(av, (t - 0.5) * 2.0) + Vector((0.04 * sx * math.sin((t - 0.5) * 2.0 * math.pi), 0.0, 0.0))
                th = phase + t * 3.6 * sx
                rad_h = 0.058 * (1.0 - 0.25 * t)
                c_pts.append((p.x + math.cos(th) * rad_h * 0.72, p.y + math.sin(th) * rad_h, p.z + math.sin(th) * rad_h * 0.65))
                rr = 0.020 * (1.0 - 0.30 * t)
                c_rads.append((rr, rr * 0.85))
            _cadd(lname, _add_thorny_vine(
                bm, idx_map, c_pts, c_rads,
                mat_vine=("Mat_ZBarkMid" if c_i != 1 else "Mat_ZLeafDark"),
                mat_thorn="Mat_ZLeafDark", thorn_count=0, n=5, twist_total=1.2,
            ))

        # Rugged plantar pad & 4 crooked splayed 2-segment tree-root talons firmly grounded on Z=0.0
        _cadd(lname, loft_rings(bm, [
            ring_ellipse(fv.x, fv.y, 0.004, 0.062, 0.072, n=6),
            ring_ellipse(av.x, av.y, 0.088, 0.048, 0.048, n=6),
        ], close_caps=(True, True), mat_idx=idx_map["Mat_ZBarkMid"]))

        out_dir = Vector((fv.x - hv.x * 0.4, fv.y * 1.15, 0.0)).normalized()
        lat_dir = Vector((-out_dir.y, out_dir.x, 0.0)).normalized()
        for lat_m, fwd_m, r_b in (
            (-0.68,  0.85, 0.022),
            ( 0.00,  1.15, 0.025),
            ( 0.68,  0.85, 0.022),
            ( 0.00, -0.75, 0.020),
        ):
            t_dir = (out_dir * fwd_m + lat_dir * lat_m).normalized()
            len_t = 0.175 if fwd_m > 0 else 0.115
            p_b = Vector((fv.x, fv.y, 0.022)) + t_dir * 0.032
            p_m = p_b + t_dir * (len_t * 0.52) + Vector((0.0, 0.0, 0.014))
            p_t = p_b + t_dir * len_t - Vector((0.0, 0.0, 0.017))
            _cadd(lname, loft_rings(bm, [
                ring_ellipse(p_b.x, p_b.y, p_b.z, r_b, r_b * 0.85, n=5),
                ring_ellipse(p_m.x, p_m.y, p_m.z, r_b * 0.65, r_b * 0.58, n=5),
                ring_ellipse(p_t.x, p_t.y, max(0.004, p_t.z), 0.004, 0.004, n=5),
            ], close_caps=(True, True), mat_idx=idx_map["Mat_ZBarkDark"]))

    # 3. Hunched Twisted Moss-Bark Stalk Torso (Z = 0.44 .. 0.99 m) + Braided Root Tendons + Sap-Heart
    _cadd("stalk", loft_rings(bm, [
        ring_ellipse(0.0,  0.015, 0.440, 0.165, 0.125, n=12),
        ring_ellipse(0.0,  0.008, 0.560, 0.145, 0.112, n=12),
        ring_ellipse(0.0, -0.015, 0.690, 0.156, 0.118, n=12),
        ring_ellipse(0.0, -0.045, 0.830, 0.132, 0.104, n=12),
        ring_ellipse(0.0, -0.082, 0.985, 0.095, 0.088, n=12),
    ], close_caps=(True, True), mat_idx=idx_map["Mat_ZBarkDark"]))

    # Recessed glowing green sap-heart nestled inside chest pocket between tendons
    _cadd("stalk", add_box(
        bm, center=(0.016, -0.102, 0.720), size=(0.046, 0.036, 0.062),
        rot=(0.15, -0.20, 0.25), bevel=0.012, taper_top=(0.82, 0.82), mat_idx=idx_map["Mat_ZHeartGlow"],
    ))

    # 8 swirling thorny bark & vine tendons wrapping stalk up into calyx
    for k in range(8):
        ang0 = (2.0 * math.pi * k) / 8.0
        ang1 = ang0 + 1.05 * (1.0 if k % 2 == 0 else -1.0)
        s_pts = []
        s_rads = []
        for st in range(5):
            t = st / 4.0
            ang = ang0 * (1.0 - t) + ang1 * t
            zc = 0.45 + 0.53 * t
            yc = 0.015 - 0.095 * (t ** 1.3)
            rx = (0.158 - 0.062 * t)
            ry = (0.120 - 0.032 * t)
            s_pts.append((math.cos(ang) * rx, yc + math.sin(ang) * ry, zc))
            rr = 0.022 - 0.006 * t
            s_rads.append((rr, rr * 0.85))
        m_v = "Mat_ZLeafDark" if k % 3 == 0 else ("Mat_ZBarkMid" if k % 3 == 1 else "Mat_ZVinePale")
        _cadd("stalk", _add_thorny_vine(
            bm, idx_map, s_pts, s_rads,
            mat_vine=m_v, mat_thorn="Mat_ZLeafDark",
            thorn_count=(3 if k % 2 == 0 else 0), thorn_len=0.020, n=5, twist_total=1.4,
        ))

    # 4. 6 Colossal Flexible Thorny Plant-Vine Whip Arms with Forked Grappling Claws (3 per side)
    def _build_whip_vine(bucket, main_pts, main_rads, fork_specs, mat_v, thorns=10, thorn_l=0.030, twist=2.4):
        _cadd(bucket, _add_thorny_vine(
            bm, idx_map, main_pts, main_rads,
            mat_vine=mat_v, mat_thorn="Mat_ZLeafDark",
            thorn_count=thorns, thorn_len=thorn_l, n=6, twist_total=twist,
        ))
        for f_pts, f_rads, f_mat, f_th in fork_specs:
            _cadd(bucket, _add_thorny_vine(
                bm, idx_map, f_pts, f_rads,
                mat_vine=f_mat, mat_thorn="Mat_ZLeafDark",
                thorn_count=f_th, thorn_len=thorn_l * 0.72, n=5, twist_total=1.2,
            ))

    for side, sx in (("L", 1.0), ("R", -1.0)):
        # Vine_Main: massive low-sweeping thorny arm curling high into a 3-pronged claw
        main_pts = [
            (0.10 * sx, -0.01, 0.62),
            (0.28 * sx, -0.05, 0.50),
            (0.50 * sx, -0.09, 0.44),
            (0.74 * sx, -0.10, 0.48),
            (0.94 * sx, -0.06, 0.64),
            (1.02 * sx, -0.09, 0.84),
            (0.94 * sx, -0.15, 1.04),
        ]
        main_rads = [(0.034, 0.032), (0.031, 0.029), (0.027, 0.025), (0.023, 0.021), (0.018, 0.017), (0.012, 0.011), (0.005, 0.005)]
        main_forks = [
            ([(0.94 * sx, -0.06, 0.64), (1.06 * sx,  0.02, 0.78), (1.08 * sx,  0.06, 0.96)],
             [(0.014, 0.013), (0.009, 0.008), (0.003, 0.003)], "Mat_ZLeafMid", 3),
            ([(1.01 * sx, -0.08, 0.80), (0.98 * sx, -0.22, 0.94), (0.88 * sx, -0.28, 1.05)],
             [(0.012, 0.011), (0.008, 0.007), (0.003, 0.003)], "Mat_ZVinePale", 2),
        ]
        _build_whip_vine(f"Vine_Main_{side}", main_pts, main_rads, main_forks, "Mat_ZLeafMid", thorns=11, thorn_l=0.032, twist=2.6 * sx)

        # Vine_Mid: arching forward-flaring thorny whip + 2-pronged claw hook
        mid_pts = [
            (0.09 * sx, -0.04, 0.72),
            (0.24 * sx, -0.12, 0.66),
            (0.40 * sx, -0.21, 0.62),
            (0.54 * sx, -0.26, 0.68),
            (0.62 * sx, -0.30, 0.80),
            (0.56 * sx, -0.35, 0.96),
        ]
        mid_rads = [(0.026, 0.024), (0.023, 0.021), (0.019, 0.018), (0.015, 0.014), (0.010, 0.009), (0.004, 0.004)]
        mid_forks = [
            ([(0.54 * sx, -0.26, 0.68), (0.68 * sx, -0.22, 0.78), (0.72 * sx, -0.16, 0.90)],
             [(0.011, 0.010), (0.007, 0.006), (0.003, 0.003)], "Mat_ZLeafMid", 2),
        ]
        _build_whip_vine(f"Vine_Mid_{side}", mid_pts, mid_rads, mid_forks, "Mat_ZVinePale", thorns=8, thorn_l=0.026, twist=2.2 * sx)

        # Vine_Back: rear upper sweeping whip crowning behind petals
        back_pts = [
            (0.08 * sx, 0.06, 0.68),
            (0.22 * sx, 0.14, 0.68),
            (0.38 * sx, 0.20, 0.74),
            (0.50 * sx, 0.18, 0.88),
            (0.56 * sx, 0.10, 1.04),
        ]
        back_rads = [(0.024, 0.022), (0.020, 0.019), (0.016, 0.015), (0.011, 0.010), (0.004, 0.004)]
        _build_whip_vine(f"Vine_Back_{side}", back_pts, back_rads, [], "Mat_ZLeafDark", thorns=7, thorn_l=0.024, twist=1.8 * sx)

    # 5. Oversized Articulated Carnivorous Blood-Flower Head (head_scale=1.38, split 4-jaw bones)
    build_head_rafflesia(
        bm, idx_map, regions, proportions=None,
        center=(0.0, -0.10, 1.04), fwd_dir=(0.0, -0.96, -0.28),
        head_scale=1.38, build_neck=False, split_jaw_regions=True,
    )

    # 6. Finalize pure-tri flat-shaded mesh & bind to 52-bone Creature Armature
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()

    def _idx_set(vlist):
        return [v.index for v in vlist if v.is_valid]

    single_assignments = {
        "Pelvis":  _idx_set(chain_verts.get("pelvis", [])),
        "Head":    _idx_set(regions.get("head", [])),
        "Jaw_Top": _idx_set(regions.get("jaw_top", [])),
        "Jaw_Bot": _idx_set(regions.get("jaw_bot", [])),
        "Jaw_L":   _idx_set(regions.get("jaw_L", [])),
        "Jaw_R":   _idx_set(regions.get("jaw_R", [])),
    }

    bone_specs = [
        ("Pelvis",   None,       (0.0,  0.02, 0.36), (0.0,  0.02, 0.48), True),
        ("Stalk_01", "Pelvis",   (0.0,  0.02, 0.48), (0.0,  0.00, 0.68), True),
        ("Stalk_02", "Stalk_01", (0.0,  0.00, 0.68), (0.0, -0.04, 0.86), True),
        ("Neck",     "Stalk_02", (0.0, -0.04, 0.86), (0.0, -0.08, 0.99), True),
        ("Head",     "Neck",     (0.0, -0.10, 1.04), (0.0, -0.26, 0.99), True),
        ("Jaw_Top",  "Head",     ( 0.00, -0.132, 1.040), ( 0.00, -0.290, 1.000), True),
        ("Jaw_Bot",  "Head",     ( 0.00, -0.132, 1.020), ( 0.00, -0.280, 0.920), True),
        ("Jaw_L",    "Head",     ( 0.04, -0.132, 1.030), ( 0.16, -0.260, 0.980), True),
        ("Jaw_R",    "Head",     (-0.04, -0.132, 1.030), (-0.16, -0.260, 0.980), True),
    ]
    chain_assignments = [
        (["Stalk_01", "Stalk_02", "Neck"], _idx_set(chain_verts.get("stalk", []))),
    ]

    for lname, sx, fy, hip, knee, ankle, foot_c in leg_configs:
        b_th, b_sh, b_ft = f"{lname}_Thigh", f"{lname}_Shin", f"{lname}_Foot"
        bone_specs.append((b_th, "Pelvis", hip, knee, True))
        bone_specs.append((b_sh, b_th,     knee, ankle, True))
        bone_specs.append((b_ft, b_sh,     ankle, foot_c, True))
        chain_assignments.append(([b_th, b_sh, b_ft], _idx_set(chain_verts[lname])))

    for side, sx in (("L", 1.0), ("R", -1.0)):
        vine_defs = (
            (f"Vine_Main_{side}", [
                (0.10 * sx, -0.01, 0.62), (0.28 * sx, -0.05, 0.50), (0.50 * sx, -0.09, 0.44),
                (0.74 * sx, -0.10, 0.48), (0.94 * sx, -0.06, 0.64), (1.02 * sx, -0.09, 0.84), (0.94 * sx, -0.15, 1.04),
            ]),
            (f"Vine_Mid_{side}", [
                (0.09 * sx, -0.04, 0.72), (0.24 * sx, -0.12, 0.66), (0.40 * sx, -0.21, 0.62),
                (0.54 * sx, -0.26, 0.68), (0.62 * sx, -0.30, 0.80), (0.56 * sx, -0.35, 0.96),
            ]),
            (f"Vine_Back_{side}", [
                (0.08 * sx, 0.06, 0.68), (0.22 * sx, 0.14, 0.68), (0.38 * sx, 0.20, 0.74),
                (0.50 * sx, 0.18, 0.88), (0.56 * sx, 0.10, 1.04),
            ]),
        )
        for vprefix, pts in vine_defs:
            v_bones = []
            parent = "Stalk_02"
            for i in range(len(pts) - 1):
                bn = f"{vprefix}_{i + 1:02d}"
                bone_specs.append((bn, parent, pts[i], pts[i + 1], True))
                v_bones.append(bn)
                parent = bn
            chain_assignments.append((v_bones, _idx_set(chain_verts[vprefix])))

    body_obj, body_tris = finalize_mesh("Mutant_Rafflesia_Body", bm, materials, collection=col_char)
    apply_box_uvs(body_obj, tex_scale=1.7)
    arm_obj = create_creature_armature("Mutant_Rafflesia_Rig", bone_specs, collection=col_rig)
    skin_creature_to_armature(
        body_obj, arm_obj, chain_assignments, single_assignments, fallback_bone="Pelvis",
    )
    return body_obj, body_tris, arm_obj, []


# ---------------------------------------------------------------------------
# MUTANT #2: SCYTHE STALKER (Ref Image 3 — Digitigrade Mantis-Blade Chitin Predator)
# ---------------------------------------------------------------------------
def build_mutant_scythe_stalker(materials, idx_map, col_char, col_gear, col_rig):
    """Hunched asymmetric chitin predator with split-mandible head & colossal bone mantis scythe."""
    bm = bmesh.new()
    regions = {}
    chain_verts = {}

    def _cadd(key, verts):
        chain_verts.setdefault(key, []).extend(verts)

    def _idx_set(vlist):
        return [v.index for v in vlist if v.is_valid]

    # 1. Hunched Gaunt Pelvis & Leaning Thoracic Stalk (Z = 0.88 .. 1.54 m, hunched toward -Y)
    _cadd("pelvis", loft_rings(bm, [
        ring_ellipse(0.0, 0.085, 0.860, 0.135, 0.098, n=10),
        ring_ellipse(0.0, 0.075, 0.945, 0.145, 0.105, n=10),
        ring_ellipse(0.0, 0.055, 1.030, 0.118, 0.092, n=10),
    ], close_caps=(True, True), mat_idx=idx_map["Mat_ZClothDirty"]))

    # Torn waist rags hanging asymmetrically around hip belt
    for rx, ry, ln, rot_y in ((-0.10, -0.02, 0.22, 0.14), (0.11, -0.01, 0.19, -0.12), (0.0, 0.15, 0.24, 0.0)):
        _cadd("pelvis", add_box(
            bm, center=(rx, ry, 0.86 - ln * 0.45), size=(0.085, 0.018, ln),
            rot=(0.12, rot_y, 0.0), taper_top=(1.2, 1.0), mat_idx=idx_map["Mat_MChitinDark"],
        ))

    # Hunched spine/ribcage trunk leaning fiercely forward (-Y) with organic diagonal carapace straps
    v_torso = loft_rings(bm, [
        ring_ellipse(0.0,  0.045, 1.030, 0.112, 0.088, n=10),
        ring_ellipse(0.0,  0.005, 1.160, 0.124, 0.098, n=10),
        ring_ellipse(0.0, -0.065, 1.300, 0.156, 0.114, n=10),
        ring_ellipse(0.0, -0.145, 1.430, 0.168, 0.118, n=10),
        ring_ellipse(0.0, -0.225, 1.525, 0.085, 0.082, n=10),
    ], close_caps=(True, True), mat_idx=idx_map["Mat_ZSkinGrey"])
    for f in {f for v in v_torso for f in v.link_faces}:
        c = f.calc_center_median()
        # Diagonal organic carapace boundary creeping over right shoulder & ribs (eliminates flat line seam)
        if c.y > -0.01 or (c.x < -0.04 + 0.18 * (c.z - 1.28) * 0.5 and c.z > 1.08):
            f.material_index = idx_map["Mat_MChitinDark"]
    _cadd("spine", v_torso)

    # Diagonal jagged chitin rib-straps & sinew bridging carapace to exposed left ribcage
    for rz, ry in ((1.38, -0.11), (1.30, -0.07), (1.22, -0.04), (1.14, 0.0)):
        _cadd("spine", _add_tapered_ribbon(
            bm, idx_map,
            [(-0.08, ry + 0.04, rz + 0.02), (-0.01, ry - 0.08, rz), (0.08, ry - 0.07, rz - 0.03), (0.12, ry + 0.02, rz - 0.04)],
            [0.028, 0.026, 0.018, 0.006], [0.012, 0.012, 0.009, 0.004],
            up_hint=(0.0, 0.0, 1.0), mat_front="Mat_MChitinMid", mat_back="Mat_MChitinDark",
        ))

    # 6 Overlapping Dorsal/Right-Shoulder Chitin Armor Carapace Plates + 8 Bone Spine Spikes
    for pz, py, prx, pry, prot in (
        (1.16, 0.055, 0.125, 0.052,  0.22),
        (1.27, 0.012, 0.145, 0.058,  0.34),
        (1.37,-0.045, 0.162, 0.064,  0.46),
        (1.46,-0.125, 0.172, 0.068,  0.58),
    ):
        _cadd("spine", add_box(
            bm, center=(-0.025, py, pz), size=(prx * 1.9, pry * 1.4, 0.095),
            rot=(prot, -0.12, 0.06), bevel=0.014, taper_top=(0.86, 0.78), mat_idx=idx_map["Mat_MChitinMid"],
        ))
    for k in range(8):
        t = k / 7.0
        pz = 1.05 + 0.45 * t
        py = 0.10 - 0.25 * (t ** 1.3)
        bp = Vector((-0.015, py, pz))
        tp = bp + Vector((0.0, 0.11 + 0.05 * math.sin(t * math.pi), 0.08))
        _cadd("spine", add_cone(bm, tuple(bp), tuple(tp), 0.015, segments=4, mat_idx=idx_map["Mat_MScytheBone"]))

    # 2. Digitigrade Reverse-Jointed Predator Legs (Hip -> Forward Knee -> High Back Hock -> 2-Claw Hoof)
    leg_configs = []
    for side, sx in (("L", 1.0), ("R", -1.0)):
        lname = f"Leg_{side}"
        hip   = (0.125 * sx,  0.06, 0.90)
        knee  = (0.215 * sx, -0.16, 0.62)
        ankle = (0.255 * sx,  0.14, 0.30)
        toe   = (0.235 * sx, -0.08, 0.02)
        leg_configs.append((lname, hip, knee, ankle, toe))

        hv, kv, av, tv = Vector(hip), Vector(knee), Vector(ankle), Vector(toe)
        l_spine = [
            tuple(hv),
            tuple(hv.lerp(kv, 0.50)),
            tuple(kv),
            tuple(kv.lerp(av, 0.50)),
            tuple(av),
            tuple(av.lerp(tv, 0.50)),
            tuple(tv + Vector((0.0, 0.0, 0.02))),
        ]
        v_leg = loft_rings(bm, _perp_chain_rings(
            l_spine, [(0.072, 0.066), (0.062, 0.056), (0.058, 0.052), (0.044, 0.042), (0.040, 0.036), (0.030, 0.028), (0.036, 0.032)], n=7,
        ), close_caps=(True, True), mat_idx=idx_map["Mat_MChitinDark"])
        for f in {f for v in v_leg for f in v.link_faces}:
            if f.calc_center_median().z < 0.34:
                f.material_index = idx_map["Mat_MChitinMid"]
        _cadd(lname, v_leg)

        # Chitin knee spur & hock spike
        _cadd(lname, add_cone(bm, tuple(kv), tuple(kv + Vector((0.03 * sx, -0.09, 0.06))), 0.018, segments=4, mat_idx=idx_map["Mat_MScytheBone"]))
        _cadd(lname, add_cone(bm, tuple(av), tuple(av + Vector((0.02 * sx, 0.09, 0.04))), 0.015, segments=4, mat_idx=idx_map["Mat_MScytheBone"]))

        # Sculpted arched chitin toe-pad + 2 forward split bone-claws & rear dewclaw grounded on Z=0.0
        _cadd(lname, _add_organic_shell(
            bm, (tv.x, tv.y - 0.01, 0.025), (0.044, 0.068, 0.026),
            mat_idx=idx_map["Mat_MChitinMid"], n=8, seed=7.2 + sx, crag=0.14,
        ))
        for cx_off, cy_t, rb in ((-0.028, -0.22, 0.017), (0.028, -0.22, 0.017), (0.0, 0.10, 0.014)):
            _cadd(lname, add_cone(
                bm, (tv.x + cx_off * 0.4, tv.y + (-0.03 if cy_t < 0 else 0.03), 0.018),
                (tv.x + cx_off, cy_t, 0.006), rb, segments=5, mat_idx=idx_map["Mat_MScytheBone"],
            ))

    # 3. Colossal Right Bone-Scythe Arm (X < 0)
    sc_sh = (-0.17, -0.12, 1.44)
    sc_up = (-0.28, -0.15, 1.40)
    sc_el = (-0.38, -0.18, 1.12)
    sc_wr = (-0.46, -0.22, 0.86)
    sc_bd = (-0.42, -0.44, 0.34)
    sc_hk = (-0.31, -0.56, 0.16)

    # Bulky armored shoulder pauldrons + upper/forearm
    _cadd("scythe", add_box(
        bm, center=(-0.23, -0.13, 1.44), size=(0.16, 0.16, 0.14),
        rot=(0.15, -0.25, 0.10), bevel=0.020, mat_idx=idx_map["Mat_MChitinMid"],
    ))
    _cadd("scythe", loft_rings(bm, _perp_chain_rings(
        [sc_sh, sc_up, sc_el, sc_wr],
        [(0.056, 0.056), (0.054, 0.052), (0.046, 0.046), (0.042, 0.038)], n=7,
    ), close_caps=(True, True), mat_idx=idx_map["Mat_MChitinDark"]))
    for sp in range(3):
        sb = Vector(sc_el).lerp(Vector(sc_wr), 0.25 + 0.32 * sp)
        _cadd("scythe", add_cone(bm, tuple(sb), tuple(sb + Vector((-0.07, 0.04, 0.05))), 0.012, segments=4, mat_idx=idx_map["Mat_MScytheBone"]))

    # Massive curved 1.05m Mantis Bone Scythe Blade + blood edge & secondary hook spur
    blade_pts = [
        sc_wr,
        (-0.49, -0.28, 0.68),
        (-0.46, -0.36, 0.50),
        sc_bd,
        (-0.37, -0.51, 0.24),
        sc_hk,
    ]
    v_blade = _add_tapered_ribbon(
        bm, idx_map, blade_pts,
        [0.088, 0.115, 0.102, 0.080, 0.048, 0.008],
        [0.036, 0.034, 0.028, 0.022, 0.014, 0.006],
        up_hint=(1.0, 0.0, 0.0), mat_front="Mat_MScytheBone", mat_back="Mat_MChitinMid",
    )
    for f in {f for v in v_blade for f in v.link_faces}:
        if f.calc_center_median().y < -0.43:
            f.material_index = idx_map["Mat_ZBloodDried"]
    _cadd("scythe", v_blade)
    _cadd("scythe", add_cone(bm, sc_bd, (-0.30, -0.32, 0.42), 0.022, segments=5, mat_idx=idx_map["Mat_MScytheBone"]))
    # 5 jagged serrated bone teeth along inner cutting edge of mantis scythe
    for k in range(5):
        t = 0.22 + 0.15 * k
        sb = Vector(sc_wr).lerp(Vector(sc_bd), t)
        st = sb + Vector((0.045, -0.035, 0.022))
        _cadd("scythe", add_cone(bm, tuple(sb), tuple(st), 0.011, segments=4, mat_idx=idx_map["Mat_ZBloodFresh"]))

    # 4. Emaciated Left Grasping Claw Arm (X > 0)
    cl_sh = (0.16, -0.12, 1.40)
    cl_up = (0.24, -0.16, 1.36)
    cl_el = (0.29, -0.14, 1.10)
    cl_wr = (0.26, -0.28, 0.90)
    cl_hd = (0.21, -0.36, 0.78)
    _cadd("clutch", loft_rings(bm, _perp_chain_rings(
        [cl_sh, cl_up, cl_el, cl_wr, cl_hd],
        [(0.038, 0.036), (0.034, 0.032), (0.028, 0.028), (0.024, 0.020), (0.026, 0.016)], n=6,
    ), close_caps=(True, True), mat_idx=idx_map["Mat_ZSkinGrey"]))
    # Sculpted slender fleshy clutching palm + 4 multi-segment claws + opposing 5th thumb
    _cadd("clutch", _add_organic_shell(
        bm, cl_hd, (0.032, 0.028, 0.024), rot=(0.2, 0.1, -0.3),
        mat_idx=idx_map["Mat_ZSkinGrey"], n=8, seed=8.8, crag=0.14,
    ))
    for f_i in range(4):
        fo = (f_i - 1.5) * 0.015
        fb = Vector(cl_hd) + Vector((fo * 0.4, fo, 0.0))
        fm = fb + Vector((-0.02, -0.045, -0.055))
        ft = fm + Vector((-0.04, -0.015, -0.045))
        _cadd("clutch", loft_rings(bm, [
            ring_ellipse(fb.x, fb.y, fb.z, 0.009, 0.009, n=5),
            ring_ellipse(fm.x, fm.y, fm.z, 0.006, 0.006, n=5),
            ring_ellipse(ft.x, ft.y, ft.z, 0.002, 0.002, n=5),
        ], close_caps=(True, True), mat_idx=idx_map["Mat_MScytheBone"]))
    tb = Vector(cl_hd) + Vector((-0.018, -0.018, 0.008))
    tm = tb + Vector((-0.030, -0.028, -0.024))
    tt = tm + Vector((-0.018, -0.016, -0.032))
    _cadd("clutch", loft_rings(bm, [
        ring_ellipse(tb.x, tb.y, tb.z, 0.010, 0.009, n=5),
        ring_ellipse(tm.x, tm.y, tm.z, 0.006, 0.006, n=5),
        ring_ellipse(tt.x, tt.y, tt.z, 0.002, 0.002, n=5),
    ], close_caps=(True, True), mat_idx=idx_map["Mat_MScytheBone"]))

    # 5. Insectoid Split-Mandible Head mounted low/forward at (0, -0.28, 1.56)
    build_head_scythe_stalker(bm, idx_map, regions, center=(0.0, -0.28, 1.56), fwd_dir=(0.0, -0.96, -0.28), scale=1.0)

    # 6. Finalize pure-tri mesh & bind to 29-bone Creature Rig
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()

    single_assignments = {
        "Pelvis":     _idx_set(chain_verts["pelvis"]),
        "Head":       _idx_set(regions["head"]),
        "Mandible_L": _idx_set(regions["mandible_L"]),
        "Mandible_R": _idx_set(regions["mandible_R"]),
        "Jaw_Bot":    _idx_set(regions["jaw_bot"]),
    }

    bone_specs = [
        ("Pelvis",          None,       (0.0,  0.08, 0.88), (0.0,  0.06, 1.02), True),
        ("Spine_01",        "Pelvis",   (0.0,  0.06, 1.02), (0.0, -0.02, 1.24), True),
        ("Spine_02",        "Spine_01", (0.0, -0.02, 1.24), (0.0, -0.14, 1.44), True),
        ("Hunch_Neck",      "Spine_02", (0.0, -0.14, 1.44), (0.0, -0.24, 1.53), True),
        ("Head",            "Hunch_Neck",(0.0, -0.26, 1.55), (0.0, -0.40, 1.51), True),
        ("Mandible_L",      "Head",     ( 0.05, -0.32, 1.54), ( 0.04, -0.48, 1.49), True),
        ("Mandible_R",      "Head",     (-0.05, -0.32, 1.54), (-0.04, -0.48, 1.49), True),
        ("Jaw_Bot",         "Head",     ( 0.00, -0.32, 1.51), ( 0.00, -0.46, 1.42), True),
        ("Tongue_01",       "Jaw_Bot",  ( 0.00, -0.34, 1.49), ( 0.00, -0.42, 1.40), True),
        ("Tongue_02",       "Tongue_01",( 0.00, -0.42, 1.40), ( 0.00, -0.44, 1.32), True),
        ("Scythe_Shoulder", "Spine_02", sc_sh, sc_up, True),
        ("Scythe_Upper",    "Scythe_Shoulder", sc_up, sc_el, True),
        ("Scythe_Fore",     "Scythe_Upper",    sc_el, sc_wr, True),
        ("Scythe_Blade",    "Scythe_Fore",     sc_wr, sc_bd, True),
        ("Scythe_Hook",     "Scythe_Blade",    sc_bd, sc_hk, True),
        ("Clutch_Shoulder", "Spine_02", cl_sh, cl_up, True),
        ("Clutch_Upper",    "Clutch_Shoulder", cl_up, cl_el, True),
        ("Clutch_Fore",     "Clutch_Upper",    cl_el, cl_wr, True),
        ("Clutch_Hand",     "Clutch_Fore",     cl_wr, cl_hd, True),
    ]
    chain_assignments = [
        (["Spine_01", "Spine_02", "Hunch_Neck"], _idx_set(chain_verts["spine"])),
        (["Tongue_01", "Tongue_02"],             _idx_set(regions["tongue"])),
        (["Scythe_Shoulder", "Scythe_Upper", "Scythe_Fore", "Scythe_Blade", "Scythe_Hook"], _idx_set(chain_verts["scythe"])),
        (["Clutch_Shoulder", "Clutch_Upper", "Clutch_Fore", "Clutch_Hand"],                 _idx_set(chain_verts["clutch"])),
    ]
    for lname, hip, knee, ankle, toe in leg_configs:
        b1, b2, b3, b4 = f"{lname}_Thigh", f"{lname}_Shin", f"{lname}_Ankle", f"{lname}_Toe"
        bone_specs.extend([
            (b1, "Pelvis", hip,   knee,  True),
            (b2, b1,       knee,  ankle, True),
            (b3, b2,       ankle, toe,   True),
            (b4, b3,       toe,   (toe[0], toe[1] - 0.12, toe[2]), True),
        ])
        chain_assignments.append(([b1, b2, b3, b4], _idx_set(chain_verts[lname])))

    body_obj, body_tris = finalize_mesh("Mutant_Scythe_Stalker_Body", bm, materials, collection=col_char)
    apply_box_uvs(body_obj, tex_scale=1.7)
    arm_obj = create_creature_armature("Mutant_Scythe_Stalker_Rig", bone_specs, collection=col_rig)
    skin_creature_to_armature(body_obj, arm_obj, chain_assignments, single_assignments, fallback_bone="Pelvis")
    return body_obj, body_tris, arm_obj, []


# ---------------------------------------------------------------------------
# MUTANT #3: THORN SHROUD SERAPH (Ref Image 1 — Tri-Stilt Bone-Filigree Crown Beast)
# ---------------------------------------------------------------------------
def build_mutant_thorn_shroud(materials, idx_map, col_char, col_gear, col_rig):
    """Tall haunting eyeless filigree monster on 3 curved blade-stilts with 6 articulated razor wings."""
    bm = bmesh.new()
    regions = {}
    chain_verts = {}

    def _cadd(key, verts):
        chain_verts.setdefault(key, []).extend(verts)

    def _idx_set(vlist):
        return [v.index for v in vlist if v.is_valid]

    # 1. Pale Gaunt Pelvis & Torso Sheathed in 14 Baroque Bone-Blade Filigree Ribbons (Z = 0.84..1.54m)
    _cadd("pelvis", loft_rings(bm, [
        ring_ellipse(0.0, 0.0, 0.82, 0.122, 0.088, n=10),
        ring_ellipse(0.0, 0.0, 0.90, 0.128, 0.092, n=10),
        ring_ellipse(0.0, 0.0, 0.97, 0.105, 0.080, n=10),
    ], close_caps=(True, True), mat_idx=idx_map["Mat_MShroudDark"]))

    _cadd("torso", loft_rings(bm, [
        ring_ellipse(0.0,  0.00, 0.97, 0.102, 0.078, n=10),
        ring_ellipse(0.0, -0.01, 1.12, 0.118, 0.086, n=10),
        ring_ellipse(0.0, -0.02, 1.30, 0.148, 0.102, n=10),
        ring_ellipse(0.0, -0.02, 1.46, 0.156, 0.096, n=10),
        ring_ellipse(0.0, -0.03, 1.56, 0.062, 0.060, n=10),
    ], close_caps=(True, True), mat_idx=idx_map["Mat_MShroudSkin"]))

    # 6 Creeping dark root-veins snaking over pale chest & collar + diagonal filigree lattice
    for sx in (1.0, -1.0):
        _cadd("torso", _add_tapered_ribbon(
            bm, idx_map,
            [(0.02 * sx, -0.095, 1.50), (0.06 * sx, -0.102, 1.38), (0.03 * sx, -0.096, 1.24), (0.07 * sx, -0.088, 1.08)],
            [0.012, 0.014, 0.011, 0.004], [0.008, 0.008, 0.006, 0.003],
            up_hint=(0.0, -1.0, 0.0), mat_front="Mat_MShroudDark", mat_back="Mat_MShroudDark",
        ))
    # 14 Diagonal Organic Filigree Ribbons crisscrossing torso & ribs like sculpted latticework (Ref Image 1)
    for k in range(14):
        sx = 1.0 if k % 2 == 0 else -1.0
        row = k // 2
        z0 = 0.96 + 0.078 * row
        tilt = 0.095 if (row % 2 == 0) else -0.075
        pts = [
            (0.015 * sx, -0.092, z0 + tilt * 0.4),
            (0.088 * sx, -0.106, z0 + tilt),
            (0.158 * sx, -0.042, z0 + tilt * 0.2),
            (0.132 * sx,  0.076, z0 - tilt * 0.6),
            (0.025 * sx,  0.104, z0 - tilt * 0.2),
        ]
        _cadd("torso", _add_tapered_ribbon(
            bm, idx_map, pts, [0.020, 0.036, 0.032, 0.024, 0.008], [0.010, 0.012, 0.010, 0.008, 0.004],
            up_hint=(0.0, -1.0, 0.35), twist_total=0.85 * sx,
            mat_front="Mat_MShroudBone", mat_back="Mat_MShroudDark",
        ))

    # 2. 3 Sinuous Curved Organic Blade-Stilt Legs (`Stilt_FL`, `Stilt_FR`, `Stilt_Rear`) poised on Z=0.0
    stilt_defs = (
        ("Stilt_FL",   [( 0.10, -0.04, 0.86), ( 0.22, -0.12, 0.56), ( 0.27, -0.18, 0.26), ( 0.24, -0.20, 0.015)]),
        ("Stilt_FR",   [(-0.10, -0.04, 0.86), (-0.22, -0.12, 0.56), (-0.27, -0.18, 0.26), (-0.24, -0.20, 0.015)]),
        ("Stilt_Rear", [( 0.00,  0.08, 0.86), ( 0.00,  0.22, 0.56), ( 0.00,  0.28, 0.26), ( 0.00,  0.24, 0.015)]),
    )
    for sname, spts in stilt_defs:
        _cadd(sname, loft_rings(bm, _perp_chain_rings(
            spts, [(0.056, 0.052), (0.046, 0.042), (0.032, 0.028), (0.012, 0.010)], n=6,
        ), close_caps=(True, True), mat_idx=idx_map["Mat_MShroudDark"]))
        # Filigree bone spur ribbon wrapping down outer blade of each stilt
        spur_pts = [
            (spts[0][0] * 1.15, spts[0][1] * 1.15, 0.84),
            (spts[1][0] * 1.18, spts[1][1] * 1.18, 0.58),
            (spts[2][0] * 1.12, spts[2][1] * 1.12, 0.26),
            (spts[3][0],        spts[3][1],        0.005),
        ]
        _cadd(sname, _add_tapered_ribbon(
            bm, idx_map, spur_pts, [0.052, 0.064, 0.044, 0.010], [0.018, 0.018, 0.014, 0.006],
            up_hint=(0.0, 0.0, 1.0), mat_front="Mat_MShroudBone", mat_back="Mat_MShroudDark",
        ))
        _cadd(sname, add_cone(
            bm, spts[2], (spts[2][0] * 1.25, spts[2][1] * 1.25, 0.42),
            0.018, segments=4, mat_idx=idx_map["Mat_MShroudBone"],
        ))
        _cadd(sname, _add_organic_shell(
            bm, (spts[2][0] * 1.02, spts[2][1] * 1.02, 0.24), (0.032, 0.032, 0.042),
            mat_idx=idx_map["Mat_MShroudBone"], n=6, seed=2.4, crag=0.18,
        ))

    # 3. 6 Articulated Sweeping Razor-Blade Wings (3 per side behind shoulder/scapula)
    wing_defs = []
    for side, sx in (("L", 1.0), ("R", -1.0)):
        wing_defs.extend([
            (f"Wing_{side}1", [(0.11 * sx, 0.05, 1.46), (0.34 * sx, 0.10, 1.62), (0.60 * sx, 0.06, 1.84), (0.82 * sx, -0.02, 2.02)],
             [0.048, 0.068, 0.046, 0.008]),
            (f"Wing_{side}2", [(0.12 * sx, 0.06, 1.38), (0.36 * sx, 0.14, 1.48), (0.64 * sx, 0.12, 1.60), (0.86 * sx,  0.04, 1.72)],
             [0.044, 0.062, 0.042, 0.008]),
            (f"Wing_{side}3", [(0.10 * sx, 0.07, 1.28), (0.32 * sx, 0.16, 1.30), (0.54 * sx, 0.14, 1.36), (0.72 * sx,  0.06, 1.44)],
             [0.040, 0.052, 0.036, 0.007]),
        ])
    for wname, wpts, ww in wing_defs:
        _cadd(wname, _add_tapered_ribbon(
            bm, idx_map, wpts, ww, [0.018, 0.016, 0.012, 0.004],
            up_hint=(0.0, -1.0, 0.3), twist_total=0.45 * (1.0 if "_L" in wname else -1.0),
            mat_front="Mat_MShroudBone", mat_back="Mat_MShroudDark",
        ))

    # 4. Elongated Veined Pale Arms (`Arm_L/R`) with Dark Tendril Veins & Slender Claws
    arm_configs = []
    for side, sx in (("L", 1.0), ("R", -1.0)):
        aname = f"Arm_{side}"
        sh = (0.16 * sx, -0.02, 1.44)
        el = (0.34 * sx, -0.03, 1.18)
        wr = (0.46 * sx, -0.08, 0.94)
        hd = (0.51 * sx, -0.11, 0.80)
        arm_configs.append((aname, sh, el, wr, hd))
        _cadd(aname, loft_rings(bm, _perp_chain_rings(
            [sh, el, wr, hd], [(0.042, 0.040), (0.032, 0.030), (0.024, 0.022), (0.026, 0.015)], n=7,
        ), close_caps=(True, True), mat_idx=idx_map["Mat_MShroudSkin"]))
        # Shoulder carapace blade + dark branching vein ridges along forearm
        _cadd(aname, _add_tapered_ribbon(
            bm, idx_map,
            [(0.14 * sx, -0.04, 1.47), (0.28 * sx, -0.05, 1.49), (0.42 * sx, -0.02, 1.42)],
            [0.055, 0.048, 0.008], [0.016, 0.014, 0.004],
            up_hint=(0.0, 0.0, 1.0), mat_front="Mat_MShroudBone", mat_back="Mat_MShroudDark",
        ))
        _cadd(aname, _add_tapered_ribbon(
            bm, idx_map,
            [(0.28 * sx, -0.01, 1.24), (0.38 * sx, -0.04, 1.06), (0.46 * sx, -0.07, 0.92)],
            [0.014, 0.012, 0.005], [0.010, 0.008, 0.004],
            up_hint=(sx, 0.0, 0.0), mat_front="Mat_MShroudDark", mat_back="Mat_MShroudDark",
        ))
        _cadd(aname, _add_organic_shell(
            bm, hd, (0.026, 0.028, 0.032), mat_idx=idx_map["Mat_MShroudSkin"], n=6, seed=4.2 + sx, crag=0.14,
        ))
        for k in range(4):
            fo = (k - 1.5) * 0.014
            bp = Vector(hd) + Vector((0.0, fo, 0.0))
            tp = bp + Vector((0.035 * sx, fo * 0.4, -0.085))
            _cadd(aname, add_cone(bm, tuple(bp), tuple(tp), 0.006, segments=4, mat_idx=idx_map["Mat_MShroudBone"]))
        _cadd(aname, add_cone(
            bm, (hd[0] - 0.012 * sx, hd[1] - 0.018, hd[2] + 0.008),
            (hd[0] - 0.038 * sx, hd[1] - 0.045, hd[2] - 0.048),
            0.006, segments=4, mat_idx=idx_map["Mat_MShroudBone"],
        ))

    # 5. Eyeless Shrouded Head + Screaming Jaw + Towering Blade Crown (`crown_L/C/R`)
    build_head_thorn_shroud(bm, idx_map, regions, center=(0.0, -0.04, 1.66), fwd_dir=(0.0, -0.98, 0.18), scale=1.08)

    bm.verts.ensure_lookup_table()
    bm.verts.index_update()

    single_assignments = {
        "Pelvis":     _idx_set(chain_verts["pelvis"]),
        "Head":       _idx_set(regions.get("head", [])),
        "Jaw_Scream": _idx_set(regions.get("jaw_scream", [])),
        "Crown_L":    _idx_set(regions.get("crown_L", [])),
        "Crown_C":    _idx_set(regions.get("crown_C", [])),
        "Crown_R":    _idx_set(regions.get("crown_R", [])),
    }

    bone_specs = [
        ("Pelvis",     None,       (0.0,  0.00, 0.84), (0.0,  0.00, 0.96), True),
        ("Spine_01",   "Pelvis",   (0.0,  0.00, 0.96), (0.0, -0.01, 1.22), True),
        ("Spine_02",   "Spine_01", (0.0, -0.01, 1.22), (0.0, -0.02, 1.48), True),
        ("Neck",       "Spine_02", (0.0, -0.02, 1.48), (0.0, -0.03, 1.60), True),
        ("Head",       "Neck",     (0.0, -0.04, 1.64), (0.0, -0.20, 1.68), True),
        ("Jaw_Scream", "Head",     (0.0, -0.04, 1.59), (0.0, -0.14, 1.54), True),
        ("Crown_L",    "Head",     ( 0.05, -0.04, 1.72), ( 0.09, -0.04, 2.08), True),
        ("Crown_C",    "Head",     ( 0.00, -0.05, 1.72), ( 0.00, -0.06, 2.12), True),
        ("Crown_R",    "Head",     (-0.05, -0.04, 1.72), (-0.09, -0.04, 2.08), True),
    ]
    chain_assignments = [
        (["Spine_01", "Spine_02", "Neck"], _idx_set(chain_verts["torso"])),
    ]
    for sname, spts in stilt_defs:
        sbones = []
        par = "Pelvis"
        for i in range(len(spts) - 1):
            bn = f"{sname}_{i + 1:02d}"
            bone_specs.append((bn, par, spts[i], spts[i + 1], True))
            sbones.append(bn)
            par = bn
        chain_assignments.append((sbones, _idx_set(chain_verts[sname])))

    for wname, wpts, _ in wing_defs:
        wbones = []
        par = "Spine_02"
        for i in range(len(wpts) - 1):
            bn = f"{wname}_{i + 1:02d}"
            bone_specs.append((bn, par, wpts[i], wpts[i + 1], True))
            wbones.append(bn)
            par = bn
        chain_assignments.append((wbones, _idx_set(chain_verts[wname])))

    for aname, sh, el, wr, hd in arm_configs:
        b1, b2, b3 = f"{aname}_Upper", f"{aname}_Fore", f"{aname}_Hand"
        bone_specs.extend([
            (b1, "Spine_02", sh, el, True),
            (b2, b1,         el, wr, True),
            (b3, b2,         wr, hd, True),
        ])
        chain_assignments.append(([b1, b2, b3], _idx_set(chain_verts[aname])))

    body_obj, body_tris = finalize_mesh("Mutant_Thorn_Shroud_Body", bm, materials, collection=col_char)
    apply_box_uvs(body_obj, tex_scale=1.7)
    arm_obj = create_creature_armature("Mutant_Thorn_Shroud_Rig", bone_specs, collection=col_rig)
    skin_creature_to_armature(body_obj, arm_obj, chain_assignments, single_assignments, fallback_bone="Pelvis")
    return body_obj, body_tris, arm_obj, []


# ---------------------------------------------------------------------------
# MUTANT #4: ARACHNID MAW (6-Legged Chitin Belly-Maw & Scorpion Stinger Crawler)
# ---------------------------------------------------------------------------
def build_mutant_arachnid_maw(materials, idx_map, col_char, col_gear, col_rig):
    """Low-slung 6-legged chitin crawler with 6-eyed front split-maw, acid sacs & scorpion tail."""
    bm = bmesh.new()
    regions = {}
    chain_verts = {}

    def _cadd(key, verts):
        chain_verts.setdefault(key, []).extend(verts)

    def _idx_set(vlist):
        return [v.index for v in vlist if v.is_valid]

    # 1. Armored Front Thorax (`Pelvis`) & Bloated Acid-Sac Abdomen (`Abdomen`)
    _cadd("pelvis", loft_rings(bm, [
        ring_ellipse(0.0, -0.32, 0.48, 0.165, 0.105, n=10),
        ring_ellipse(0.0, -0.14, 0.46, 0.215, 0.132, n=10),
        ring_ellipse(0.0,  0.04, 0.45, 0.185, 0.118, n=10),
    ], close_caps=(True, True), mat_idx=idx_map["Mat_MArachChitin"]))

    v_abd = loft_rings(bm, [
        ring_ellipse(0.0, 0.04, 0.46, 0.175, 0.115, n=10),
        ring_ellipse(0.0, 0.24, 0.51, 0.265, 0.175, n=10),
        ring_ellipse(0.0, 0.44, 0.54, 0.230, 0.155, n=10),
        ring_ellipse(0.0, 0.58, 0.52, 0.105, 0.085, n=10),
    ], close_caps=(True, True), mat_idx=idx_map["Mat_MArachChitin"])
    for f in {f for v in v_abd for f in v.link_faces}:
        if f.calc_center_median().z < 0.44:
            f.material_index = idx_map["Mat_MArachUnder"]
    _cadd("abdomen", v_abd)

    # 6 Glowing Pulsing Dorsal Acid Sacs studded on bloated abdomen + armored carapace ribs
    for sx in (1.0, -1.0):
        for py, pz, rx in ((0.18, 0.63, 0.072), (0.31, 0.66, 0.088), (0.43, 0.64, 0.064)):
            _cadd("abdomen", add_box(
                bm, center=(0.11 * sx, py, pz), size=(rx, rx * 1.25, rx * 0.90),
                rot=(0.15, 0.25 * sx, 0.10 * sx), bevel=rx * 0.28, mat_idx=idx_map["Mat_ZAcidGlow"],
            ))
    for k in range(3):
        yy = -0.18 + 0.12 * k
        _cadd("pelvis", add_box(
            bm, center=(0.0, yy, 0.58), size=(0.34 - 0.03 * k, 0.10, 0.042),
            rot=(-0.18, 0.0, 0.0), bevel=0.010, mat_idx=idx_map["Mat_MChitinMid"],
        ))

    # 2. 4-Bone Curling Overhead Scorpion Stinger Tail (`Tail_01..04`)
    tail_pts = [(0.0, 0.54, 0.54), (0.0, 0.62, 0.80), (0.0, 0.44, 1.04), (0.0, 0.16, 1.14), (0.0, -0.12, 1.02)]
    v_tail = loft_rings(bm, _perp_chain_rings(
        tail_pts, [(0.095, 0.085), (0.075, 0.068), (0.056, 0.052), (0.042, 0.038), (0.018, 0.018)], n=7,
    ), close_caps=(True, True), mat_idx=idx_map["Mat_MArachChitin"])
    _cadd("tail", v_tail)
    # Glowing acid venom bulb + razor curved stinger barb at tail tip
    _cadd("tail", add_box(
        bm, center=(0.0, 0.14, 1.13), size=(0.082, 0.115, 0.078),
        rot=(-0.25, 0.0, 0.0), bevel=0.022, mat_idx=idx_map["Mat_ZAcidGlow"],
    ))
    _cadd("tail", add_cone(bm, (0.0, 0.10, 1.12), (0.0, -0.16, 0.98), 0.026, segments=5, mat_idx=idx_map["Mat_MScytheBone"]))

    # 3. 6 Tall Arching Insectoid Spider-Legs (`Leg_FL/FR`, `Leg_ML/MR`, `Leg_BL/BR`)
    leg_configs = []
    for tag, fy_h, fy_k, fy_f, rad_k, z_k in (
        ("F", -0.22, -0.46, -0.62, 0.68, 0.78),
        ("M",  0.00, -0.02, -0.04, 0.86, 0.82),
        ("B",  0.24,  0.48,  0.64, 0.72, 0.76),
    ):
        for side, sx in (("L", 1.0), ("R", -1.0)):
            lname = f"Leg_{tag}{side}"
            hip   = (0.18 * sx, fy_h, 0.45)
            knee  = (rad_k * sx, fy_k, z_k)
            ankle = (rad_k * 1.12 * sx, fy_f, 0.24)
            toe   = (rad_k * 1.04 * sx, fy_f * 1.06, 0.008)
            leg_configs.append((lname, hip, knee, ankle, toe))

            _cadd(lname, loft_rings(bm, _perp_chain_rings(
                [hip, knee, ankle, toe],
                [(0.056, 0.052), (0.046, 0.042), (0.028, 0.026), (0.008, 0.008)], n=6,
            ), close_caps=(True, True), mat_idx=idx_map["Mat_MArachChitin"]))
            _cadd(lname, add_box(
                bm, center=(knee[0] * 0.96, knee[1], knee[2] + 0.025),
                size=(0.082, 0.088, 0.058), rot=(0.2, 0.35 * sx, 0.0),
                bevel=0.012, mat_idx=idx_map["Mat_MChitinMid"],
            ))
            _cadd(lname, add_cone(
                bm, knee, (knee[0] + 0.06 * sx, fy_k, z_k + 0.10),
                0.020, segments=4, mat_idx=idx_map["Mat_MScytheBone"],
            ))
            _cadd(lname, add_cone(
                bm, ankle, (toe[0] + 0.04 * sx, toe[1] - 0.04 if fy_f <= 0 else toe[1] + 0.04, 0.004),
                0.016, segments=4, mat_idx=idx_map["Mat_MScytheBone"],
            ))

    # 4. Colossal 6-Eyed Front Split-Maw & Articulated Palps
    build_head_arachnid_maw(bm, idx_map, regions, center=(0.0, -0.34, 0.48), fwd_dir=(0.0, -0.98, -0.18), scale=1.05)

    bm.verts.ensure_lookup_table()
    bm.verts.index_update()

    single_assignments = {
        "Pelvis":  _idx_set(chain_verts["pelvis"]),
        "Abdomen": _idx_set(chain_verts["abdomen"]),
        "Head":    _idx_set(regions["head"]),
        "Maw_Top": _idx_set(regions["maw_top"]),
        "Maw_Bot": _idx_set(regions["maw_bot"]),
    }

    bone_specs = [
        ("Pelvis",    None,      (0.0,  0.02, 0.44), (0.0, -0.18, 0.46), True),
        ("Abdomen",   "Pelvis",  (0.0,  0.04, 0.46), (0.0,  0.48, 0.52), True),
        ("Head",      "Pelvis",  (0.0, -0.28, 0.48), (0.0, -0.46, 0.45), True),
        ("Maw_Top",   "Head",    (0.0, -0.32, 0.52), (0.0, -0.56, 0.50), True),
        ("Maw_Bot",   "Head",    (0.0, -0.32, 0.44), (0.0, -0.54, 0.36), True),
        ("Palp_L_01", "Head",    ( 0.16, -0.34, 0.46), ( 0.25, -0.46, 0.44), True),
        ("Palp_L_02", "Palp_L_01",( 0.25, -0.46, 0.44), ( 0.19, -0.60, 0.40), True),
        ("Palp_R_01", "Head",    (-0.16, -0.34, 0.46), (-0.25, -0.46, 0.44), True),
        ("Palp_R_02", "Palp_R_01",(-0.25, -0.46, 0.44), (-0.19, -0.60, 0.40), True),
    ]
    tail_bones = []
    t_par = "Abdomen"
    for i in range(4):
        bn = f"Tail_{i + 1:02d}"
        bone_specs.append((bn, t_par, tail_pts[i], tail_pts[i + 1], True))
        tail_bones.append(bn)
        t_par = bn

    chain_assignments = [
        (tail_bones,                   _idx_set(chain_verts["tail"])),
        (["Palp_L_01", "Palp_L_02"],   _idx_set(regions["palp_L"])),
        (["Palp_R_01", "Palp_R_02"],   _idx_set(regions["palp_R"])),
    ]
    for lname, hip, knee, ankle, toe in leg_configs:
        b1, b2, b3 = f"{lname}_Coxa", f"{lname}_Femur", f"{lname}_Tarsus"
        bone_specs.extend([
            (b1, "Pelvis", hip,   knee,  True),
            (b2, b1,       knee,  ankle, True),
            (b3, b2,       ankle, toe,   True),
        ])
        chain_assignments.append(([b1, b2, b3], _idx_set(chain_verts[lname])))

    body_obj, body_tris = finalize_mesh("Mutant_Arachnid_Maw_Body", bm, materials, collection=col_char)
    apply_box_uvs(body_obj, tex_scale=1.7)
    arm_obj = create_creature_armature("Mutant_Arachnid_Maw_Rig", bone_specs, collection=col_rig)
    skin_creature_to_armature(body_obj, arm_obj, chain_assignments, single_assignments, fallback_bone="Pelvis")
    return body_obj, body_tris, arm_obj, []


# ---------------------------------------------------------------------------
# MUTANT #1b (PREVIOUS EXPERIMENT): FUNGAL BLOOM
# ---------------------------------------------------------------------------
def build_mutant_fungal_bloom(materials, idx_map, col_char, col_gear, col_rig):
    P = make_proportions(height=1.80, female=False, shoulder_scale=0.98)
    bm = bmesh.new()
    regions = {}

    build_head_fungal_bloom(
        bm, idx_map, regions, P, skin_mat="Mat_ZSkinGrey",
    )
    T = _build_zombie_base(
        bm, idx_map, regions, P,
        shirt_mat="Mat_OliveDark", sleeve_mat="Mat_OliveDark",
        pants_mat="Mat_ZClothDirty", skin_mat="Mat_ZSkinGrey",
        stain_mat="Mat_ZFungusDark", boot_mat="Mat_Boots",
        body_type="gaunt", bare_arm_R=True, torn_pant_L=True,
        finger_len_mul=1.18, torso_stain="blood_chest",
    )
    s = T["s"]

    _tag(_add_jagged_rip_cuff(
        bm, (0.0, 0.004 * s), T["pelvis_rx"] * 1.04, 0.104 * s,
        0.905 * s, "Z", idx_map["Mat_OliveDark"], amp=0.022 * s, n=12,
    ), regions, "torso")
    for sx_s, y_s, ang_s, d_s in ((1.0, -0.01, -0.2, 0.13), (-1.0, -0.01, 0.2, 0.15), (0.6, 0.08, 0.1, 0.14), (-0.6, 0.08, -0.1, 0.12)):
        _tag(add_box(
            bm,
            center=(sx_s * (T["pelvis_rx"] * 0.85), y_s * s, (0.905 - 0.36 * d_s) * s),
            size=(0.042 * s, 0.012 * s, d_s * s),
            rot=(0.08 * (1 if y_s > 0 else -1), sx_s * 0.12, ang_s),
            taper_top=(1.15, 1.0),
            mat_idx=idx_map["Mat_OliveDark"],
        ), regions, "hips_soft")
    _tag(loft_rings(bm, [
        ring_ellipse(0.0, 0.004 * s, 0.920 * s, T["pelvis_rx"] + 0.010 * s, 0.106 * s, n=10),
        ring_ellipse(0.0, 0.004 * s, 0.962 * s, T["pelvis_rx"] + 0.010 * s, 0.106 * s, n=10),
    ], close_caps=(True, True), mat_idx=idx_map["Mat_BeltLeather"]), regions, "hips_rigid")

    torso_fans = [
        ((-0.095,  0.095, 1.385), (-0.42,  0.65, 0.62), (0.0,  0.25, 1.0), 0.145, 112.0, 0.018, 11),
        ((-0.115,  0.075, 1.435), (-0.55,  0.42, 0.72), (0.1,  0.20, 1.0), 0.120, 106.0, 0.016, 12),
        ((-0.075,  0.112, 1.295), (-0.30,  0.82, 0.45), (0.0,  0.30, 1.0), 0.115, 104.0, 0.015, 13),
        ((-0.032,  0.090, 1.448), (-0.20,  0.72, 0.66), (0.0,  0.25, 1.0), 0.098, 106.0, 0.014, 16),
        (( 0.038,  0.088, 1.410), ( 0.32,  0.78, 0.54), (0.0,  0.25, 1.0), 0.092, 102.0, 0.014, 17),
        (( 0.064, -0.084, 1.375), ( 0.48, -0.78, 0.40), (0.0, -0.25, 1.0), 0.092, 102.0, 0.014, 14),
        (( 0.086, -0.070, 1.335), ( 0.62, -0.68, 0.36), (0.0, -0.20, 1.0), 0.078,  96.0, 0.012, 15),
    ]
    for pos, ndir, udir, rad, spr, th, seed in torso_fans:
        _tag(_add_fungal_fan(
            bm, idx_map,
            origin=(pos[0] * s, pos[1] * s, pos[2] * s),
            normal_dir=ndir, up_dir=udir,
            radius=rad * s, spread_deg=spr, thickness=th * s, seed=seed,
        ), regions, "torso")

    ay, az = P["arm"][1], P["arm"][2]
    _tag(add_cylinder(
        bm, (-0.46 * s, ay - 0.032 * s, az + 0.012 * s), (-0.64 * s, ay + 0.018 * s, az - 0.022 * s),
        0.007 * s, 0.004 * s, segments=5, mat_idx=idx_map["Mat_ZFungusRoot"],
    ), regions, "arm_R")
    _tag(add_cylinder(
        bm, (-0.52 * s, ay + 0.026 * s, az + 0.018 * s), (-0.66 * s, ay - 0.022 * s, az + 0.008 * s),
        0.006 * s, 0.0035 * s, segments=5, mat_idx=idx_map["Mat_ZFungusRoot"],
    ), regions, "arm_R")
    _tag(add_cylinder(
        bm, (P["hip"][0] + 0.022 * s, -0.044 * s, 0.44 * s), (P["hip"][0] - 0.024 * s, -0.036 * s, 0.28 * s),
        0.007 * s, 0.004 * s, segments=5, mat_idx=idx_map["Mat_ZFungusRoot"],
    ), regions, "leg_L")

    body_obj, body_tris, arm_obj = _finalize_zombie(
        "Mutant_Fungal_Bloom", bm, materials, regions, P, col_char, col_rig,
    )
    return body_obj, body_tris, arm_obj, []


# ---------------------------------------------------------------------------
# MUTANT #5: BILE JUGGERNAUT (Armored Bloater/Boomer/Demolisher Fat Tank Boss)
# ---------------------------------------------------------------------------
def _organic_ring(cx, cy, cz, rx, ry, n=12, wobble=0.07, seed=0.0, flat_back=0.0, sag_front=0.0, z_curve=0.0):
    """Build an organic irregular horror ring (n verts) with fat-fold sag & anatomical bumps."""
    pts = []
    for i in range(n):
        ang = 2.0 * math.pi * i / n
        ca, sa = math.cos(ang), math.sin(ang)
        w = 1.0 + wobble * math.sin(3.0 * ang + seed) + (wobble * 0.55) * math.cos(5.0 * ang - seed * 0.8)
        px = cx + ca * rx * w
        # Character front is -Y (sa < 0) and back is +Y (sa > 0)
        y_off = sa * ry * w
        if sa > 0.0 and flat_back > 0.0:
            y_off *= (1.0 - flat_back * (sa ** 2))
        if sa < 0.0 and sag_front != 0.0:
            y_off += sag_front * (abs(sa) ** 1.4)
        pz = cz + z_curve * (sa * sa - 0.5)
        if sa < 0.0 and sag_front < 0.0:
            # Hang abdominal roll slightly downward at the front crease
            pz += sag_front * 0.25 * (abs(sa) ** 1.5)
        pts.append((px, cy + y_off, pz))
    return pts


def _add_organic_shell(bm, center, radii, rot=(0.0, 0.0, 0.0), mat_idx=0, n=8, seed=0.0, crag=0.16):
    """Build an irregular faceted organic carapace plate, tumorous pad, or muscle mound via loft_rings."""
    c0 = Vector(center)
    rx, ry, rz = radii
    rot_m = Euler(rot, "XYZ").to_matrix()
    rings = []
    for t, r_sc, z_sc in ((0.0, 0.45, -1.0), (0.30, 0.96, -0.38), (0.68, 1.00, 0.40), (1.0, 0.38, 1.00)):
        pts = []
        for i in range(n):
            ang = 2.0 * math.pi * i / n
            w = 1.0 + crag * math.sin(3.0 * ang + seed + t * 1.4) + (crag * 0.5) * math.cos(4.0 * ang - seed)
            local = Vector((math.cos(ang) * rx * r_sc * w, math.sin(ang) * ry * r_sc * w, rz * z_sc))
            pts.append(tuple(c0 + rot_m @ local))
        rings.append(pts)
    return loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_idx)


def _add_boil_cluster(bm, idx_map, center, normal_dir, radius, seed=0.0):
    """Erupt a bruised flesh crater ring crowned by a faceted glowing bile pustule + satellite micro-boils."""
    c0 = Vector(center)
    nrm = Vector(normal_dir).normalized()
    up_h = Vector((0.0, 0.0, 1.0)) if abs(nrm.z) < 0.90 else Vector((1.0, 0.0, 0.0))
    u = nrm.cross(up_h).normalized()
    v = nrm.cross(u).normalized()

    verts = []
    # Bruised crater collar hugging skin
    verts.extend(loft_rings(bm, [
        [tuple(c0 - nrm * (radius * 0.35) + u * (math.cos(2 * math.pi * i / 8) * radius * 1.25)
               + v * (math.sin(2 * math.pi * i / 8) * radius * 1.25)) for i in range(8)],
        [tuple(c0 + nrm * (radius * 0.15) + u * (math.cos(2 * math.pi * i / 8) * radius * 0.92)
               + v * (math.sin(2 * math.pi * i / 8) * radius * 0.92)) for i in range(8)],
    ], close_caps=(True, True), mat_idx=idx_map["Mat_MTankBruise"]))
    # Main glowing bile cyst
    verts.extend(loft_rings(bm, [
        [tuple(c0 + u * (math.cos(2 * math.pi * i / 8) * radius * 0.84)
               + v * (math.sin(2 * math.pi * i / 8) * radius * 0.84)) for i in range(8)],
        [tuple(c0 + nrm * (radius * 0.55) + u * (math.cos(2 * math.pi * i / 8) * radius * 0.72)
               + v * (math.sin(2 * math.pi * i / 8) * radius * 0.72)) for i in range(8)],
        [tuple(c0 + nrm * (radius * 0.92) + u * (math.cos(2 * math.pi * i / 8) * radius * 0.32)
               + v * (math.sin(2 * math.pi * i / 8) * radius * 0.32)) for i in range(8)],
    ], close_caps=(True, True), mat_idx=idx_map["Mat_MBileGlow"]))
    # 2 satellite micro-pustules
    for k, ang in enumerate((seed + 0.6, seed + 2.9)):
        sr = radius * (0.42 if k == 0 else 0.34)
        sc = c0 + (u * math.cos(ang) + v * math.sin(ang)) * (radius * 0.88) + nrm * (radius * 0.06)
        verts.extend(loft_rings(bm, [
            [tuple(sc + u * (math.cos(2 * math.pi * i / 6) * sr) + v * (math.sin(2 * math.pi * i / 6) * sr)) for i in range(6)],
            [tuple(sc + nrm * (sr * 0.85) + u * (math.cos(2 * math.pi * i / 6) * sr * 0.45)
                   + v * (math.sin(2 * math.pi * i / 6) * sr * 0.45)) for i in range(6)],
        ], close_caps=(True, True), mat_idx=idx_map["Mat_MBileGlow"]))
    return verts


def _add_dorsal_plate(bm, cz, cy_back, half_w, height, thick, tilt_x=0.0, mat_idx=0):
    """Loft a smooth curved anatomical dorsal carapace shield hugging the back's curvature."""
    cos_t = math.cos(tilt_x)
    sin_t = math.sin(tilt_x)

    def _p(x, y_local, z_local):
        ry = y_local * cos_t - z_local * sin_t
        rz = y_local * sin_t + z_local * cos_t
        return (x, cy_back + ry, cz + rz)

    # 5-point arch cross-section (inner left -> mid -> peak -> outer flank) closed into a 10-vertex loop per Z station
    xs = (-1.0, -0.52, 0.0, 0.52, 1.0)
    rings = []
    for z_frac, w_sc, t_sc, y_arch in (
        (-0.50, 0.78, 0.45, -0.02),
        (-0.15, 1.00, 0.95,  0.01),
        ( 0.22, 0.94, 1.00,  0.02),
        ( 0.50, 0.64, 0.42, -0.01),
    ):
        zl = z_frac * height
        hw = half_w * w_sc
        tk = thick * t_sc
        outer = []
        inner = []
        for s_f in xs:
            px = s_f * hw
            # Curve forward along flanks (-Y) so plate edges tuck cleanly into back muscle
            y_curve = y_arch - 0.14 * hw * (s_f * s_f)
            outer.append(_p(px, y_curve + tk * (1.0 - 0.55 * (s_f * s_f)), zl))
            inner.append(_p(px * 0.94, y_curve - tk * 0.22, zl))
        rings.append(outer + list(reversed(inner)))
    return loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_idx)


def build_mutant_bile_juggernaut(materials, idx_map, col_char, col_gear, col_rig):
    """Colossal slow-moving fat tank zombie w/ clean back carapace, sagging fat folds, belly-maw & sculpted hands."""
    bm = bmesh.new()
    regions = {}
    chain_verts = {}

    def _cadd(key, verts):
        chain_verts.setdefault(key, []).extend(verts)

    def _idx_set(vlist):
        return [v.index for v in vlist if v.is_valid]

    # 1. Wide Heavy Pelvis & Draped Ragged War-Kilt Skirt (strictly outside pelvis skin — zero hip/glute clipping)
    _cadd("pelvis", loft_rings(bm, [
        _organic_ring(0.0, -0.02, 0.66, 0.33, 0.24, n=14, wobble=0.04, seed=1.0),
        _organic_ring(0.0, -0.02, 0.80, 0.36, 0.26, n=14, wobble=0.04, seed=1.6),
        _organic_ring(0.0, -0.03, 0.92, 0.35, 0.25, n=14, wobble=0.04, seed=2.2),
    ], close_caps=(True, True), mat_idx=idx_map["Mat_MTankBruise"]))

    # Draped ragged war-kilt skirt (`n=14`, flares gently from Z=0.88 down to jagged Z=0.56..0.64 outside thigh/hip wall)
    def _kilt_ring(z_base, rx, ry, jag=0.0, y_off=-0.02, seed=0.0):
        pts = []
        for i in range(14):
            ang = 2.0 * math.pi * i / 14.0
            ca, sa = math.cos(ang), math.sin(ang)
            w = 1.0 + 0.04 * math.sin(3.0 * ang + seed)
            pz = z_base + jag * (0.65 * math.sin(5.0 * ang + 0.8) + 0.35 * math.cos(3.0 * ang - 0.4))
            pts.append((ca * rx * w, y_off + sa * ry * w, pz))
        return pts

    _cadd("pelvis", loft_rings(bm, [
        _kilt_ring(0.60, 0.435, 0.320, jag=0.042, y_off=-0.015, seed=2.4),
        _kilt_ring(0.75, 0.405, 0.295, jag=0.015, y_off=-0.020, seed=2.7),
        _kilt_ring(0.88, 0.388, 0.285, jag=0.004, y_off=-0.025, seed=3.0),
    ], close_caps=(False, False), mat_idx=idx_map["Mat_ZClothDirty"]))
    _cadd("pelvis", loft_rings(bm, [
        _kilt_ring(0.82, 0.396, 0.292, jag=0.002, y_off=-0.025, seed=3.1),
        _kilt_ring(0.90, 0.394, 0.290, jag=0.002, y_off=-0.025, seed=3.2),
    ], close_caps=(False, False), mat_idx=idx_map["Mat_MTankArmor"]))
    _cadd("pelvis", _add_organic_shell(
        bm, (0.0, -0.315, 0.85), (0.075, 0.030, 0.055),
        mat_idx=idx_map["Mat_ZRebar"], n=8, seed=3.1, crag=0.14,
    ))

    # 2. Sagging Layered Abdominal Fat Folds (continuous smooth rear back Y=+0.21..+0.24, recessed front at Y=-0.42 behind belly-maw)
    v_gut = loft_rings(bm, [
        _organic_ring(0.0, -0.07, 0.84, 0.37, 0.26, n=14, wobble=0.05, seed=3.4, flat_back=0.10, sag_front=-0.030),
        _organic_ring(0.0, -0.11, 0.94, 0.44, 0.30, n=14, wobble=0.06, seed=4.0, flat_back=0.12, sag_front=-0.055),
        _organic_ring(0.0, -0.10, 1.03, 0.42, 0.27, n=14, wobble=0.05, seed=4.6, flat_back=0.12, sag_front=-0.015),
        _organic_ring(0.0, -0.10, 1.14, 0.44, 0.28, n=14, wobble=0.05, seed=5.2, flat_back=0.12, sag_front= 0.000),
        _organic_ring(0.0, -0.11, 1.28, 0.45, 0.30, n=14, wobble=0.06, seed=5.8, flat_back=0.10, sag_front=-0.045),
        _organic_ring(0.0, -0.09, 1.38, 0.42, 0.28, n=14, wobble=0.05, seed=6.4, flat_back=0.08, sag_front=-0.020),
        _organic_ring(0.0, -0.08, 1.47, 0.42, 0.28, n=14, wobble=0.05, seed=7.0, flat_back=0.08),
    ], close_caps=(True, True), mat_idx=idx_map["Mat_MTankSkin"])
    _cadd("belly_gut", v_gut)

    # 4 Erupted Bile Boil Clusters tucked cleanly along side flanks of bloated gut
    for sx in (1.0, -1.0):
        for py, pz, r_b, sd in ((-0.16, 0.96, 0.065, 1.1), (-0.10, 1.24, 0.072, 2.2)):
            _cadd("belly_gut", _add_boil_cluster(
                bm, idx_map, (0.41 * sx, py, pz), (sx, py * 1.2, 0.15), r_b, seed=sd,
            ))

    # RUPTURED OVAL BELLY-MAW (true XZ-plane oral cavity along Y, smooth scar collar, arched lips & staggered curved teeth)
    def _mouth_xz_ring(cy, rx, rz, n=14, seed=0.0):
        pts = []
        for i in range(n):
            ang = 2.0 * math.pi * i / n
            w = 1.0 + 0.04 * math.sin(3.0 * ang + seed)
            pts.append((math.cos(ang) * rx * w, cy, 1.14 + math.sin(ang) * rz * w))
        return pts

    _cadd("belly_gut", loft_rings(bm, [
        _mouth_xz_ring(-0.27, 0.155, 0.078, n=14, seed=8.1),
        _mouth_xz_ring(-0.37, 0.210, 0.105, n=14, seed=8.4),
        _mouth_xz_ring(-0.45, 0.228, 0.112, n=14, seed=8.7),
    ], close_caps=(True, False), mat_idx=idx_map["Mat_ZMouth"]))
    # Smooth bruised flesh outer scar collar tapering cleanly around belly-maw into abdominal wall
    _cadd("belly_gut", loft_rings(bm, [
        _mouth_xz_ring(-0.40, 0.258, 0.146, n=14, seed=9.0),
        _mouth_xz_ring(-0.46, 0.240, 0.124, n=14, seed=9.2),
    ], close_caps=(False, False), mat_idx=idx_map["Mat_MTankBruise"]))
    # Recessed glowing molten bile organ deep inside hollow belly-maw cavity
    _cadd("belly_gut", _add_organic_shell(
        bm, (0.0, -0.355, 1.14), (0.115, 0.052, 0.068), rot=(0.15, 0.25, 0.08),
        mat_idx=idx_map["Mat_MBileGlow"], n=8, seed=9.1, crag=0.14,
    ))

    def _lip_arch(x_span, y_mid, y_corner, z_corner, z_apex, n_pts=9):
        pts, w1, w2 = [], [], []
        for i in range(n_pts):
            t = (i / (n_pts - 1)) * 2.0 - 1.0  # -1..1
            c_arc = math.cos(0.5 * math.pi * t)
            pts.append((t * x_span, y_corner + (y_mid - y_corner) * (c_arc ** 0.75), z_corner + (z_apex - z_corner) * (c_arc ** 0.85)))
            w1.append(0.014 + 0.050 * (c_arc ** 0.7))
            w2.append(0.012 + 0.036 * (c_arc ** 0.7))
        return pts, w1, w2

    top_pts, top_w1, top_w2 = _lip_arch(0.236, -0.490, -0.405, 1.142, 1.278, n_pts=9)
    b_top = _add_tapered_ribbon(
        bm, idx_map, top_pts, top_w1, top_w2,
        up_hint=(0.0, -1.0, 0.25), mat_front="Mat_ZBloodFresh", mat_back="Mat_MTankBruise",
    )
    for i in range(9):
        frac = (i / 8.0) - 0.5
        c_arc = math.cos(math.pi * frac)
        bx = frac * 0.35
        bz = 1.148 + 0.112 * (c_arc ** 0.85)
        by = -0.455 + 0.045 * abs(frac)
        is_c = (i % 2 == 1)
        tip_z = bz - (0.095 if is_c else 0.062) * (0.55 + 0.45 * c_arc)
        b_top.extend(add_cone(
            bm, (bx, by, bz), (bx * 0.92 + 0.006 * math.sin(i * 1.9), by + 0.028, tip_z),
            (0.016 if is_c else 0.011), segments=5, mat_idx=idx_map["Mat_MScytheBone"],
        ))
    _cadd("belly_maw_top", b_top)

    bot_pts, bot_w1, bot_w2 = _lip_arch(0.236, -0.495, -0.405, 1.138, 1.002, n_pts=9)
    b_bot = _add_tapered_ribbon(
        bm, idx_map, bot_pts, bot_w1, bot_w2,
        up_hint=(0.0, -1.0, -0.25), mat_front="Mat_ZBloodFresh", mat_back="Mat_MTankBruise",
    )
    for i in range(9):
        frac = (i / 8.0) - 0.5
        c_arc = math.cos(math.pi * frac)
        bx = frac * 0.34
        bz = 1.132 - 0.112 * (c_arc ** 0.85)
        by = -0.458 + 0.045 * abs(frac)
        is_c = (i % 2 == 0)
        tip_z = bz + (0.090 if is_c else 0.058) * (0.55 + 0.45 * c_arc)
        b_bot.extend(add_cone(
            bm, (bx, by, bz), (bx * 0.92 - 0.006 * math.cos(i * 1.7), by + 0.028, tip_z),
            (0.015 if is_c else 0.011), segments=5, mat_idx=idx_map["Mat_MScytheBone"],
        ))
    _cadd("belly_maw_bot", b_bot)

    # 3. Towering Hunched Barrel Chest, Smooth Unified Dorsal Silhouette, 5 Shingled Back Arch-Plates & Prominent Spine Spikes
    v_chest = loft_rings(bm, [
        _organic_ring(0.0, -0.08, 1.44, 0.43, 0.29, n=14, wobble=0.05, seed=10.1, flat_back=0.08),
        _organic_ring(0.0, -0.07, 1.60, 0.48, 0.31, n=14, wobble=0.05, seed=10.7, flat_back=0.08),
        _organic_ring(0.0, -0.07, 1.76, 0.49, 0.32, n=14, wobble=0.05, seed=11.3, flat_back=0.08),
        _organic_ring(0.0, -0.10, 1.92, 0.42, 0.28, n=14, wobble=0.05, seed=11.9, flat_back=0.06),
        _organic_ring(0.0, -0.14, 2.04, 0.28, 0.21, n=14, wobble=0.04, seed=12.4),
        _organic_ring(0.0, -0.18, 2.12, 0.15, 0.12, n=14, wobble=0.04, seed=12.9),
    ], close_caps=(True, True), mat_idx=idx_map["Mat_MTankSkin"])
    _cadd("chest", v_chest)

    # 5 Neatly Shingled Curved Dorsal Carapace Arch-Plates hugging upper-to-mid back cleanly
    for cz, cy_b, hw, ht, tk, tlx in (
        (2.01, 0.09, 0.24, 0.17, 0.065,  0.55),
        (1.86, 0.19, 0.34, 0.20, 0.078,  0.24),
        (1.69, 0.22, 0.32, 0.20, 0.076,  0.08),
        (1.52, 0.21, 0.25, 0.18, 0.068, -0.06),
        (1.37, 0.19, 0.17, 0.15, 0.056, -0.12),
    ):
        _cadd("chest", _add_dorsal_plate(
            bm, cz, cy_b, hw, ht, tk, tilt_x=tlx, mat_idx=idx_map["Mat_MTankArmor"],
        ))
    # 2 Clean Curved Clavicle/Pec Ridge Plates tucked into front shoulder traps
    for sx in (1.0, -1.0):
        _cadd("chest", _add_organic_shell(
            bm, (0.26 * sx, -0.22, 1.72), (0.14, 0.08, 0.08), rot=(0.24, -0.22 * sx, 0.16 * sx),
            mat_idx=idx_map["Mat_MTankArmor"], n=8, seed=7.1 + sx, crag=0.12,
        ))
    # 6 Prominent Dorsal Vertebral Bone Spikes erupting clearly outside the carapace spine
    for k, (pz, py_base, r_sp, tip_dy, tip_dz) in enumerate((
        (1.38, 0.24, 0.022, 0.15, 0.06),
        (1.53, 0.27, 0.026, 0.17, 0.08),
        (1.69, 0.29, 0.030, 0.19, 0.10),
        (1.85, 0.26, 0.032, 0.18, 0.12),
        (1.98, 0.17, 0.028, 0.14, 0.15),
        (2.07, 0.04, 0.024, 0.08, 0.17),
    )):
        _cadd("chest", add_cone(
            bm, (0.0, py_base, pz), (0.014 * math.sin(k * 1.9), py_base + tip_dy, pz + tip_dz),
            r_sp, segments=5, mat_idx=idx_map["Mat_MScytheBone"],
        ))
    # Raised varicose chest & dorsal flank veins + 4 neatly seated dorsal seam boil clusters
    for sx in (1.0, -1.0):
        _cadd("chest", _add_tapered_ribbon(
            bm, idx_map,
            [(0.06 * sx, -0.34, 1.66), (0.20 * sx, -0.30, 1.78), (0.34 * sx, -0.18, 1.88)],
            [0.016, 0.020, 0.010], [0.010, 0.012, 0.006],
            up_hint=(0.0, -1.0, 0.2), mat_front="Mat_ZVeinDark", mat_back="Mat_MTankBruise",
        ))
        _cadd("chest", _add_tapered_ribbon(
            bm, idx_map,
            [(0.10 * sx, -0.36, 1.48), (0.26 * sx, -0.28, 1.56), (0.38 * sx, -0.14, 1.64)],
            [0.014, 0.018, 0.009], [0.009, 0.010, 0.005],
            up_hint=(0.0, -1.0, 0.0), mat_front="Mat_ZVeinDark", mat_back="Mat_MTankBruise",
        ))
    for bx, by, bz, br, sd in (
        (-0.18, 0.24, 1.90, 0.060, 1.4),
        ( 0.19, 0.24, 1.84, 0.056, 2.5),
        (-0.16, 0.26, 1.62, 0.058, 3.6),
        ( 0.16, 0.25, 1.56, 0.054, 4.7),
    ):
        _cadd("chest", _add_boil_cluster(bm, idx_map, (bx, by, bz), (bx * 0.5, 1.0, 0.2), br, seed=sd))

    # 4. Clean Muscular Gorilla Arms & Sculpted Coherent Hands (`Arm_L` 5-digit claw vs `Arm_R` heavy armored gorilla fist)
    arm_configs = []
    for side, sx, scale_arm in (("L", 1.0, 1.00), ("R", -1.0, 1.30)):
        aname = f"Arm_{side}"
        sh = (0.36 * sx, -0.10, 1.82)
        up = (0.52 * sx, -0.12, 1.72)
        el = (0.62 * sx, -0.06, 1.24)
        wr = (0.64 * sx, -0.16, 0.78)
        hd = (0.60 * sx, -0.22, 0.50)
        arm_configs.append((aname, sh, up, el, wr, hd))

        sh_v, up_v, el_v, wr_v, hd_v = Vector(sh), Vector(up), Vector(el), Vector(wr), Vector(hd)
        arm_pts = [
            tuple(sh_v),
            tuple(up_v),
            tuple(up_v.lerp(el_v, 0.38)),
            tuple(up_v.lerp(el_v, 0.72)),
            tuple(el_v),
            tuple(el_v.lerp(wr_v, 0.34)),
            tuple(el_v.lerp(wr_v, 0.68)),
            tuple(wr_v),
            tuple(wr_v.lerp(hd_v, 0.85)),
        ]
        arm_rads = [
            (0.148 * scale_arm, 0.142 * scale_arm),
            (0.160 * scale_arm, 0.152 * scale_arm),
            (0.138 * scale_arm, 0.132 * scale_arm),
            (0.120 * scale_arm, 0.114 * scale_arm),
            (0.112 * scale_arm, 0.108 * scale_arm),
            (0.142 * scale_arm, 0.132 * scale_arm),
            (0.134 * scale_arm, 0.122 * scale_arm),
            (0.108 * scale_arm, 0.098 * scale_arm),
            (0.098 * scale_arm, 0.090 * scale_arm),
        ]
        v_arm = loft_rings(bm, _perp_chain_rings(arm_pts, arm_rads, n=10), close_caps=(True, True), mat_idx=idx_map["Mat_MTankSkin"])
        _cadd(aname, v_arm)

        # Single sleek curved shoulder pauldron hugging deltoid + zero-clipping matching n=10 forearm bandage cuff
        _cadd(aname, _add_organic_shell(
            bm, (0.50 * sx, -0.10, 1.80), (0.155 * scale_arm, 0.145 * scale_arm, 0.115 * scale_arm),
            rot=(0.14, -0.38 * sx, 0.0), mat_idx=idx_map["Mat_MTankArmor"], n=8, seed=2.4 + sx, crag=0.14,
        ))
        _cadd(aname, loft_rings(bm, _perp_chain_rings(
            [tuple(el_v.lerp(wr_v, 0.56)), tuple(el_v.lerp(wr_v, 0.88))],
            [(0.148 * scale_arm, 0.138 * scale_arm), (0.126 * scale_arm, 0.116 * scale_arm)], n=10,
        ), close_caps=(False, False), mat_idx=idx_map["Mat_ZClothDirty"]))
        _cadd(aname, _add_tapered_ribbon(
            bm, idx_map,
            [(0.58 * sx, -0.20, 1.48), (0.64 * sx, -0.23, 1.18), (0.64 * sx, -0.26, 0.88)],
            [0.018 * scale_arm, 0.022 * scale_arm, 0.012 * scale_arm],
            [0.010 * scale_arm, 0.012 * scale_arm, 0.008 * scale_arm],
            up_hint=(sx, -1.0, 0.0), mat_front="Mat_ZVeinDark", mat_back="Mat_MTankBruise",
        ))
        _cadd(aname, add_cone(
            bm, el, (el[0] + 0.08 * sx, el[1] + 0.15, el[2] + 0.10),
            0.034 * scale_arm, segments=5, mat_idx=idx_map["Mat_MScytheBone"],
        ))
        _cadd(aname, _add_boil_cluster(
            bm, idx_map, (0.66 * sx, -0.11, 1.05), (sx, -0.35, 0.1), 0.046 * scale_arm, seed=4.2 + sx,
        ))

        if sx < 0:
            # RIGHT HAND: Solid Clenched Armored Gorilla Fist (no twisted U-turn tubes or dangling bars)
            w_bridge = tuple(wr_v.lerp(hd_v, 0.72))
            _cadd(aname, loft_rings(bm, _perp_chain_rings(
                [w_bridge, (hd[0], hd[1] - 0.01, hd[2]), (hd[0], hd[1] - 0.02, hd[2] - 0.075)],
                [(0.118, 0.106), (0.128, 0.120), (0.108, 0.102)], n=10,
            ), close_caps=(True, True), mat_idx=idx_map["Mat_MTankSkin"]))
            # Outer/dorsal calcified gauntlet cap wrapping knuckles
            _cadd(aname, _add_organic_shell(
                bm, (hd[0] - 0.038, hd[1] - 0.015, hd[2] - 0.035), (0.095, 0.122, 0.105),
                rot=(0.08, 0.18, -0.04), mat_idx=idx_map["Mat_MTankArmor"], n=8, seed=5.4, crag=0.12,
            ))
            # 4 Distinct Curled Fist Fingers (non-reversing segments tucked snugly against palm + short knuckle studs)
            for fi in range(4):
                fy = (fi - 1.5) * 0.050
                k0 = (hd[0] - 0.045, hd[1] + fy, hd[2] - 0.045)
                k1 = (hd[0] - 0.038, hd[1] + fy - 0.005, hd[2] - 0.112)
                k2 = (hd[0] + 0.032, hd[1] + fy, hd[2] - 0.108)
                _cadd(aname, loft_rings(bm, _perp_chain_rings(
                    [k0, k1], [(0.028, 0.026), (0.026, 0.024)], n=6,
                ), close_caps=(True, True), mat_idx=idx_map["Mat_MTankArmor"]))
                _cadd(aname, loft_rings(bm, _perp_chain_rings(
                    [k1, k2], [(0.025, 0.023), (0.021, 0.019)], n=6,
                ), close_caps=(True, True), mat_idx=idx_map["Mat_MTankArmor"]))
                _cadd(aname, add_cone(
                    bm, (k1[0] - 0.012, k1[1], k1[2] + 0.025),
                    (k1[0] - 0.042, k1[1] - 0.015, k1[2] - 0.018),
                    0.015, segments=5, mat_idx=idx_map["Mat_MScytheBone"],
                ))
            # Heavy Opposing Armored Thumb tucked flush across inner-front knuckles (no protruding crab pincer)
            t0 = (hd[0] + 0.048, hd[1] - 0.055, hd[2] + 0.005)
            t1 = (hd[0] + 0.055, hd[1] - 0.095, hd[2] - 0.055)
            t2 = (hd[0] + 0.015, hd[1] - 0.085, hd[2] - 0.105)
            _cadd(aname, loft_rings(bm, _perp_chain_rings(
                [t0, t1], [(0.034, 0.030), (0.028, 0.026)], n=6,
            ), close_caps=(True, True), mat_idx=idx_map["Mat_MTankArmor"]))
            _cadd(aname, loft_rings(bm, _perp_chain_rings(
                [t1, t2], [(0.027, 0.025), (0.022, 0.020)], n=6,
            ), close_caps=(True, True), mat_idx=idx_map["Mat_MTankArmor"]))
        else:
            # LEFT HAND: Proportional Broad Muscular Palm + 4 Articulated 3-Segment Clawed Fingers + Opposing Thumb
            w_bridge = tuple(wr_v.lerp(hd_v, 0.72))
            _cadd(aname, loft_rings(bm, _perp_chain_rings(
                [w_bridge, (hd[0], hd[1] - 0.01, hd[2] + 0.01), (hd[0] - 0.01, hd[1] - 0.01, hd[2] - 0.06)],
                [(0.094, 0.082), (0.088, 0.098), (0.072, 0.092)], n=10,
            ), close_caps=(True, True), mat_idx=idx_map["Mat_MTankSkin"]))
            _cadd(aname, _add_organic_shell(
                bm, (hd[0] + 0.03, hd[1] - 0.01, hd[2] - 0.02), (0.052, 0.082, 0.065),
                rot=(0.06, -0.16, 0.0), mat_idx=idx_map["Mat_MTankArmor"], n=8, seed=7.2, crag=0.12,
            ))
            _cadd(aname, _add_organic_shell(
                bm, (hd[0] - 0.04, hd[1] - 0.01, hd[2] - 0.03), (0.045, 0.072, 0.055),
                rot=(0.0, 0.0, 0.0), mat_idx=idx_map["Mat_MTankBruise"], n=6, seed=7.6, crag=0.10,
            ))
            # 4 Articulated 3-part monster fingers (proximal flesh -> mid bruised joint -> thick curved bone claw)
            for f_i in range(4):
                fo = (f_i - 1.5) * 0.044
                fb = (hd[0] + 0.005, hd[1] + fo - 0.005, hd[2] - 0.05)
                fm = (hd[0] - 0.012, hd[1] + fo - 0.018, hd[2] - 0.125)
                fk = (hd[0] - 0.045, hd[1] + fo - 0.028, hd[2] - 0.180)
                ft = (hd[0] - 0.088, hd[1] + fo - 0.042, hd[2] - 0.225)
                _cadd(aname, loft_rings(bm, _perp_chain_rings(
                    [fb, fm], [(0.024, 0.022), (0.020, 0.018)], n=6,
                ), close_caps=(True, True), mat_idx=idx_map["Mat_MTankSkin"]))
                _cadd(aname, loft_rings(bm, _perp_chain_rings(
                    [fm, fk], [(0.020, 0.018), (0.016, 0.015)], n=6,
                ), close_caps=(True, True), mat_idx=idx_map["Mat_MTankBruise"]))
                _cadd(aname, add_cone(bm, fk, ft, 0.017, segments=5, mat_idx=idx_map["Mat_MScytheBone"]))
            # Thick Opposing Clawed Thumb on inner-front edge (-X, -Y)
            tb = (hd[0] - 0.045, hd[1] - 0.062, hd[2] + 0.015)
            tm = (hd[0] - 0.085, hd[1] - 0.102, hd[2] - 0.045)
            tk = (hd[0] - 0.095, hd[1] - 0.095, hd[2] - 0.105)
            tt = (hd[0] - 0.075, hd[1] - 0.075, hd[2] - 0.155)
            _cadd(aname, loft_rings(bm, _perp_chain_rings(
                [tb, tm, tk], [(0.028, 0.025), (0.023, 0.020), (0.017, 0.015)], n=6,
            ), close_caps=(True, True), mat_idx=idx_map["Mat_MTankSkin"]))
            _cadd(aname, add_cone(bm, tk, tt, 0.018, segments=5, mat_idx=idx_map["Mat_MScytheBone"]))

    # 5. Muscular Elephantine Tank Legs (`Leg_L`, `Leg_R`), Organic Knee Crests & 4-Toed Monster Feet on Z=0
    leg_configs = []
    for side, sx in (("L", 1.0), ("R", -1.0)):
        lname = f"Leg_{side}"
        hip   = (0.24 * sx,  0.00, 0.72)
        knee  = (0.27 * sx, -0.05, 0.40)
        ankle = (0.26 * sx,  0.02, 0.12)
        foot  = (0.26 * sx, -0.06, 0.02)
        leg_configs.append((lname, hip, knee, ankle, foot))

        v_leg = loft_rings(bm, [
            _organic_ring(0.26 * sx,  0.01, 0.10, 0.132, 0.128, n=12, wobble=0.05, seed=1.1 + sx),
            _organic_ring(0.26 * sx,  0.02, 0.18, 0.138, 0.138, n=12, wobble=0.05, seed=1.5 + sx),
            _organic_ring(0.26 * sx,  0.04, 0.28, 0.156, 0.168, n=12, wobble=0.05, seed=1.9 + sx),
            _organic_ring(0.27 * sx, -0.04, 0.40, 0.155, 0.152, n=12, wobble=0.04, seed=2.3 + sx),
            _organic_ring(0.26 * sx, -0.03, 0.52, 0.186, 0.178, n=12, wobble=0.05, seed=2.7 + sx),
            _organic_ring(0.25 * sx, -0.01, 0.64, 0.194, 0.184, n=12, wobble=0.05, seed=3.1 + sx),
            _organic_ring(0.24 * sx,  0.00, 0.76, 0.180, 0.172, n=12, wobble=0.05, seed=3.5 + sx),
        ], close_caps=(True, True), mat_idx=idx_map["Mat_MTankSkin"])
        _cadd(lname, v_leg)

        # Raised varicose leg vein + organic shingled bone-fungal knee crest
        _cadd(lname, _add_tapered_ribbon(
            bm, idx_map,
            [(0.32 * sx, -0.08, 0.66), (0.35 * sx, -0.06, 0.44), (0.31 * sx, 0.02, 0.20)],
            [0.016, 0.018, 0.010], [0.010, 0.011, 0.006],
            up_hint=(sx, 0.0, 0.0), mat_front="Mat_ZVeinDark", mat_back="Mat_MTankBruise",
        ))
        _cadd(lname, _add_organic_shell(
            bm, (0.27 * sx, -0.15, 0.39), (0.102, 0.072, 0.118), rot=(0.12, 0.08 * sx, 0.0),
            mat_idx=idx_map["Mat_MTankArmor"], n=8, seed=4.2 + sx, crag=0.20,
        ))
        _cadd(lname, _add_organic_shell(
            bm, (0.22 * sx, -0.14, 0.44), (0.064, 0.052, 0.068), rot=(0.18, 0.20 * sx, 0.0),
            mat_idx=idx_map["Mat_MScytheBone"], n=6, seed=4.8 + sx, crag=0.16,
        ))

        # Sculpted Wide Arched Elephantine Foot seated cleanly on Z = 0.0 + 4 Articulated Clawed Toes + Heel Spur
        _cadd(lname, loft_rings(bm, [
            _organic_ring(0.26 * sx,  0.04, 0.095, 0.118, 0.125, n=10, wobble=0.05, seed=5.1 + sx),
            _organic_ring(0.26 * sx, -0.02, 0.052, 0.132, 0.155, n=10, wobble=0.06, seed=5.5 + sx),
            _organic_ring(0.26 * sx, -0.05, 0.008, 0.136, 0.162, n=10, wobble=0.05, seed=5.9 + sx),
        ], close_caps=(True, True), mat_idx=idx_map["Mat_MTankBruise"]))
        # 4 Distinct Fleshy Toe Mounds + Crooked Bone Claws fanning forward
        for ti, (tx_o, ty_o, tw) in enumerate((
            (-0.088 * sx, -0.17, 0.032),
            (-0.028 * sx, -0.19, 0.036),
            ( 0.032 * sx, -0.19, 0.034),
            ( 0.086 * sx, -0.16, 0.030),
        )):
            t_pos = (0.26 * sx + tx_o, ty_o, 0.028)
            _cadd(lname, _add_organic_shell(
                bm, t_pos, (tw, 0.052, 0.026), mat_idx=idx_map["Mat_MTankSkin"], n=6, seed=6.3 + ti, crag=0.12,
            ))
            _cadd(lname, add_cone(
                bm, (t_pos[0], t_pos[1] - 0.025, 0.028),
                (t_pos[0] + tx_o * 0.22, t_pos[1] - 0.105, 0.005),
                0.022, segments=5, mat_idx=idx_map["Mat_MScytheBone"],
            ))
        # Rear calcified heel spur
        _cadd(lname, add_cone(
            bm, (0.26 * sx, 0.08, 0.045), (0.26 * sx, 0.18, 0.025),
            0.026, segments=5, mat_idx=idx_map["Mat_MScytheBone"],
        ))

    # 6. Larger Gnarled Eyeless Split-Jaw Tank Head protruding cleanly forward of chest traps
    build_head_bile_juggernaut(bm, idx_map, regions, center=(0.0, -0.42, 1.85), fwd_dir=(0.0, -0.96, -0.26), scale=1.34)

    bm.verts.ensure_lookup_table()
    bm.verts.index_update()

    single_assignments = {
        "Pelvis":        _idx_set(chain_verts["pelvis"]),
        "Belly_Gut":     _idx_set(chain_verts["belly_gut"]),
        "Belly_Maw_Top": _idx_set(chain_verts["belly_maw_top"]),
        "Belly_Maw_Bot": _idx_set(chain_verts["belly_maw_bot"]),
        "Head":          _idx_set(regions.get("head", [])),
        "Jaw_L":         _idx_set(regions.get("jaw_L", [])),
        "Jaw_R":         _idx_set(regions.get("jaw_R", [])),
    }

    bone_specs = [
        ("Pelvis",        None,       (0.0,  0.00, 0.68), (0.0,  0.00, 0.92), True),
        ("Belly_Gut",     "Pelvis",   (0.0, -0.14, 0.90), (0.0, -0.18, 1.44), True),
        ("Belly_Maw_Top", "Belly_Gut",(0.0, -0.36, 1.24), (0.0, -0.52, 1.24), True),
        ("Belly_Maw_Bot", "Belly_Gut",(0.0, -0.36, 1.04), (0.0, -0.52, 1.04), True),
        ("Spine_01",      "Pelvis",   (0.0, -0.04, 0.92), (0.0, -0.10, 1.52), True),
        ("Spine_02",      "Spine_01", (0.0, -0.10, 1.52), (0.0, -0.18, 1.98), True),
        ("Head",          "Spine_02", (0.0, -0.30, 1.84), (0.0, -0.50, 1.80), True),
        ("Jaw_L",         "Head",     ( 0.06, -0.34, 1.76), ( 0.05, -0.56, 1.70), True),
        ("Jaw_R",         "Head",     (-0.06, -0.34, 1.76), (-0.05, -0.56, 1.70), True),
        ("Tongue_01",     "Head",     ( 0.00, -0.38, 1.76), ( 0.00, -0.48, 1.66), True),
        ("Tongue_02",     "Tongue_01",( 0.00, -0.48, 1.66), ( 0.00, -0.54, 1.58), True),
    ]
    chain_assignments = [
        (["Spine_01", "Spine_02"],   _idx_set(chain_verts["chest"])),
        (["Tongue_01", "Tongue_02"], _idx_set(regions.get("tongue", []))),
    ]
    for aname, sh, up, el, wr, hd in arm_configs:
        b1, b2, b3, b4 = f"{aname}_Shoulder", f"{aname}_Upper", f"{aname}_Fore", f"{aname}_Hand"
        bone_specs.extend([
            (b1, "Spine_02", sh, up, True),
            (b2, b1,         up, el, True),
            (b3, b2,         el, wr, True),
            (b4, b3,         wr, hd, True),
        ])
        chain_assignments.append(([b1, b2, b3, b4], _idx_set(chain_verts[aname])))

    for lname, hip, knee, ankle, foot in leg_configs:
        b1, b2, b3 = f"{lname}_Thigh", f"{lname}_Shin", f"{lname}_Foot"
        bone_specs.extend([
            (b1, "Pelvis", hip,   knee,  True),
            (b2, b1,       knee,  ankle, True),
            (b3, b2,       ankle, foot,  True),
        ])
        chain_assignments.append(([b1, b2, b3], _idx_set(chain_verts[lname])))

    body_obj, body_tris = finalize_mesh("Mutant_Bile_Juggernaut_Body", bm, materials, collection=col_char)
    apply_box_uvs(body_obj, tex_scale=2.6)
    arm_obj = create_creature_armature("Mutant_Bile_Juggernaut_Rig", bone_specs, collection=col_rig)
    skin_creature_to_armature(body_obj, arm_obj, chain_assignments, single_assignments, fallback_bone="Pelvis")
    return body_obj, body_tris, arm_obj, []


MUTANT_BUILDERS = [
    ("rafflesia",       build_mutant_rafflesia),
    ("scythe_stalker",  build_mutant_scythe_stalker),
    ("thorn_shroud",    build_mutant_thorn_shroud),
    ("arachnid_maw",    build_mutant_arachnid_maw),
    ("bile_juggernaut", build_mutant_bile_juggernaut),
    ("fungal_bloom",    build_mutant_fungal_bloom),
]

MUTANT_META = {
    "rafflesia": {
        "index": 1,
        "skill_pose": "rafflesia_lash",
        "render_name": "mutant_01_rafflesia.png",
        "body_ortho": 2.48,
        "body_tgt_z": 0.68,
        "head_ortho": 1.06,
        "head_cam_y": -2.60,
        "head_z_off": -0.02,
        "idle_stage": "idle",
        "head_stage": "lunge_bite",
        "skill_stage": "vine_thrash",
        "vfx_mat": "Mat_ZHeartGlow",
    },
    "scythe_stalker": {
        "index": 2,
        "skill_pose": "scythe_stalker",
        "render_name": "mutant_02_scythe_stalker.png",
        "body_ortho": 2.38,
        "body_tgt_z": 0.88,
        "head_ortho": 0.78,
        "head_cam_y": -2.20,
        "head_z_off": -0.04,
        "idle_stage": "idle",
        "head_stage": "slash",
        "skill_stage": "reaper_lunge",
        "vfx_mat": "Mat_MEyeAcid",
    },
    "thorn_shroud": {
        "index": 3,
        "skill_pose": "thorn_shroud",
        "render_name": "mutant_03_thorn_shroud.png",
        "body_ortho": 2.65,
        "body_tgt_z": 1.08,
        "head_ortho": 0.96,
        "head_cam_y": -2.40,
        "head_z_off": 0.10,
        "idle_stage": "idle",
        "head_stage": "sweep",
        "skill_stage": "razor_bloom",
        "vfx_mat": "Mat_MShroudBone",
    },
    "arachnid_maw": {
        "index": 4,
        "skill_pose": "arachnid_maw",
        "render_name": "mutant_04_arachnid_maw.png",
        "body_ortho": 2.38,
        "body_tgt_z": 0.56,
        "head_ortho": 0.82,
        "head_cam_y": -2.00,
        "head_z_off": -0.02,
        "idle_stage": "idle",
        "head_stage": "bite",
        "skill_stage": "acid_pounce",
        "vfx_mat": "Mat_ZAcidGlow",
    },
    "bile_juggernaut": {
        "index": 5,
        "skill_pose": "bile_juggernaut",
        "render_name": "mutant_05_bile_juggernaut.png",
        "body_ortho": 2.85,
        "body_tgt_z": 1.12,
        "head_ortho": 0.98,
        "head_cam_y": -2.40,
        "head_z_off": -0.04,
        "idle_stage": "idle",
        "head_stage": "roar",
        "skill_stage": "seismic_slam",
        "vfx_mat": "Mat_MBileGlow",
    },
    "fungal_bloom": {
        "index": 1,
        "skill_pose": "echo_click",
        "render_name": "mutant_01_fungal_bloom.png",
    },
}
