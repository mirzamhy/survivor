"""Radically non-human mutant head sculpts matching Loomis/Asaro faceless low-poly style."""
import math
import bmesh
from mathutils import Vector

from mesh_utils import add_box, add_cone, add_cylinder, loft_rings, ring_ellipse
from zombie_head import _add_jagged_teeth


def _add_fungal_fan(
    bm, mat_idx, origin, normal_dir, up_dir, radius, spread_deg=110.0,
    thickness=0.018, mat_top="Mat_ZFungusCap", mat_bot="Mat_ZFungusGill",
    mat_rim="Mat_ZFungusPale", n_arc=6, cup=0.14, seed=0,
):
    """Build a watertight faceted low-poly curved shelf-fungus fan erupting from `origin`."""
    orig = Vector(origin)
    fwd = Vector(normal_dir)
    if fwd.length < 1e-6:
        fwd = Vector((0.0, 0.0, 1.0))
    fwd.normalize()

    u_ref = Vector(up_dir)
    up = u_ref - fwd * u_ref.dot(fwd)
    if up.length < 1e-6:
        fb = Vector((0.0, 0.0, 1.0)) if abs(fwd.z) < 0.9 else Vector((0.0, 1.0, 0.0))
        up = fb - fwd * fb.dot(fwd)
    up.normalize()
    side = up.cross(fwd).normalized()

    spread_rad = math.radians(spread_deg)
    rings = []
    stages = (
        (0.14, 0.00, 0.50, 0.35),
        (0.62, cup * 1.15, 0.44, 1.00),
        (1.00, cup * 0.80, 0.14, 1.00),
    )
    for r_fac, lift_fac, th_fac, wave_amp in stages:
        top_pts = []
        bot_pts = []
        for k in range(n_arc):
            frac = k / (n_arc - 1)
            theta = (frac - 0.5) * spread_rad
            ca, sa = math.cos(theta), math.sin(theta)
            scallop = 1.0 + 0.15 * wave_amp * math.sin(k * 2.1 + seed)
            r = radius * r_fac * scallop
            lat = 0.25 if r_fac < 0.25 else 1.0
            rdir = fwd * ca + side * (sa * lat)
            wobble = 0.06 * radius * wave_amp * math.cos(k * 1.7 + seed)
            center_pt = orig + rdir * r + up * (lift_fac * radius + wobble)
            ht = thickness * th_fac
            top_pts.append(tuple(center_pt + up * ht))
            bot_pts.append(tuple(center_pt - up * ht))
        rings.append(top_pts + list(reversed(bot_pts)))

    verts = loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_idx[mat_top])
    faces = {f for v in verts for f in v.link_faces}
    for f in faces:
        f.normal_update()
        ndot = f.normal.dot(up)
        r_dist = (f.calc_center_median() - orig).length
        if ndot < -0.20:
            f.material_index = mat_idx[mat_bot]
        elif r_dist > radius * 0.72:
            f.material_index = mat_idx[mat_rim]
        else:
            f.material_index = mat_idx[mat_top]
    return verts


def build_head_fungal_bloom(bm, mat_idx, regions, proportions=None, skin_mat="Mat_ZSkinGrey"):
    """Build non-human Cordyceps split-flower head: zero human face, ruptured split lobes & coral maw."""
    s = proportions["scale"] if proportions is not None else 1.0
    neck_verts = []
    head_verts = []

    # 1. Gnarled gaunt neck loft (connects cleanly to torso collar, zero face above jaw)
    neck_rings = [
        ring_ellipse(0.0,       0.008 * s, 1.462 * s, 0.056 * s, 0.054 * s, n=8),
        ring_ellipse(0.003 * s, 0.002 * s, 1.500 * s, 0.050 * s, 0.048 * s, n=8),
        ring_ellipse(0.006 * s, -0.004 * s, 1.538 * s, 0.048 * s, 0.048 * s, n=8),
        ring_ellipse(0.006 * s, -0.008 * s, 1.576 * s, 0.054 * s, 0.054 * s, n=8),
    ]
    v_neck = loft_rings(bm, neck_rings, close_caps=(True, True), mat_idx=mat_idx[skin_mat])
    for f in {f for v in v_neck for f in v.link_faces}:
        c = f.calc_center_median()
        if c.z > 1.535 * s:
            f.material_index = mat_idx["Mat_ZFungusDark"] if c.y > 0.0 else mat_idx["Mat_ZBloodDried"]
    neck_verts.extend(v_neck)

    # 2. Inner dark cranial/throat stem + ruined crooked lower jaw emerging beneath the bloom
    stem_rings = [
        ring_ellipse(0.0, -0.010 * s, 1.568 * s, 0.046 * s, 0.048 * s, n=8),
        ring_ellipse(0.0, -0.014 * s, 1.615 * s, 0.044 * s, 0.046 * s, n=8),
        ring_ellipse(0.0, -0.006 * s, 1.668 * s, 0.040 * s, 0.044 * s, n=8),
    ]
    head_verts.extend(loft_rings(bm, stem_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_ZFungusDark"]))

    # Crooked broken lower mandible (tilted & blood-caked, zero nose/cheeks/eyes)
    head_verts.extend(add_box(
        bm,
        center=(0.003 * s, -0.064 * s, 1.564 * s),
        size=(0.064 * s, 0.068 * s, 0.032 * s),
        rot=(-0.18, 0.09, 0.06),
        bevel=0.005 * s,
        taper_top=(0.82, 0.88),
        mat_idx=mat_idx[skin_mat],
    ))
    head_verts.extend(add_box(
        bm,
        center=(0.003 * s, -0.066 * s, 1.584 * s),
        size=(0.044 * s, 0.048 * s, 0.022 * s),
        rot=(-0.10, 0.09, 0.0),
        mat_idx=mat_idx["Mat_ZMouth"],
    ))
    head_verts.extend(add_box(
        bm,
        center=(-0.004 * s, -0.088 * s, 1.556 * s),
        size=(0.036 * s, 0.022 * s, 0.022 * s),
        rot=(-0.22, -0.08, 0.0),
        mat_idx=mat_idx["Mat_ZBloodDried"],
    ))
    # Jagged teeth rising from ruined crooked jaw
    head_verts.extend(_add_jagged_teeth(bm, mat_idx, s, 1.0, 0.022))

    # 3. Two split ruptured cranial-mycelial lobes forming a vertical crimson fissure down X=0
    for sx, cx, rad_x, h_top, rot_y in (
        ( 1.0,  0.038, 0.042, 1.745,  0.14),
        (-1.0, -0.034, 0.038, 1.725, -0.16),
    ):
        lobe_rings = [
            ring_ellipse(cx * s,        -0.012 * s, 1.592 * s, rad_x * 0.78 * s, 0.052 * s, n=8),
            ring_ellipse((cx + 0.006*sx)*s, -0.022 * s, 1.638 * s, rad_x * 1.05 * s, 0.062 * s, n=8),
            ring_ellipse((cx + 0.004*sx)*s, -0.016 * s, 1.692 * s, rad_x * 0.96 * s, 0.058 * s, n=8),
            ring_ellipse(cx * s,         0.004 * s, h_top * s, rad_x * 0.56 * s, 0.042 * s, n=8),
        ]
        v_lobe = loft_rings(bm, lobe_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_ZFungusDark"])
        for f in {f for v in v_lobe for f in v.link_faces}:
            c = f.calc_center_median()
            # Inner split walls (facing X=0 and front -Y) show exposed crimson flesh/fissure
            if abs(c.x) < 0.026 * s and c.y < 0.0 * s:
                f.material_index = mat_idx["Mat_ZFlesh"]
            elif abs(c.x) < 0.036 * s and c.y < -0.025 * s:
                f.material_index = mat_idx["Mat_ZBloodDried"]
        head_verts.extend(v_lobe)

    # 4. 18 Dense Overlapping Radial Split-Flower Coral Plates (completely replacing face & cranium)
    outer_fans = [
        # Left Face Bloom Wing (6 big wild scalloped petals bursting outward-left-forward)
        (( 0.032, -0.036, 1.618), ( 0.78, -0.60,  0.14), ( 0.00, -0.25, 1.0), 0.135, 114.0, 0.016, 1),
        (( 0.036, -0.026, 1.658), ( 0.80, -0.48,  0.34), (-0.10, -0.25, 1.0), 0.155, 120.0, 0.018, 2),
        (( 0.034, -0.018, 1.702), ( 0.68, -0.34,  0.65), (-0.15, -0.25, 1.0), 0.162, 122.0, 0.018, 3),
        (( 0.024, -0.022, 1.738), ( 0.42, -0.42,  0.80), (-0.10, -0.30, 1.0), 0.138, 116.0, 0.016, 4),
        (( 0.022, -0.050, 1.642), ( 0.48, -0.84,  0.22), ( 0.00, -0.20, 1.0), 0.112, 108.0, 0.014, 5),
        (( 0.018, -0.048, 1.688), ( 0.36, -0.82,  0.44), ( 0.00, -0.25, 1.0), 0.122, 110.0, 0.015, 6),
        # Right Face Bloom Wing (5 asymmetric staggered petals flaring outward-right-forward)
        ((-0.028, -0.036, 1.615), (-0.76, -0.62,  0.10), ( 0.05, -0.25, 1.0), 0.118, 110.0, 0.015, 7),
        ((-0.034, -0.022, 1.656), (-0.82, -0.45,  0.35), ( 0.10, -0.25, 1.0), 0.140, 118.0, 0.016, 8),
        ((-0.028, -0.018, 1.700), (-0.62, -0.35,  0.70), ( 0.15, -0.25, 1.0), 0.132, 114.0, 0.016, 9),
        ((-0.018, -0.048, 1.648), (-0.42, -0.86,  0.28), ( 0.00, -0.20, 1.0), 0.102, 104.0, 0.014, 10),
        ((-0.016, -0.042, 1.720), (-0.30, -0.52,  0.80), ( 0.05, -0.30, 1.0), 0.116, 108.0, 0.014, 11),
        # Back & Crown Coral Armor Shell (4 thick plates covering rear of skull 100%)
        (( 0.005,  0.012, 1.745), ( 0.08,  0.48,  0.88), ( 0.00,  0.20, 1.0), 0.145, 122.0, 0.018, 12),
        ((-0.022,  0.046, 1.698), (-0.42,  0.84,  0.34), ( 0.00,  0.25, 1.0), 0.128, 114.0, 0.016, 13),
        (( 0.028,  0.046, 1.668), ( 0.48,  0.82,  0.30), ( 0.00,  0.25, 1.0), 0.124, 112.0, 0.016, 14),
        (( 0.000,  0.054, 1.622), ( 0.00,  0.94,  0.22), ( 0.00,  0.30, 1.0), 0.115, 110.0, 0.015, 15),
    ]
    for pos, ndir, udir, rad, spr, th, seed in outer_fans:
        head_verts.extend(_add_fungal_fan(
            bm, mat_idx,
            origin=(pos[0] * s, pos[1] * s, pos[2] * s),
            normal_dir=ndir, up_dir=udir,
            radius=rad * s, spread_deg=spr, thickness=th * s, seed=seed,
        ))

    # Inner Fissure Wet-Gill Plates flaring directly out of the central vertical split (X ~ ±0.014)
    inner_gills = [
        (( 0.014, -0.054, 1.628), ( 0.28, -0.94, -0.10), (-0.25, 0.1, 1.0), 0.068, 92.0, 0.011, 21),
        ((-0.014, -0.056, 1.652), (-0.28, -0.94,  0.12), ( 0.25, 0.1, 1.0), 0.072, 94.0, 0.011, 22),
        (( 0.010, -0.050, 1.692), ( 0.20, -0.92,  0.32), (-0.20, 0.1, 1.0), 0.070, 92.0, 0.011, 23),
    ]
    for pos, ndir, udir, rad, spr, th, seed in inner_gills:
        head_verts.extend(_add_fungal_fan(
            bm, mat_idx,
            origin=(pos[0] * s, pos[1] * s, pos[2] * s),
            normal_dir=ndir, up_dir=udir,
            radius=rad * s, spread_deg=spr, thickness=th * s,
            mat_top="Mat_ZFungusGill", mat_bot="Mat_ZFlesh", mat_rim="Mat_ZFungusCap",
            seed=seed,
        ))

    # 5. Creeping mycelial root tendrils snaking from split jaw/cranium down neck & collar
    for p0, p1 in (
        (( 0.036, -0.056, 1.618), ( 0.048, -0.044, 1.545)),
        (( 0.048, -0.044, 1.545), ( 0.038, -0.036, 1.482)),
        ((-0.034, -0.052, 1.612), (-0.046, -0.032, 1.535)),
        ((-0.046, -0.032, 1.535), (-0.036, -0.022, 1.478)),
        (( 0.022,  0.056, 1.608), ( 0.034,  0.046, 1.518)),
        ((-0.024,  0.058, 1.602), (-0.036,  0.044, 1.515)),
    ):
        head_verts.extend(add_cylinder(
            bm,
            (p0[0] * s, p0[1] * s, p0[2] * s),
            (p1[0] * s, p1[1] * s, p1[2] * s),
            0.0068 * s, 0.0040 * s, segments=5, mat_idx=mat_idx["Mat_ZFungusRoot"],
        ))

    regions.setdefault("neck", []).extend(neck_verts)
    regions.setdefault("head", []).extend(head_verts)


def _add_curved_leaf(bm, mat_idx, origin, fwd_dir, up_dir, length, width, thickness=0.010,
                     curl=0.18, mat_top="Mat_ZLeafMid", mat_bot="Mat_ZLeafDark"):
    """Build a watertight 4-ring tapered curved botanical leaf with crisp central vein diamond profile."""
    orig = Vector(origin)
    fwd = Vector(fwd_dir).normalized()
    u_ref = Vector(up_dir)
    up = u_ref - fwd * u_ref.dot(fwd)
    if up.length < 1e-6:
        fb = Vector((0.0, 0.0, 1.0)) if abs(fwd.z) < 0.9 else Vector((0.0, 1.0, 0.0))
        up = fb - fwd * fb.dot(fwd)
    up.normalize()
    side = up.cross(fwd).normalized()

    rings = []
    # 4 stages from petiole stem -> wide mid-blade -> arched curl -> pointed tip
    for t, w_f, th_f, c_f in (
        (0.05, 0.16, 0.55, 0.00),
        (0.38, 1.00, 0.50, 0.15),
        (0.74, 0.68, 0.34, 0.55),
        (1.00, 0.10, 0.14, 1.00),
    ):
        c_pt = orig + fwd * (length * t) - up * (length * curl * c_f)
        hw = 0.5 * width * w_f
        ht = 0.5 * thickness * th_f
        rings.append([
            tuple(c_pt + up * ht),
            tuple(c_pt + side * hw),
            tuple(c_pt - up * ht * 0.9),
            tuple(c_pt - side * hw),
        ])

    verts = loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_idx[mat_top])
    for f in {f for v in verts for f in v.link_faces}:
        f.normal_update()
        if f.normal.dot(up) < -0.15:
            f.material_index = mat_idx[mat_bot]
    return verts


def _add_ruffled_blood_petal(
    bm, mat_idx, center, radial_dir, fwd_dir, length, max_width,
    thickness=0.018, curl_fwd=0.03, ruffle_amp=0.016, ruffle_freq=2.3, seed=0,
    mat_front="Mat_ZRaffPetal", mat_ridge="Mat_ZRaffPetalBright", mat_back="Mat_ZRaffPetalDark",
):
    """Build a corrugated, jagged-edged low-poly carnivorous petal (no spots, layered folds)."""
    c0 = Vector(center)
    rad = Vector(radial_dir).normalized()
    fwd = Vector(fwd_dir).normalized()
    side = fwd.cross(rad)
    if side.length < 1e-6:
        fb = Vector((1.0, 0.0, 0.0)) if abs(fwd.x) < 0.9 else Vector((0.0, 0.0, 1.0))
        side = fwd.cross(fb)
    side.normalize()

    n_arc = 6
    rings = []
    # 5 radial stages: narrow base -> widening cup -> wide corrugated mid -> flared ruffle -> jagged edge
    stages = (
        (0.16, 0.34, 0.52,  0.00, 0.25),
        (0.40, 0.68, 0.48,  0.22, 0.55),
        (0.68, 0.96, 0.40,  0.60, 0.90),
        (0.88, 1.00, 0.28,  0.90, 1.00),
        (1.00, 0.72, 0.16,  1.00, 0.85),
    )
    for r_f, w_f, th_f, curl_f, pleat_f in stages:
        top_pts = []
        bot_pts = []
        for k in range(n_arc):
            s_norm = (k / (n_arc - 1)) - 0.5  # -0.5 .. +0.5
            jag = 1.0 + (0.14 * pleat_f * math.cos(k * 2.5 + seed * 1.3) if r_f > 0.60 else 0.0)
            r_here = length * r_f * jag
            ruffle = ruffle_amp * pleat_f * math.sin(s_norm * math.pi * ruffle_freq + seed * 1.7)
            cup_z = curl_fwd * curl_f + 0.010 * length * (s_norm * s_norm) * pleat_f
            c_pt = c0 + rad * r_here + side * (max_width * w_f * s_norm) + fwd * (cup_z + ruffle)
            ht = 0.5 * thickness * th_f
            top_pts.append(tuple(c_pt + fwd * ht))
            bot_pts.append(tuple(c_pt - fwd * ht))
        rings.append(top_pts + list(reversed(bot_pts)))

    verts = loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_idx[mat_front])
    for f in {f for v in verts for f in v.link_faces}:
        f.normal_update()
        cen = f.calc_center_median()
        r_proj = (cen - c0).dot(rad)
        ndot = f.normal.dot(fwd)
        if ndot < -0.35 or r_proj < length * 0.36:
            f.material_index = mat_idx[mat_back]
        elif r_proj > length * 0.72 and ndot > 0.10:
            f.material_index = mat_idx[mat_ridge]
        else:
            f.material_index = mat_idx[mat_front]
    return verts


def _add_stamen_filament(bm, mat_idx, start_pt, dir_vec, fwd_dir, length, r0=0.0052, r1=0.0018, curl_angle=1.15, seed=0):
    """Build a gnarled curling yellow-ochre filament tendril around the jaws."""
    p0 = Vector(start_pt)
    d = Vector(dir_vec).normalized()
    fwd = Vector(fwd_dir).normalized()
    tan_side = fwd.cross(d)
    if tan_side.length < 1e-6:
        tan_side = Vector((1.0, 0.0, 0.0))
    tan_side.normalize()
    up_perp = tan_side.cross(d).normalized()

    spine = []
    rads = []
    segs = 4
    twist_sign = 1.0 if (seed % 2 == 0) else -1.0
    for i in range(segs + 1):
        t = i / segs
        ang = t * curl_angle * twist_sign
        step_dir = d * math.cos(t * 0.85) + fwd * math.sin(t * 0.75) + tan_side * (0.45 * math.sin(ang)) + up_perp * (0.18 * math.cos(t * 3.0 + seed))
        step_dir.normalize()
        spine.append(tuple(p0 + step_dir * (length * t)))
        r = r0 * (1.0 - t) + r1 * t
        rads.append((r, r))

    rings = []
    for i, sp in enumerate(spine):
        v = Vector(sp)
        tvec = Vector(spine[min(segs, i + 1)]) - Vector(spine[max(0, i - 1)])
        if tvec.length < 1e-6:
            tvec = d
        tvec.normalize()
        u_vec = fwd - tvec * fwd.dot(tvec)
        if u_vec.length < 1e-6:
            u_vec = tan_side
        u_vec.normalize()
        s_vec = u_vec.cross(tvec).normalized()
        rr = rads[i][0]
        rings.append([
            tuple(v + u_vec * rr),
            tuple(v + s_vec * rr),
            tuple(v - u_vec * rr),
            tuple(v - s_vec * rr),
        ])
    return loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_idx["Mat_ZRaffStamen"])


