"""Hand-authored Loomis/Asaro faceted faceless horror zombie head, hollow orbital pits, snarling jaw & mutations."""
import math
import bmesh
from mesh_utils import add_box, add_cylinder, loft_rings, ring_ellipse
from head_sculpt import _build_ear


def _add_jagged_teeth(bm, mat_idx, s, x_mul, jaw_open, tooth_mat="Mat_ZBone", missing_right=False):
    """Add sculpted low-poly upper & lower tooth fangs tucked cleanly inside the open mouth cavity."""
    verts = []
    upper_slots = (-0.011, -0.0055, 0.0, 0.0055, 0.011)
    for idx, ux in enumerate(upper_slots):
        if missing_right and idx == 0:
            continue
        ax = abs(ux) / 0.012
        py = (-0.093 + 0.007 * ax) * s
        h = (0.0072 if idx in (1, 3) else 0.0056) * s
        cz = (1.5915 - 0.35 * h) * s
        verts.extend(add_box(
            bm,
            center=(ux * s * x_mul, py, cz),
            size=(0.0038 * s, 0.0040 * s, h),
            rot=(-0.10, (idx - 2) * 0.05, 0.0),
            taper_top=(1.25, 1.15),
            mat_idx=mat_idx[tooth_mat],
        ))

    if jaw_open >= 0.006:
        lower_slots = (-0.009, -0.003, 0.003, 0.009)
        for idx, lx in enumerate(lower_slots):
            ax = abs(lx) / 0.012
            py = (-0.091 + 0.007 * ax) * s
            h = (0.0066 if idx in (0, 3) else 0.0052) * s
            cz = (1.577 - jaw_open + 0.55 * h) * s
            verts.extend(add_box(
                bm,
                center=(lx * s * x_mul, py, cz),
                size=(0.0036 * s, 0.0038 * s, h),
                rot=(0.12, (idx - 1.5) * 0.05, 0.0),
                taper_top=(0.58, 0.62),
                mat_idx=mat_idx[tooth_mat],
            ))
    return verts


