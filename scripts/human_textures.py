"""Seamless 256x256 procedural PBR textures for Survivors, Zombies & Weapons.

Generates shared Roughness + Normal maps per surface class (deduplicated across materials in glTF)
and per-material BaseColor maps tinted around each palette color, blended with baked Vertex AO ('Col').
"""
import bpy
import numpy as np

from mutant_textures import (
    _c,
    _domain_warp,
    _height_to_normal_rgba,
    _mix,
    _periodic_fbm,
    _periodic_value_noise,
    _periodic_voronoi,
)

HUMAN_TEX_SIZE = 256
_SURFACE_CACHE = {}
_ALBEDO_CACHE = {}


def _ensure_packed_human_image(name, rgba_2d, colorspace="sRGB"):
    img = bpy.data.images.get(name)
    if img is None or img.size[0] != HUMAN_TEX_SIZE or img.size[1] != HUMAN_TEX_SIZE:
        if img is not None:
            bpy.data.images.remove(img)
        img = bpy.data.images.new(
            name=name,
            width=HUMAN_TEX_SIZE,
            height=HUMAN_TEX_SIZE,
            alpha=False,
            float_buffer=False,
        )
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(rgba_2d.ravel())
    img.pack()
    return img


def _build_surface_maps(surf_class):
    """Build cached 256x256 micro-height, roughness & normal maps shared per material surface class."""
    if surf_class in _SURFACE_CACHE:
        return _SURFACE_CACHE[surf_class]

    n = HUMAN_TEX_SIZE
    lin = np.linspace(0.0, 1.0, n, endpoint=False, dtype=np.float32)
    gy, gx = np.meshgrid(lin, lin, indexing="ij")

    if surf_class == "fabric_tactical":
        fbm_fold = _periodic_fbm(n, 5, seed=601)
        fine_grain = _periodic_value_noise(n, 96, seed=605)
        wx = _periodic_fbm(n, 3, seed=607)
        wy = _periodic_fbm(n, 3, seed=613)
        crease = _domain_warp(np.sin((gy * 2.5 + fbm_fold * 0.6) * 2.0 * np.pi) * 0.5 + 0.5, wx, wy, 7.0)
        detail = 0.88 * fbm_fold + 0.12 * fine_grain
        height = np.clip(0.50 * fbm_fold + 0.35 * crease + 0.15 * fine_grain, 0.0, 1.0)
        rough_map = np.clip(0.80 + 0.10 * fine_grain - 0.08 * fbm_fold, 0.72, 0.94)
        norm_rgba = _height_to_normal_rgba(height, strength=1.35)
        extra = {"crease": crease, "fbm": fbm_fold}

    elif surf_class == "fabric_denim":
        fbm_wear = _periodic_fbm(n, 5, seed=621)
        fine_grain = _periodic_value_noise(n, 96, seed=625)
        detail = 0.85 * fbm_wear + 0.15 * fine_grain
        height = np.clip(detail, 0.0, 1.0)
        rough_map = np.clip(0.82 + 0.09 * fine_grain - 0.08 * fbm_wear, 0.74, 0.94)
        norm_rgba = _height_to_normal_rgba(height, strength=1.50)
        extra = {"fbm": fbm_wear}

    elif surf_class == "fabric_flannel":
        fbm_soft = _periodic_fbm(n, 5, seed=631)
        fine_grain = _periodic_value_noise(n, 88, seed=635)
        bx = 0.5 + 0.5 * np.cos(gx * 4.0 * np.pi)
        by = 0.5 + 0.5 * np.cos(gy * 4.0 * np.pi)
        fx = np.exp(-((np.sin(gx * 2.0 * np.pi)) ** 2) * 18.0)
        fy = np.exp(-((np.sin(gy * 2.0 * np.pi)) ** 2) * 18.0)
        plaid_dark = np.clip(0.42 * bx + 0.42 * by - 0.28 * (bx * by), 0.0, 1.0)
        plaid_stripe = np.clip(fx + fy, 0.0, 1.0)
        detail = 0.84 * fbm_soft + 0.16 * fine_grain
        height = np.clip(detail, 0.0, 1.0)
        rough_map = np.clip(0.84 + 0.08 * fine_grain, 0.78, 0.95)
        norm_rgba = _height_to_normal_rgba(height, strength=1.20)
        extra = {"plaid_dark": plaid_dark, "plaid_stripe": plaid_stripe, "fbm": fbm_soft}

    elif surf_class == "zcloth_grime":
        fbm_a = _periodic_fbm(n, 5, seed=641)
        fbm_b = _periodic_fbm(n, 4, seed=647)
        fine_grain = _periodic_value_noise(n, 96, seed=651)
        wx = _periodic_fbm(n, 3, seed=653)
        wy = _periodic_fbm(n, 3, seed=659)
        stain = _domain_warp(np.clip((fbm_a - 0.56) * 2.4, 0.0, 1.0), wx, wy, 7.0)
        blood = _domain_warp(np.clip((fbm_b - 0.70) * 3.2, 0.0, 1.0), wy, wx, 6.0)
        detail = 0.86 * fbm_a + 0.14 * fine_grain
        height = np.clip(0.55 * fbm_a + 0.30 * fbm_b + 0.15 * fine_grain, 0.0, 1.0)
        rough_map = np.clip(0.84 + 0.08 * fine_grain - 0.24 * blood + 0.06 * stain, 0.52, 0.96)
        norm_rgba = _height_to_normal_rgba(height, strength=1.80)
        extra = {"stain": stain, "blood": blood, "fbm": fbm_a}

    elif surf_class == "human_skin":
        fbm_a = _periodic_fbm(n, 4, seed=661)
        pores, _, _ = _periodic_voronoi(n, 48, seed=667)
        detail = 0.65 * fbm_a + 0.35 * pores
        height = np.clip(0.65 * fbm_a + 0.35 * pores, 0.0, 1.0)
        rough_map = np.clip(0.66 + 0.10 * fbm_a + 0.04 * (1.0 - pores), 0.58, 0.78)
        norm_rgba = _height_to_normal_rgba(height, strength=1.1)
        extra = {"fbm": fbm_a, "pores": pores}

    elif surf_class == "zombie_skin":
        fbm_a = _periodic_fbm(n, 5, seed=673)
        fbm_b = _periodic_fbm(n, 4, seed=677)
        wx = _periodic_fbm(n, 3, seed=683)
        wy = _periodic_fbm(n, 3, seed=691)
        vein = np.exp(-np.abs(_domain_warp(fbm_a - 0.5, wx, wy, 9.0)) * 18.0)
        mottle = np.clip((fbm_b - 0.52) * 2.2, 0.0, 1.0)
        pores, _, _ = _periodic_voronoi(n, 56, seed=701)
        pit = np.clip(1.0 - pores * 2.4, 0.0, 1.0)
        detail = 0.60 * fbm_a + 0.40 * fbm_b
        height = np.clip(0.50 * fbm_a + 0.30 * fbm_b + 0.25 * vein - 0.22 * pit, 0.0, 1.0)
        rough_map = np.clip(0.62 + 0.16 * fbm_a - 0.14 * vein + 0.10 * pit, 0.44, 0.84)
        norm_rgba = _height_to_normal_rgba(height, strength=3.4)
        extra = {"vein": vein, "mottle": mottle, "pit": pit, "fbm": fbm_b}

    elif surf_class == "hair_strand":
        fbm_a = _periodic_fbm(n, 4, seed=709)
        strand = 0.5 + 0.5 * np.sin((gx * 26.0 + fbm_a * 2.2) * np.pi)
        strand2 = 0.5 + 0.5 * np.sin((gx * 54.0 + fbm_a * 3.0) * np.pi)
        detail = 0.55 * strand + 0.25 * strand2 + 0.20 * fbm_a
        height = np.clip(0.55 * strand + 0.30 * strand2 + 0.15 * fbm_a, 0.0, 1.0)
        rough_map = np.clip(0.76 + 0.14 * (1.0 - strand) + 0.06 * fbm_a, 0.66, 0.92)
        norm_rgba = _height_to_normal_rgba(height, strength=2.8)
        extra = {"strand": strand, "fbm": fbm_a}

    elif surf_class == "leather_worn":
        fbm_a = _periodic_fbm(n, 4, seed=719)
        f1, edge, _ = _periodic_voronoi(n, 38, seed=727)
        grain = np.clip(1.0 - f1 * 1.4, 0.0, 1.0)
        scuff = np.clip((fbm_a - 0.62) * 2.4, 0.0, 1.0)
        detail = 0.55 * grain + 0.45 * fbm_a
        height = np.clip(0.50 * grain + 0.35 * fbm_a + 0.15 * edge, 0.0, 1.0)
        rough_map = np.clip(0.58 + 0.18 * scuff - 0.10 * grain, 0.48, 0.78)
        norm_rgba = _height_to_normal_rgba(height, strength=2.7)
        extra = {"scuff": scuff, "grain": grain, "fbm": fbm_a}

    elif surf_class == "metal_brushed":
        fbm_a = _periodic_fbm(n, 5, seed=733)
        fine = _periodic_value_noise(n, 96, seed=739)
        streak_h = 0.5 * _periodic_value_noise(n, 96, seed=741) + 0.5 * np.roll(fine, 4, axis=1)
        scratch = np.clip((fbm_a - 0.68) * 2.6, 0.0, 1.0)
        detail = 0.68 * fbm_a + 0.32 * streak_h
        height = np.clip(0.60 * fbm_a + 0.25 * streak_h + 0.15 * scratch, 0.0, 1.0)
        rough_map = np.clip(0.30 + 0.16 * fbm_a - 0.08 * scratch, 0.22, 0.50)
        norm_rgba = _height_to_normal_rgba(height, strength=1.10)
        extra = {"scratch": scratch, "fbm": fbm_a}

    elif surf_class == "metal_rusted":
        fbm_a = _periodic_fbm(n, 5, seed=743)
        fbm_b = _periodic_fbm(n, 4, seed=751)
        pores, _, _ = _periodic_voronoi(n, 40, seed=757)
        rust = np.clip((fbm_a - 0.46) * 2.0, 0.0, 1.0)
        pit = np.clip(1.0 - pores * 2.2, 0.0, 1.0)
        detail = 0.55 * fbm_a + 0.45 * fbm_b
        height = np.clip(0.55 * fbm_a + 0.35 * fbm_b - 0.35 * pit, 0.0, 1.0)
        rough_map = np.clip(0.44 + 0.34 * rust + 0.14 * pit, 0.38, 0.86)
        norm_rgba = _height_to_normal_rgba(height, strength=3.4)
        extra = {"rust": rust, "pit": pit, "fbm": fbm_b}

    elif surf_class == "polymer_grip":
        fbm_a = _periodic_fbm(n, 4, seed=761)
        stipple = _periodic_value_noise(n, 112, seed=763)
        detail = 0.65 * fbm_a + 0.35 * stipple
        height = np.clip(detail, 0.0, 1.0)
        rough_map = np.clip(0.66 + 0.14 * stipple - 0.08 * fbm_a, 0.56, 0.84)
        norm_rgba = _height_to_normal_rgba(height, strength=1.30)
        extra = {"fbm": fbm_a}

    elif surf_class == "wood_grain":
        fbm_a = _periodic_fbm(n, 4, seed=769)
        ring = 0.5 + 0.5 * np.sin((gy * 12.0 + np.sin(gx * 2.0 * np.pi) * 0.4 + fbm_a * 2.6) * np.pi)
        detail = 0.65 * ring + 0.35 * fbm_a
        height = np.clip(0.60 * ring + 0.40 * fbm_a, 0.0, 1.0)
        rough_map = np.clip(0.64 + 0.14 * (1.0 - ring), 0.54, 0.80)
        norm_rgba = _height_to_normal_rgba(height, strength=2.5)
        extra = {"ring": ring, "fbm": fbm_a}

    elif surf_class == "gore_wet":
        fbm_a = _periodic_fbm(n, 5, seed=773)
        fbm_b = _periodic_fbm(n, 4, seed=787)
        wx = _periodic_fbm(n, 3, seed=797)
        wy = _periodic_fbm(n, 3, seed=809)
        streak = np.exp(-np.abs(_domain_warp(fbm_a - 0.5, wx, wy, 9.0)) * 16.0)
        detail = 0.55 * fbm_a + 0.45 * fbm_b
        height = np.clip(0.52 * fbm_a + 0.28 * fbm_b + 0.22 * streak, 0.0, 1.0)
        rough_map = np.clip(0.24 + 0.22 * (1.0 - fbm_b) - 0.10 * streak, 0.14, 0.52)
        norm_rgba = _height_to_normal_rgba(height, strength=3.2)
        extra = {"streak": streak, "fbm": fbm_b}

    else:  # bone_worn
        fbm_a = _periodic_fbm(n, 4, seed=811)
        fine = _periodic_value_noise(n, 32, seed=821)
        detail = 0.60 * fbm_a + 0.40 * fine
        height = np.clip(0.60 * fbm_a + 0.40 * fine, 0.0, 1.0)
        rough_map = np.clip(0.54 + 0.18 * (1.0 - fbm_a), 0.44, 0.76)
        norm_rgba = _height_to_normal_rgba(height, strength=2.9)
        extra = {"fbm": fbm_a, "fine": fine}

    rough_rgba = np.empty((n, n, 4), dtype=np.float32)
    rough_rgba[..., 0] = rough_map
    rough_rgba[..., 1] = rough_map
    rough_rgba[..., 2] = rough_map
    rough_rgba[..., 3] = 1.0

    surf_data = {
        "detail": detail,
        "extra": extra,
        "rough_rgba": np.ascontiguousarray(rough_rgba, dtype=np.float32),
        "norm_rgba": np.ascontiguousarray(norm_rgba, dtype=np.float32),
    }
    _SURFACE_CACHE[surf_class] = surf_data
    return surf_data