def _add_irregular_fang_row(bm, mat_idx, specs, mat_fang="Mat_ZBone", mat_tip=None):
    """Build jagged uneven curved/angled predator fangs from `[(base_xyz, tip_xyz, rad, hook_vec), ...]`."""
    verts = []
    for bp, tp, rb, hook in specs:
        bv, tv, hv = Vector(bp), Vector(tp), Vector(hook)
        mid = bv.lerp(tv, 0.54) + hv
        verts.extend(add_cylinder(bm, tuple(bv), tuple(mid), rb, rb * 0.58, segments=5, mat_idx=mat_idx[mat_fang]))
        verts.extend(add_cone(bm, tuple(mid), tuple(tv), rb * 0.58, segments=4, mat_idx=mat_idx[mat_tip or mat_fang]))
    return verts


def _add_saliva_strands(bm, mat_idx, anchors, drop_vec=(0.0, 0.0, -0.025), rad=0.0022):
    """Build glistening curved wet saliva/mucus droplets & drool threads anchored to gums/fangs."""
    verts = []
    dv = Vector(drop_vec)
    for idx, (bp, ep, sag) in enumerate(anchors):
        p0, p2 = Vector(bp), Vector(ep)
        p1 = p0.lerp(p2, 0.52) + dv * sag
        verts.extend(add_cylinder(bm, tuple(p0), tuple(p1), rad, rad * 0.72, segments=4, mat_idx=mat_idx["Mat_MSaliva"]))
        verts.extend(add_cylinder(bm, tuple(p1), tuple(p2), rad * 0.72, rad * 0.85, segments=4, mat_idx=mat_idx["Mat_MSaliva"]))
        if idx % 2 == 0:
            verts.extend(add_cone(bm, tuple(p1), tuple(p1 + dv * 1.15), rad * 1.15, segments=4, mat_idx=mat_idx["Mat_MSaliva"]))
    return verts