def _add_neck_bile_sac(bm, mat_idx, s, x_mul):
    """Build asymmetric swollen mutated bile sac under the jawline/throat (tagged to neck)."""
    sac_rings = [
        ring_ellipse(0.010 * s * x_mul, -0.036 * s, 1.468 * s, 0.032 * s * x_mul, 0.026 * s, n=8),
        ring_ellipse(0.014 * s * x_mul, -0.054 * s, 1.494 * s, 0.044 * s * x_mul, 0.036 * s, n=8, squash_front=1.18),
        ring_ellipse(0.012 * s * x_mul, -0.058 * s, 1.518 * s, 0.040 * s * x_mul, 0.032 * s, n=8, squash_front=1.15),
        ring_ellipse(0.006 * s * x_mul, -0.046 * s, 1.536 * s, 0.024 * s * x_mul, 0.020 * s, n=8),
    ]
    verts = loft_rings(bm, sac_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_ZSkinToxic"])
    # Embedded glowing acid fissures / blisters along the sac wall
    for px, py, pz, r in (
        ( 0.028, -0.072, 1.504, 0.012),
        (-0.006, -0.078, 1.492, 0.010),
        ( 0.036, -0.054, 1.516, 0.009),
    ):
        verts.extend(add_box(
            bm,
            center=(px * s * x_mul, py * s, pz * s),
            size=(r * s, r * 0.85 * s, r * 1.15 * s),
            rot=(0.30, 0.35, 0.25),
            bevel=r * 0.22 * s,
            mat_idx=mat_idx["Mat_ZAcidGlow"],
        ))
    return verts


def _add_zombie_headgear(bm, mat_idx, s, x_mul, headgear, hair_mat):
    """Build horror hair variants, tattered stalker cowl, bloated scalp, or juggernaut brow plate."""
    verts = []

    if headgear == "messy_patchy":
        hair_cap = [
            ring_ellipse(0.0, 0.010 * s, 1.724 * s, 0.079 * s * x_mul, 0.102 * s, n=12, squash_front=1.02, tilt_y=0.06),
            ring_ellipse(0.0, 0.016 * s, 1.762 * s, 0.072 * s * x_mul, 0.094 * s, n=12, tilt_y=0.05),
            ring_ellipse(0.0, 0.022 * s, 1.786 * s, 0.044 * s * x_mul, 0.062 * s, n=12, tilt_y=0.04),
        ]
        for i in (3, 4, 5):
            px, py, pz = hair_cap[0][i]
            hair_cap[0][i] = (px * 0.92, py * 0.95, pz + 0.014 * s)
        verts.extend(loft_rings(bm, hair_cap, close_caps=(True, True), mat_idx=mat_idx[hair_mat]))
        verts.extend(add_box(
            bm,
            center=(0.028 * s * x_mul, -0.064 * s, 1.744 * s),
            size=(0.054 * s * x_mul, 0.036 * s, 0.022 * s),
            rot=(-0.20, 0.16, -0.22),
            taper_top=(0.72, 0.68),
            mat_idx=mat_idx[hair_mat],
        ))
        verts.extend(add_box(
            bm,
            center=(-0.032 * s * x_mul, 0.076 * s, 1.655 * s),
            size=(0.046 * s * x_mul, 0.028 * s, 0.056 * s),
            rot=(0.24, -0.14, 0.12),
            taper_top=(0.80, 0.70),
            mat_idx=mat_idx[hair_mat],
        ))

    elif headgear == "stalker_rags":
        # Sleek tattered dark shroud hugging back/sides of skull (hollow faceless sockets stay wide open)
        shroud_levels = [
            (1.520 * s, 0.082 * s * x_mul, 0.096 * s, 0.064 * s * x_mul, 0.011 * s),
            (1.620 * s, 0.086 * s * x_mul, 0.104 * s, 0.074 * s * x_mul, 0.011 * s),
            (1.708 * s, 0.084 * s * x_mul, 0.108 * s, 0.070 * s * x_mul, 0.011 * s),
            (1.768 * s, 0.074 * s * x_mul, 0.100 * s, 0.056 * s * x_mul, 0.010 * s),
        ]
        n_arc = 7
        s_rings = []
        for (cz, rx, ry, gap_x, thick) in shroud_levels:
            gap_ang = math.asin(min(0.90, gap_x / rx))
            a0, a1 = -0.5 * math.pi + gap_ang, 1.5 * math.pi - gap_ang
            op, ip = [], []
            for i in range(n_arc):
                ang = a0 + (i / (n_arc - 1)) * (a1 - a0)
                ca, sa = math.cos(ang), math.sin(ang)
                op.append((rx * ca, 0.012 * s + ry * sa, cz))
                ip.append(((rx - thick) * ca, 0.012 * s + (ry - thick) * sa, cz))
            s_rings.append(op + list(reversed(ip)))
        verts.extend(loft_rings(bm, s_rings, close_caps=(True, True), mat_idx=mat_idx["Mat_ZShroudDark"]))
        verts.extend(add_box(
            bm,
            center=(0.016 * s * x_mul, -0.064 * s, 1.744 * s),
            size=(0.056 * s * x_mul, 0.030 * s, 0.020 * s),
            rot=(-0.18, 0.16, -0.18),
            taper_top=(0.72, 0.68),
            mat_idx=mat_idx[hair_mat],
        ))

    elif headgear == "ragged_female":
        # Long wild asymmetrical tattered Banshee hair veiling sides & sweeping back
        hair_cap = [
            ring_ellipse(0.0, 0.008 * s, 1.716 * s, 0.080 * s * x_mul, 0.104 * s, n=12, squash_front=1.05, tilt_y=0.06),
            ring_ellipse(0.0, 0.014 * s, 1.754 * s, 0.076 * s * x_mul, 0.100 * s, n=12, tilt_y=0.05),
            ring_ellipse(0.0, 0.020 * s, 1.784 * s, 0.054 * s * x_mul, 0.074 * s, n=12, tilt_y=0.04),
            ring_ellipse(0.0, 0.022 * s, 1.796 * s, 0.022 * s * x_mul, 0.030 * s, n=12),
        ]
        verts.extend(loft_rings(bm, hair_cap, close_caps=(True, True), mat_idx=mat_idx[hair_mat]))
        # Uneven stringy fringe partially masking brow
        for px, py, pz, rx, ry in (
            ( 0.028, -0.078, 1.700, -0.20, -0.26),
            (-0.030, -0.076, 1.706, -0.16,  0.22),
        ):
            verts.extend(add_box(
                bm,
                center=(px * s * x_mul, py * s, pz * s),
                size=(0.036 * s * x_mul, 0.018 * s, 0.028 * s),
                rot=(rx, 0.0, ry),
                taper_top=(0.65, 0.65),
                mat_idx=mat_idx[hair_mat],
            ))
        # Long stringy tattered locks framing cheeks down to shoulders & sweeping down back
        left_lock = [
            ring_ellipse(0.058 * s * x_mul, -0.018 * s, 1.720 * s, 0.015 * s, 0.022 * s, n=6),
            ring_ellipse(0.068 * s * x_mul, -0.036 * s, 1.642 * s, 0.016 * s, 0.022 * s, n=6),
            ring_ellipse(0.064 * s * x_mul, -0.026 * s, 1.545 * s, 0.012 * s, 0.016 * s, n=6),
            ring_ellipse(0.054 * s * x_mul, -0.014 * s, 1.465 * s, 0.005 * s, 0.007 * s, n=6),
        ]
        right_lock = [
            ring_ellipse(-0.058 * s * x_mul, -0.016 * s, 1.720 * s, 0.014 * s, 0.020 * s, n=6),
            ring_ellipse(-0.066 * s * x_mul, -0.030 * s, 1.652 * s, 0.014 * s, 0.018 * s, n=6),
            ring_ellipse(-0.058 * s * x_mul, -0.018 * s, 1.585 * s, 0.005 * s, 0.008 * s, n=6),
        ]
        back_veil = [
            ring_ellipse(0.0, 0.064 * s, 1.692 * s, 0.068 * s * x_mul, 0.032 * s, n=8),
            ring_ellipse(0.0, 0.084 * s, 1.600 * s, 0.074 * s * x_mul, 0.030 * s, n=8),
            ring_ellipse(-0.018 * s, 0.092 * s, 1.500 * s, 0.054 * s * x_mul, 0.020 * s, n=8),
            ring_ellipse(-0.028 * s, 0.090 * s, 1.435 * s, 0.024 * s * x_mul, 0.010 * s, n=8),
        ]
        verts.extend(loft_rings(bm, left_lock, close_caps=(True, True), mat_idx=mat_idx[hair_mat]))
        verts.extend(loft_rings(bm, right_lock, close_caps=(True, True), mat_idx=mat_idx[hair_mat]))
        verts.extend(loft_rings(bm, back_veil, close_caps=(True, True), mat_idx=mat_idx[hair_mat]))

    elif headgear == "boomer_bloated":
        # Thin wispy balding strands on back/sides + glowing volatile blisters on crown & left temple
        for sx in (1.0, -1.0):
            verts.extend(add_box(
                bm,
                center=(sx * 0.066 * s * x_mul, 0.022 * s, 1.682 * s),
                size=(0.018 * s, 0.058 * s, 0.044 * s),
                rot=(0.10, sx * -0.12, 0.0),
                mat_idx=mat_idx[hair_mat],
            ))
        for pos, rad, bmat in (
            (( 0.028, -0.034, 1.772), 0.022, "Mat_ZBoilDark"),
            (( 0.036, -0.024, 1.784), 0.015, "Mat_ZBoilGlow"),
            ((-0.044,  0.008, 1.758), 0.020, "Mat_ZBoilDark"),
            (( 0.052,  0.032, 1.724), 0.016, "Mat_ZBoilGlow"),
        ):
            verts.extend(add_box(
                bm,
                center=(pos[0] * s * x_mul, pos[1] * s, pos[2] * s),
                size=(rad * s, rad * s, rad * s),
                rot=(0.4, 0.3, 0.2),
                bevel=rad * 0.22 * s,
                mat_idx=mat_idx[bmat],
            ))

    elif headgear == "juggernaut_scarred":
        # Heavy scarred skull + surgical brow staples + shattered riot plate fragment bolted to right temple
        for sx in (1.0, -1.0):
            verts.extend(add_box(
                bm,
                center=(sx * 0.066 * s * x_mul, 0.025 * s, 1.688 * s),
                size=(0.020 * s, 0.060 * s, 0.044 * s),
                rot=(0.08, sx * -0.12, 0.0),
                taper_top=(0.82, 0.78),
                mat_idx=mat_idx[hair_mat],
            ))
        # Shattered metal helmet fragment bolted to right upper temple (-X)
        verts.extend(add_box(
            bm,
            center=(-0.054 * s * x_mul, -0.022 * s, 1.742 * s),
            size=(0.048 * s * x_mul, 0.088 * s, 0.044 * s),
            rot=(-0.18, -0.45, 0.14),
            taper_top=(0.76, 0.82),
            mat_idx=mat_idx["Mat_ZRiotArmor"],
        ))
        # Metal surgical staples along left forehead scar (+X)
        for k in range(3):
            t = k - 1
            verts.extend(add_box(
                bm,
                center=((0.026 + t * 0.012) * s * x_mul, -0.074 * s, (1.716 - t * 0.011) * s),
                size=(0.005 * s, 0.008 * s, 0.011 * s),
                rot=(0.0, 0.45, -0.30),
                mat_idx=mat_idx["Mat_GunSteel"],
            ))

    elif headgear == "hazmat_torn":
        # Sleek torn yellow biohazard hood peeled open around face with jagged right-side tear
        levels = [
            (1.505 * s, 0.084 * s * x_mul, 0.096 * s, 0.056 * s * x_mul, 0.014 * s),
            (1.595 * s, 0.096 * s * x_mul, 0.112 * s, 0.072 * s * x_mul, 0.014 * s),
            (1.685 * s, 0.098 * s * x_mul, 0.120 * s, 0.074 * s * x_mul, 0.014 * s),
            (1.758 * s, 0.092 * s * x_mul, 0.122 * s, 0.062 * s * x_mul, 0.014 * s),
            (1.805 * s, 0.054 * s * x_mul, 0.084 * s, 0.026 * s * x_mul, 0.012 * s),
        ]
        n_arc = 7
        rings = []
        for lidx, (cz, rx, ry, gap_x, thick) in enumerate(levels):
            gap_ang = math.asin(min(0.88, gap_x / rx))
            a_start = -0.5 * math.pi + gap_ang
            tear_shift = 0.24 if lidx in (1, 2) else 0.06
            a_end = 1.5 * math.pi - gap_ang - tear_shift
            op, ip = [], []
            for i in range(n_arc):
                ang = a_start + (i / (n_arc - 1)) * (a_end - a_start)
                ca, sa = math.cos(ang), math.sin(ang)
                op.append((rx * ca, 0.010 * s + ry * sa, cz))
                ip.append(((rx - thick) * ca, 0.010 * s + (ry - thick) * sa, cz))
            rings.append(op + list(reversed(ip)))
        verts.extend(loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_idx["Mat_ZHazmatYellow"]))
        verts.extend(add_box(
            bm,
            center=(0.0, 0.012 * s, 1.800 * s),
            size=(0.078 * s * x_mul, 0.118 * s, 0.018 * s),
            taper_top=(0.52, 0.62),
            mat_idx=mat_idx["Mat_ZHazmatYellow"],
        ))
        verts.extend(add_box(
            bm,
            center=(0.0, 0.014 * s, 1.810 * s),
            size=(0.014 * s, 0.105 * s, 0.007 * s),
            taper_top=(0.70, 0.70),
            mat_idx=mat_idx["Mat_ZHazmatTrim"],
        ))

    return verts


