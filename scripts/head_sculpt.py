"""Hand-authored Loomis/Asaro faceted low-poly head, ears, hair, beard & headgear variants."""
import math
import bmesh
from mesh_utils import add_box, add_cylinder, loft_rings, ring_ellipse


def _build_ear(bm, mat_idx, sx, s=1.0, skin_mat="Mat_Skin", x_mul=1.0):
    """Build a sculpted C-shaped low-poly ear on side sx (+1.0 = L, -1.0 = R)."""
    def E(x, y, z):
        return (sx * x * s * x_mul, y * s, z * s)

    pts_base = [
        E(0.066, 0.012, 1.612),
        E(0.078, 0.018, 1.610),
        E(0.083, 0.032, 1.628),
        E(0.081, 0.030, 1.658),
        E(0.071, 0.014, 1.664),
        E(0.069, 0.008, 1.638),
    ]
    pts_inner = [
        E(0.070, 0.015, 1.618),
        E(0.076, 0.019, 1.617),
        E(0.078, 0.028, 1.630),
        E(0.076, 0.026, 1.652),
        E(0.071, 0.016, 1.656),
        E(0.071, 0.012, 1.636),
    ]
    v_back = [bm.verts.new((p[0] - sx * 0.004 * s, p[1], p[2])) for p in pts_base]
    v_rim = [bm.verts.new(p) for p in pts_base]
    v_cup = [bm.verts.new(p) for p in pts_inner]

    ear_faces = []
    n = len(pts_base)
    for i in range(n):
        j = (i + 1) % n
        ear_faces.append(bm.faces.new((v_back[i], v_back[j], v_rim[j], v_rim[i])))
        ear_faces.append(bm.faces.new((v_rim[i], v_rim[j], v_cup[j], v_cup[i])))
    ear_faces.append(bm.faces.new(v_cup))
    ear_faces.append(bm.faces.new(list(reversed(v_back))))

    for f in ear_faces:
        f.material_index = mat_idx[skin_mat]
    bmesh.ops.recalc_face_normals(bm, faces=ear_faces)
    return v_back + v_rim + v_cup


def _add_fem_face_locks(bm, mat_idx, s, x_mul, hair_mat, style="bangs_side"):
    """Build front-visible low-poly feminine hair locks curving smoothly from hairline around cheeks/shoulders."""
    verts = []
    if style == "bangs_side":
        # Swept asymmetric fringe bangs flush below cap/bandana/hairline
        verts.extend(add_box(
            bm,
            center=(-0.014 * s * x_mul, -0.084 * s, 1.704 * s),
            size=(0.066 * s * x_mul, 0.022 * s, 0.024 * s),
            rot=(-0.18, 0.12, 0.16),
            taper_top=(0.86, 0.80),
            mat_idx=mat_idx[hair_mat],
        ))
        verts.extend(add_box(
            bm,
            center=(0.032 * s * x_mul, -0.078 * s, 1.702 * s),
            size=(0.042 * s * x_mul, 0.020 * s, 0.022 * s),
            rot=(-0.14, -0.10, -0.20),
            taper_top=(0.82, 0.80),
            mat_idx=mat_idx[hair_mat],
        ))
        # Softly curved temple-to-jaw framing strands (tucked inward at tip so they never look like stiff sticks)
        for sx in (1.0, -1.0):
            lock_rings = [
                ring_ellipse(sx * 0.058 * s * x_mul, -0.016 * s, 1.724 * s, 0.015 * s, 0.024 * s, n=6),
                ring_ellipse(sx * 0.066 * s * x_mul, -0.034 * s, 1.658 * s, 0.015 * s, 0.024 * s, n=6),
                ring_ellipse(sx * 0.058 * s * x_mul, -0.026 * s, 1.592 * s, 0.012 * s, 0.018 * s, n=6),
                ring_ellipse(sx * 0.046 * s * x_mul, -0.012 * s, 1.545 * s, 0.005 * s, 0.008 * s, n=6),
            ]
            verts.extend(loft_rings(bm, lock_rings, close_caps=(True, True), mat_idx=mat_idx[hair_mat]))

    elif style == "hood_locks":
        # Long cheek-framing strands emerging smoothly inside the hood down onto scarf
        for sx in (1.0, -1.0):
            lock_rings = [
                ring_ellipse(sx * 0.056 * s * x_mul, -0.034 * s, 1.724 * s, 0.015 * s, 0.022 * s, n=6),
                ring_ellipse(sx * 0.062 * s * x_mul, -0.048 * s, 1.648 * s, 0.016 * s, 0.022 * s, n=6),
                ring_ellipse(sx * 0.056 * s * x_mul, -0.046 * s, 1.572 * s, 0.013 * s, 0.016 * s, n=6),
                ring_ellipse(sx * 0.048 * s * x_mul, -0.036 * s, 1.505 * s, 0.006 * s, 0.009 * s, n=6),
            ]
            verts.extend(loft_rings(bm, lock_rings, close_caps=(True, True), mat_idx=mat_idx[hair_mat]))

    elif style == "long_shoulder":
        # Flowing tapered cowgirl hair cascading cleanly beneath hat brim onto chest/shoulders
        for sx in (1.0, -1.0):
            side_rings = [
                ring_ellipse(sx * 0.068 * s * x_mul, -0.016 * s, 1.708 * s, 0.018 * s, 0.028 * s, n=6),
                ring_ellipse(sx * 0.076 * s * x_mul, -0.032 * s, 1.630 * s, 0.020 * s, 0.030 * s, n=6),
                ring_ellipse(sx * 0.076 * s * x_mul, -0.040 * s, 1.555 * s, 0.017 * s, 0.024 * s, n=6),
                ring_ellipse(sx * 0.064 * s * x_mul, -0.034 * s, 1.488 * s, 0.008 * s, 0.012 * s, n=6),
            ]
            verts.extend(loft_rings(bm, side_rings, close_caps=(True, True), mat_idx=mat_idx[hair_mat]))
        # Full layered back hair veil
        back_rings = [
            ring_ellipse(0.0, 0.064 * s, 1.695 * s, 0.070 * s * x_mul, 0.034 * s, n=8),
            ring_ellipse(0.0, 0.082 * s, 1.615 * s, 0.078 * s * x_mul, 0.032 * s, n=8),
            ring_ellipse(0.0, 0.086 * s, 1.525 * s, 0.068 * s * x_mul, 0.024 * s, n=8),
            ring_ellipse(0.0, 0.084 * s, 1.480 * s, 0.044 * s * x_mul, 0.012 * s, n=8),
        ]
        verts.extend(loft_rings(bm, back_rings, close_caps=(True, True), mat_idx=mat_idx[hair_mat]))

    return verts