def _build_material_albedo(surf_class, mat_name, base_hex):
    cache_key = (surf_class, mat_name, base_hex)
    if cache_key in _ALBEDO_CACHE:
        return _ALBEDO_CACHE[cache_key]

    n = HUMAN_TEX_SIZE
    surf = _build_surface_maps(surf_class)
    base_rgb = _c(base_hex)
    ex = surf["extra"]
    det = surf["detail"]

    if surf_class == "fabric_tactical":
        rgb = base_rgb * (0.91 + 0.14 * det[..., None])
        rgb = _mix(rgb, base_rgb * 0.82 + _c("#1E1D1A") * 0.18, (1.0 - ex["crease"]) * 0.18)

    elif surf_class == "fabric_denim":
        rgb = base_rgb * (0.88 + 0.18 * det[..., None])
        fade = np.clip((ex["fbm"] - 0.55) * 2.2, 0.0, 1.0)
        rgb = _mix(rgb, np.minimum(1.0, base_rgb * 1.20 + 0.04), fade * 0.30)

    elif surf_class == "fabric_flannel":
        rgb = base_rgb * (0.92 + 0.12 * det[..., None])
        rgb = _mix(rgb, base_rgb * 0.42 + _c("#161010") * 0.58, ex["plaid_dark"] * 0.58)
        rgb = _mix(rgb, base_rgb * 1.15 + _c("#E8DDD2") * 0.12, ex["plaid_stripe"] * 0.28)

    elif surf_class == "zcloth_grime":
        rgb = base_rgb * (0.88 + 0.18 * det[..., None])
        rgb = _mix(rgb, _c("#241F1A"), ex["stain"] * 0.50)
        rgb = _mix(rgb, _c("#421010"), ex["blood"] * 0.46)

    elif surf_class == "human_skin":
        rgb = base_rgb * (0.94 + 0.10 * det[..., None])

    elif surf_class == "zombie_skin":
        rgb = base_rgb * (0.84 + 0.26 * det[..., None])
        rgb = _mix(rgb, base_rgb * 0.65 + _c("#4E4246") * 0.35, ex["mottle"] * 0.46)
        rgb = _mix(rgb, _c("#281D26"), np.clip(ex["vein"] * 0.68 + ex["pit"] * 0.35, 0.0, 1.0))

    elif surf_class == "hair_strand":
        rgb = base_rgb * (0.82 + 0.32 * ex["strand"][..., None])

    elif surf_class == "leather_worn":
        rgb = base_rgb * (0.86 + 0.22 * det[..., None])
        rgb = _mix(rgb, np.minimum(1.0, base_rgb * 1.28 + 0.04), ex["scuff"] * 0.40)

    elif surf_class == "metal_brushed":
        rgb = base_rgb * (0.91 + 0.14 * det[..., None])
        rgb = _mix(rgb, np.minimum(1.0, base_rgb * 1.22 + 0.04), ex["scratch"] * 0.24)

    elif surf_class == "metal_rusted":
        rgb = base_rgb * (0.84 + 0.24 * det[..., None])
        rgb = _mix(rgb, _c("#682E1B"), ex["rust"] * 0.55)
        rgb = _mix(rgb, _c("#1E1815"), ex["pit"] * 0.42)

    elif surf_class == "polymer_grip":
        rgb = base_rgb * (0.91 + 0.14 * det[..., None])

    elif surf_class == "wood_grain":
        rgb = base_rgb * (0.80 + 0.34 * det[..., None])

    elif surf_class == "gore_wet":
        rgb = base_rgb * (0.76 + 0.36 * det[..., None])
        rgb = _mix(rgb, np.minimum(1.0, base_rgb * 1.32 + _c("#240404")), ex["streak"] * 0.42)

    else:  # bone_worn
        rgb = base_rgb * (0.86 + 0.24 * det[..., None])
        stain = np.clip((ex["fbm"] - 0.66) * 2.5, 0.0, 1.0)
        rgb = _mix(rgb, _c("#584232"), stain * 0.40)

    albedo_rgba = np.empty((n, n, 4), dtype=np.float32)
    albedo_rgba[..., :3] = np.clip(rgb, 0.0, 1.0)
    albedo_rgba[..., 3] = 1.0
    out = np.ascontiguousarray(albedo_rgba, dtype=np.float32)
    _ALBEDO_CACHE[cache_key] = out
    return out