def build_zombie_head(
    bm,
    mat_idx,
    regions,
    proportions=None,
    gender="male",
    skin_mat="Mat_ZSkinGreen",
    hair_mat="Mat_HairBlack",
    headgear="messy_patchy",
    jaw_open=0.017,
    gaunt=0.80,
    head_scale_xy=1.0,
    asym_wound="none",
    blood_chin=True,
    dark_tears=False,
    neck_sac=False,
    boomer_blisters=False,
):
    """Build detailed Loomis/Asaro faceted faceless horror zombie head (zero eyeballs, deep orbital pits)."""
    s = proportions["scale"] if proportions is not None else 1.0
    is_fem = (gender == "female")
    x_mul = (0.89 if is_fem else 1.0) * head_scale_xy
    jaw_dz = max(0.006, min(0.028, jaw_open))

    # Predatory low scowling brow + gaunt sunken cheeks + open jaw
    brow_y = (-0.095 if is_fem else -0.107) - 0.002 * gaunt
    nose_y = -0.109 if is_fem else -0.120
    nose_z = 1.627 if is_fem else 1.622
    chin_y = (-0.088 if is_fem else -0.100) + 0.004

    mid_coords = {
        "m_crown":      (0.0,  0.020, 1.790),
        "m_fore_top":   (0.0, -0.056, 1.758),
        "m_fore_mid":   (0.0, -0.084 if is_fem else -0.088, 1.720),
        "m_brow":       (0.0,  brow_y, 1.673),
        "m_bridge":     (0.0, -0.090 if is_fem else -0.092, 1.658),
        "m_nose_tip":   (0.0,  nose_y, nose_z),
        "m_nose_base":  (0.0, -0.098 if is_fem else -0.100, 1.613 if is_fem else 1.610),
        "m_philtrum":   (0.0, -0.097 if is_fem else -0.098, 1.602 if is_fem else 1.600),
        "m_lip_up":     (0.0, -0.106 if is_fem else -0.104, 1.594 if is_fem else 1.592),
        "m_mouth_up":   (0.0, -0.090, 1.590),
        "m_mouth_cav":  (0.0, -0.066, 1.585 - 0.50 * jaw_dz),
        "m_mouth_lo":   (0.0, -0.090, 1.580 - jaw_dz),
        "m_lip_lo":     (0.0, (-0.102 if is_fem else -0.100), (1.576 if is_fem else 1.578) - jaw_dz),
        "m_chin_cleft": (0.0, (-0.086 if is_fem else -0.088), 1.568 - jaw_dz),
        "m_chin":       (0.0,  chin_y, (1.555 if is_fem else 1.553) - jaw_dz),
        "m_chin_under": (0.0, -0.066, 1.542 - 0.85 * jaw_dz),
        "m_throat":     (0.0, -0.036, 1.520 - 0.25 * jaw_dz),
        "m_neck_front": (0.0, -0.036 if is_fem else -0.042, 1.465),
        "m_neck_back":  (0.0,  0.046 if is_fem else 0.056, 1.465),
        "m_nape":       (0.0,  0.050 if is_fem else 0.056, 1.545),
        "m_occ_low":    (0.0,  0.086, 1.605),
        "m_occ_mid":    (0.0,  0.102, 1.668),
        "m_occ_top":    (0.0,  0.084, 1.738),
    }

    jaw_w = (0.046 if is_fem else 0.064) * head_scale_xy
    chin_w = (0.013 if is_fem else 0.023) * head_scale_xy
    neck_mul = (0.72 if is_fem else 1.0) * (1.0 + 0.45 * (head_scale_xy - 1.0))
    eye_rec = 0.011 * gaunt + 0.005
    hol_in_y = 0.011 * gaunt
    hol_in_x = 0.006 * gaunt

    side_coords = {
        "s_fore_top":   (0.052 * x_mul, -0.044, 1.752),
        "s_fore_mid":   (0.048 * x_mul, -0.074 if is_fem else -0.076, 1.716),
        "s_temple_top": (0.072 * x_mul, -0.012, 1.738),
        "s_temple":     (0.068 * x_mul - 0.003 * gaunt, -0.036, 1.682),
        "s_temple_low": (0.070 * x_mul, -0.018, 1.652),

        "s_brow_in":    (0.022 * x_mul, brow_y, 1.674),
        "s_brow_out":   (0.052 * x_mul, (-0.084 if is_fem else -0.088) - 0.002 * gaunt, 1.675),
        "s_eye_in":     (0.016 * x_mul, -0.078 + eye_rec, 1.657),
        "s_eye_top":    (0.034 * x_mul, -0.074 + eye_rec, 1.662),
        "s_eye_bot":    (0.034 * x_mul, -0.079 + eye_rec, 1.647),
        "s_eye_out":    (0.054 * x_mul, -0.070 + eye_rec, 1.654),

        "s_nose_side":  (0.0085 if is_fem else 0.011, -0.095 if is_fem else -0.098, 1.630),
        "s_nose_wing":  (0.012 if is_fem else 0.016, -0.094 if is_fem else -0.096, 1.613),
        "s_cheek_in":   (0.042 * x_mul, -0.078, 1.634),
        "s_cheek_bone": ((0.072 + 0.003 * gaunt) * x_mul, -0.046, 1.638 if is_fem else 1.635),
        "s_cheek_hol":  ((0.054 - hol_in_x) * x_mul, (-0.054 if is_fem else -0.046) + hol_in_y, 1.598),

        "s_lip_up":     (0.014 if is_fem else 0.016, -0.096, 1.593),
        "s_mouth_cor":  (0.021 if is_fem else 0.023, -0.086, 1.586 - 0.35 * jaw_dz),
        "s_lip_lo":     (0.014 if is_fem else 0.015, -0.093, 1.577 - jaw_dz),
        "s_chin_side":  (chin_w, (-0.082 if is_fem else -0.086), 1.556 - jaw_dz),
        "s_jaw_mid":    ((0.039 if is_fem else 0.045) * x_mul, -0.042, (1.564 if is_fem else 1.556) - 0.65 * jaw_dz),
        "s_jaw_cor":    (jaw_w,  0.008, 1.584 if is_fem else 1.578),
        "s_jaw_under":  ((0.036 if is_fem else 0.042) * x_mul, -0.034, (1.538 if is_fem else 1.534) - 0.55 * jaw_dz),

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

    lip_m = "Mat_ZLipDead"
    chin_m = "Mat_ZBloodDried" if blood_chin else lip_m
    jaw_m = skin_mat
    scalp_m = skin_mat if headgear in ("juggernaut_scarred", "boomer_bloated", "hazmat_torn") else hair_mat

    tris_half = [
        ("m_crown", "s_fore_top", "m_fore_top", scalp_m),
        ("m_crown", "s_temple_top", "s_fore_top", scalp_m),
        ("m_crown", "s_occ_top_s", "s_temple_top", scalp_m),
        ("m_crown", "m_occ_top", "s_occ_top_s", scalp_m),

        ("m_fore_top", "s_fore_top", "s_fore_mid", skin_mat),
        ("m_fore_top", "s_fore_mid", "m_fore_mid", skin_mat),
        ("s_fore_top", "s_temple_top", "s_temple", scalp_m),
        ("s_fore_top", "s_temple", "s_fore_mid", skin_mat),

        ("m_fore_mid", "s_fore_mid", "s_brow_in", skin_mat),
        ("m_fore_mid", "s_brow_in", "m_brow", skin_mat),
        ("s_fore_mid", "s_brow_out", "s_brow_in", skin_mat),
        ("s_fore_mid", "s_temple", "s_brow_out", skin_mat),
        ("s_temple", "s_temple_low", "s_brow_out", skin_mat),
        ("s_brow_out", "s_temple_low", "s_eye_out", "Mat_ZSkinDark"),

        # Deep faceless hollow orbital sockets (zero eyeballs)
        ("m_brow", "s_brow_in", "s_eye_in", "Mat_ZSkinDark"),
        ("m_brow", "s_eye_in", "m_bridge", skin_mat),
        ("s_brow_in", "s_eye_top", "s_eye_in", "Mat_ZSocket"),
        ("s_brow_in", "s_brow_out", "s_eye_top", "Mat_ZSocket"),
        ("s_brow_out", "s_eye_out", "s_eye_top", "Mat_ZSocket"),
        ("s_eye_in", "s_eye_top", "s_eye_bot", "Mat_ZSocket"),
        ("s_eye_top", "s_eye_out", "s_eye_bot", "Mat_ZSocket"),

        ("m_bridge", "s_eye_in", "s_nose_side", skin_mat),
        ("m_bridge", "s_nose_side", "m_nose_tip", skin_mat),
        ("s_eye_in", "s_eye_bot", "s_cheek_in", "Mat_ZSkinDark"),
        ("s_eye_in", "s_cheek_in", "s_nose_side", skin_mat),
        ("s_eye_bot", "s_eye_out", "s_cheek_in", "Mat_ZSkinDark"),
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
        ("s_nose_wing", "s_lip_up", "m_philtrum", skin_mat),

        # Open snarling mouth + inner throat cavity
        ("m_philtrum", "s_lip_up", "m_lip_up", lip_m),
        ("m_lip_up", "s_lip_up", "s_mouth_cor", lip_m),
        ("m_lip_up", "s_mouth_cor", "m_mouth_up", lip_m),
        ("m_mouth_up", "s_mouth_cor", "m_mouth_cav", "Mat_ZMouth"),
        ("m_mouth_cav", "s_mouth_cor", "m_mouth_lo", "Mat_ZMouth"),
        ("m_mouth_lo", "s_mouth_cor", "s_lip_lo", lip_m),
        ("m_mouth_lo", "s_lip_lo", "m_lip_lo", lip_m),

        ("m_lip_lo", "s_lip_lo", "s_chin_side", chin_m),
        ("m_lip_lo", "s_chin_side", "m_chin_cleft", chin_m),
        ("m_chin_cleft", "s_chin_side", "m_chin", chin_m),
        ("s_lip_lo", "s_mouth_cor", "s_chin_side", chin_m if blood_chin else jaw_m),
        ("s_mouth_cor", "s_cheek_hol", "s_jaw_mid", jaw_m),
        ("s_mouth_cor", "s_jaw_mid", "s_chin_side", jaw_m),
        ("s_cheek_hol", "s_cheek_bone", "s_jaw_cor", skin_mat),
        ("s_cheek_hol", "s_jaw_cor", "s_jaw_mid", jaw_m),
        ("s_cheek_bone", "s_temple_low", "s_ear_base", skin_mat),
        ("s_cheek_bone", "s_ear_base", "s_jaw_cor", skin_mat),

        ("m_chin", "s_chin_side", "s_jaw_under", chin_m if blood_chin else jaw_m),
        ("m_chin", "s_jaw_under", "m_chin_under", chin_m if blood_chin else jaw_m),
        ("s_chin_side", "s_jaw_mid", "s_jaw_under", jaw_m),
        ("s_jaw_mid", "s_jaw_cor", "s_jaw_under", jaw_m),
        ("m_chin_under", "s_jaw_under", "m_throat", "Mat_ZBloodDried" if blood_chin else skin_mat),
        ("s_jaw_under", "s_jaw_cor", "s_mastoid", skin_mat),
        ("s_jaw_under", "s_mastoid", "s_nape_side", skin_mat),
        ("m_throat", "s_jaw_under", "s_neck_front", skin_mat),
        ("m_throat", "s_neck_front", "m_neck_front", "Mat_ZBloodDried" if blood_chin else skin_mat),
        ("s_jaw_under", "s_nape_side", "s_neck_side", skin_mat),
        ("s_jaw_under", "s_neck_side", "s_neck_front", skin_mat),
        ("s_nape_side", "s_neck_back", "s_neck_side", skin_mat),
        ("s_nape_side", "m_nape", "s_neck_back", skin_mat),
        ("m_nape", "m_neck_back", "s_neck_back", skin_mat),

        ("m_neck_front", "s_neck_front", "s_neck_side", skin_mat),
        ("m_neck_front", "s_neck_side", "s_neck_back", skin_mat),
        ("m_neck_front", "s_neck_back", "m_neck_back", skin_mat),

        ("s_temple_low", "s_temple_top", "s_side_skull", scalp_m),
        ("s_temple_low", "s_side_skull", "s_ear_base", scalp_m),
        ("s_temple_top", "s_occ_top_s", "s_side_skull", scalp_m),
        ("s_ear_base", "s_side_skull", "s_mastoid", scalp_m),
        ("s_ear_base", "s_mastoid", "s_jaw_cor", skin_mat),
        ("s_side_skull", "s_occ_top_s", "s_occ_mid_s", scalp_m),
        ("s_side_skull", "s_occ_mid_s", "s_occ_low_s", scalp_m),
        ("s_side_skull", "s_occ_low_s", "s_mastoid", scalp_m),
        ("s_mastoid", "s_occ_low_s", "s_nape_side", skin_mat),
        ("s_occ_low_s", "m_occ_low", "m_nape", skin_mat),
        ("s_occ_low_s", "m_nape", "s_nape_side", skin_mat),
        ("m_occ_top", "s_occ_mid_s", "s_occ_top_s", scalp_m),
        ("m_occ_top", "m_occ_mid", "s_occ_mid_s", scalp_m),
        ("m_occ_mid", "s_occ_low_s", "s_occ_mid_s", scalp_m),
        ("m_occ_mid", "m_occ_low", "s_occ_low_s", scalp_m),
    ]

    def _override_mat(side, a, b, c, mname):
        key = frozenset((a, b, c))
        if dark_tears:
            if "s_eye_in" in key and "s_eye_bot" in key and "s_cheek_in" in key:
                return "Mat_ZSocket"
            if "s_eye_bot" in key and "s_eye_out" in key and "s_cheek_in" in key:
                return "Mat_ZBloodDried"
        if asym_wound == "cheek_r" and side == "R":
            if "s_cheek_hol" in key and ("s_mouth_cor" in key or "s_jaw_mid" in key):
                return "Mat_ZFlesh"
            if "s_mouth_cor" in key and "s_jaw_mid" in key and "s_chin_side" in key:
                return "Mat_ZBloodDried"
            if "s_cheek_hol" in key and "s_nose_wing" in key:
                return "Mat_ZBloodDried"
        elif asym_wound == "cheek_l_blood" and side == "L":
            if any(k in key for k in ("s_mouth_cor", "s_chin_side", "s_lip_lo")):
                return "Mat_ZBloodFresh"
            if "s_cheek_hol" in key and "s_jaw_mid" in key:
                return "Mat_ZBloodDried"
        elif asym_wound == "brow_scar" and side == "L":
            if "s_fore_mid" in key and ("s_brow_in" in key or "s_brow_out" in key):
                return "Mat_ZFlesh"
            if "m_fore_mid" in key and "s_fore_mid" in key and "s_brow_in" in key:
                return "Mat_ZBone"
        elif asym_wound == "toxic_boils" and side == "L":
            if "s_cheek_hol" in key and "s_jaw_mid" in key:
                return "Mat_ZSkinDark"
            if "m_throat" in key and "s_neck_front" in key:
                return "Mat_ZSkinDark"
        return mname

    created_faces = []
    for a, b, c, mname in tris_half:
        vl = [verts_mid[n] if n.startswith("m_") else verts_l[n] for n in (a, b, c)]
        fl = bm.faces.new(vl)
        fl.material_index = mat_idx[_override_mat("L", a, b, c, mname)]
        created_faces.append(fl)

        vr = [verts_mid[n] if n.startswith("m_") else verts_r[n] for n in (a, c, b)]
        fr = bm.faces.new(vr)
        fr.material_index = mat_idx[_override_mat("R", a, b, c, mname)]
        created_faces.append(fr)

    bmesh.ops.recalc_face_normals(bm, faces=created_faces)

    # Keep chin strictly attached to Head even when jaw_open lowers m_chin_under below 1.528*s
    neck_keys = {"m_throat", "m_neck_front", "m_neck_back", "m_nape",
                 "s_neck_front", "s_neck_side", "s_neck_back", "s_nape_side"}
    neck_verts = []
    head_verts = []
    for k, v in verts_mid.items():
        (neck_verts if k in neck_keys else head_verts).append(v)
    for k, v in list(verts_l.items()) + list(verts_r.items()):
        (neck_verts if k in neck_keys else head_verts).append(v)

    # Faceless horror: ZERO eyeballs — only jagged fangs inside deep mouth cavity
    head_verts.extend(_add_jagged_teeth(
        bm, mat_idx, s, x_mul, jaw_dz,
        missing_right=(asym_wound == "cheek_r"),
    ))

    if asym_wound == "cheek_r":
        for k in range(3):
            head_verts.extend(add_box(
                bm,
                center=(-(0.025 + k * 0.0065) * s * x_mul, (-0.072 + k * 0.008) * s, (1.584 - 0.3 * jaw_dz) * s),
                size=(0.0045 * s, 0.0055 * s, 0.0075 * s),
                rot=(0.0, 0.0, 0.35),
                mat_idx=mat_idx["Mat_ZBone"],
            ))
    elif asym_wound == "toxic_boils":
        for pos, rad, bmat in (
            (( 0.044, -0.056, 1.608), 0.011, "Mat_ZAcidGlow"),
            (( 0.052, -0.042, 1.592), 0.009, "Mat_ZBoilDark"),
            (( 0.036, -0.068, 1.576), 0.008, "Mat_ZAcidGlow"),
            ((-0.042, -0.048, 1.552), 0.010, "Mat_ZAcidGlow"),
        ):
            head_verts.extend(add_box(
                bm,
                center=(pos[0] * s * x_mul, pos[1] * s, pos[2] * s),
                size=(rad * s, rad * s, rad * s),
                rot=(0.35, 0.45, 0.25),
                bevel=rad * 0.22 * s,
                mat_idx=mat_idx[bmat],
            ))

    if boomer_blisters:
        for pos, rad, bmat in (
            (( 0.048, -0.056, 1.622), 0.015, "Mat_ZBoilDark"),
            (( 0.058, -0.044, 1.602), 0.013, "Mat_ZBoilGlow"),
            (( 0.042, -0.064, 1.582), 0.011, "Mat_ZBoilGlow"),
            ((-0.050, -0.046, 1.628), 0.013, "Mat_ZBoilDark"),
        ):
            head_verts.extend(add_box(
                bm,
                center=(pos[0] * s * x_mul, pos[1] * s, pos[2] * s),
                size=(rad * s, rad * s, rad * s),
                rot=(0.30, 0.40, 0.20),
                bevel=rad * 0.24 * s,
                mat_idx=mat_idx[bmat],
            ))

    if neck_sac:
        neck_verts.extend(_add_neck_bile_sac(bm, mat_idx, s, x_mul))

    # Sculpted C-shaped ears (matching human survivor style)
    head_verts.extend(_build_ear(bm, mat_idx, 1.0, s=s, skin_mat=skin_mat, x_mul=x_mul))
    head_verts.extend(_build_ear(bm, mat_idx, -1.0, s=s, skin_mat=skin_mat, x_mul=x_mul))

    head_verts.extend(_add_zombie_headgear(bm, mat_idx, s, x_mul, headgear, hair_mat))

    regions.setdefault("neck", []).extend(neck_verts)
    regions.setdefault("head", []).extend(head_verts)