def _add_ponytail(bm, mat_idx, s, hair_mat, tie_mat="Mat_BeltLeather", low=False):
    """Add sculpted tapering ponytail behind the skull; `low=True` clears cowboy hat brims."""
    verts = []
    if low:
        verts.extend(add_cylinder(
            bm,
            (0.0, 0.088 * s, 1.635 * s),
            (0.0, 0.114 * s, 1.628 * s),
            0.017 * s, 0.017 * s, segments=6, mat_idx=mat_idx[tie_mat],
        ))
        tail_rings = [
            ring_ellipse(0.0, 0.115 * s, 1.625 * s, 0.023 * s, 0.021 * s, n=6),
            ring_ellipse(0.0, 0.132 * s, 1.575 * s, 0.028 * s, 0.024 * s, n=6),
            ring_ellipse(0.0, 0.118 * s, 1.515 * s, 0.020 * s, 0.018 * s, n=6),
            ring_ellipse(0.0, 0.106 * s, 1.475 * s, 0.008 * s, 0.008 * s, n=6),
        ]
    else:
        verts.extend(add_cylinder(
            bm,
            (0.0, 0.098 * s, 1.676 * s),
            (0.0, 0.125 * s, 1.674 * s),
            0.018 * s, 0.018 * s, segments=6, mat_idx=mat_idx[tie_mat],
        ))
        tail_rings = [
            ring_ellipse(0.0, 0.126 * s, 1.672 * s, 0.030 * s, 0.026 * s, n=6),
            ring_ellipse(0.022 * s, 0.152 * s, 1.612 * s, 0.038 * s, 0.032 * s, n=6),
            ring_ellipse(0.046 * s, 0.126 * s, 1.535 * s, 0.028 * s, 0.024 * s, n=6),
            ring_ellipse(0.058 * s, 0.100 * s, 1.480 * s, 0.010 * s, 0.010 * s, n=6),
        ]
    verts.extend(loft_rings(bm, tail_rings, close_caps=(True, True), mat_idx=mat_idx[hair_mat]))
    return verts


