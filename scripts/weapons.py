"""17 Real-world scale low-poly weapons in a unified canonical frame.

Canonical weapon coordinate frame:
  - Origin (0, 0, 0) : right-hand grip base / palm center
  - +Z               : muzzle / forward barrel / blade tip
  - +Y               : top (sights, carry handle, upper bow limb)
  - +X / -X          : weapon right / left

Every weapon exposes `WEAPON_META[wid]` with `spec_length`, `foregrip` (for 2-bone IK),
`muzzle`, and `hold_type`, and mounts cleanly onto any character via `rig_mixamo.hold()`.
"""
import math
import bmesh
from mesh_utils import add_box, add_cylinder, finalize_mesh


# ---------------------------------------------------------------------------
# Sidearms & Melee / Bow (existing 7 + Revolver)
# ---------------------------------------------------------------------------
def build_weapon_pistol(materials, idx_map, collection=None, name="Weapon_Pistol"):
    """Glock 17 (202 mm): serrated slide, accessory rail, angled grip, safety trigger, white sights."""
    bm = bmesh.new()
    add_box(bm, center=(0.0, -0.024, -0.010), size=(0.028, 0.095, 0.044),
            rot=(-0.26, 0.0, 0.0), mat_idx=idx_map["Mat_GunPolymer"])
    for gz in (-0.018, 0.002, 0.022):
        add_box(bm, center=(0.0, gz - 0.012, 0.014 - gz * 0.25),
                size=(0.029, 0.010, 0.008), mat_idx=idx_map["Mat_GunPolymer"])
    add_box(bm, center=(0.0, 0.024, 0.048), size=(0.027, 0.018, 0.172),
            mat_idx=idx_map["Mat_GunPolymer"])
    add_box(bm, center=(0.0, -0.004, 0.046), size=(0.014, 0.006, 0.042),
            mat_idx=idx_map["Mat_GunPolymer"])
    add_box(bm, center=(0.0, 0.008, 0.066), size=(0.014, 0.028, 0.006),
            mat_idx=idx_map["Mat_GunPolymer"])
    add_box(bm, center=(0.0, 0.008, 0.044), size=(0.007, 0.022, 0.006),
            rot=(0.35, 0.0, 0.0), mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(0.0, 0.042, 0.061), size=(0.028, 0.024, 0.202),
            mat_idx=idx_map["Mat_GunMetal"])
    for sz in (-0.030, -0.020, -0.010, 0.125, 0.135):
        add_box(bm, center=(0.0, 0.042, sz), size=(0.030, 0.020, 0.004),
                mat_idx=idx_map["Mat_GunSteel"])
    add_cylinder(bm, (0.0, 0.040, 0.155), (0.0, 0.040, 0.165), 0.007, 0.007,
                 segments=6, mat_idx=idx_map["Mat_GunSteel"])
    add_box(bm, center=(0.0, 0.057, -0.032), size=(0.018, 0.007, 0.010),
            mat_idx=idx_map["Mat_SightWhite"])
    add_box(bm, center=(0.0, 0.057, 0.154), size=(0.006, 0.007, 0.010),
            mat_idx=idx_map["Mat_SightWhite"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_weapon_revolver(materials, idx_map, collection=None, name="Weapon_Revolver"):
    """S&W Model 686 4-inch (~243 mm): stainless L-frame, fluted 6-shot cylinder, full underlug, red ramp sight."""
    bm = bmesh.new()
    # Curved black rubber grip at (0,0,0)
    add_box(bm, center=(0.0, -0.026, -0.014), size=(0.030, 0.098, 0.040),
            rot=(-0.38, 0.0, 0.0), taper_top=(0.88, 0.85), mat_idx=idx_map["Mat_GunPolymer"])
    # Stainless steel L-frame & top strap
    add_box(bm, center=(0.0, 0.032, 0.038), size=(0.024, 0.048, 0.098),
            mat_idx=idx_map["Mat_GunSteel"])
    add_box(bm, center=(0.0, 0.056, 0.042), size=(0.020, 0.010, 0.088),
            mat_idx=idx_map["Mat_GunSteel"])
    # Exposed hammer & trigger guard
    add_box(bm, center=(0.0, 0.058, -0.012), size=(0.009, 0.016, 0.018),
            rot=(0.40, 0.0, 0.0), mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(0.0, 0.000, 0.032), size=(0.012, 0.024, 0.038),
            mat_idx=idx_map["Mat_GunSteel"])
    # 6-shot fluted cylinder
    add_cylinder(bm, (0.0, 0.036, 0.015), (0.0, 0.036, 0.062), 0.020, 0.020,
                 segments=6, mat_idx=idx_map["Mat_GunSteel"])
    # 4-inch barrel + full-length underlug (+0.078 to +0.188 -> total ~243 mm)
    add_cylinder(bm, (0.0, 0.050, 0.078), (0.0, 0.050, 0.188), 0.010, 0.010,
                 segments=6, mat_idx=idx_map["Mat_GunSteel"])
    add_box(bm, center=(0.0, 0.036, 0.132), size=(0.017, 0.022, 0.108),
            mat_idx=idx_map["Mat_GunSteel"])
    # Red ramp front sight
    add_box(bm, center=(0.0, 0.062, 0.178), size=(0.005, 0.010, 0.014),
            mat_idx=idx_map["Mat_RedDot"])
    return finalize_mesh(name, bm, materials, collection=collection)


# ---------------------------------------------------------------------------
# Submachine Gun & Assault / Battle Rifles
# ---------------------------------------------------------------------------
def build_weapon_smg(materials, idx_map, collection=None, name="Weapon_SMG"):
    """HK MP5A2 (680 mm): tall stamped receiver, cocking tube w/ left lever, rotary drum sight, curved mag, fixed stock."""
    bm = bmesh.new()
    # Grip at (0,0,0)
    add_box(bm, center=(0.0, -0.030, -0.010), size=(0.028, 0.092, 0.038),
            rot=(-0.30, 0.0, 0.0), mat_idx=idx_map["Mat_GunPolymer"])
    # Fixed A2 polymer stock (-0.255 to -0.055)
    add_box(bm, center=(0.0, 0.018, -0.165), size=(0.034, 0.095, 0.215),
            taper_top=(1.0, 0.68), mat_idx=idx_map["Mat_GunPolymer"])
    # Tall stamped receiver (-0.055 to +0.145)
    add_box(bm, center=(0.0, 0.044, 0.045), size=(0.034, 0.054, 0.200),
            mat_idx=idx_map["Mat_GunMetal"])
    # Rotary diopter rear drum sight
    add_cylinder(bm, (0.0, 0.076, -0.020), (0.0, 0.076, 0.002), 0.011, 0.011,
                 segments=8, mat_idx=idx_map["Mat_GunSteel"])
    # Curved 30-rd 9mm magazine (+0.075)
    add_box(bm, center=(0.0, -0.042, 0.075), size=(0.020, 0.105, 0.034),
            rot=(-0.08, 0.0, 0.0), mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(0.0, -0.118, 0.088), size=(0.019, 0.072, 0.033),
            rot=(-0.22, 0.0, 0.0), mat_idx=idx_map["Mat_GunMetal"])
    # Ribbed tropical forend (+0.145 to +0.320)
    add_cylinder(bm, (0.0, 0.032, 0.145), (0.0, 0.032, 0.315), 0.024, 0.021,
                 segments=8, mat_idx=idx_map["Mat_GunPolymer"])
    # Upper cocking tube + left cocking handle (+X)
    add_cylinder(bm, (0.0, 0.060, 0.145), (0.0, 0.060, 0.340), 0.012, 0.012,
                 segments=6, mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(0.022, 0.066, 0.305), size=(0.024, 0.010, 0.012),
            rot=(0.0, 0.0, 0.35), mat_idx=idx_map["Mat_GunSteel"])
    # Shrouded front sight ring + barrel to +0.425 (total 680 mm)
    add_cylinder(bm, (0.0, 0.038, 0.315), (0.0, 0.038, 0.425), 0.010, 0.010,
                 segments=6, mat_idx=idx_map["Mat_GunSteel"])
    add_cylinder(bm, (0.0, 0.072, 0.340), (0.0, 0.072, 0.358), 0.012, 0.012,
                 segments=8, mat_idx=idx_map["Mat_GunMetal"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_weapon_m4(materials, idx_map, collection=None, name="Weapon_M4"):
    """Colt M4A1 Carbine (840 mm): telescopic stock, red-dot optic, ribbed handguard, A-frame sight, flash hider."""
    bm = bmesh.new()
    add_box(bm, center=(0.0, -0.032, -0.014), size=(0.030, 0.098, 0.042),
            rot=(-0.32, 0.0, 0.0), mat_idx=idx_map["Mat_GunPolymer"])
    add_box(bm, center=(0.0, 0.036, 0.052), size=(0.036, 0.052, 0.225),
            mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(0.021, 0.046, 0.015), size=(0.010, 0.014, 0.032),
            mat_idx=idx_map["Mat_GunSteel"])
    add_box(bm, center=(0.0, -0.002, 0.042), size=(0.014, 0.018, 0.048),
            mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(0.0, -0.038, 0.092), size=(0.026, 0.105, 0.056),
            rot=(-0.08, 0.0, 0.0), mat_idx=idx_map["Mat_GunSteel"])
    add_box(bm, center=(0.0, -0.115, 0.105), size=(0.025, 0.075, 0.054),
            rot=(-0.22, 0.0, 0.0), mat_idx=idx_map["Mat_GunSteel"])
    add_cylinder(bm, (0.0, 0.045, -0.058), (0.0, 0.045, -0.265), 0.016, 0.016,
                 segments=6, mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(0.0, 0.018, -0.258), size=(0.036, 0.112, 0.095),
            taper_top=(1.0, 0.72), mat_idx=idx_map["Mat_GunPolymer"])
    add_box(bm, center=(0.0, 0.066, 0.095), size=(0.022, 0.009, 0.240),
            mat_idx=idx_map["Mat_GunSteel"])
    add_cylinder(bm, (0.0, 0.088, 0.035), (0.0, 0.088, 0.115), 0.018, 0.018,
                 segments=8, mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(0.0, 0.074, 0.075), size=(0.024, 0.020, 0.042),
            mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(0.0, 0.088, 0.116), size=(0.010, 0.010, 0.004),
            mat_idx=idx_map["Mat_RedDot"])
    add_cylinder(bm, (0.0, 0.042, 0.165), (0.0, 0.042, 0.345), 0.026, 0.025,
                 segments=8, mat_idx=idx_map["Mat_GunPolymer"])
    for hz in (0.195, 0.235, 0.275, 0.315):
        add_cylinder(bm, (0.0, 0.042, hz), (0.0, 0.042, hz + 0.014), 0.029, 0.029,
                     segments=8, mat_idx=idx_map["Mat_GunPolymer"])
    add_box(bm, center=(0.0, 0.068, 0.372), size=(0.014, 0.046, 0.034),
            taper_top=(0.65, 1.0), mat_idx=idx_map["Mat_GunMetal"])
    add_cylinder(bm, (0.0, 0.042, 0.345), (0.0, 0.042, 0.495), 0.010, 0.010,
                 segments=6, mat_idx=idx_map["Mat_GunSteel"])
    add_cylinder(bm, (0.0, 0.042, 0.495), (0.0, 0.042, 0.535), 0.014, 0.013,
                 segments=6, mat_idx=idx_map["Mat_GunMetal"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_weapon_ak47(materials, idx_map, collection=None, name="Weapon_AK47"):
    """AKM / AK-47 (880 mm): wooden stock & handguard, upper gas tube, banana mag, slanted brake."""
    bm = bmesh.new()
    # Angled wooden grip at (0,0,0)
    add_box(bm, center=(0.0, -0.030, -0.012), size=(0.028, 0.095, 0.038),
            rot=(-0.34, 0.0, 0.0), mat_idx=idx_map["Mat_Walnut"])
    # Fixed downward-sloping wooden buttstock (-0.315 to -0.055)
    add_box(bm, center=(0.0, 0.008, -0.185), size=(0.036, 0.092, 0.260),
            rot=(-0.10, 0.0, 0.0), taper_top=(1.0, 0.65), mat_idx=idx_map["Mat_Walnut"])
    # Stamped steel receiver (-0.055 to +0.180) + top cover
    add_box(bm, center=(0.0, 0.038, 0.062), size=(0.036, 0.050, 0.235),
            mat_idx=idx_map["Mat_GunMetal"])
    # Long right-side selector lever (-X)
    add_box(bm, center=(-0.021, 0.042, 0.032), size=(0.005, 0.014, 0.095),
            mat_idx=idx_map["Mat_GunSteel"])
    # Iconic curved 30-rd banana magazine
    add_box(bm, center=(0.0, -0.042, 0.115), size=(0.026, 0.105, 0.058),
            rot=(-0.16, 0.0, 0.0), mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(0.0, -0.130, 0.145), size=(0.025, 0.095, 0.054),
            rot=(-0.44, 0.0, 0.0), mat_idx=idx_map["Mat_GunMetal"])
    # Wooden lower handguard + upper gas tube (+0.180 to +0.345)
    add_box(bm, center=(0.0, 0.028, 0.262), size=(0.038, 0.034, 0.165),
            mat_idx=idx_map["Mat_Walnut"])
    add_box(bm, center=(0.0, 0.056, 0.258), size=(0.028, 0.022, 0.148),
            mat_idx=idx_map["Mat_Walnut"])
    add_cylinder(bm, (0.0, 0.062, 0.180), (0.0, 0.062, 0.375), 0.010, 0.010,
                 segments=6, mat_idx=idx_map["Mat_GunMetal"])
    # Barrel + front sight block + slant muzzle brake (+0.345 to +0.565 -> 880 mm)
    add_cylinder(bm, (0.0, 0.042, 0.345), (0.0, 0.042, 0.540), 0.010, 0.010,
                 segments=6, mat_idx=idx_map["Mat_GunSteel"])
    add_box(bm, center=(0.0, 0.066, 0.515), size=(0.014, 0.038, 0.024),
            taper_top=(0.6, 1.0), mat_idx=idx_map["Mat_GunMetal"])
    add_cylinder(bm, (0.0, 0.042, 0.540), (0.0, 0.042, 0.565), 0.012, 0.012,
                 segments=6, mat_idx=idx_map["Mat_GunMetal"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_weapon_scar(materials, idx_map, collection=None, name="Weapon_SCAR"):
    """FN SCAR-H Mk17 (965 mm): FDE monolithic upper, black lower + straight 7.62 mag, folding boot stock, holo sight."""
    bm = bmesh.new()
    add_box(bm, center=(0.0, -0.032, -0.014), size=(0.030, 0.095, 0.040),
            rot=(-0.30, 0.0, 0.0), mat_idx=idx_map["Mat_GunPolymer"])
    # Folding "boot" FDE polymer stock (-0.320 to -0.055)
    add_box(bm, center=(0.0, 0.038, -0.185), size=(0.036, 0.062, 0.255),
            mat_idx=idx_map["Mat_CoyoteTan"])
    add_box(bm, center=(0.0, 0.008, -0.285), size=(0.038, 0.115, 0.068),
            mat_idx=idx_map["Mat_CoyoteTan"])
    # Black polymer lower + straight 20-rd 7.62 mag
    add_box(bm, center=(0.0, 0.020, 0.045), size=(0.038, 0.030, 0.200),
            mat_idx=idx_map["Mat_GunPolymer"])
    add_box(bm, center=(0.0, -0.052, 0.095), size=(0.028, 0.135, 0.068),
            rot=(-0.05, 0.0, 0.0), mat_idx=idx_map["Mat_CoyoteTan"])
    # FDE monolithic extruded upper + angular handguard (-0.055 to +0.395)
    add_box(bm, center=(0.0, 0.052, 0.170), size=(0.042, 0.046, 0.450),
            mat_idx=idx_map["Mat_CoyoteTan"])
    # Full-length top rail + boxy holographic sight
    add_box(bm, center=(0.0, 0.078, 0.170), size=(0.022, 0.008, 0.440),
            mat_idx=idx_map["Mat_GunSteel"])
    add_box(bm, center=(0.0, 0.098, 0.075), size=(0.030, 0.034, 0.064),
            mat_idx=idx_map["Mat_GunPolymer"])
    add_box(bm, center=(0.0, 0.098, 0.108), size=(0.014, 0.014, 0.004),
            mat_idx=idx_map["Mat_RedDot"])
    # Angled foregrip on lower rail
    add_box(bm, center=(0.0, 0.012, 0.295), size=(0.026, 0.036, 0.075),
            rot=(0.45, 0.0, 0.0), mat_idx=idx_map["Mat_GunPolymer"])
    # Piston gas block + barrel + flash hider to +0.645 (total 965 mm)
    add_cylinder(bm, (0.0, 0.050, 0.395), (0.0, 0.050, 0.610), 0.011, 0.011,
                 segments=6, mat_idx=idx_map["Mat_GunSteel"])
    add_box(bm, center=(0.0, 0.074, 0.415), size=(0.016, 0.036, 0.034),
            mat_idx=idx_map["Mat_GunMetal"])
    add_cylinder(bm, (0.0, 0.050, 0.610), (0.0, 0.050, 0.645), 0.015, 0.014,
                 segments=6, mat_idx=idx_map["Mat_GunMetal"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_weapon_aug(materials, idx_map, collection=None, name="Weapon_AUG"):
    """Steyr AUG A3 Bullpup (790 mm): OD-green bullpup stock, rear waffle mag behind grip, vertical foregrip, top optic."""
    bm = bmesh.new()
    # Trigger grip at (0,0,0) with oversized trigger guard
    add_box(bm, center=(0.0, -0.030, -0.010), size=(0.028, 0.092, 0.040),
            rot=(-0.22, 0.0, 0.0), mat_idx=idx_map["Mat_OliveMil"])
    add_box(bm, center=(0.0, -0.008, 0.022), size=(0.016, 0.048, 0.052),
            mat_idx=idx_map["Mat_OliveMil"])
    # Sweeping bullpup receiver/stock (-0.345 to +0.115)
    add_box(bm, center=(0.0, 0.032, -0.115), size=(0.042, 0.088, 0.460),
            taper_top=(0.95, 0.78), mat_idx=idx_map["Mat_OliveMil"])
    # Rear waffle magazine BEHIND grip (-0.175)
    add_box(bm, center=(0.0, -0.062, -0.185), size=(0.026, 0.125, 0.056),
            rot=(-0.18, 0.0, 0.0), mat_idx=idx_map["Mat_GunPolymer"])
    # Top Picatinny rail + compact optical scope
    add_box(bm, center=(0.0, 0.082, -0.020), size=(0.022, 0.010, 0.220),
            mat_idx=idx_map["Mat_GunMetal"])
    add_cylinder(bm, (0.0, 0.104, -0.055), (0.0, 0.104, 0.055), 0.018, 0.018,
                 segments=8, mat_idx=idx_map["Mat_GunMetal"])
    # Folding vertical foregrip ahead of trigger (+0.155)
    add_cylinder(bm, (0.0, 0.025, 0.155), (0.0, -0.075, 0.165), 0.014, 0.013,
                 segments=6, mat_idx=idx_map["Mat_OliveMil"])
    # Extended 20-inch barrel + tulip flash hider (+0.115 to +0.445 -> 790 mm)
    add_cylinder(bm, (0.0, 0.048, 0.115), (0.0, 0.048, 0.415), 0.011, 0.011,
                 segments=6, mat_idx=idx_map["Mat_GunSteel"])
    add_cylinder(bm, (0.0, 0.048, 0.415), (0.0, 0.048, 0.445), 0.014, 0.015,
                 segments=6, mat_idx=idx_map["Mat_GunMetal"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_weapon_m14(materials, idx_map, collection=None, name="Weapon_M14"):
    """M14 Battle Rifle (1126 mm): full walnut rifle stock, ventilated dark handguard, 20-rd mag, 22-inch barrel."""
    bm = bmesh.new()
    # Angled rifle wrist grip at (0,0,0) + walnut buttstock (-0.340 to +0.345)
    add_box(bm, center=(0.0, -0.008, -0.010), size=(0.036, 0.048, 0.115),
            rot=(-0.36, 0.0, 0.0), mat_idx=idx_map["Mat_Walnut"])
    add_box(bm, center=(0.0, -0.028, -0.205), size=(0.038, 0.102, 0.255),
            taper_top=(0.95, 0.56), mat_idx=idx_map["Mat_Walnut"])
    add_box(bm, center=(0.0, 0.020, 0.185), size=(0.042, 0.042, 0.340),
            mat_idx=idx_map["Mat_Walnut"])
    # Ventilated dark upper handguard (+0.145 to +0.345)
    add_box(bm, center=(0.0, 0.046, 0.245), size=(0.034, 0.022, 0.200),
            mat_idx=idx_map["Mat_GunPolymer"])
    # Steel receiver + right operating rod handle (-X) + 20-rd straight box mag
    add_box(bm, center=(0.0, 0.044, 0.090), size=(0.038, 0.036, 0.155),
            mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(-0.024, 0.046, 0.115), size=(0.014, 0.012, 0.075),
            mat_idx=idx_map["Mat_GunSteel"])
    add_box(bm, center=(0.0, -0.042, 0.125), size=(0.026, 0.105, 0.068),
            rot=(-0.04, 0.0, 0.0), mat_idx=idx_map["Mat_GunMetal"])
    # Gas cylinder + 22" barrel + slotted flash suppressor (+0.345 to +0.786 -> 1126 mm)
    add_cylinder(bm, (0.0, 0.024, 0.345), (0.0, 0.024, 0.560), 0.010, 0.010,
                 segments=6, mat_idx=idx_map["Mat_GunMetal"])
    add_cylinder(bm, (0.0, 0.044, 0.345), (0.0, 0.044, 0.740), 0.011, 0.010,
                 segments=6, mat_idx=idx_map["Mat_GunSteel"])
    add_cylinder(bm, (0.0, 0.044, 0.740), (0.0, 0.044, 0.786), 0.013, 0.013,
                 segments=6, mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(0.0, 0.062, 0.725), size=(0.008, 0.018, 0.016),
            mat_idx=idx_map["Mat_GunMetal"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_weapon_sniper(materials, idx_map, collection=None, name="Weapon_Sniper"):
    """M24 SWS / Remington 700 (1092 mm): OD-green composite stock, 10x 3-turret scope, bolt handle, Harris bipod."""
    bm = bmesh.new()
    # OD-green composite rifle stock (-0.340 to +0.345)
    add_box(bm, center=(0.0, -0.008, -0.010), size=(0.036, 0.046, 0.110),
            rot=(-0.38, 0.0, 0.0), mat_idx=idx_map["Mat_OliveMil"])
    add_box(bm, center=(0.0, -0.022, -0.205), size=(0.038, 0.104, 0.255),
            taper_top=(0.95, 0.62), mat_idx=idx_map["Mat_OliveMil"])
    add_box(bm, center=(0.0, 0.020, 0.190), size=(0.042, 0.040, 0.350),
            mat_idx=idx_map["Mat_OliveMil"])
    # Heavy receiver + right bolt handle (-X)
    add_cylinder(bm, (0.0, 0.048, 0.015), (0.0, 0.048, 0.195), 0.019, 0.019,
                 segments=8, mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(-0.026, 0.038, 0.045), size=(0.024, 0.012, 0.012),
            rot=(0.0, 0.0, -0.35), mat_idx=idx_map["Mat_GunSteel"])
    # 10x Leupold telescopic scope + 3 turrets + rings
    add_cylinder(bm, (0.0, 0.088, -0.045), (0.0, 0.088, 0.265), 0.020, 0.026,
                 segments=8, mat_idx=idx_map["Mat_GunPolymer"])
    for tz in (0.045, 0.165):
        add_box(bm, center=(0.0, 0.070, tz), size=(0.022, 0.024, 0.018),
                mat_idx=idx_map["Mat_GunMetal"])
    add_cylinder(bm, (0.0, 0.110, 0.095), (0.0, 0.122, 0.095), 0.008, 0.008,
                 segments=6, mat_idx=idx_map["Mat_GunSteel"])
    add_cylinder(bm, (0.0, 0.088, 0.095), (-0.032, 0.088, 0.095), 0.008, 0.008,
                 segments=6, mat_idx=idx_map["Mat_GunSteel"])
    # Heavy free-floating 24" barrel (+0.195 to +0.752 -> 1092 mm)
    add_cylinder(bm, (0.0, 0.048, 0.195), (0.0, 0.048, 0.752), 0.013, 0.011,
                 segments=8, mat_idx=idx_map["Mat_GunMetal"])
    # Deployed Harris front bipod
    for sx in (1.0, -1.0):
        add_cylinder(bm, (sx * 0.015, 0.002, 0.340), (sx * 0.095, -0.175, 0.365),
                     0.006, 0.006, segments=6, mat_idx=idx_map["Mat_GunSteel"])
    return finalize_mesh(name, bm, materials, collection=collection)


# ---------------------------------------------------------------------------
# Shotguns & Light Machine Gun
# ---------------------------------------------------------------------------
def build_weapon_pump(materials, idx_map, collection=None, name="Weapon_Pump"):
    """Remington 870 Tactical (972 mm): sloped milled receiver, under-barrel tube mag, ribbed pump, 6-shell side saddle."""
    bm = bmesh.new()
    add_box(bm, center=(0.0, -0.008, -0.010), size=(0.036, 0.046, 0.110),
            rot=(-0.36, 0.0, 0.0), mat_idx=idx_map["Mat_GunPolymer"])
    add_box(bm, center=(0.0, -0.024, -0.200), size=(0.038, 0.100, 0.245),
            taper_top=(0.95, 0.60), mat_idx=idx_map["Mat_GunPolymer"])
    # Solid steel receiver with sloped contour
    add_box(bm, center=(0.0, 0.034, 0.095), size=(0.038, 0.056, 0.185),
            mat_idx=idx_map["Mat_GunMetal"])
    # 6-shell red side saddle on receiver left (+X)
    add_box(bm, center=(0.022, 0.034, 0.095), size=(0.008, 0.034, 0.132),
            mat_idx=idx_map["Mat_GunPolymer"])
    for sz in (0.042, 0.062, 0.082, 0.102, 0.122, 0.142):
        add_cylinder(bm, (0.028, 0.020, sz), (0.028, 0.058, sz),
                     0.007, 0.007, segments=6, mat_idx=idx_map["Mat_ShellRed"])
    # Under-barrel mag tube & barrel (+0.185 to +0.630 -> 972 mm)
    add_cylinder(bm, (0.0, 0.022, 0.185), (0.0, 0.022, 0.590), 0.013, 0.013,
                 segments=8, mat_idx=idx_map["Mat_GunMetal"])
    add_cylinder(bm, (0.0, 0.050, 0.185), (0.0, 0.050, 0.630), 0.013, 0.012,
                 segments=8, mat_idx=idx_map["Mat_GunSteel"])
    # Ribbed pump forend
    add_cylinder(bm, (0.0, 0.022, 0.275), (0.0, 0.022, 0.445), 0.025, 0.024,
                 segments=8, mat_idx=idx_map["Mat_GunPolymer"])
    add_box(bm, center=(0.0, 0.065, 0.620), size=(0.006, 0.008, 0.010),
            mat_idx=idx_map["Mat_SightWhite"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_weapon_double_barrel(materials, idx_map, collection=None, name="Weapon_DoubleBarrel"):
    """Side-by-side 26-inch shotgun (1050 mm): walnut stock & forend, engraved steel action, twin barrels, brass bead."""
    bm = bmesh.new()
    add_box(bm, center=(0.0, 0.006, -0.015), size=(0.036, 0.044, 0.115),
            rot=(-0.34, 0.0, 0.0), mat_idx=idx_map["Mat_Walnut"])
    add_box(bm, center=(0.0, -0.024, -0.195), size=(0.038, 0.098, 0.235),
            taper_top=(0.95, 0.58), mat_idx=idx_map["Mat_Walnut"])
    add_box(bm, center=(0.0, 0.028, 0.068), size=(0.044, 0.046, 0.112),
            mat_idx=idx_map["Mat_GunSteel"])
    add_box(bm, center=(0.0, 0.056, 0.038), size=(0.012, 0.010, 0.038),
            mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(0.0, -0.004, 0.058), size=(0.016, 0.024, 0.048),
            mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(0.0, 0.014, 0.225), size=(0.046, 0.026, 0.210),
            mat_idx=idx_map["Mat_Walnut"])
    for sx in (-0.013, 0.013):
        add_cylinder(bm, (sx, 0.038, 0.120), (sx, 0.038, 0.740),
                     0.012, 0.011, segments=6, mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(0.0, 0.049, 0.430), size=(0.010, 0.005, 0.615),
            mat_idx=idx_map["Mat_GunSteel"])
    add_box(bm, center=(0.0, 0.054, 0.732), size=(0.006, 0.006, 0.008),
            mat_idx=idx_map["Mat_Brass"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_weapon_spas12(materials, idx_map, collection=None, name="Weapon_SPAS12"):
    """Franchi SPAS-12 Combat Shotgun (1041 mm): chunky receiver, barrel heat shield, tubular top-folding hook stock."""
    bm = bmesh.new()
    # Angled pistol grip at (0,0,0)
    add_box(bm, center=(0.0, -0.030, -0.010), size=(0.032, 0.095, 0.042),
            rot=(-0.34, 0.0, 0.0), mat_idx=idx_map["Mat_GunPolymer"])
    # Heavy industrial receiver (-0.055 to +0.180)
    add_box(bm, center=(0.0, 0.038, 0.062), size=(0.044, 0.064, 0.235),
            mat_idx=idx_map["Mat_GunMetal"])
    # Unmistakable top-folding tubular steel stock + signature rear hook (-0.340 to -0.055)
    for sx in (-0.016, 0.016):
        add_cylinder(bm, (sx, 0.050, -0.055), (sx, 0.025, -0.320),
                     0.008, 0.008, segments=6, mat_idx=idx_map["Mat_GunSteel"])
    add_box(bm, center=(0.0, -0.005, -0.325), size=(0.042, 0.098, 0.028),
            mat_idx=idx_map["Mat_GunPolymer"])
    # Signature downward folding hook on top of stock
    add_box(bm, center=(0.0, 0.072, -0.250), size=(0.036, 0.012, 0.125),
            mat_idx=idx_map["Mat_GunSteel"])
    # Perforated heat shield + pump forend + mag tube + barrel (+0.180 to +0.680 -> 1041 mm)
    add_box(bm, center=(0.0, 0.054, 0.365), size=(0.040, 0.032, 0.370),
            mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(0.0, 0.022, 0.355), size=(0.046, 0.034, 0.220),
            mat_idx=idx_map["Mat_GunPolymer"])
    add_cylinder(bm, (0.0, 0.022, 0.180), (0.0, 0.022, 0.635), 0.013, 0.013,
                 segments=6, mat_idx=idx_map["Mat_GunSteel"])
    add_cylinder(bm, (0.0, 0.054, 0.550), (0.0, 0.054, 0.680), 0.013, 0.012,
                 segments=6, mat_idx=idx_map["Mat_GunMetal"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_weapon_lmg(materials, idx_map, collection=None, name="Weapon_LMG"):
    """M249 SAW (1035 mm): boxy feed-cover receiver, 200-rd ammo box w/ brass belt, carry handle, heavy stock, bipod."""
    bm = bmesh.new()
    add_box(bm, center=(0.0, -0.032, -0.012), size=(0.032, 0.098, 0.042),
            rot=(-0.30, 0.0, 0.0), mat_idx=idx_map["Mat_GunPolymer"])
    # Heavy hydraulic polymer buttstock (-0.310 to -0.065)
    add_box(bm, center=(0.0, 0.025, -0.188), size=(0.044, 0.105, 0.245),
            taper_top=(1.0, 0.72), mat_idx=idx_map["Mat_GunPolymer"])
    # Boxy steel receiver + hinged feed cover (-0.065 to +0.255)
    add_box(bm, center=(0.0, 0.052, 0.095), size=(0.062, 0.078, 0.320),
            mat_idx=idx_map["Mat_GunMetal"])
    # 200-round OD green ammo box underneath + visible brass ammo belt into feed tray (+X)
    add_box(bm, center=(0.0, -0.052, 0.155), size=(0.092, 0.125, 0.125),
            mat_idx=idx_map["Mat_OliveDark"])
    add_box(bm, center=(0.042, 0.022, 0.155), size=(0.018, 0.072, 0.048),
            rot=(0.0, 0.0, -0.22), mat_idx=idx_map["Mat_Brass"])
    # Heat shield + heavy barrel + carry handle + deployed bipod (+0.255 to +0.725 -> 1035 mm)
    add_box(bm, center=(0.0, 0.064, 0.365), size=(0.046, 0.038, 0.220),
            mat_idx=idx_map["Mat_GunPolymer"])
    add_box(bm, center=(-0.018, 0.108, 0.345), size=(0.014, 0.032, 0.085),
            mat_idx=idx_map["Mat_GunSteel"])
    add_cylinder(bm, (0.0, 0.056, 0.255), (0.0, 0.056, 0.685), 0.014, 0.013,
                 segments=6, mat_idx=idx_map["Mat_GunSteel"])
    add_cylinder(bm, (0.0, 0.056, 0.685), (0.0, 0.056, 0.725), 0.017, 0.016,
                 segments=6, mat_idx=idx_map["Mat_GunMetal"])
    for sx in (1.0, -1.0):
        add_cylinder(bm, (sx * 0.022, 0.032, 0.445), (sx * 0.115, -0.185, 0.475),
                     0.008, 0.008, segments=6, mat_idx=idx_map["Mat_GunMetal"])
    return finalize_mesh(name, bm, materials, collection=collection)


# ---------------------------------------------------------------------------
# Non-Firearms (Pipe Wrench, Compound Bow, Arrow, Knife)
# ---------------------------------------------------------------------------
def build_weapon_pipe_wrench(materials, idx_map, collection=None, name="Weapon_PipeWrench"):
    """Heavy red pipe wrench (520 mm): cast-iron red handle, adjusting knurl nut, twin serrated jaws."""
    bm = bmesh.new()
    add_box(bm, center=(0.0, 0.0, 0.112), size=(0.022, 0.034, 0.415),
            taper_top=(1.0, 1.25), mat_idx=idx_map["Mat_WrenchRed"])
    add_box(bm, center=(0.0, 0.0, -0.095), size=(0.028, 0.040, 0.026),
            mat_idx=idx_map["Mat_WrenchRed"])
    add_box(bm, center=(0.0, 0.014, 0.325), size=(0.030, 0.064, 0.072),
            mat_idx=idx_map["Mat_WrenchRed"])
    add_cylinder(bm, (0.0, 0.026, 0.285), (0.0, 0.026, 0.325), 0.019, 0.019,
                 segments=8, mat_idx=idx_map["Mat_GunSteel"])
    add_box(bm, center=(0.0, -0.008, 0.375), size=(0.026, 0.052, 0.048),
            mat_idx=idx_map["Mat_GunSteel"])
    add_box(bm, center=(0.0, 0.030, 0.392), size=(0.024, 0.032, 0.066),
            mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(0.0, 0.002, 0.412), size=(0.024, 0.064, 0.026),
            mat_idx=idx_map["Mat_GunMetal"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_weapon_compound_bow(materials, idx_map, collection=None, name="Weapon_CompoundBow"):
    """Compound bow (~820 mm tall along Y, shooting +Z): machined riser, split limbs, cams, string, 3-pin sight, stabilizer."""
    bm = bmesh.new()
    add_box(bm, center=(0.0, 0.0, 0.0), size=(0.024, 0.110, 0.036),
            mat_idx=idx_map["Mat_GunPolymer"])
    add_box(bm, center=(0.0, 0.125, 0.020), size=(0.022, 0.175, 0.034),
            rot=(-0.18, 0.0, 0.0), mat_idx=idx_map["Mat_OliveMil"])
    add_box(bm, center=(0.0, -0.125, 0.020), size=(0.022, 0.175, 0.034),
            rot=(0.18, 0.0, 0.0), mat_idx=idx_map["Mat_OliveMil"])
    for sy in (1.0, -1.0):
        for sx in (-0.011, 0.011):
            add_cylinder(bm, (sx, sy * 0.205, 0.035), (sx, sy * 0.385, -0.135),
                         0.009, 0.007, segments=6, mat_idx=idx_map["Mat_Carbon"])
        add_cylinder(bm, (-0.014, sy * 0.390, -0.142), (0.014, sy * 0.390, -0.142),
                     0.036, 0.036, segments=8, mat_idx=idx_map["Mat_BowCam"])
    add_cylinder(bm, (0.0, -0.405, -0.165), (0.0, 0.405, -0.165),
                 0.003, 0.003, segments=5, mat_idx=idx_map["Mat_SightWhite"])
    add_cylinder(bm, (0.012, -0.375, -0.130), (0.012, 0.375, -0.130),
                 0.0025, 0.0025, segments=5, mat_idx=idx_map["Mat_GunSteel"])
    add_box(bm, center=(0.024, 0.085, 0.055), size=(0.020, 0.026, 0.048),
            mat_idx=idx_map["Mat_BowCam"])
    add_box(bm, center=(0.024, 0.085, 0.075), size=(0.008, 0.016, 0.010),
            mat_idx=idx_map["Mat_RedDot"])
    add_cylinder(bm, (0.0, -0.055, 0.035), (0.0, -0.055, 0.245),
                 0.009, 0.012, segments=6, mat_idx=idx_map["Mat_Carbon"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_weapon_arrow(materials, idx_map, collection=None, name="Weapon_Arrow"):
    """Carbon arrow (750 mm along +Z): carbon shaft, steel broadhead, 3 red vanes, nock."""
    bm = bmesh.new()
    add_cylinder(bm, (0.0, 0.0, -0.120), (0.0, 0.0, 0.580),
                 0.005, 0.005, segments=6, mat_idx=idx_map["Mat_Carbon"])
    add_box(bm, center=(0.0, 0.0, 0.600), size=(0.022, 0.004, 0.042),
            taper_top=(0.15, 0.4), mat_idx=idx_map["Mat_GunSteel"])
    for k in range(3):
        ang = (2.0 * math.pi * k) / 3.0
        add_box(bm, center=(math.cos(ang) * 0.011, math.sin(ang) * 0.011, -0.070),
                size=(0.003, 0.016, 0.058), rot=(0.0, 0.0, ang + math.pi * 0.5),
                mat_idx=idx_map["Mat_VaneRed"])
    add_cylinder(bm, (0.0, 0.0, -0.130), (0.0, 0.0, -0.118),
                 0.006, 0.005, segments=6, mat_idx=idx_map["Mat_SightWhite"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_weapon_knife(materials, idx_map, collection=None, name="Weapon_Knife"):
    """Survival knife (280 mm along +Z): wrapped grip, pommel, crossguard, clip-point steel blade."""
    bm = bmesh.new()
    add_cylinder(bm, (0.0, 0.0, -0.068), (0.0, 0.0, -0.052),
                 0.016, 0.014, segments=6, mat_idx=idx_map["Mat_GunMetal"])
    add_cylinder(bm, (0.0, 0.0, -0.052), (0.0, 0.0, 0.058),
                 0.013, 0.014, segments=6, mat_idx=idx_map["Mat_LeatherDark"])
    add_box(bm, center=(0.0, 0.0, 0.064), size=(0.018, 0.054, 0.010),
            mat_idx=idx_map["Mat_GunMetal"])
    add_box(bm, center=(0.0, 0.0, 0.140), size=(0.006, 0.028, 0.142),
            taper_top=(0.45, 0.22), mat_idx=idx_map["Mat_GunSteel"])
    return finalize_mesh(name, bm, materials, collection=collection)


WEAPON_META = {
    "pistol":        {"spec_length": 0.202, "foregrip": (0.0, 0.01, 0.05),   "muzzle": (0.0, 0.04, 0.165), "ejection": (-0.018, 0.044, 0.045),  "shell_type": "rifle",   "vfx_profile": "pistol",  "hold_type": "pistol"},
    "revolver":      {"spec_length": 0.243, "foregrip": (0.0, 0.01, 0.05),   "muzzle": (0.0, 0.05, 0.188), "ejection": None,                      "shell_type": None,      "vfx_profile": "pistol",  "hold_type": "pistol"},
    "smg":           {"spec_length": 0.680, "foregrip": (0.0, 0.02, 0.235),  "muzzle": (0.0, 0.04, 0.425), "ejection": (-0.022, 0.045, 0.095),  "shell_type": "rifle",   "vfx_profile": "rifle",   "hold_type": "rifle"},
    "m4":            {"spec_length": 0.840, "foregrip": (0.0, 0.03, 0.255),  "muzzle": (0.0, 0.04, 0.535), "ejection": (-0.025, 0.052, 0.085),  "shell_type": "rifle",   "vfx_profile": "rifle",   "hold_type": "rifle"},
    "ak47":          {"spec_length": 0.880, "foregrip": (0.0, 0.02, 0.260),  "muzzle": (0.0, 0.04, 0.565), "ejection": (-0.025, 0.052, 0.085),  "shell_type": "rifle",   "vfx_profile": "rifle",   "hold_type": "rifle"},
    "scar":          {"spec_length": 0.965, "foregrip": (0.0, 0.02, 0.290),  "muzzle": (0.0, 0.05, 0.645), "ejection": (-0.025, 0.052, 0.085),  "shell_type": "rifle",   "vfx_profile": "rifle",   "hold_type": "rifle"},
    "aug":           {"spec_length": 0.790, "foregrip": (0.0, -0.02, 0.160), "muzzle": (0.0, 0.05, 0.445), "ejection": (-0.025, 0.046, -0.115), "shell_type": "rifle",   "vfx_profile": "rifle",   "hold_type": "rifle"},
    "m14":           {"spec_length": 1.126, "foregrip": (0.0, 0.02, 0.250),  "muzzle": (0.0, 0.04, 0.786), "ejection": (-0.025, 0.052, 0.085),  "shell_type": "rifle",   "vfx_profile": "rifle",   "hold_type": "rifle"},
    "sniper":        {"spec_length": 1.092, "foregrip": (0.0, 0.02, 0.255),  "muzzle": (0.0, 0.05, 0.752), "ejection": (-0.026, 0.055, 0.065),  "shell_type": "rifle",   "vfx_profile": "heavy",   "hold_type": "rifle"},
    "pump":          {"spec_length": 0.972, "foregrip": (0.0, 0.02, 0.355),  "muzzle": (0.0, 0.05, 0.630), "ejection": (-0.026, 0.046, 0.115),  "shell_type": "shotgun", "vfx_profile": "shotgun", "hold_type": "rifle"},
    "double_barrel": {"spec_length": 1.050, "foregrip": (0.0, 0.01, 0.245),  "muzzle": (0.0, 0.04, 0.740), "ejection": None,                      "shell_type": None,      "vfx_profile": "shotgun", "hold_type": "rifle"},
    "spas12":        {"spec_length": 1.041, "foregrip": (0.0, 0.02, 0.345),  "muzzle": (0.0, 0.05, 0.680), "ejection": (-0.026, 0.046, 0.115),  "shell_type": "shotgun", "vfx_profile": "shotgun", "hold_type": "rifle"},
    "lmg":           {"spec_length": 1.035, "foregrip": (0.0, 0.03, 0.345),  "muzzle": (0.0, 0.06, 0.725), "ejection": (-0.036, 0.052, 0.125),  "shell_type": "rifle",   "vfx_profile": "heavy",   "hold_type": "rifle"},
    "pipe_wrench":   {"spec_length": 0.520, "foregrip": (0.0, 0.0, 0.220),   "muzzle": (0.0, 0.0, 0.425),  "ejection": None,                      "shell_type": None,      "vfx_profile": "melee",   "hold_type": "melee"},
    "compound_bow":  {"spec_length": 0.410, "foregrip": (0.0, 0.0, 0.0),     "muzzle": (0.0, 0.0, 0.245),  "ejection": None,                      "shell_type": None,      "vfx_profile": "bow",     "hold_type": "bow"},
    "arrow":         {"spec_length": 0.750, "foregrip": (0.0, 0.0, 0.0),     "muzzle": (0.0, 0.0, 0.620),  "ejection": None,                      "shell_type": None,      "vfx_profile": "bow",     "hold_type": "arrow"},
    "knife":         {"spec_length": 0.280, "foregrip": (0.0, 0.0, 0.0),     "muzzle": (0.0, 0.0, 0.212),  "ejection": None,                      "shell_type": None,      "vfx_profile": "melee",   "hold_type": "melee"},
}

ALL_WEAPON_BUILDERS = [
    ("pistol",        build_weapon_pistol,        0.202),
    ("revolver",      build_weapon_revolver,      0.243),
    ("smg",           build_weapon_smg,           0.680),
    ("m4",            build_weapon_m4,            0.840),
    ("ak47",          build_weapon_ak47,          0.880),
    ("scar",          build_weapon_scar,          0.965),
    ("aug",           build_weapon_aug,           0.790),
    ("m14",           build_weapon_m14,           1.126),
    ("sniper",        build_weapon_sniper,        1.092),
    ("pump",          build_weapon_pump,          0.972),
    ("double_barrel", build_weapon_double_barrel, 1.050),
    ("spas12",        build_weapon_spas12,        1.041),
    ("lmg",           build_weapon_lmg,           1.035),
    ("pipe_wrench",   build_weapon_pipe_wrench,   0.520),
    ("compound_bow",  build_weapon_compound_bow,  0.410),
    ("arrow",         build_weapon_arrow,         0.750),
    ("knife",         build_weapon_knife,         0.280),
]