# Map every non-emissive, non-glass human/zombie/weapon material to (surf_class, norm_strength, spec_ior, sss_w)
HUMAN_MAT_TEX_MAP = {
    # Skin & Hair
    "Mat_Skin":         ("human_skin",      0.28, 0.34, 0.14),
    "Mat_SkinLight":    ("human_skin",      0.28, 0.34, 0.14),
    "Mat_SkinWarm":     ("human_skin",      0.28, 0.34, 0.14),
    "Mat_SkinTan":      ("human_skin",      0.28, 0.34, 0.14),
    "Mat_SkinMed":      ("human_skin",      0.28, 0.34, 0.14),
    "Mat_Lip":          ("human_skin",      0.24, 0.38, 0.14),
    "Mat_LipWarm":      ("human_skin",      0.24, 0.42, 0.14),
    "Mat_Stubble":      ("human_skin",      0.38, 0.28, 0.10),
    "Mat_Hair":         ("hair_strand",     0.46, 0.24, 0.00),
    "Mat_HairBlack":    ("hair_strand",     0.46, 0.24, 0.00),
    "Mat_HairBrown":    ("hair_strand",     0.46, 0.24, 0.00),
    "Mat_HairGrey":     ("hair_strand",     0.46, 0.24, 0.00),
    "Mat_Beard":        ("hair_strand",     0.48, 0.22, 0.00),

    # Tactical / Everyday Survivor Apparel
    "Mat_Beanie":       ("fabric_tactical", 0.42, 0.18, 0.00),
    "Mat_Jacket":       ("fabric_tactical", 0.42, 0.20, 0.00),
    "Mat_JacketTrim":   ("fabric_tactical", 0.42, 0.20, 0.00),
    "Mat_Shirt":        ("fabric_tactical", 0.40, 0.18, 0.00),
    "Mat_Pants":        ("fabric_tactical", 0.42, 0.18, 0.00),
    "Mat_Bandage":      ("fabric_tactical", 0.40, 0.18, 0.00),
    "Mat_Backpack":     ("fabric_tactical", 0.46, 0.20, 0.00),
    "Mat_SleepingRoll": ("fabric_tactical", 0.42, 0.18, 0.00),
    "Mat_OliveMil":     ("fabric_tactical", 0.42, 0.20, 0.00),
    "Mat_OliveDark":    ("fabric_tactical", 0.42, 0.20, 0.00),
    "Mat_CoyoteTan":    ("fabric_tactical", 0.42, 0.20, 0.00),
    "Mat_ScrubBlue":    ("fabric_tactical", 0.36, 0.20, 0.00),
    "Mat_ScrubDark":    ("fabric_tactical", 0.38, 0.20, 0.00),
    "Mat_FieldJacket":  ("fabric_tactical", 0.42, 0.20, 0.00),
    "Mat_MedWhite":     ("fabric_tactical", 0.36, 0.20, 0.00),
    "Mat_MedRed":       ("fabric_tactical", 0.38, 0.22, 0.00),
    "Mat_BandanaRed":   ("fabric_tactical", 0.40, 0.20, 0.00),
    "Mat_OilStain":     ("fabric_tactical", 0.42, 0.22, 0.00),
    "Mat_WorkGrey":     ("fabric_tactical", 0.42, 0.20, 0.00),
    "Mat_HoodGreen":    ("fabric_tactical", 0.42, 0.20, 0.00),
    "Mat_ScarfRust":    ("fabric_tactical", 0.42, 0.18, 0.00),
    "Mat_Shearling":    ("fabric_tactical", 0.46, 0.16, 0.00),
    "Mat_VaneRed":      ("fabric_tactical", 0.34, 0.24, 0.00),
    "Mat_ShellRed":     ("fabric_tactical", 0.30, 0.28, 0.00),
    "Mat_DenimBlue":    ("fabric_denim",    0.44, 0.18, 0.00),
    "Mat_FlannelRed":   ("fabric_flannel",  0.38, 0.18, 0.00),
    "Mat_FlannelDark":  ("fabric_flannel",  0.38, 0.18, 0.00),
    "Mat_FlannelCheck": ("fabric_flannel",  0.38, 0.18, 0.00),

    # Leather & Boots
    "Mat_BeltLeather":  ("leather_worn",    0.60, 0.30, 0.00),
    "Mat_Boots":        ("leather_worn",    0.62, 0.30, 0.00),
    "Mat_LeatherDark":  ("leather_worn",    0.60, 0.32, 0.00),
    "Mat_VestLeather":  ("leather_worn",    0.60, 0.30, 0.00),
    "Mat_CowboyBrown":  ("leather_worn",    0.58, 0.28, 0.00),
    "Mat_BootSole":     ("polymer_grip",    0.38, 0.22, 0.00),
    "Mat_KneePad":      ("polymer_grip",    0.36, 0.32, 0.00),
    "Mat_GripTape":     ("polymer_grip",    0.40, 0.20, 0.00),

    # Weapons & Metals
    "Mat_MetalDark":    ("metal_brushed",   0.32, 0.55, 0.00),
    "Mat_GunMetal":     ("metal_brushed",   0.32, 0.58, 0.00),
    "Mat_GunSteel":     ("metal_brushed",   0.30, 0.65, 0.00),
    "Mat_Brass":        ("metal_brushed",   0.30, 0.65, 0.00),
    "Mat_BowCam":       ("metal_brushed",   0.32, 0.58, 0.00),
    "Mat_ZRiotArmor":   ("metal_brushed",   0.36, 0.45, 0.00),
    "Mat_MetalRust":    ("metal_rusted",    0.70, 0.38, 0.00),
    "Mat_ZRebar":       ("metal_rusted",    0.72, 0.40, 0.00),
    "Mat_WrenchRed":    ("metal_rusted",    0.54, 0.42, 0.00),
    "Mat_ToolYellow":   ("metal_rusted",    0.48, 0.36, 0.00),
    "Mat_GunPolymer":   ("polymer_grip",    0.36, 0.30, 0.00),
    "Mat_Carbon":       ("polymer_grip",    0.34, 0.36, 0.00),
    "Mat_WoodBat":      ("wood_grain",      0.56, 0.26, 0.00),
    "Mat_Walnut":       ("wood_grain",      0.52, 0.28, 0.00),

    # Zombie Skins, Grimy Clothes & Trauma
    "Mat_ZSkinGreen":   ("zombie_skin",     0.68, 0.26, 0.14),
    "Mat_ZSkinPale":    ("zombie_skin",     0.66, 0.26, 0.14),
    "Mat_ZSkinGrey":    ("zombie_skin",     0.68, 0.26, 0.14),
    "Mat_ZSkinBruised": ("zombie_skin",     0.72, 0.28, 0.16),
    "Mat_ZSkinToxic":   ("zombie_skin",     0.70, 0.28, 0.14),
    "Mat_ZSkinDark":    ("zombie_skin",     0.70, 0.26, 0.14),
    "Mat_ZLipDead":     ("zombie_skin",     0.64, 0.30, 0.16),
    "Mat_ZVeinDark":    ("zombie_skin",     0.74, 0.28, 0.14),
    "Mat_ZBoilDark":    ("zombie_skin",     0.76, 0.30, 0.14),
    "Mat_ZShirtTorn":   ("zcloth_grime",    0.52, 0.18, 0.00),
    "Mat_ZTieDark":     ("zcloth_grime",    0.50, 0.20, 0.00),
    "Mat_ZClothDirty":  ("zcloth_grime",    0.52, 0.18, 0.00),
    "Mat_ZNurseDress":  ("zcloth_grime",    0.50, 0.18, 0.00),
    "Mat_ZCardigan":    ("zcloth_grime",    0.50, 0.18, 0.00),
    "Mat_ZTrackRed":    ("zcloth_grime",    0.50, 0.20, 0.00),
    "Mat_ZTrackDark":   ("zcloth_grime",    0.50, 0.20, 0.00),
    "Mat_ZRiotNavy":    ("zcloth_grime",    0.48, 0.22, 0.00),
    "Mat_ZHazmatYellow":("zcloth_grime",    0.46, 0.26, 0.00),
    "Mat_ZHazmatTrim":  ("zcloth_grime",    0.46, 0.26, 0.00),
    "Mat_ZShroudDark":  ("zcloth_grime",    0.52, 0.18, 0.00),
    "Mat_ZFlesh":       ("gore_wet",        0.72, 0.42, 0.20),
    "Mat_ZBloodDried":  ("gore_wet",        0.70, 0.34, 0.12),
    "Mat_ZBloodFresh":  ("gore_wet",        0.72, 0.44, 0.22),
    "Mat_ZMouth":       ("gore_wet",        0.64, 0.32, 0.00),
    "Mat_ZSocket":      ("gore_wet",        0.54, 0.22, 0.00),
    "Mat_ZBone":        ("bone_worn",       0.62, 0.28, 0.08),
}