def _add_headgear(bm, mat_idx, s, x_mul, headgear, hair_mat,
                  ponytail=False, ponytail_low=False, ponytail_tie="Mat_BeltLeather",
                  face_hair="none"):
    """Build headgear or hairstyle scaled cleanly to s and skull width x_mul."""
    verts = []
    if headgear == "beanie":
        cuff_rings = [
            ring_ellipse(0.0, 0.004 * s, 1.712 * s, 0.084 * s * x_mul, 0.108 * s, n=12, squash_front=1.08, tilt_y=0.06),
            ring_ellipse(0.0, 0.008 * s, 1.744 * s, 0.085 * s * x_mul, 0.109 * s, n=12, squash_front=1.08, tilt_y=0.06),
        ]
        verts.extend(loft_rings(bm, cuff_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_Beanie"]))
        dome_rings = [
            ring_ellipse(0.0, 0.013 * s, 1.738 * s, 0.078 * s * x_mul, 0.101 * s, n=12, squash_front=1.02, tilt_y=0.06),
            ring_ellipse(0.0, 0.016 * s, 1.770 * s, 0.068 * s * x_mul, 0.088 * s, n=12, tilt_y=0.05),
            ring_ellipse(0.0, 0.020 * s, 1.795 * s, 0.044 * s * x_mul, 0.056 * s, n=12, tilt_y=0.04),
            ring_ellipse(0.0, 0.022 * s, 1.806 * s, 0.016 * s * x_mul, 0.020 * s, n=12, tilt_y=0.02),
        ]
        verts.extend(loft_rings(bm, dome_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_Beanie"]))

    elif headgear == "cap":
        # Tactical olive baseball cap + curved front brim
        cap_rings = [
            ring_ellipse(0.0, 0.006 * s, 1.712 * s, 0.083 * s * x_mul, 0.108 * s, n=12, squash_front=1.06, tilt_y=0.05),
            ring_ellipse(0.0, 0.010 * s, 1.745 * s, 0.080 * s * x_mul, 0.104 * s, n=12, squash_front=1.04, tilt_y=0.05),
            ring_ellipse(0.0, 0.014 * s, 1.776 * s, 0.064 * s * x_mul, 0.085 * s, n=12, tilt_y=0.04),
            ring_ellipse(0.0, 0.018 * s, 1.798 * s, 0.032 * s * x_mul, 0.042 * s, n=12, tilt_y=0.02),
        ]
        verts.extend(loft_rings(bm, cap_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_OliveDark"]))
        # Curved front bill visor
        verts.extend(add_box(
            bm,
            center=(0.0, -0.125 * s, 1.706 * s),
            size=(0.132 * s, 0.095 * s, 0.010 * s),
            rot=(-0.12, 0.0, 0.0),
            taper_top=(0.82, 0.90),
            mat_idx=mat_idx["Mat_OliveDark"],
        ))

    elif headgear == "short_hair":
        # Sculpted faceted male short hair crown + swept front-left fringe
        hair_cap = [
            ring_ellipse(0.0, 0.008 * s, 1.718 * s, 0.081 * s * x_mul, 0.105 * s, n=12, squash_front=1.06, tilt_y=0.06),
            ring_ellipse(0.0, 0.014 * s, 1.756 * s, 0.077 * s * x_mul, 0.101 * s, n=12, tilt_y=0.05),
            ring_ellipse(0.0, 0.018 * s, 1.786 * s, 0.056 * s * x_mul, 0.076 * s, n=12, tilt_y=0.04),
            ring_ellipse(0.0, 0.020 * s, 1.798 * s, 0.024 * s * x_mul, 0.032 * s, n=12),
        ]
        verts.extend(loft_rings(bm, hair_cap, close_caps=(True, True), mat_idx=mat_idx[hair_mat]))
        verts.extend(add_box(
            bm,
            center=(0.014 * s * x_mul, -0.076 * s, 1.744 * s),
            size=(0.086 * s * x_mul, 0.046 * s, 0.026 * s),
            rot=(-0.18, 0.08, -0.14),
            taper_top=(0.82, 0.72),
            mat_idx=mat_idx[hair_mat],
        ))

    elif headgear == "ponytail":
        # Sculpted hair cap + tapering faceted ponytail down the back
        hair_cap = [
            ring_ellipse(0.0, 0.008 * s, 1.718 * s, 0.080 * s * x_mul, 0.104 * s, n=12, squash_front=1.05, tilt_y=0.06),
            ring_ellipse(0.0, 0.014 * s, 1.754 * s, 0.076 * s * x_mul, 0.100 * s, n=12, tilt_y=0.05),
            ring_ellipse(0.0, 0.020 * s, 1.784 * s, 0.054 * s * x_mul, 0.074 * s, n=12, tilt_y=0.04),
            ring_ellipse(0.0, 0.022 * s, 1.796 * s, 0.022 * s * x_mul, 0.030 * s, n=12),
        ]
        verts.extend(loft_rings(bm, hair_cap, close_caps=(True, True), mat_idx=mat_idx[hair_mat]))
        verts.extend(_add_ponytail(bm, mat_idx, s, hair_mat, tie_mat=ponytail_tie, low=False))

    elif headgear == "ranger_hair":
        # Uncovered sculpted ranger hairstyle (Lena Female): full cap + nape hair + low side-swept fall
        hair_cap = [
            ring_ellipse(0.0, 0.008 * s, 1.718 * s, 0.080 * s * x_mul, 0.104 * s, n=12, squash_front=1.05, tilt_y=0.06),
            ring_ellipse(0.0, 0.014 * s, 1.754 * s, 0.076 * s * x_mul, 0.100 * s, n=12, tilt_y=0.05),
            ring_ellipse(0.0, 0.020 * s, 1.784 * s, 0.054 * s * x_mul, 0.074 * s, n=12, tilt_y=0.04),
            ring_ellipse(0.0, 0.022 * s, 1.796 * s, 0.022 * s * x_mul, 0.030 * s, n=12),
        ]
        verts.extend(loft_rings(bm, hair_cap, close_caps=(True, True), mat_idx=mat_idx[hair_mat]))
        nape_rings = [
            ring_ellipse(0.0, 0.048 * s, 1.615 * s, 0.062 * s * x_mul, 0.044 * s, n=8),
            ring_ellipse(0.0, 0.042 * s, 1.670 * s, 0.072 * s * x_mul, 0.056 * s, n=8),
            ring_ellipse(0.0, 0.032 * s, 1.710 * s, 0.076 * s * x_mul, 0.062 * s, n=8),
        ]
        verts.extend(loft_rings(bm, nape_rings, close_caps=(True, True), mat_idx=mat_idx[hair_mat]))
        verts.extend(add_cylinder(
            bm,
            (0.0, 0.092 * s, 1.644 * s),
            (0.0, 0.118 * s, 1.640 * s),
            0.019 * s, 0.019 * s, segments=6, mat_idx=mat_idx[ponytail_tie],
        ))
        ranger_tail = [
            ring_ellipse(0.0,       0.118 * s, 1.640 * s, 0.032 * s, 0.026 * s, n=6),
            ring_ellipse(0.032 * s, 0.140 * s, 1.580 * s, 0.040 * s, 0.032 * s, n=6),
            ring_ellipse(0.068 * s, 0.105 * s, 1.500 * s, 0.030 * s, 0.024 * s, n=6),
            ring_ellipse(0.082 * s, 0.072 * s, 1.445 * s, 0.012 * s, 0.010 * s, n=6),
        ]
        verts.extend(loft_rings(bm, ranger_tail, close_caps=(True, True), mat_idx=mat_idx[hair_mat]))

    elif headgear == "bandana_goggles":
        # Hair crown peeking slightly, red folded bandana, plus welding goggles on forehead (Rico)
        hair_top = [
            ring_ellipse(0.0, 0.012 * s, 1.734 * s, 0.078 * s * x_mul, 0.102 * s, n=12),
            ring_ellipse(0.0, 0.018 * s, 1.775 * s, 0.062 * s * x_mul, 0.082 * s, n=12),
            ring_ellipse(0.0, 0.020 * s, 1.794 * s, 0.024 * s * x_mul, 0.034 * s, n=12),
        ]
        verts.extend(loft_rings(bm, hair_top, close_caps=(True, True), mat_idx=mat_idx[hair_mat]))
        band_rings = [
            ring_ellipse(0.0, 0.004 * s, 1.696 * s, 0.084 * s * x_mul, 0.109 * s, n=12, squash_front=1.08, tilt_y=0.05),
            ring_ellipse(0.0, 0.008 * s, 1.738 * s, 0.084 * s * x_mul, 0.109 * s, n=12, squash_front=1.08, tilt_y=0.05),
        ]
        verts.extend(loft_rings(bm, band_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_BandanaRed"]))
        # Fluttering knot tails at back
        for sx in (1.0, -1.0):
            verts.extend(add_box(
                bm,
                center=(sx * 0.024 * s, 0.125 * s, 1.688 * s),
                size=(0.018 * s, 0.055 * s, 0.022 * s),
                rot=(0.45, 0.0, sx * -0.35),
                taper_top=(0.5, 0.6),
                mat_idx=mat_idx["Mat_BandanaRed"],
            ))
        # Welding goggles resting on forehead over bandana
        for sx in (1.0, -1.0):
            verts.extend(add_cylinder(
                bm,
                (sx * 0.034 * s, -0.095 * s, 1.720 * s),
                (sx * 0.034 * s, -0.118 * s, 1.720 * s),
                0.024 * s, 0.022 * s, segments=8, mat_idx=mat_idx["Mat_GunMetal"],
            ))
            verts.extend(add_cylinder(
                bm,
                (sx * 0.034 * s, -0.117 * s, 1.720 * s),
                (sx * 0.034 * s, -0.121 * s, 1.720 * s),
                0.018 * s, 0.018 * s, segments=8, mat_idx=mat_idx["Mat_GlassDark"],
            ))
        verts.extend(add_box(
            bm,
            center=(0.0, -0.106 * s, 1.720 * s),
            size=(0.026 * s, 0.014 * s, 0.012 * s),
            mat_idx=mat_idx["Mat_BeltLeather"],
        ))

    elif headgear == "hood":
        # Subtle tucked bangs inside hood rim + deep forest-green hood (Lena)
        for sx in (1.0, -1.0):
            verts.extend(add_box(
                bm,
                center=(sx * 0.038 * s * x_mul, -0.058 * s, 1.738 * s),
                size=(0.034 * s, 0.022 * s, 0.028 * s),
                rot=(0.12, 0.0, sx * -0.15),
                mat_idx=mat_idx[hair_mat],
            ))
        # C-shaped thick hood shell wrapping around top, sides, and back of skull
        levels = [
            (1.505 * s, 0.088 * s, 0.098 * s, 0.044 * s, 0.014 * s),  # collar drape
            (1.595 * s, 0.096 * s, 0.110 * s, 0.062 * s, 0.015 * s),  # jaw/ear wrap
            (1.685 * s, 0.098 * s, 0.118 * s, 0.068 * s, 0.015 * s),  # cheek/temple wrap
            (1.758 * s, 0.092 * s, 0.122 * s, 0.056 * s, 0.014 * s),  # upper brow overhang
            (1.805 * s, 0.052 * s, 0.084 * s, 0.024 * s, 0.012 * s),  # crown apex
        ]
        n_arc = 7
        rings = []
        for (cz, rx, ry, gap_x, thick) in levels:
            gap_ang = math.asin(min(0.85, gap_x / rx))
            a_start = -0.5 * math.pi + gap_ang
            a_end = 1.5 * math.pi - gap_ang
            outer_pts, inner_pts = [], []
            for i in range(n_arc):
                t = i / (n_arc - 1)
                ang = a_start + t * (a_end - a_start)
                ca, sa = math.cos(ang), math.sin(ang)
                outer_pts.append((rx * ca, 0.008 * s + ry * sa, cz))
                inner_pts.append(((rx - thick) * ca, 0.008 * s + (ry - thick) * sa, cz))
            rings.append(outer_pts + list(reversed(inner_pts)))
        verts.extend(loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_idx["Mat_HoodGreen"]))
        # Top hood peak cap closing the crown smoothly
        verts.extend(add_box(
            bm,
            center=(0.0, 0.006 * s, 1.802 * s),
            size=(0.098 * s, 0.145 * s, 0.024 * s),
            taper_top=(0.65, 0.78),
            mat_idx=mat_idx["Mat_HoodGreen"],
        ))

    elif headgear == "cowboy":
        # Wide-brim brown cowboy hat with pinched crown, leather band, and curved side brims (Tom)
        # Crown
        crown_rings = [
            ring_ellipse(0.0, 0.006 * s, 1.716 * s, 0.084 * s * x_mul, 0.108 * s, n=12, squash_front=1.06, tilt_y=0.05),
            ring_ellipse(0.0, 0.008 * s, 1.765 * s, 0.074 * s * x_mul, 0.096 * s, n=12, tilt_y=0.04),
            ring_ellipse(0.0, 0.010 * s, 1.812 * s, 0.054 * s * x_mul, 0.076 * s, n=12, tilt_y=0.03),
        ]
        verts.extend(loft_rings(bm, crown_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_CowboyBrown"]))
        # Leather hatband
        band_rings = [
            ring_ellipse(0.0, 0.006 * s, 1.720 * s, 0.086 * s * x_mul, 0.110 * s, n=12, squash_front=1.06, tilt_y=0.05),
            ring_ellipse(0.0, 0.007 * s, 1.738 * s, 0.085 * s * x_mul, 0.109 * s, n=12, squash_front=1.06, tilt_y=0.05),
        ]
        verts.extend(loft_rings(bm, band_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_VestLeather"]))
        # Wide sculpted brim (upturned at +/-X, dipped gently at front/back)
        inner_brim = ring_ellipse(0.0, 0.006 * s, 1.716 * s, 0.082 * s * x_mul, 0.106 * s, n=12)
        outer_brim = ring_ellipse(0.0, 0.004 * s, 1.710 * s, 0.168 * s, 0.188 * s, n=12)
        for i, (px, py, pz) in enumerate(outer_brim):
            # Curl left/right sides upward, dip front/back slightly
            side_factor = (abs(px) / (0.168 * s)) ** 2
            fb_factor = (abs(py) / (0.188 * s)) ** 2
            outer_brim[i] = (px, py, pz + (0.026 * side_factor - 0.012 * fb_factor) * s)
        outer_top = [(px, py, pz + 0.008 * s) for (px, py, pz) in outer_brim]
        inner_top = [(px, py, pz + 0.008 * s) for (px, py, pz) in inner_brim]
        verts.extend(loft_rings(bm, [inner_brim, outer_brim, outer_top, inner_top],
                                close_caps=(False, False), mat_idx=mat_idx["Mat_CowboyBrown"]))

    if ponytail and headgear != "ponytail":
        verts.extend(_add_ponytail(bm, mat_idx, s, hair_mat, tie_mat=ponytail_tie, low=ponytail_low))

    if face_hair != "none":
        verts.extend(_add_fem_face_locks(bm, mat_idx, s, x_mul, hair_mat, style=face_hair))

    return verts


def build_character_head(
    bm,
    mat_idx,
    regions,
    proportions=None,
    gender="male",
    skin_mat="Mat_Skin",
    hair_mat="Mat_Hair",
    lip_mat="Mat_Lip",
    stubble_mat="Mat_Stubble",
    headgear="beanie",
    beard="stubble",
    ponytail=False,
    ponytail_low=False,
    ponytail_tie="Mat_BeltLeather",
    face_hair="none",
):
    """Build anatomical faceless low-poly head, neck, ears, hair/beard & headgear."""
    s = proportions["scale"] if proportions is not None else 1.0
    is_fem = (gender == "female")
    x_mul = 0.89 if is_fem else 1.0

    # Midline vertices (X = 0): female gets softer brow, delicate nose, fuller lips, smaller chin
    brow_y = -0.090 if is_fem else -0.102
    nose_y = -0.109 if is_fem else -0.120
    nose_z = 1.627 if is_fem else 1.622
    chin_y = -0.088 if is_fem else -0.100
    mid_coords = {
        "m_crown":      (0.0,  0.020, 1.790),
        "m_fore_top":   (0.0, -0.056, 1.758),
        "m_fore_mid":   (0.0, -0.084 if is_fem else -0.088, 1.720),
        "m_brow":       (0.0,  brow_y, 1.676),
        "m_bridge":     (0.0, -0.090 if is_fem else -0.092, 1.658),
        "m_nose_tip":   (0.0,  nose_y, nose_z),
        "m_nose_base":  (0.0, -0.098 if is_fem else -0.100, 1.613 if is_fem else 1.610),
        "m_philtrum":   (0.0, -0.097 if is_fem else -0.098, 1.602 if is_fem else 1.600),
        "m_lip_up":     (0.0, -0.106 if is_fem else -0.104, 1.594 if is_fem else 1.592),
        "m_mouth":      (0.0, -0.095 if is_fem else -0.094, 1.585),
        "m_lip_lo":     (0.0, -0.104 if is_fem else -0.102, 1.575 if is_fem else 1.577),
        "m_chin_cleft": (0.0, -0.089 if is_fem else -0.091, 1.567),
        "m_chin":       (0.0,  chin_y, 1.554 if is_fem else 1.552),
        "m_chin_under": (0.0, -0.070 if is_fem else -0.072, 1.542 if is_fem else 1.540),
        "m_throat":     (0.0, -0.036, 1.522),
        "m_neck_front": (0.0, -0.036 if is_fem else -0.042, 1.465),
        "m_neck_back":  (0.0,  0.046 if is_fem else 0.056, 1.465),
        "m_nape":       (0.0,  0.050 if is_fem else 0.056, 1.545),
        "m_occ_low":    (0.0,  0.086, 1.605),
        "m_occ_mid":    (0.0,  0.102, 1.668),
        "m_occ_top":    (0.0,  0.084, 1.738),
    }

    # Left-side (+X) landmark coordinates: female gets slender neck & heart-shaped jaw
    jaw_w = 0.047 if is_fem else 0.064
    chin_w = 0.013 if is_fem else 0.024
    neck_mul = 0.72 if is_fem else 1.0
    side_coords = {
        "s_fore_top":   (0.052 * x_mul, -0.044, 1.752),
        "s_fore_mid":   (0.048 * x_mul, -0.074 if is_fem else -0.076, 1.716),
        "s_temple_top": (0.072 * x_mul, -0.012, 1.738),
        "s_temple":     (0.068 * x_mul, -0.038, 1.682),
        "s_temple_low": (0.070 * x_mul, -0.018, 1.652),

        "s_brow_in":    (0.022 * x_mul, brow_y, 1.678),
        "s_brow_out":   (0.052 * x_mul, -0.081 if is_fem else -0.085, 1.676),
        "s_eye_in":     (0.016 * x_mul, -0.082, 1.658),
        "s_eye_top":    (0.034 * x_mul, -0.079, 1.662),
        "s_eye_bot":    (0.034 * x_mul, -0.083, 1.648),
        "s_eye_out":    (0.054 * x_mul, -0.074, 1.654),

        "s_nose_side":  (0.0085 if is_fem else 0.011, -0.095 if is_fem else -0.098, 1.630),
        "s_nose_wing":  (0.012 if is_fem else 0.016, -0.094 if is_fem else -0.096, 1.613),
        "s_cheek_in":   (0.042 * x_mul, -0.078, 1.634),
        "s_cheek_bone": (0.072 * x_mul, -0.044, 1.638 if is_fem else 1.635),
        "s_cheek_hol":  (0.054 * x_mul, -0.056 if is_fem else -0.048, 1.598),

        "s_lip_up":     (0.014 if is_fem else 0.016, -0.096, 1.593),
        "s_mouth_cor":  (0.021 if is_fem else 0.023, -0.086, 1.586),
        "s_lip_lo":     (0.014 if is_fem else 0.015, -0.095, 1.577),
        "s_chin_side":  (chin_w, -0.084 if is_fem else -0.088, 1.556),
        "s_jaw_mid":    (0.039 * x_mul if is_fem else 0.045 * x_mul, -0.044, 1.564 if is_fem else 1.556),
        "s_jaw_cor":    (jaw_w,  0.008, 1.584 if is_fem else 1.578),
        "s_jaw_under":  (0.036 * x_mul if is_fem else 0.042 * x_mul, -0.036, 1.538 if is_fem else 1.534),

        "s_neck_front": (0.038 * neck_mul, -0.030, 1.465),
        "s_neck_side":  (0.048 * neck_mul,  0.014, 1.465),
        "s_neck_back":  (0.038 * neck_mul,  0.048, 1.465),
        "s_nape_side":  (0.044 * neck_mul,  0.046, 1.546),
        "s_mastoid":    (0.062 * x_mul,  0.036, 1.608),
        "s_ear_base":   (0.070 * x_mul,  0.012, 1.634),
        "s_side_skull": (0.074 * x_mul,  0.028, 1.682),
        "s_occ_low_s":  (0.052 * x_mul,  0.072, 1.608),
        "s_occ_mid_s":  (0.060 * x_mul,  0.084, 1.668),
        "s_occ_top_s":  (0.056 * x_mul,  0.070, 1.740),
    }

    verts_mid = {k: bm.verts.new((c[0] * s, c[1] * s, c[2] * s)) for k, c in mid_coords.items()}
    verts_l = {k: bm.verts.new((c[0] * s, c[1] * s, c[2] * s)) for k, c in side_coords.items()}
    verts_r = {k: bm.verts.new((-c[0] * s, c[1] * s, c[2] * s)) for k, c in side_coords.items()}

    # Choose material role tags
    jaw_mat = (
        "Mat_Beard" if beard == "full"
        else (stubble_mat if beard == "stubble" else skin_mat)
    )
    upper_lip_mat = hair_mat if beard == "mustache" else lip_mat
    chin_cleft_mat = hair_mat if beard == "mustache" else jaw_mat

    tris_half = [
        ("m_crown", "s_fore_top", "m_fore_top", hair_mat),
        ("m_crown", "s_temple_top", "s_fore_top", hair_mat),
        ("m_crown", "s_occ_top_s", "s_temple_top", hair_mat),
        ("m_crown", "m_occ_top", "s_occ_top_s", hair_mat),

        ("m_fore_top", "s_fore_top", "s_fore_mid", skin_mat),
        ("m_fore_top", "s_fore_mid", "m_fore_mid", skin_mat),
        ("s_fore_top", "s_temple_top", "s_temple", hair_mat),
        ("s_fore_top", "s_temple", "s_fore_mid", skin_mat),

        ("m_fore_mid", "s_fore_mid", "s_brow_in", skin_mat),
        ("m_fore_mid", "s_brow_in", "m_brow", skin_mat),
        ("s_fore_mid", "s_brow_out", "s_brow_in", skin_mat),
        ("s_fore_mid", "s_temple", "s_brow_out", skin_mat),
        ("s_temple", "s_temple_low", "s_brow_out", skin_mat),
        ("s_brow_out", "s_temple_low", "s_eye_out", skin_mat),

        ("m_brow", "s_brow_in", "s_eye_in", skin_mat),
        ("m_brow", "s_eye_in", "m_bridge", skin_mat),
        ("s_brow_in", "s_eye_top", "s_eye_in", skin_mat),
        ("s_brow_in", "s_brow_out", "s_eye_top", skin_mat),
        ("s_brow_out", "s_eye_out", "s_eye_top", skin_mat),
        ("s_eye_in", "s_eye_top", "s_eye_bot", skin_mat),
        ("s_eye_top", "s_eye_out", "s_eye_bot", skin_mat),

        ("m_bridge", "s_eye_in", "s_nose_side", skin_mat),
        ("m_bridge", "s_nose_side", "m_nose_tip", skin_mat),
        ("s_eye_in", "s_eye_bot", "s_cheek_in", skin_mat),
        ("s_eye_in", "s_cheek_in", "s_nose_side", skin_mat),
        ("s_eye_bot", "s_eye_out", "s_cheek_in", skin_mat),
        ("s_eye_out", "s_cheek_bone", "s_cheek_in", skin_mat),
        ("s_eye_out", "s_temple_low", "s_cheek_bone", skin_mat),
        ("m_nose_tip", "s_nose_side", "s_nose_wing", skin_mat),
        ("m_nose_tip", "s_nose_wing", "m_nose_base", skin_mat),
        ("s_nose_side", "s_cheek_in", "s_nose_wing", skin_mat),

        ("m_nose_base", "s_nose_wing", "m_philtrum", skin_mat),
        ("s_nose_wing", "s_cheek_in", "s_cheek_hol", skin_mat),
        ("s_cheek_in", "s_cheek_bone", "s_cheek_hol", skin_mat),
        ("s_nose_wing", "s_cheek_hol", "s_mouth_cor", skin_mat),
        ("s_nose_wing", "s_mouth_cor", "s_lip_up", skin_mat),
        ("s_nose_wing", "s_lip_up", "m_philtrum", upper_lip_mat if beard == "mustache" else skin_mat),

        ("m_philtrum", "s_lip_up", "m_lip_up", upper_lip_mat),
        ("m_lip_up", "s_lip_up", "s_mouth_cor", upper_lip_mat),
        ("m_lip_up", "s_mouth_cor", "m_mouth", upper_lip_mat),
        ("m_mouth", "s_mouth_cor", "s_lip_lo", lip_mat),
        ("m_mouth", "s_lip_lo", "m_lip_lo", lip_mat),

        ("m_lip_lo", "s_lip_lo", "s_chin_side", chin_cleft_mat),
        ("m_lip_lo", "s_chin_side", "m_chin_cleft", chin_cleft_mat),
        ("m_chin_cleft", "s_chin_side", "m_chin", chin_cleft_mat),
        ("s_lip_lo", "s_mouth_cor", "s_chin_side", jaw_mat),
        ("s_mouth_cor", "s_cheek_hol", "s_jaw_mid", jaw_mat),
        ("s_mouth_cor", "s_jaw_mid", "s_chin_side", jaw_mat),
        ("s_cheek_hol", "s_cheek_bone", "s_jaw_cor", skin_mat),
        ("s_cheek_hol", "s_jaw_cor", "s_jaw_mid", jaw_mat),
        ("s_cheek_bone", "s_temple_low", "s_ear_base", skin_mat),
        ("s_cheek_bone", "s_ear_base", "s_jaw_cor", skin_mat),

        ("m_chin", "s_chin_side", "s_jaw_under", jaw_mat),
        ("m_chin", "s_jaw_under", "m_chin_under", jaw_mat),
        ("s_chin_side", "s_jaw_mid", "s_jaw_under", jaw_mat),
        ("s_jaw_mid", "s_jaw_cor", "s_jaw_under", jaw_mat),
        ("m_chin_under", "s_jaw_under", "m_throat", skin_mat),
        ("s_jaw_under", "s_jaw_cor", "s_mastoid", skin_mat),
        ("s_jaw_under", "s_mastoid", "s_nape_side", skin_mat),
        ("m_throat", "s_jaw_under", "s_neck_front", skin_mat),
        ("m_throat", "s_neck_front", "m_neck_front", skin_mat),
        ("s_jaw_under", "s_nape_side", "s_neck_side", skin_mat),
        ("s_jaw_under", "s_neck_side", "s_neck_front", skin_mat),
        ("s_nape_side", "s_neck_back", "s_neck_side", skin_mat),
        ("s_nape_side", "m_nape", "s_neck_back", skin_mat),
        ("m_nape", "m_neck_back", "s_neck_back", skin_mat),

        ("m_neck_front", "s_neck_front", "s_neck_side", skin_mat),
        ("m_neck_front", "s_neck_side", "s_neck_back", skin_mat),
        ("m_neck_front", "s_neck_back", "m_neck_back", skin_mat),

        ("s_temple_low", "s_temple_top", "s_side_skull", hair_mat),
        ("s_temple_low", "s_side_skull", "s_ear_base", hair_mat),
        ("s_temple_top", "s_occ_top_s", "s_side_skull", hair_mat),
        ("s_ear_base", "s_side_skull", "s_mastoid", hair_mat),
        ("s_ear_base", "s_mastoid", "s_jaw_cor", skin_mat),
        ("s_side_skull", "s_occ_top_s", "s_occ_mid_s", hair_mat),
        ("s_side_skull", "s_occ_mid_s", "s_occ_low_s", hair_mat),
        ("s_side_skull", "s_occ_low_s", "s_mastoid", hair_mat),
        ("s_mastoid", "s_occ_low_s", "s_nape_side", skin_mat),
        ("s_occ_low_s", "m_occ_low", "m_nape", skin_mat),
        ("s_occ_low_s", "m_nape", "s_nape_side", skin_mat),
        ("m_occ_top", "s_occ_mid_s", "s_occ_top_s", hair_mat),
        ("m_occ_top", "m_occ_mid", "s_occ_mid_s", hair_mat),
        ("m_occ_mid", "s_occ_low_s", "s_occ_mid_s", hair_mat),
        ("m_occ_mid", "m_occ_low", "s_occ_low_s", hair_mat),
    ]

    created_faces = []
    for a, b, c, mname in tris_half:
        vl = [verts_mid[n] if n.startswith("m_") else verts_l[n] for n in (a, b, c)]
        fl = bm.faces.new(vl)
        fl.material_index = mat_idx[mname]
        created_faces.append(fl)

        vr = [verts_mid[n] if n.startswith("m_") else verts_r[n] for n in (a, c, b)]
        fr = bm.faces.new(vr)
        fr.material_index = mat_idx[mname]
        created_faces.append(fr)

    bmesh.ops.recalc_face_normals(bm, faces=created_faces)

    all_skull_verts = list(verts_mid.values()) + list(verts_l.values()) + list(verts_r.values())
    neck_verts = [v for v in all_skull_verts if v.co.z < 1.528 * s]
    head_verts = [v for v in all_skull_verts if v.co.z >= 1.528 * s]

    # Subtle sculpted chin beard volume for Jake (follows jawline cleanly without boxy wings)
    if beard == "full":
        head_verts.extend(add_box(
            bm,
            center=(0.0, -0.078 * s, 1.552 * s),
            size=(0.052 * s, 0.048 * s, 0.034 * s),
            rot=(-0.18, 0.0, 0.0),
            taper_top=(1.08, 0.92),
            mat_idx=mat_idx["Mat_Beard"],
        ))
    elif beard == "mustache":
        head_verts.extend(add_box(
            bm,
            center=(0.0, -0.104 * s, 1.594 * s),
            size=(0.042 * s, 0.014 * s, 0.011 * s),
            taper_top=(0.65, 0.8),
            mat_idx=mat_idx[hair_mat],
        ))

    # Sculpted C-shaped ears (L & R)
    head_verts.extend(_build_ear(bm, mat_idx, 1.0, s=s, skin_mat=skin_mat, x_mul=x_mul))
    head_verts.extend(_build_ear(bm, mat_idx, -1.0, s=s, skin_mat=skin_mat, x_mul=x_mul))

    # Headgear / Hairstyle
    head_verts.extend(_add_headgear(
        bm, mat_idx, s, x_mul, headgear, hair_mat,
        ponytail=ponytail, ponytail_low=ponytail_low, ponytail_tie=ponytail_tie,
        face_hair=face_hair,
    ))

    regions.setdefault("neck", []).extend(neck_verts)
    regions.setdefault("head", []).extend(head_verts)


def build_sculpted_head_and_beanie(bm, mat_idx, regions):
    """Backward-compatible wrapper for prototype survivor build."""
    build_character_head(
        bm, mat_idx, regions,
        proportions=None, gender="male",
        skin_mat="Mat_Skin", hair_mat="Mat_Hair",
        lip_mat="Mat_Lip", stubble_mat="Mat_Stubble",
        headgear="beanie", beard="stubble",
    )