def build_head_rafflesia(
    bm, mat_idx, regions, proportions=None,
    center=None, fwd_dir=None, head_scale=1.0, build_neck=True, split_jaw_regions=False,
):
    """Build terrified carnivorous Blood-Flower Monster Head with optional split 4-jaw rig regions & arbitrary placement."""
    s = (proportions["scale"] if proportions is not None else 1.0) * head_scale
    neck_verts = []
    head_verts = []

    if build_neck:
        # 1. Braided gnarled woody/vine neck hunched forward toward monster maw
        neck_rings = [
            ring_ellipse(0.0,       0.012 * s, 1.455 * s, 0.064 * s, 0.062 * s, n=8),
            ring_ellipse(0.004 * s, 0.006 * s, 1.505 * s, 0.058 * s, 0.056 * s, n=8),
            ring_ellipse(-0.003*s, -0.002 * s, 1.558 * s, 0.056 * s, 0.056 * s, n=8),
            ring_ellipse(0.0,      -0.008 * s, 1.615 * s, 0.064 * s, 0.064 * s, n=8),
        ]
        v_neck = loft_rings(bm, neck_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_ZBarkDark"])
        for f in {f for v in v_neck for f in v.link_faces}:
            if f.calc_center_median().z > 1.545 * s:
                f.material_index = mat_idx["Mat_ZLeafDark"]
        neck_verts.extend(v_neck)

        for k in range(6):
            ang0 = (2.0 * math.pi * k) / 6.0
            ang1 = ang0 + 0.85 * (1.0 if k % 2 == 0 else -1.0)
            p0 = (math.cos(ang0) * 0.058 * s, (0.012 + math.sin(ang0) * 0.056) * s, 1.462 * s)
            pm = (math.cos((ang0 + ang1) * 0.5) * 0.056 * s, (0.002 + math.sin((ang0 + ang1) * 0.5) * 0.056) * s, 1.535 * s)
            p1 = (math.cos(ang1) * 0.062 * s, (-0.008 + math.sin(ang1) * 0.060) * s, 1.608 * s)
            m_cord = "Mat_ZBarkMid" if k % 3 == 0 else ("Mat_ZVinePale" if k % 3 == 1 else "Mat_ZLeafDark")
            neck_verts.extend(add_cylinder(bm, p0, pm, 0.0105 * s, 0.0095 * s, segments=5, mat_idx=mat_idx[m_cord]))
            neck_verts.extend(add_cylinder(bm, pm, p1, 0.0095 * s, 0.0080 * s, segments=5, mat_idx=mat_idx[m_cord]))

    # 2. Solid bulbous rear calyx & 10 jagged sepal armor fins enclosing throat 100% from back views
    flower_center = Vector(center) if center is not None else Vector((0.0, -0.036 * s, 1.682 * s))
    fwd = Vector(fwd_dir).normalized() if fwd_dir is not None else Vector((0.0, -0.975, -0.222)).normalized()
    side_u = Vector((1.0, 0.0, 0.0))
    if abs(fwd.dot(side_u)) > 0.9:
        side_u = Vector((0.0, 1.0, 0.0))
    side_u = (side_u - fwd * side_u.dot(fwd)).normalized()
    side_v = fwd.cross(side_u).normalized()

    calyx_rings = []
    for f_off, rx, ry in (
        (-0.145, 0.038, 0.036),
        (-0.112, 0.092, 0.072),
        (-0.070, 0.120, 0.092),
        (-0.028, 0.114, 0.086),
    ):
        c_cal = flower_center + fwd * (f_off * s)
        calyx_rings.append([
            tuple(c_cal + side_u * (math.cos(2.0 * math.pi * i / 10) * rx * s)
                        + side_v * (math.sin(2.0 * math.pi * i / 10) * ry * s))
            for i in range(10)
        ])
    v_calyx = loft_rings(bm, calyx_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_ZLeafDark"])
    for f in {f for v in v_calyx for f in v.link_faces}:
        if (f.calc_center_median() - flower_center).dot(fwd) < -0.095 * s:
            f.material_index = mat_idx["Mat_ZBarkDark"]
    head_verts.extend(v_calyx)

    # 10 jagged green sepal armor leaves radiating behind the crimson blood-mane
    for k in range(10):
        ang = math.radians(18.0 + k * 36.0 + 4.0 * math.sin(k * 2.1))
        r_dir = side_u * math.cos(ang) + side_v * math.sin(ang)
        sep_origin = flower_center - fwd * (0.046 * s) + r_dir * (0.074 * s)
        head_verts.extend(_add_curved_leaf(
            bm, mat_idx,
            origin=sep_origin,
            fwd_dir=(r_dir - fwd * 0.22).normalized(),
            up_dir=fwd,
            length=(0.188 + 0.018 * (k % 2)) * s,
            width=0.078 * s,
            thickness=0.016 * s,
            curl=0.20,
            mat_top="Mat_ZLeafMid", mat_bot="Mat_ZLeafDark",
        ))

    # 3. Three Concentric Overlapping Tiers of Ruffled Blood-Petals (31 total -> massive carnivorous mane)
    # Tier A: 14 large ragged outer mane petals (all curling gently forward -> vibrant red crown!)
    for k in range(14):
        jitter = math.radians(5.0 * math.sin(k * 2.7))
        ang = math.radians(90.0 + k * (360.0 / 14.0)) + jitter
        r_dir = side_u * math.cos(ang) + side_v * math.sin(ang)
        curl_alt = (0.016 if k % 2 == 0 else 0.032) * s
        head_verts.extend(_add_ruffled_blood_petal(
            bm, mat_idx,
            center=flower_center - fwd * (0.010 * s),
            radial_dir=r_dir, fwd_dir=fwd,
            length=(0.228 + 0.022 * math.cos(k * 1.9)) * s,
            max_width=(0.136 + 0.012 * math.sin(k * 2.3)) * s,
            thickness=0.018 * s, curl_fwd=curl_alt, ruffle_amp=0.022 * s, ruffle_freq=2.5, seed=k + 1,
            mat_front="Mat_ZRaffPetal", mat_ridge="Mat_ZRaffPetalBright", mat_back="Mat_ZRaffPetalDark",
        ))

    # Tier B: 10 denser forward-cupped mid ruffled petals
    for k in range(10):
        ang = math.radians(108.0 + k * 36.0 + 4.5 * math.cos(k * 3.1))
        r_dir = side_u * math.cos(ang) + side_v * math.sin(ang)
        head_verts.extend(_add_ruffled_blood_petal(
            bm, mat_idx,
            center=flower_center + fwd * (0.014 * s),
            radial_dir=r_dir, fwd_dir=fwd,
            length=(0.178 + 0.016 * math.sin(k * 2.2)) * s,
            max_width=0.116 * s,
            thickness=0.016 * s, curl_fwd=0.044 * s, ruffle_amp=0.017 * s, ruffle_freq=2.6, seed=k + 20,
            mat_front="Mat_ZRaffPetal", mat_ridge="Mat_ZRaffPetalBright", mat_back="Mat_ZRaffPetalDark",
        ))

    # Tier C: 7 inner curled maroon collar petals cupping tight around jaw seam
    for k in range(7):
        ang = math.radians(90.0 + k * (360.0 / 7.0))
        r_dir = side_u * math.cos(ang) + side_v * math.sin(ang)
        head_verts.extend(_add_ruffled_blood_petal(
            bm, mat_idx,
            center=flower_center + fwd * (0.028 * s),
            radial_dir=r_dir, fwd_dir=fwd,
            length=0.124 * s, max_width=0.088 * s,
            thickness=0.014 * s, curl_fwd=0.056 * s, ruffle_amp=0.012 * s, ruffle_freq=2.1, seed=k + 40,
            mat_front="Mat_ZRaffPetalDark", mat_ridge="Mat_ZRaffPetal", mat_back="Mat_ZRaffPetalDark",
        ))

    # 4. Protruding 4-Lobed Fleshy Predator Beak-Maw + Abyssal Throat Funnel
    mouth_c = flower_center + fwd * (0.024 * s)

    # 4a. Deep Abyssal Throat Funnel (safely enclosed inside rear calyx)
    n_maw = 12
    throat_specs = (
        (-0.078, 0.016),
        (-0.040, 0.040),
        ( 0.000, 0.060),
        ( 0.024, 0.070),
        ( 0.006, 0.080),
    )
    t_rings = []
    for f_off, rad in throat_specs:
        c_ring = mouth_c + fwd * (f_off * s)
        t_rings.append([
            tuple(c_ring + (side_u * math.cos(2.0 * math.pi * i / n_maw) + side_v * math.sin(2.0 * math.pi * i / n_maw)) * (rad * s))
            for i in range(n_maw)
        ])
    v_throat = loft_rings(bm, t_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_ZFlesh"])
    for f in {f for v in v_throat for f in v.link_faces}:
        cen = f.calc_center_median()
        if (cen - mouth_c).dot(fwd) < 0.006 * s:
            f.material_index = mat_idx["Mat_ZMouth"]
        else:
            f.material_index = mat_idx["Mat_ZBloodFresh"]
    head_verts.extend(v_throat)

    def _build_jaw_lobe(ring_specs, n_pts=8):
        rings = []
        for off_u, off_v, off_f, rx, ry in ring_specs:
            c_r = mouth_c + side_u * (off_u * s) + side_v * (off_v * s) + fwd * (off_f * s)
            pts = []
            for i in range(n_pts):
                th = (2.0 * math.pi * i) / n_pts
                pts.append(tuple(c_r + side_u * (math.cos(th) * rx * s) + side_v * (math.sin(th) * ry * s)))
            rings.append(pts)
        v_j = loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_idx["Mat_ZRaffJawFlesh"])
        for f in {f for v in v_j for f in v.link_faces}:
            f.normal_update()
            cen = f.calc_center_median()
            to_axis = (mouth_c + fwd * (cen - mouth_c).dot(fwd)) - cen
            if to_axis.length > 1e-5 and f.normal.dot(to_axis.normalized()) > 0.25:
                f.material_index = mat_idx["Mat_ZFlesh"]
            elif (cen - mouth_c).dot(fwd) > 0.110 * s:
                f.material_index = mat_idx["Mat_ZBloodDried"]
        return v_j

    jaw_top_verts = _build_jaw_lobe([
        (0.0,  0.044, -0.006, 0.062, 0.028),
        (0.0,  0.056,  0.036, 0.054, 0.028),
        (0.0,  0.044,  0.084, 0.036, 0.020),
        (0.0,  0.020,  0.124, 0.014, 0.011),
        (0.0,  0.004,  0.146, 0.003, 0.003),
    ])
    jaw_bot_verts = _build_jaw_lobe([
        (0.0, -0.044, -0.006, 0.056, 0.024),
        (0.0, -0.054,  0.034, 0.046, 0.022),
        (0.0, -0.062,  0.078, 0.028, 0.016),
        (0.0, -0.068,  0.116, 0.011, 0.009),
        (0.0, -0.072,  0.136, 0.003, 0.003),
    ])
    jaw_l_verts = _build_jaw_lobe([
        (0.044, -0.004, -0.004, 0.024, 0.040),
        (0.064, -0.008,  0.032, 0.022, 0.034),
        (0.082, -0.012,  0.070, 0.014, 0.018),
        (0.095, -0.015,  0.104, 0.004, 0.005),
    ])
    jaw_r_verts = _build_jaw_lobe([
        (-0.044, -0.004, -0.004, 0.024, 0.040),
        (-0.064, -0.008,  0.032, 0.022, 0.034),
        (-0.082, -0.012,  0.070, 0.014, 0.018),
        (-0.095, -0.015,  0.104, 0.004, 0.005),
    ])

    # 5. Irregular Predator Fangs, Wet Crimson Gums, Saliva Threads & Coiled Carnivorous Lure
    jaw_focus = mouth_c + fwd * (0.064 * s) - side_v * (0.012 * s)
    top_fang_specs = []
    for i in range(12):
        frac = (i / 11.0) - 0.5
        base = mouth_c + side_u * (frac * 0.092 * s) + side_v * ((0.036 - 0.026 * abs(frac)) * s) + fwd * ((0.122 - 0.092 * (frac * frac)) * s)
        to_in = (jaw_focus - base).normalized()
        is_big = (i in (2, 4, 7, 9))
        flen = ((0.044 if is_big else 0.026) - 0.008 * abs(frac)) * s
        jitter_u = side_u * (0.004 * s * math.sin(i * 2.1))
        tip = base + (to_in * 0.60 - side_v * 0.58 - fwd * 0.14).normalized() * flen + jitter_u
        top_fang_specs.append((base, tip, (0.0056 if is_big else 0.0040) * s, -fwd * (0.005 * s)))
    jaw_top_verts.extend(_add_irregular_fang_row(bm, mat_idx, top_fang_specs, mat_fang="Mat_ZBone", mat_tip="Mat_ZBloodDried"))

    bot_fang_specs = []
    for i in range(10):
        frac = (i / 9.0) - 0.5
        base = mouth_c + side_u * (frac * 0.076 * s) + side_v * ((-0.056 + 0.018 * abs(frac)) * s) + fwd * ((0.114 - 0.082 * (frac * frac)) * s)
        to_in = (jaw_focus - base).normalized()
        is_big = (i in (1, 3, 6, 8))
        flen = ((0.040 if is_big else 0.024) - 0.006 * abs(frac)) * s
        tip = base + (to_in * 0.62 + side_v * 0.56 - fwd * 0.12).normalized() * flen
        bot_fang_specs.append((base, tip, (0.0052 if is_big else 0.0038) * s, -fwd * (0.004 * s)))
    jaw_bot_verts.extend(_add_irregular_fang_row(bm, mat_idx, bot_fang_specs, mat_fang="Mat_ZBone", mat_tip="Mat_ZRaffJawFlesh"))

    for sx, jl in ((1.0, jaw_l_verts), (-1.0, jaw_r_verts)):
        cf_specs = []
        for i in range(6):
            frac = (i / 5.0) - 0.5
            base = mouth_c + side_u * ((0.086 - 0.032 * abs(frac)) * sx * s) + side_v * ((frac * 0.044 - 0.010) * s) + fwd * ((0.088 - 0.060 * (frac * frac)) * s)
            is_big = (i % 2 == 1)
            flen = (0.030 if is_big else 0.020) * s
            tip = base + (-side_u * sx * 0.78 - fwd * 0.35 - side_v * frac * 0.25).normalized() * flen
            cf_specs.append((base, tip, (0.0048 if is_big else 0.0036) * s, -fwd * (0.004 * s)))
        jl.extend(_add_irregular_fang_row(bm, mat_idx, cf_specs, mat_fang="Mat_ZBone"))

    # Wet crimson gum cushions & drooping saliva threads on upper & lower jaws
    jaw_top_verts.extend(add_box(
        bm, center=tuple(mouth_c + fwd * (0.065 * s) + side_v * (0.028 * s)),
        size=(0.072 * s, 0.048 * s, 0.016 * s), bevel=0.005 * s, mat_idx=mat_idx["Mat_ZBloodFresh"],
    ))
    jaw_top_verts.extend(_add_saliva_strands(bm, mat_idx, [
        (mouth_c + side_u * (-0.028 * s) + side_v * (0.026 * s) + fwd * (0.085 * s),
         mouth_c + side_u * ( 0.000 * s) + side_v * (0.020 * s) + fwd * (0.095 * s), 0.7),
        (mouth_c + side_u * ( 0.000 * s) + side_v * (0.020 * s) + fwd * (0.095 * s),
         mouth_c + side_u * ( 0.028 * s) + side_v * (0.026 * s) + fwd * (0.085 * s), 0.8),
    ], drop_vec=tuple(-side_v * (0.024 * s)), rad=0.0022 * s))
    jaw_bot_verts.extend(add_box(
        bm, center=tuple(mouth_c + fwd * (0.062 * s) - side_v * (0.046 * s)),
        size=(0.062 * s, 0.044 * s, 0.014 * s), bevel=0.005 * s, mat_idx=mat_idx["Mat_ZBloodFresh"],
    ))

    # Coiled barbed carnivorous plant lure-tongue erupting out of deep throat
    lure_pts = [
        tuple(mouth_c - fwd * (0.015 * s) - side_v * (0.008 * s)),
        tuple(mouth_c + fwd * (0.032 * s) - side_v * (0.004 * s) + side_u * (0.008 * s)),
        tuple(mouth_c + fwd * (0.074 * s) - side_v * (0.018 * s) - side_u * (0.006 * s)),
        tuple(mouth_c + fwd * (0.105 * s) - side_v * (0.026 * s) + side_u * (0.004 * s)),
    ]
    for idx_l in range(3):
        head_verts.extend(add_cylinder(
            bm, lure_pts[idx_l], lure_pts[idx_l + 1],
            (0.014 - 0.003 * idx_l) * s, (0.011 - 0.003 * idx_l) * s, segments=5,
            mat_idx=mat_idx["Mat_ZRaffStamen" if idx_l == 2 else "Mat_ZBloodFresh"],
        ))

    # 8 Deeper Gullet Swallowing Fangs (fixed to throat/head)
    for i in range(8):
        ang = (2.0 * math.pi * i) / 8.0 + 0.25
        r_dir = side_u * math.cos(ang) + side_v * math.sin(ang)
        base = mouth_c + fwd * (0.010 * s) + r_dir * (0.048 * s)
        tip = base - r_dir * (0.028 * s) - fwd * (0.016 * s)
        head_verts.extend(add_cone(bm, tuple(base), tuple(tip), 0.0048 * s, segments=4, mat_idx=mat_idx["Mat_ZBone"]))

    # 6. 14 Gnarled Yellow-Ochre Stamen Filaments framing the split beak-maw
    for k in range(14):
        ang = math.radians(12.0 + k * (360.0 / 14.0) + 6.0 * math.sin(k * 2.4))
        r_dir = side_u * math.cos(ang) + side_v * math.sin(ang)
        st_pt = mouth_c + fwd * (0.014 * s) + r_dir * (0.074 * s)
        head_verts.extend(_add_stamen_filament(
            bm, mat_idx,
            start_pt=st_pt,
            dir_vec=(r_dir * 0.85 + fwd * 0.45).normalized(),
            fwd_dir=fwd,
            length=(0.080 + 0.022 * (k % 3)) * s,
            r0=0.0052 * s, r1=0.0018 * s, curl_angle=1.18, seed=k + 1,
        ))

    if split_jaw_regions:
        regions.setdefault("jaw_top", []).extend(jaw_top_verts)
        regions.setdefault("jaw_bot", []).extend(jaw_bot_verts)
        regions.setdefault("jaw_L", []).extend(jaw_l_verts)
        regions.setdefault("jaw_R", []).extend(jaw_r_verts)
    else:
        head_verts.extend(jaw_top_verts)
        head_verts.extend(jaw_bot_verts)
        head_verts.extend(jaw_l_verts)
        head_verts.extend(jaw_r_verts)

    if neck_verts:
        regions.setdefault("neck", []).extend(neck_verts)
    regions.setdefault("head", []).extend(head_verts)


def _add_tapered_ribbon(
    bm, mat_idx, spine_pts, width_list, thick_list, up_hint=(0.0, 1.0, 0.0),
    twist_total=0.0, mat_front="Mat_MShroudBone", mat_back="Mat_MShroudDark",
):
    """Loft a sweeping multi-segment curved bone/petal ribbon blade with 4-point diamond section."""
    vecs = [Vector(p) for p in spine_pts]
    m = len(vecs)
    rings = []
    uh = Vector(up_hint)
    fwd_base = (vecs[-1] - vecs[0]).normalized() if (vecs[-1] - vecs[0]).length > 1e-5 else Vector((0.0, 0.0, 1.0))

    for k in range(m):
        if k == 0:
            tan = vecs[1] - vecs[0]
        elif k == m - 1:
            tan = vecs[-1] - vecs[-2]
        else:
            tan = vecs[k + 1] - vecs[k - 1]
        if tan.length < 1e-6:
            tan = fwd_base
        tan.normalize()
        up = uh - tan * uh.dot(tan)
        if up.length < 1e-6:
            fb = Vector((0.0, -1.0, 0.0)) if abs(tan.y) < 0.9 else Vector((1.0, 0.0, 0.0))
            up = fb - tan * fb.dot(tan)
        up.normalize()
        side = up.cross(tan).normalized()

        t = k / max(1, m - 1)
        ang = twist_total * t
        ca, sa = math.cos(ang), math.sin(ang)
        u_rot = up * ca + side * sa
        s_rot = -up * sa + side * ca

        hw = 0.5 * width_list[k]
        ht = 0.5 * thick_list[k]
        rings.append([
            tuple(vecs[k] + u_rot * ht),
            tuple(vecs[k] + s_rot * hw),
            tuple(vecs[k] - u_rot * ht),
            tuple(vecs[k] - s_rot * hw),
        ])

    verts = loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_idx[mat_front])
    for f in {f for v in verts for f in v.link_faces}:
        f.normal_update()
        if f.normal.dot(uh) < -0.15:
            f.material_index = mat_idx[mat_back]
    return verts


def build_head_scythe_stalker(bm, mat_idx, regions, center=(0.0, -0.28, 1.56), fwd_dir=(0.0, -0.96, -0.28), scale=1.0):
    """Build Ref-3 hunched insectoid-skull predator head: asymmetric bulging yellow eye, 5 quills, split mandibles & wet tongue."""
    s = scale
    c0 = Vector(center)
    fwd = Vector(fwd_dir).normalized()
    side_u = Vector((1.0, 0.0, 0.0))
    side_u = (side_u - fwd * side_u.dot(fwd)).normalized()
    side_v = fwd.cross(side_u).normalized()

    def _pt(u, v, f):
        return c0 + side_u * (u * s) + side_v * (v * s) + fwd * (f * s)

    head_verts = []
    # 1. Armored asymmetric chitin cranium (bulges back & tapers down into upper snout)
    skull_specs = (
        (-0.145,  0.025, 0.064, 0.068),
        (-0.075,  0.045, 0.092, 0.095),
        ( 0.010,  0.048, 0.096, 0.092),
        ( 0.085,  0.032, 0.078, 0.074),
        ( 0.145,  0.010, 0.048, 0.044),
    )
    sk_rings = []
    for f_off, v_off, rx, ry in skull_specs:
        cr = _pt(0.0, v_off, f_off)
        sk_rings.append([
            tuple(cr + side_u * (math.cos(2.0 * math.pi * i / 10) * rx * s)
                     + side_v * (math.sin(2.0 * math.pi * i / 10) * ry * s))
            for i in range(10)
        ])
    v_sk = loft_rings(bm, sk_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_MChitinDark"])
    for f in {f for v in v_sk for f in v.link_faces}:
        cen = f.calc_center_median()
        if (cen - c0).dot(side_v) > 0.065 * s:
            f.material_index = mat_idx["Mat_MChitinMid"]
        elif (cen - c0).dot(fwd) > 0.075 * s and (cen - c0).dot(side_v) < -0.010 * s:
            f.material_index = mat_idx["Mat_ZBloodDried"]
    head_verts.extend(v_sk)

    # 1b. Faceted Armored Brow Ridges & Scarred Nasal Bridge (breaks smooth dome silhouette)
    head_verts.extend(add_box(
        bm, center=tuple(_pt(0.0, 0.056, 0.098)), size=(0.135 * s, 0.048 * s, 0.042 * s),
        rot=(-0.18, 0.0, 0.0), bevel=0.008 * s, taper_top=(0.82, 0.85), mat_idx=mat_idx["Mat_MChitinMid"],
    ))
    head_verts.extend(add_box(
        bm, center=tuple(_pt(0.0, 0.022, 0.138)), size=(0.044 * s, 0.048 * s, 0.036 * s),
        rot=(0.15, 0.0, 0.0), bevel=0.006 * s, mat_idx=mat_idx["Mat_MChitinDark"],
    ))

    # Dark deep throat pocket + wet crimson upper palate gum ridge
    head_verts.extend(add_box(
        bm, center=tuple(_pt(0.0, -0.022, 0.068)), size=(0.074 * s, 0.086 * s, 0.058 * s),
        rot=(0.15, 0.0, 0.0), mat_idx=mat_idx["Mat_ZMouth"],
    ))
    head_verts.extend(add_box(
        bm, center=tuple(_pt(0.0, -0.006, 0.106)), size=(0.068 * s, 0.044 * s, 0.018 * s),
        bevel=0.004 * s, mat_idx=mat_idx["Mat_ZFlesh"],
    ))

    # 2. Blind Armored V-Crest Chitin Visor & Swept Cranial Horn-Spurs (100% Eyeless Predator Skull!)
    head_verts.extend(_add_tapered_ribbon(
        bm, mat_idx,
        [
            _pt(-0.088, 0.052, 0.064),
            _pt(-0.048, 0.044, 0.112),
            _pt( 0.000, 0.030, 0.148),
            _pt( 0.048, 0.044, 0.112),
            _pt( 0.088, 0.052, 0.064),
        ],
        [0.028 * s, 0.038 * s, 0.044 * s, 0.038 * s, 0.028 * s],
        [0.016 * s, 0.020 * s, 0.022 * s, 0.020 * s, 0.016 * s],
        up_hint=tuple(side_v), mat_front="Mat_MChitinMid", mat_back="Mat_MChitinDark",
    ))
    head_verts.extend(_add_tapered_ribbon(
        bm, mat_idx,
        [_pt(0.0, 0.102, -0.025), _pt(0.0, 0.082, 0.055), _pt(0.0, 0.046, 0.138)],
        [0.024 * s, 0.030 * s, 0.014 * s],
        [0.018 * s, 0.020 * s, 0.010 * s],
        up_hint=tuple(side_v), mat_front="Mat_MScytheBone", mat_back="Mat_MChitinMid",
    ))
    for sx_h in (1.0, -1.0):
        head_verts.extend(add_cone(
            bm, tuple(_pt(0.062 * sx_h, 0.052, 0.092)),
            tuple(_pt(0.092 * sx_h, 0.078, 0.042)),
            0.010 * s, segments=4, mat_idx=mat_idx["Mat_MScytheBone"],
        ))

    # 3. 5 Crooked Dorsal Bone Quills / Antennae bursting backward-upward from skull crest
    for q_u, q_v, q_f, du, dv, df, qlen in (
        ( 0.00, 0.115, -0.01,  0.00,  0.90, -0.44, 0.165),
        ( 0.045, 0.108,  0.02,  0.22,  0.88, -0.40, 0.145),
        (-0.045, 0.105,  0.02, -0.22,  0.88, -0.40, 0.135),
        ( 0.065, 0.088, -0.04,  0.34,  0.76, -0.55, 0.120),
        (-0.065, 0.088, -0.04, -0.34,  0.76, -0.55, 0.115),
    ):
        bp = _pt(q_u, q_v, q_f)
        tp = bp + (side_u * du + side_v * dv + fwd * df).normalized() * (qlen * s)
        head_verts.extend(add_cone(bm, tuple(bp), tuple(tp), 0.012 * s, segments=5, mat_idx=mat_idx["Mat_MScytheBone"]))

    # 8 Uneven Predator Maxilla Fangs + glossy saliva drool threads
    max_specs = []
    for i in range(8):
        frac = (i / 7.0) - 0.5
        bp = _pt(frac * 0.082, -0.014, 0.136 - 0.032 * abs(frac))
        is_canine = (i in (1, 6))
        flen = (0.038 if is_canine else 0.022) * s
        tp = bp - side_v * flen - fwd * (0.008 * s) + side_u * (0.003 * s * math.sin(i * 2.0))
        max_specs.append((bp, tp, (0.0062 if is_canine else 0.0044) * s, -fwd * (0.004 * s)))
    head_verts.extend(_add_irregular_fang_row(bm, mat_idx, max_specs, mat_fang="Mat_MScytheBone", mat_tip="Mat_ZBloodDried"))
    head_verts.extend(_add_saliva_strands(bm, mat_idx, [
        (_pt(-0.026, -0.022, 0.124), _pt(0.0, -0.028, 0.130), 0.8),
        (_pt( 0.000, -0.028, 0.130), _pt(0.026, -0.022, 0.124), 0.7),
    ], drop_vec=tuple(-side_v * (0.022 * s)), rad=0.0022 * s))

    # 4. Chunkier Armored Left & Right Split Mandible Pinchers + Serrated Bone Tusks
    for sx, rname in ((1.0, "mandible_L"), (-1.0, "mandible_R")):
        m_verts = []
        m_verts.extend(_add_tapered_ribbon(
            bm, mat_idx,
            [_pt(0.056 * sx, -0.018, 0.040), _pt(0.094 * sx, -0.032, 0.095), _pt(0.078 * sx, -0.048, 0.172), _pt(0.028 * sx, -0.052, 0.228)],
            [0.044 * s, 0.036 * s, 0.024 * s, 0.008 * s],
            [0.028 * s, 0.024 * s, 0.016 * s, 0.006 * s],
            up_hint=tuple(side_u * sx), mat_front="Mat_MChitinMid", mat_back="Mat_MChitinDark",
        ))
        tb = _pt(0.072 * sx, -0.044, 0.162)
        tm = _pt(0.048 * sx, -0.048, 0.210)
        tt = _pt(0.012 * sx, -0.046, 0.252)
        m_verts.extend(add_cylinder(bm, tuple(tb), tuple(tm), 0.010 * s, 0.007 * s, segments=5, mat_idx=mat_idx["Mat_MScytheBone"]))
        m_verts.extend(add_cone(bm, tuple(tm), tuple(tt), 0.007 * s, segments=5, mat_idx=mat_idx["Mat_ZBloodDried"]))
        for k in range(4):
            fb = _pt((0.082 - 0.014 * k) * sx, -0.036, (0.098 + 0.026 * k))
            ft = fb - side_u * (0.028 * sx * s) + side_v * (0.008 * s)
            m_verts.extend(add_cone(bm, tuple(fb), tuple(ft), 0.0052 * s, segments=4, mat_idx=mat_idx["Mat_MScytheBone"]))
        regions.setdefault(rname, []).extend(m_verts)

    # 5. Dropped Jagged Lower Split-Jaw (`jaw_bot`) + Double-Row Fangs + Forked Wet Tongue
    j_verts = []
    j_verts.extend(_add_tapered_ribbon(
        bm, mat_idx,
        [_pt(0.0, -0.048, 0.035), _pt(0.0, -0.072, 0.088), _pt(0.0, -0.096, 0.145), _pt(0.0, -0.104, 0.194)],
        [0.068 * s, 0.060 * s, 0.042 * s, 0.016 * s],
        [0.024 * s, 0.022 * s, 0.018 * s, 0.008 * s],
        up_hint=tuple(side_v), mat_front="Mat_ZFlesh", mat_back="Mat_MChitinDark",
    ))
    bot_specs = []
    for i in range(8):
        frac = (i / 7.0) - 0.5
        bp = _pt(frac * 0.064, -0.082, 0.158 - 0.038 * abs(frac))
        is_c = (i in (1, 6))
        tp = bp + side_v * ((0.034 if is_c else 0.022) * s) - fwd * (0.006 * s)
        bot_specs.append((bp, tp, (0.0054 if is_c else 0.0040) * s, -fwd * (0.003 * s)))
    j_verts.extend(_add_irregular_fang_row(bm, mat_idx, bot_specs, mat_fang="Mat_MScytheBone"))
    regions.setdefault("jaw_bot", []).extend(j_verts)

    # Forked glossy wet blood-tongue hanging down with forked tips
    t_verts = _add_tapered_ribbon(
        bm, mat_idx,
        [_pt(0.0, -0.052, 0.070), _pt(0.005, -0.078, 0.135), _pt(0.010, -0.135, 0.168), _pt(0.0, -0.192, 0.156)],
        [0.032 * s, 0.028 * s, 0.020 * s, 0.010 * s],
        [0.014 * s, 0.012 * s, 0.009 * s, 0.005 * s],
        up_hint=tuple(fwd), mat_front="Mat_MTongueWet", mat_back="Mat_ZBloodDried",
    )
    for fsx in (1.0, -1.0):
        t_verts.extend(add_cone(
            bm, tuple(_pt(0.004 * fsx, -0.188, 0.156)), tuple(_pt(0.020 * fsx, -0.236, 0.144)),
            0.0065 * s, segments=4, mat_idx=mat_idx["Mat_MTongueWet"],
        ))
    t_verts.extend(_add_saliva_strands(bm, mat_idx, [
        (_pt(0.0, -0.135, 0.166), _pt(0.014, -0.180, 0.155), 0.7),
    ], drop_vec=tuple(-side_v * (0.020 * s)), rad=0.0020 * s))
    regions.setdefault("tongue", []).extend(t_verts)
    regions.setdefault("head", []).extend(head_verts)


def _add_cupped_shroud_frond(
    bm, mat_idx, spine_pts, width_list, thick_list, normal_hint=(0.0, -1.0, 0.0),
    cup_depth=0.010, twist_total=0.0, mat_front="Mat_MShroudBone", mat_back="Mat_MShroudDark",
):
    """Loft a sculpted 6-vertex concave/cupped organic bone-petal frond with crisp central keel ridge."""
    vecs = [Vector(p) for p in spine_pts]
    m = len(vecs)
    rings = []
    nh = Vector(normal_hint)
    fwd_base = (vecs[-1] - vecs[0]).normalized() if (vecs[-1] - vecs[0]).length > 1e-5 else Vector((0.0, 0.0, 1.0))

    for k in range(m):
        if k == 0:
            tan = vecs[1] - vecs[0]
        elif k == m - 1:
            tan = vecs[-1] - vecs[-2]
        else:
            tan = vecs[k + 1] - vecs[k - 1]
        if tan.length < 1e-6:
            tan = fwd_base
        tan.normalize()
        nrm = nh - tan * nh.dot(tan)
        if nrm.length < 1e-6:
            fb = Vector((0.0, -1.0, 0.0)) if abs(tan.y) < 0.9 else Vector((1.0, 0.0, 0.0))
            nrm = fb - tan * fb.dot(tan)
        nrm.normalize()
        side = nrm.cross(tan).normalized()

        t = k / max(1, m - 1)
        ang = twist_total * t
        ca, sa = math.cos(ang), math.sin(ang)
        n_rot = nrm * ca + side * sa
        s_rot = -nrm * sa + side * ca

        hw = 0.5 * width_list[k]
        ht = 0.5 * thick_list[k]
        cup = cup_depth * math.sin(math.pi * min(1.0, t * 1.15))
        # 6-point cupped petal section: outer convex keel -> R wing -> inner concave R -> inner center -> inner L -> L wing
        rings.append([
            tuple(vecs[k] + n_rot * (ht * 1.15)),
            tuple(vecs[k] + s_rot * hw - n_rot * cup),
            tuple(vecs[k] + s_rot * (hw * 0.45) - n_rot * (ht * 0.85 + cup * 0.55)),
            tuple(vecs[k] - n_rot * (ht * 0.95 + cup * 0.35)),
            tuple(vecs[k] - s_rot * (hw * 0.45) - n_rot * (ht * 0.85 + cup * 0.55)),
            tuple(vecs[k] - s_rot * hw - n_rot * cup),
        ])

    verts = loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_idx[mat_front])
    for f in {f for v in verts for f in v.link_faces}:
        f.normal_update()
        if f.normal.dot(nh) < -0.18:
            f.material_index = mat_idx[mat_back]
    return verts


def build_head_thorn_shroud(bm, mat_idx, regions, center=(0.0, -0.04, 1.65), fwd_dir=(0.0, -0.96, 0.26), scale=1.0):
    """Build Ref-1 eyeless gothic sculpture head: lower nose/fanged mouth emerging from blooming lotus collar & S-curved face-veiling flame fronds."""
    s = scale
    c0 = Vector(center)
    fwd = Vector(fwd_dir).normalized()
    side_u = Vector((1.0, 0.0, 0.0))
    side_u = (side_u - fwd * side_u.dot(fwd)).normalized()
    side_v = fwd.cross(side_u).normalized()

    def _pt(u, v, f):
        return c0 + side_u * (u * s) + side_v * (v * s) + fwd * (f * s)

    head_verts = []
    # 1. Eyeless Sculpted Lower Facial Mask & Shadowed Upper Cranium Core (ZERO eyes, ZERO sockets, ZERO bald skull!)
    head_specs = (
        (-0.062, -0.028, 0.050, 0.056),
        (-0.004,  0.002, 0.072, 0.076),
        ( 0.058,  0.004, 0.066, 0.070),
        ( 0.098, -0.014, 0.048, 0.048),
    )
    h_rings = []
    for f_off, v_off, rx, ry in head_specs:
        cr = _pt(0.0, v_off, f_off)
        h_rings.append([
            tuple(cr + side_u * (math.cos(2.0 * math.pi * i / 10) * rx * s)
                     + side_v * (math.sin(2.0 * math.pi * i / 10) * ry * s))
            for i in range(10)
        ])
    v_hd = loft_rings(bm, h_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_MShroudDark"])
    for f in {f for v in v_hd for f in v.link_faces}:
        cen = f.calc_center_median()
        rel = cen - c0
        # Expose sculpted pale ash skin cleanly on the eyeless lower nose/cheek/maxilla V-window!
        if rel.dot(fwd) > 0.030 * s and rel.dot(side_v) < 0.030 * s and abs(rel.dot(side_u)) < 0.056 * s:
            f.material_index = mat_idx["Mat_MShroudSkin"]
    head_verts.extend(v_hd)

    # Prominent sculpted lower nose tip & nostrils emerging cleanly beneath the crossing eye-veil fronds
    head_verts.extend(_add_tapered_ribbon(
        bm, mat_idx,
        [_pt(0.0, 0.028, 0.088), _pt(0.0, 0.008, 0.116), _pt(0.0, -0.008, 0.130), _pt(0.0, -0.018, 0.108)],
        [0.016 * s, 0.022 * s, 0.028 * s, 0.032 * s],
        [0.012 * s, 0.016 * s, 0.020 * s, 0.014 * s],
        up_hint=tuple(fwd), mat_front="Mat_MShroudSkin", mat_back="Mat_MShroudSkin",
    ))

    # Deep dark recessed mouth cavern + sculpted parted upper lip & sharp vampire canines (100% unobstructed above collar!)
    head_verts.extend(loft_rings(bm, [
        [tuple(_pt(math.cos(2 * math.pi * i / 8) * 0.030, -0.038 + math.sin(2 * math.pi * i / 8) * 0.020, 0.056)) for i in range(8)],
        [tuple(_pt(math.cos(2 * math.pi * i / 8) * 0.032, -0.038 + math.sin(2 * math.pi * i / 8) * 0.021, 0.098)) for i in range(8)],
    ], close_caps=(True, False), mat_idx=mat_idx["Mat_ZMouth"]))
    head_verts.extend(_add_tapered_ribbon(
        bm, mat_idx,
        [
            _pt(-0.032, -0.030, 0.090),
            _pt(-0.014, -0.020, 0.110),
            _pt( 0.000, -0.022, 0.116),
            _pt( 0.014, -0.020, 0.110),
            _pt( 0.032, -0.030, 0.090),
        ],
        [0.007 * s, 0.011 * s, 0.010 * s, 0.011 * s, 0.007 * s],
        [0.007 * s, 0.009 * s, 0.009 * s, 0.009 * s, 0.007 * s],
        up_hint=tuple(side_v), mat_front="Mat_ZLipDead", mat_back="Mat_ZMouth",
    ))
    u_shroud_specs = []
    for i, ux in enumerate((-0.024, -0.017, -0.010, -0.0035, 0.0035, 0.010, 0.017, 0.024)):
        is_canine = (i in (1, 6))
        flen = (0.026 if is_canine else 0.012) * s
        bp = _pt(ux, -0.023, 0.110 - 0.22 * abs(ux))
        tp = bp - side_v * flen - fwd * (0.002 * s)
        u_shroud_specs.append((bp, tp, (0.0046 if is_canine else 0.0028) * s, -fwd * (0.002 * s)))
    head_verts.extend(_add_irregular_fang_row(bm, mat_idx, u_shroud_specs, mat_fang="Mat_ZBone", mat_tip="Mat_ZBone"))

    # Articulated agonized lower jaw & chin (`jaw_scream`) resting cleanly ABOVE the lotus collar!
    j_verts = loft_rings(bm, [
        [tuple(_pt(math.cos(2.0 * math.pi * i / 8) * 0.038, -0.060 + math.sin(2.0 * math.pi * i / 8) * 0.016, 0.040)) for i in range(8)],
        [tuple(_pt(math.cos(2.0 * math.pi * i / 8) * 0.030, -0.070 + math.sin(2.0 * math.pi * i / 8) * 0.015, 0.094)) for i in range(8)],
        [tuple(_pt(math.cos(2.0 * math.pi * i / 8) * 0.017, -0.074 + math.sin(2.0 * math.pi * i / 8) * 0.011, 0.112)) for i in range(8)],
    ], close_caps=(True, True), mat_idx=mat_idx["Mat_MShroudSkin"])
    j_verts.extend(_add_tapered_ribbon(
        bm, mat_idx,
        [_pt(-0.025, -0.056, 0.090), _pt(0.0, -0.060, 0.108), _pt(0.025, -0.056, 0.090)],
        [0.007 * s, 0.010 * s, 0.007 * s], [0.006 * s, 0.008 * s, 0.006 * s],
        up_hint=tuple(side_v), mat_front="Mat_ZLipDead", mat_back="Mat_ZMouth",
    ))
    l_shroud_specs = []
    for i, ux in enumerate((-0.017, -0.010, -0.0035, 0.0035, 0.010, 0.017)):
        is_c = (i in (0, 5))
        bp = _pt(ux, -0.059, 0.104 - 0.20 * abs(ux))
        tp = bp + side_v * ((0.018 if is_c else 0.010) * s) - fwd * (0.002 * s)
        l_shroud_specs.append((bp, tp, (0.0036 if is_c else 0.0025) * s, -fwd * (0.002 * s)))
    j_verts.extend(_add_irregular_fang_row(bm, mat_idx, l_shroud_specs, mat_fang="Mat_ZBone", mat_tip="Mat_ZBone"))
    regions.setdefault("jaw_scream", []).extend(j_verts)

    # 2. Lush 3-Tier Cupped Lotus/Calyx Collar Cradling UNDER the Chin & Jawline (never blocking the mouth/nose!)
    collar_tiers = (
        # (n_pet, angle_offset, v_base, f_rad, out_reach, up_lift, p_width)
        (10, 0.00, -0.118, 0.056, 0.150, 0.048, 0.056),
        (10, 0.31, -0.102, 0.050, 0.128, 0.058, 0.050),
        ( 6, 0.16, -0.094, 0.048, 0.106, 0.028, 0.046),
    )
    for t_idx, (n_pet, a_off, v_base, f_rad, out_r, lift_v, p_w) in enumerate(collar_tiers):
        for k in range(n_pet):
            if t_idx == 2:
                ang = -0.5 * math.pi + ((k / max(1, n_pet - 1)) - 0.5) * 1.90
            else:
                ang = (2.0 * math.pi * k) / n_pet + a_off
            ca, sa = math.cos(ang), math.sin(ang)
            r_out = (side_u * ca + fwd * (-sa * 0.94)).normalized()
            is_front = max(0.0, r_out.dot(fwd))
            # Keep front-center petals cupped strictly UNDER the chin (`v <= -0.068`) so chin, mouth & nose read 100% clearly!
            chin_cup = (0.32 if is_front > 0.45 else 1.0)
            reach = out_r * (0.94 if is_front > 0.45 else 1.0)
            bp = _pt(0.0, v_base, 0.015) + r_out * (f_rad * s)
            pts = [
                tuple(bp),
                tuple(bp + r_out * (reach * 0.38 * s) + side_v * (lift_v * 0.16 * chin_cup * s)),
                tuple(bp + r_out * (reach * 0.78 * s) + side_v * (lift_v * 0.52 * chin_cup * s)),
                tuple(bp + r_out * (reach * 1.00 * s) + side_v * (lift_v * 0.88 * chin_cup * s)),
                tuple(bp + r_out * (reach * 0.90 * s) + side_v * (lift_v * 1.12 * chin_cup * s)),
            ]
            head_verts.extend(_add_cupped_shroud_frond(
                bm, mat_idx, pts,
                [p_w * 0.52 * s, p_w * 0.96 * s, p_w * 1.08 * s, p_w * 0.70 * s, 0.008 * s],
                [0.016 * s, 0.015 * s, 0.012 * s, 0.009 * s, 0.004 * s],
                normal_hint=tuple((r_out * 0.72 - side_v * 0.58).normalized()),
                cup_depth=0.010 * s, twist_total=0.18 * ca,
                mat_front="Mat_MShroudBone", mat_back="Mat_MShroudDark",
            ))

    # 3. Inner Face-Shrouding S-Curve Veil Fronds: frame outer cheeks (`|u|>=0.048` below nose), then sweep INWARD above `v>=0.032` to consume eyes/forehead!
    veil_specs = (
        # Left cheek -> sweeps over left eye/brow -> curls gracefully right-upward (Ref Image 1 signature S-frond!)
        ( 0.062, -0.072, 0.075,   0.054, -0.005, 0.108,   0.026, 0.068, 0.128,  -0.008, 0.165, 0.106,  -0.048, 0.275, 0.072,  0.056,  0.45),
        ( 0.084, -0.062, 0.048,   0.078,  0.016, 0.092,   0.056, 0.098, 0.106,   0.032, 0.195, 0.086,   0.078, 0.305, 0.052,  0.060, -0.40),
        ( 0.036,  0.034, 0.106,   0.014,  0.078, 0.132,  -0.012, 0.145, 0.120,   0.016, 0.230, 0.092,   0.052, 0.325, 0.058,  0.046,  0.36),
        # Right cheek -> sweeps over right eye/brow -> curls gracefully left-upward
        (-0.060, -0.072, 0.076,  -0.052, -0.004, 0.110,  -0.024, 0.072, 0.130,   0.012, 0.172, 0.108,   0.054, 0.285, 0.074,  0.054, -0.46),
        (-0.084, -0.060, 0.046,  -0.080,  0.018, 0.090,  -0.058, 0.102, 0.104,  -0.034, 0.198, 0.084,  -0.082, 0.298, 0.048,  0.058,  0.38),
        (-0.034,  0.036, 0.108,  -0.010,  0.082, 0.134,   0.018, 0.150, 0.122,  -0.012, 0.238, 0.090,  -0.046, 0.332, 0.056,  0.044, -0.34),
        # Temple-wrapping side cowl petals sealing left & right profile silhouettes
        ( 0.094, -0.048, 0.010,   0.102,  0.032, 0.038,   0.088, 0.122, 0.048,   0.068, 0.215, 0.028,   0.108, 0.305,-0.005,  0.056, -0.32),
        (-0.094, -0.048, 0.010,  -0.102,  0.032, 0.038,  -0.088, 0.122, 0.048,  -0.068, 0.215, 0.028,  -0.108, 0.305,-0.005,  0.056,  0.32),
    )
    for u0, v0, f0, u1, v1, f1, u2, v2, f2, u3, v3, f3, u4, v4, f4, mw, tw in veil_specs:
        v_pts = [_pt(u0, v0, f0), _pt(u1, v1, f1), _pt(u2, v2, f2), _pt(u3, v3, f3), _pt(u4, v4, f4)]
        n_dir = (fwd * 0.85 + side_u * (0.45 if u0 >= 0 else -0.45)).normalized()
        head_verts.extend(_add_cupped_shroud_frond(
            bm, mat_idx, v_pts,
            [mw * 0.56 * s, mw * 0.98 * s, mw * 0.94 * s, mw * 0.56 * s, 0.006 * s],
            [0.015 * s, 0.016 * s, 0.013 * s, 0.009 * s, 0.004 * s],
            normal_hint=tuple(n_dir), cup_depth=0.010 * s, twist_total=tw,
            mat_front="Mat_MShroudBone", mat_back="Mat_MShroudDark",
        ))

    # 4. 14 Flowing Flame-Crown S-Curved Fronds (`crown_L`, `crown_C`, `crown_R` — wide S-waves like Ref Image 1!)
    regions.setdefault("crown_L", [])
    regions.setdefault("crown_C", [])
    regions.setdefault("crown_R", [])
    crown_specs = (
        # (u_base, v_base, f_base,  s_amp_u, s_amp_f, h_total, max_w, phase, bucket)
        ( 0.000, 0.058,  0.062,  -0.065,  0.036, 0.48, 0.058, 0.4, "crown_C"),
        ( 0.026, 0.055,  0.044,   0.072,  0.026, 0.53, 0.050, 1.8, "crown_C"),
        (-0.028, 0.052,  0.046,  -0.078,  0.030, 0.45, 0.064, 0.9, "crown_C"),
        ( 0.010, 0.044, -0.018,   0.056, -0.034, 0.50, 0.058, 2.4, "crown_C"),
        (-0.014, 0.040, -0.052,  -0.052, -0.048, 0.41, 0.056, 3.1, "crown_C"),
        # Left sweeping S-flame fronds (lush outward-and-upward S-curls!)
        ( 0.060, 0.030,  0.046,   0.115,  0.022, 0.46, 0.066, 0.2, "crown_L"),
        ( 0.082, 0.020,  0.006,   0.145, -0.018, 0.43, 0.060, 1.3, "crown_L"),
        ( 0.070, 0.024, -0.042,   0.120, -0.048, 0.38, 0.054, 2.2, "crown_L"),
        ( 0.044, 0.048,  0.020,   0.088,  0.012, 0.50, 0.042, 2.9, "crown_L"),
        # Right sweeping S-flame fronds
        (-0.060, 0.030,  0.046,  -0.120,  0.024, 0.44, 0.068, 0.7, "crown_R"),
        (-0.084, 0.020,  0.006,  -0.150, -0.020, 0.41, 0.060, 1.7, "crown_R"),
        (-0.070, 0.024, -0.042,  -0.125, -0.050, 0.37, 0.054, 2.6, "crown_R"),
        (-0.046, 0.048,  0.020,  -0.092,  0.014, 0.51, 0.040, 3.5, "crown_R"),
        ( 0.000, 0.026, -0.068,   0.045, -0.062, 0.35, 0.058, 1.1, "crown_C"),
    )
    for ub, vb, fb, au, af, ht, mw, ph, bkt in crown_specs:
        c_pts = []
        for st in range(6):
            t = st / 5.0
            # Authentic Ref-1 S-flame wave: sweeps across belly, flares outward, and curls skyward at tip!
            s_wave = 0.55 * au * math.sin(1.25 * math.pi * t) + 0.65 * au * (t ** 1.5) + 0.032 * math.sin(t * 5.0 + ph)
            f_wave = 0.030 * math.sin(math.pi * t) + af * (t ** 1.4)
            c_pts.append(_pt(ub + s_wave, vb + ht * t, fb + f_wave))
        n_hint = (fwd * (0.75 if fb >= -0.02 else -0.65) + side_u * (0.55 if ub > 0.02 else (-0.55 if ub < -0.02 else 0.0))).normalized()
        rib = _add_cupped_shroud_frond(
            bm, mat_idx, c_pts,
            [mw * 0.56 * s, mw * 0.98 * s, mw * 1.06 * s, mw * 0.74 * s, mw * 0.36 * s, 0.006 * s],
            [0.016 * s, 0.016 * s, 0.013 * s, 0.010 * s, 0.006 * s, 0.003 * s],
            normal_hint=tuple(n_hint), cup_depth=0.012 * s,
            twist_total=0.58 * (1.0 if ph % 1.0 > 0.5 else -1.0),
            mat_front="Mat_MShroudBone", mat_back="Mat_MShroudDark",
        )
        regions[bkt].extend(rib)

    regions.setdefault("head", []).extend(head_verts)


def build_head_arachnid_maw(bm, mat_idx, regions, center=(0.0, -0.34, 0.48), fwd_dir=(0.0, -0.98, -0.18), scale=1.0):
    """Build colossal horizontal 6-eyed chitin split-maw with glowing spider eyes, 24 fangs & serrated acid palps."""
    s = scale
    c0 = Vector(center)
    fwd = Vector(fwd_dir).normalized()
    side_u = Vector((1.0, 0.0, 0.0))
    side_u = (side_u - fwd * side_u.dot(fwd)).normalized()
    side_v = fwd.cross(side_u).normalized()

    def _pt(u, v, f):
        return c0 + side_u * (u * s) + side_v * (v * s) + fwd * (f * s)

    head_verts = []
    # Deep wide abyssal mouth gullet sealing rear jaw seam even at wide gape (zero see-through corners!)
    g_rings = []
    for f_off, rx, ry in ((-0.10, 0.15, 0.10), (-0.01, 0.18, 0.13), (0.08, 0.16, 0.11)):
        cr = _pt(0.0, 0.0, f_off)
        g_rings.append([
            tuple(cr + side_u * (math.cos(2.0 * math.pi * i / 10) * rx * s)
                     + side_v * (math.sin(2.0 * math.pi * i / 10) * ry * s))
            for i in range(10)
        ])
    head_verts.extend(loft_rings(bm, g_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_ZMouth"]))

    # 8 Pharyngeal backward-hooked gullet teeth inside deep mouth cavern
    for i in range(8):
        ang = (2.0 * math.pi * i) / 8.0 + 0.20
        bp = _pt(math.cos(ang) * 0.145, math.sin(ang) * 0.095, 0.035)
        tp = bp - side_u * (math.cos(ang) * 0.036 * s) - side_v * (math.sin(ang) * 0.032 * s) - fwd * (0.022 * s)
        head_verts.extend(add_cone(bm, tuple(bp), tuple(tp), 0.0068 * s, segments=4, mat_idx=mat_idx["Mat_MScytheBone"]))

    # 1. Armored Upper Carapace Hood (`maw_top`) + Eye Hood Ridges + 6 Spider-Eyes + Huge Venom Saber-Canines
    top_verts = loft_rings(bm, [
        [tuple(_pt(math.cos(2.0 * math.pi * i / 8) * 0.175, 0.055 + math.sin(2.0 * math.pi * i / 8) * 0.052, -0.08)) for i in range(8)],
        [tuple(_pt(math.cos(2.0 * math.pi * i / 8) * 0.195, 0.068 + math.sin(2.0 * math.pi * i / 8) * 0.058,  0.04)) for i in range(8)],
        [tuple(_pt(math.cos(2.0 * math.pi * i / 8) * 0.165, 0.056 + math.sin(2.0 * math.pi * i / 8) * 0.042,  0.16)) for i in range(8)],
        [tuple(_pt(math.cos(2.0 * math.pi * i / 8) * 0.092, 0.026 + math.sin(2.0 * math.pi * i / 8) * 0.022,  0.24)) for i in range(8)],
    ], close_caps=(True, True), mat_idx=mat_idx["Mat_MArachChitin"])

    # Blind Armored Chitin Carapace Crests & Sensory Horn-Spurs (ZERO spider eyes!)
    top_verts.extend(_add_tapered_ribbon(
        bm, mat_idx,
        [_pt(0.0, 0.118, -0.04), _pt(0.0, 0.105, 0.09), _pt(0.0, 0.056, 0.228)],
        [0.046 * s, 0.054 * s, 0.020 * s],
        [0.024 * s, 0.026 * s, 0.012 * s],
        up_hint=tuple(side_v), mat_front="Mat_MChitinMid", mat_back="Mat_MArachChitin",
    ))
    for sx_r in (1.0, -1.0):
        top_verts.extend(_add_tapered_ribbon(
            bm, mat_idx,
            [_pt(0.115 * sx_r, 0.086, 0.02), _pt(0.096 * sx_r, 0.072, 0.14), _pt(0.054 * sx_r, 0.042, 0.224)],
            [0.036 * s, 0.042 * s, 0.016 * s],
            [0.020 * s, 0.022 * s, 0.010 * s],
            up_hint=tuple(side_v), mat_front="Mat_MChitinMid", mat_back="Mat_MArachChitin",
        ))
        top_verts.extend(add_cone(
            bm, tuple(_pt(0.125 * sx_r, 0.068, 0.145)),
            tuple(_pt(0.168 * sx_r, 0.098, 0.085)),
            0.014 * s, segments=4, mat_idx=mat_idx["Mat_MScytheBone"],
        ))

    # Wet crimson upper gum ridge + 10 uneven jagged fangs + 2 HUGE curved venom-tipped saber-canines
    top_verts.extend(add_box(
        bm, center=tuple(_pt(0.0, 0.022, 0.155)), size=(0.22 * s, 0.068 * s, 0.022 * s),
        bevel=0.006 * s, mat_idx=mat_idx["Mat_ZBloodFresh"],
    ))
    top_arch_specs = []
    for i in range(10):
        frac = (i / 9.0) - 0.5
        bp = _pt(frac * 0.22, 0.024 - 0.018 * abs(frac), 0.200 - 0.105 * (frac * frac))
        is_big = (i % 3 == 0)
        flen = ((0.052 if is_big else 0.030) - 0.010 * abs(frac)) * s
        tp = bp - side_v * flen - fwd * (0.014 * s) + side_u * (0.006 * s * math.sin(i * 2.0))
        top_arch_specs.append((bp, tp, (0.0085 if is_big else 0.0058) * s, fwd * (0.008 * s)))
    top_verts.extend(_add_irregular_fang_row(bm, mat_idx, top_arch_specs, mat_fang="Mat_MScytheBone", mat_tip="Mat_ZAcidGlow"))

    for sx in (1.0, -1.0):
        sb = _pt(0.095 * sx, 0.022, 0.188)
        sm = _pt(0.105 * sx, -0.028, 0.220)
        st = _pt(0.072 * sx, -0.074, 0.195)
        top_verts.extend(add_cylinder(bm, tuple(sb), tuple(sm), 0.016 * s, 0.010 * s, segments=5, mat_idx=mat_idx["Mat_MScytheBone"]))
        top_verts.extend(add_cone(bm, tuple(sm), tuple(st), 0.010 * s, segments=5, mat_idx=mat_idx["Mat_ZAcidGlow"]))
    top_verts.extend(_add_saliva_strands(bm, mat_idx, [
        (_pt(-0.075, 0.018, 0.182), _pt(-0.025, 0.012, 0.196), 0.8),
        (_pt( 0.025, 0.012, 0.196), _pt( 0.075, 0.018, 0.182), 0.9),
    ], drop_vec=tuple(-side_v * (0.032 * s)), rad=0.0028 * s))
    regions.setdefault("maw_top", []).extend(top_verts)

    # 2. Heavy Split Lower Chitin Jaw (`maw_bot`) + Acid-Barbed Tongue + 2 Lower Sabers + 10 Jagged Fangs
    bot_verts = loft_rings(bm, [
        [tuple(_pt(math.cos(2.0 * math.pi * i / 8) * 0.165, -0.052 + math.sin(2.0 * math.pi * i / 8) * 0.044, -0.06)) for i in range(8)],
        [tuple(_pt(math.cos(2.0 * math.pi * i / 8) * 0.178, -0.066 + math.sin(2.0 * math.pi * i / 8) * 0.048,  0.06)) for i in range(8)],
        [tuple(_pt(math.cos(2.0 * math.pi * i / 8) * 0.145, -0.072 + math.sin(2.0 * math.pi * i / 8) * 0.036,  0.17)) for i in range(8)],
        [tuple(_pt(math.cos(2.0 * math.pi * i / 8) * 0.076, -0.068 + math.sin(2.0 * math.pi * i / 8) * 0.018,  0.23)) for i in range(8)],
    ], close_caps=(True, True), mat_idx=mat_idx["Mat_MArachChitin"])
    for f in {f for v in bot_verts for f in v.link_faces}:
        if (f.calc_center_median() - c0).dot(side_v) > -0.055 * s:
            f.material_index = mat_idx["Mat_MArachUnder"]
    bot_verts.extend(add_box(
        bm, center=tuple(_pt(0.0, -0.044, 0.148)), size=(0.19 * s, 0.064 * s, 0.020 * s),
        bevel=0.006 * s, mat_idx=mat_idx["Mat_ZBloodFresh"],
    ))
    bot_arch_specs = []
    for i in range(10):
        frac = (i / 9.0) - 0.5
        bp = _pt(frac * 0.19, -0.054 + 0.014 * abs(frac), 0.192 - 0.095 * (frac * frac))
        is_big = (i % 3 == 1)
        tp = bp + side_v * ((0.046 if is_big else 0.028) * s) - fwd * (0.010 * s)
        bot_arch_specs.append((bp, tp, (0.0080 if is_big else 0.0054) * s, fwd * (0.006 * s)))
    bot_verts.extend(_add_irregular_fang_row(bm, mat_idx, bot_arch_specs, mat_fang="Mat_MScytheBone"))
    for sx in (1.0, -1.0):
        sb = _pt(0.078 * sx, -0.058, 0.184)
        sm = _pt(0.088 * sx, -0.016, 0.214)
        st = _pt(0.058 * sx,  0.024, 0.192)
        bot_verts.extend(add_cylinder(bm, tuple(sb), tuple(sm), 0.014 * s, 0.009 * s, segments=5, mat_idx=mat_idx["Mat_MScytheBone"]))
        bot_verts.extend(add_cone(bm, tuple(sm), tuple(st), 0.009 * s, segments=5, mat_idx=mat_idx["Mat_ZAcidGlow"]))

    # Writhing acid-barbed spider tongue rising out of lower jaw trough
    bot_verts.extend(_add_tapered_ribbon(
        bm, mat_idx,
        [_pt(0.0, -0.036, 0.04), _pt(0.012, -0.024, 0.11), _pt(-0.010, -0.038, 0.18), _pt(0.0, -0.062, 0.245)],
        [0.042 * s, 0.038 * s, 0.028 * s, 0.010 * s],
        [0.018 * s, 0.016 * s, 0.012 * s, 0.005 * s],
        up_hint=tuple(side_v), mat_front="Mat_MTongueWet", mat_back="Mat_ZBloodDried",
    ))
    bot_verts.extend(add_cone(bm, tuple(_pt(0.0, -0.048, 0.215)), tuple(_pt(0.0, -0.070, 0.268)), 0.008 * s, segments=4, mat_idx=mat_idx["Mat_ZAcidGlow"]))
    regions.setdefault("maw_bot", []).extend(bot_verts)

    # 3. Twin Articulated Serrated Acid-Palps (`palp_L`, `palp_R`)
    for sx, pname in ((1.0, "palp_L"), (-1.0, "palp_R")):
        p_verts = _add_tapered_ribbon(
            bm, mat_idx,
            [_pt(0.165 * sx, -0.012, -0.02), _pt(0.245 * sx, -0.022, 0.08), _pt(0.255 * sx, -0.032, 0.19), _pt(0.185 * sx, -0.040, 0.27)],
            [0.052 * s, 0.044 * s, 0.032 * s, 0.008 * s],
            [0.040 * s, 0.034 * s, 0.024 * s, 0.006 * s],
            up_hint=tuple(side_u * sx), mat_front="Mat_MArachChitin", mat_back="Mat_MArachUnder",
        )
        for k in range(3):
            sb = _pt((0.235 - 0.015 * k) * sx, -0.026, 0.11 + 0.055 * k)
            st = sb - side_u * (0.038 * sx * s)
            p_verts.extend(add_cone(bm, tuple(sb), tuple(st), 0.0068 * s, segments=4, mat_idx=mat_idx["Mat_MScytheBone"]))
        regions.setdefault(pname, []).extend(p_verts)

    regions.setdefault("head", []).extend(head_verts)


def build_head_bile_juggernaut(bm, mat_idx, regions, center=(0.0, -0.35, 1.84), fwd_dir=(0.0, -0.96, -0.26), scale=1.34):
    """Build large gnarled eyeless heavy tank head fused into hunched neck with brow ridges, cheek muscles & split jaw."""
    s = scale
    c0 = Vector(center)
    fwd = Vector(fwd_dir).normalized()
    side_u = Vector((1.0, 0.0, 0.0))
    side_u = (side_u - fwd * side_u.dot(fwd)).normalized()
    side_v = fwd.cross(side_u).normalized()

    def _pt(u, v, f):
        return c0 + side_u * (u * s) + side_v * (v * s) + fwd * (f * s)

    def _organic_head_ring(f_off, v_off, rx, ry, n=12, seed=0, crest=0.0):
        cr = _pt(0.0, v_off, f_off)
        pts = []
        for i in range(n):
            ang = 2.0 * math.pi * i / n
            ca, sa = math.cos(ang), math.sin(ang)
            wob = 1.0 + 0.08 * math.sin(3.0 * ang + seed) + 0.05 * math.cos(5.0 * ang - seed * 0.7)
            top_crest = crest * max(0.0, sa) ** 2
            pts.append(tuple(
                cr + side_u * (ca * rx * wob * s) + side_v * ((sa * ry * wob + top_crest) * s)
            ))
        return pts

    head_verts = []
    # 1. Gnarled thick neck/throat muscle collar blending head solidly back into chest traps
    neck_rings = [
        _organic_head_ring(-0.22, -0.020, 0.168, 0.128, n=12, seed=1.1, crest=0.025),
        _organic_head_ring(-0.14,  0.025, 0.158, 0.118, n=12, seed=1.8, crest=0.020),
        _organic_head_ring(-0.06,  0.048, 0.148, 0.105, n=12, seed=2.4, crest=0.014),
    ]
    v_neck = loft_rings(bm, neck_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_MTankSkin"])
    for f in {f for v in v_neck for f in v.link_faces}:
        if (f.calc_center_median() - c0).dot(side_v) < 0.01 * s:
            f.material_index = mat_idx["Mat_MTankBruise"]
    head_verts.extend(v_neck)

    # 2. Rugged bloated cranium & upper maxilla strictly ABOVE v=0.005 so open mouth cavity never gets occluded
    cr_rings = [
        _organic_head_ring(-0.14, 0.062, 0.132, 0.095, n=12, seed=3.0, crest=0.018),
        _organic_head_ring(-0.04, 0.078, 0.152, 0.098, n=12, seed=3.7, crest=0.022),
        _organic_head_ring( 0.05, 0.072, 0.145, 0.086, n=12, seed=4.4, crest=0.016),
        _organic_head_ring( 0.12, 0.060, 0.126, 0.066, n=12, seed=5.1, crest=0.012),
        _organic_head_ring( 0.16, 0.048, 0.096, 0.042, n=12, seed=5.8, crest=0.006),
        _organic_head_ring( 0.19, 0.036, 0.052, 0.022, n=12, seed=6.3, crest=0.000),
    ]
    v_cr = loft_rings(bm, cr_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_MTankSkin"])
    for f in {f for v in v_cr for f in v.link_faces}:
        cen = f.calc_center_median()
        if (cen - c0).dot(side_v) < 0.028 * s:
            f.material_index = mat_idx["Mat_MTankBruise"]
    head_verts.extend(v_cr)

    # 3. Overlapping Sculpted Fungal-Bone Brow Ridges & Sagittal Crown Crust (pure lofted organic shells)
    def _brow_shell(su, sv, sf, ru, rv, rf, tilt_u=0.0, tilt_v=0.0, seed=0):
        base = _pt(su, sv, sf)
        ax_u = (side_u + side_v * tilt_u).normalized()
        ax_v = (side_v + fwd * tilt_v).normalized()
        ax_f = ax_u.cross(ax_v).normalized()
        rings = []
        for t, r_sc, f_sc in ((0.0, 0.72, -0.35), (0.35, 1.04, 0.10), (0.70, 0.88, 0.65), (1.0, 0.36, 1.00)):
            c_r = base + ax_f * (f_sc * rf * s)
            rings.append([
                tuple(c_r + ax_u * (math.cos(2 * math.pi * i / 8) * ru * r_sc * (1.0 + 0.16 * math.sin(3 * i + seed)) * s)
                          + ax_v * (math.sin(2 * math.pi * i / 8) * rv * r_sc * (1.0 + 0.14 * math.cos(2 * i - seed)) * s))
                for i in range(8)
            ])
        return loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_idx["Mat_MTankArmor"])

    for su, sv, sf, ru, rv, rf, tu, tv, sd in (
        ( 0.000, 0.084, 0.126, 0.102, 0.042, 0.042,  0.00,  0.22, 0.6),
        (-0.074, 0.086, 0.105, 0.076, 0.044, 0.038,  0.22,  0.18, 1.2),
        ( 0.076, 0.090, 0.102, 0.078, 0.046, 0.040, -0.20,  0.20, 2.4),
        ( 0.000, 0.132, 0.035, 0.114, 0.058, 0.054,  0.04, -0.22, 3.6),
        ( 0.000, 0.118,-0.075, 0.128, 0.068, 0.058, -0.05, -0.35, 4.8),
        (-0.115, 0.050, 0.058, 0.060, 0.048, 0.044,  0.30,  0.05, 5.5),
        ( 0.118, 0.054, 0.054, 0.062, 0.050, 0.046, -0.30,  0.05, 6.2),
    ):
        head_verts.extend(_brow_shell(su, sv, sf, ru, rv, rf, tilt_u=tu, tilt_v=tv, seed=sd))

    # Asymmetric glowing amber bile pustule boils on crown/snout/temples (ZERO eye-pits / ZERO eyes!)
    for sx_b, u_b, v_b, f_b in ((1.0, 0.092, 0.096, 0.095), (-1.0, -0.090, 0.092, 0.098)):
        head_verts.extend(add_cone(
            bm, tuple(_pt(u_b, v_b, f_b)),
            tuple(_pt(u_b + 0.032 * sx_b, v_b + 0.038, f_b + 0.022)),
            0.018 * s, segments=5, mat_idx=mat_idx["Mat_MScytheBone"],
        ))
    for bu, bv, bf, br in (
        (-0.082, 0.062, 0.108, 0.028),
        ( 0.116, 0.078, 0.064, 0.034),
        (-0.108, 0.068, 0.055, 0.030),
        ( 0.046, 0.156,-0.008, 0.038),
        (-0.054, 0.138,-0.042, 0.032),
    ):
        head_verts.extend(loft_rings(bm, [
            [tuple(_pt(bu, bv, bf) + side_u * (math.cos(2 * math.pi * i / 8) * br * 0.9 * s)
                   + side_v * (math.sin(2 * math.pi * i / 8) * br * 0.9 * s) - fwd * (0.008 * s)) for i in range(8)],
            [tuple(_pt(bu, bv, bf) + side_u * (math.cos(2 * math.pi * i / 8) * br * 0.65 * s)
                   + side_v * (math.sin(2 * math.pi * i / 8) * br * 0.65 * s) + fwd * (br * 0.65 * s)) for i in range(8)],
        ], close_caps=(True, True), mat_idx=mat_idx["Mat_MBileGlow"]))

    # 4. Deep Tapered Oral Tunnel + Jagged Arched Upper Gum Ribbon + Cheek/Masseter Muscle Anchors
    head_verts.extend(loft_rings(bm, [
        _organic_head_ring(-0.03, -0.028, 0.062, 0.046, n=10, seed=8.1),
        _organic_head_ring( 0.04, -0.026, 0.076, 0.052, n=10, seed=8.4),
        _organic_head_ring( 0.11, -0.022, 0.068, 0.042, n=10, seed=8.7),
    ], close_caps=(True, True), mat_idx=mat_idx["Mat_ZMouth"]))
    # Curved arched upper lip / gum bridge (eliminates flat horizontal red bar)
    head_verts.extend(_add_tapered_ribbon(
        bm, mat_idx,
        [
            _pt(-0.092, -0.022, 0.098),
            _pt(-0.052,  0.006, 0.136),
            _pt( 0.000,  0.016, 0.152),
            _pt( 0.052,  0.006, 0.136),
            _pt( 0.092, -0.022, 0.098),
        ],
        [0.024 * s, 0.030 * s, 0.034 * s, 0.030 * s, 0.024 * s],
        [0.018 * s, 0.024 * s, 0.026 * s, 0.024 * s, 0.018 * s],
        up_hint=tuple(side_v), mat_front="Mat_ZBloodFresh", mat_back="Mat_MTankBruise",
    ))
    # Thick fleshy cheek / masseter muscle ribbons connecting skull down to split jaw hinges
    for sx in (1.0, -1.0):
        head_verts.extend(_add_tapered_ribbon(
            bm, mat_idx,
            [
                _pt(0.115 * sx,  0.045, -0.02),
                _pt(0.105 * sx, -0.018,  0.02),
                _pt(0.088 * sx, -0.062,  0.04),
            ],
            [0.048 * s, 0.046 * s, 0.038 * s],
            [0.026 * s, 0.028 * s, 0.024 * s],
            up_hint=tuple(side_u * sx), mat_front="Mat_MTankBruise", mat_back="Mat_ZFlesh",
        ))

    up_specs = []
    for i in range(12):
        frac = (i / 11.0) - 0.5
        bp = _pt(frac * 0.150, -0.002 + 0.014 * (1.0 - 2.2 * abs(frac)), 0.152 - 0.062 * abs(frac))
        is_c = (i in (1, 4, 7, 10))
        flen = (0.048 if is_c else 0.028) * s
        tp = bp - side_v * flen - fwd * (0.009 * s) + side_u * (0.006 * s * math.sin(i * 2.1))
        up_specs.append((bp, tp, (0.0086 if is_c else 0.0058) * s, -fwd * (0.006 * s)))
    head_verts.extend(_add_irregular_fang_row(bm, mat_idx, up_specs, mat_fang="Mat_MScytheBone", mat_tip="Mat_ZBloodDried"))
    head_verts.extend(_add_saliva_strands(bm, mat_idx, [
        (_pt(-0.056, -0.008, 0.132), _pt(-0.016,  0.004, 0.148), 0.9),
        (_pt( 0.016,  0.004, 0.148), _pt( 0.056, -0.008, 0.132), 0.85),
    ], drop_vec=tuple(-side_v * (0.040 * s)), rad=0.0028 * s))

    # 5. Beefy Articulated Split Lower Mandibles (`jaw_L` and `jaw_R`) w/ outer bone jaw-ridge & 7 crooked fangs
    for sx, jname in ((1.0, "jaw_L"), (-1.0, "jaw_R")):
        j_verts = _add_tapered_ribbon(
            bm, mat_idx,
            [
                _pt(0.088 * sx, -0.042, -0.025),
                _pt(0.092 * sx, -0.072,  0.055),
                _pt(0.072 * sx, -0.086,  0.145),
                _pt(0.030 * sx, -0.084,  0.205),
            ],
            [0.084 * s, 0.074 * s, 0.058 * s, 0.028 * s],
            [0.044 * s, 0.038 * s, 0.030 * s, 0.016 * s],
            up_hint=tuple(side_v), mat_front="Mat_ZBloodFresh", mat_back="Mat_MTankSkin",
        )
        # Outer calcified jawbone ridge armor plate so jaw reads solid from front/3/4 angles
        j_verts.extend(_add_tapered_ribbon(
            bm, mat_idx,
            [
                _pt(0.102 * sx, -0.058, -0.005),
                _pt(0.096 * sx, -0.084,  0.095),
                _pt(0.052 * sx, -0.094,  0.192),
            ],
            [0.040 * s, 0.036 * s, 0.018 * s],
            [0.024 * s, 0.020 * s, 0.012 * s],
            up_hint=tuple(side_u * sx), mat_front="Mat_MTankArmor", mat_back="Mat_MTankBruise",
        ))
        jf_specs = []
        for k in range(7):
            frac = k / 6.0
            bp = _pt((0.034 + 0.048 * (1.0 - abs(frac - 0.45))) * sx, -0.072, 0.065 + 0.125 * frac)
            is_big = (k in (2, 5))
            tp = bp + side_v * ((0.040 if is_big else 0.025) * s) - side_u * (0.012 * sx * s)
            jf_specs.append((bp, tp, (0.0076 if is_big else 0.0052) * s, -fwd * (0.005 * s)))
        j_verts.extend(_add_irregular_fang_row(bm, mat_idx, jf_specs, mat_fang="Mat_MScytheBone", mat_tip="Mat_ZBloodDried"))
        regions.setdefault(jname, []).extend(j_verts)

    # 6. Thick Swollen Bile-Blistered Wet Tongue (`tongue`)
    t_verts = _add_tapered_ribbon(
        bm, mat_idx,
        [_pt(0.0, -0.048, 0.04), _pt(0.006, -0.068, 0.11), _pt(-0.008, -0.112, 0.158), _pt(0.0, -0.172, 0.152)],
        [0.054 * s, 0.046 * s, 0.032 * s, 0.012 * s],
        [0.026 * s, 0.022 * s, 0.016 * s, 0.008 * s],
        up_hint=tuple(fwd), mat_front="Mat_MTongueWet", mat_back="Mat_ZBloodDried",
    )
    for tu, tv, tf, tr in ((-0.010, -0.115, 0.145, 0.014), (0.012, -0.148, 0.154, 0.016), (0.0, -0.088, 0.115, 0.012)):
        cp = _pt(tu, tv, tf)
        t_verts.extend(loft_rings(bm, [
            [tuple(cp + side_u * (math.cos(2 * math.pi * i / 6) * tr * s) + fwd * (math.sin(2 * math.pi * i / 6) * tr * s)) for i in range(6)],
            [tuple(cp - side_v * (tr * 0.9 * s) + side_u * (math.cos(2 * math.pi * i / 6) * tr * 0.5 * s) + fwd * (math.sin(2 * math.pi * i / 6) * tr * 0.5 * s)) for i in range(6)],
        ], close_caps=(True, True), mat_idx=mat_idx["Mat_MBileGlow"]))
    regions.setdefault("tongue", []).extend(t_verts)
    regions.setdefault("head", []).extend(head_verts)