def apply_human_pbr_texture(mat, mat_name, base_hex, base_roughness):
    """Attach 256x256 Albedo x VertexColor('Col'), shared Roughness & Normal onto human/zombie/weapon mats."""
    spec = HUMAN_MAT_TEX_MAP.get(mat_name)
    if spec is None:
        return False

    surf_class, norm_strength, spec_ior, sss_w = spec
    surf = _build_surface_maps(surf_class)
    albedo_rgba = _build_material_albedo(surf_class, mat_name, base_hex)

    slug = mat_name.replace("Mat_", "").lower()
    img_col = _ensure_packed_human_image(f"Tex_H_{slug}_BaseColor", albedo_rgba, colorspace="sRGB")
    img_rgh = _ensure_packed_human_image(f"Tex_H_{surf_class}_Roughness", surf["rough_rgba"], colorspace="Non-Color")
    img_nrm = _ensure_packed_human_image(f"Tex_H_{surf_class}_Normal", surf["norm_rgba"], colorspace="Non-Color")

    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = float(spec_ior)
    if sss_w > 0.0 and "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = float(sss_w)
        if "Subsurface Scale" in bsdf.inputs:
            bsdf.inputs["Subsurface Scale"].default_value = 0.018
        if "Subsurface Radius" in bsdf.inputs:
            bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.32, 0.20)

    tex_col = nt.nodes.new("ShaderNodeTexImage")
    tex_col.image = img_col

    vcol = nt.nodes.new("ShaderNodeVertexColor")
    vcol.layer_name = "Col"

    mix_col = nt.nodes.new("ShaderNodeMix")
    mix_col.data_type = "RGBA"
    mix_col.blend_type = "MULTIPLY"
    mix_col.inputs["Factor"].default_value = 1.0
    rgba_inputs = [s for s in mix_col.inputs if s.type == "RGBA"]
    rgba_outputs = [s for s in mix_col.outputs if s.type == "RGBA"]
    nt.links.new(tex_col.outputs["Color"], rgba_inputs[0])
    nt.links.new(vcol.outputs["Color"], rgba_inputs[1])
    nt.links.new(rgba_outputs[0], bsdf.inputs["Base Color"])

    tex_rgh = nt.nodes.new("ShaderNodeTexImage")
    tex_rgh.image = img_rgh
    nt.links.new(tex_rgh.outputs["Color"], bsdf.inputs["Roughness"])

    tex_nrm = nt.nodes.new("ShaderNodeTexImage")
    tex_nrm.image = img_nrm
    nrm_node = nt.nodes.new("ShaderNodeNormalMap")
    nrm_node.inputs["Strength"].default_value = float(norm_strength)
    nt.links.new(tex_nrm.outputs["Color"], nrm_node.inputs["Color"])
    nt.links.new(nrm_node.outputs["Normal"], bsdf.inputs["Normal"])
    return True
