"""Modular stylized low-poly weapon VFX assets (pure-tri flat-shaded PBR, origin=(0,0,0), fwd=+Z)."""
import math
import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

from mesh_utils import add_box, add_cone, add_cylinder, finalize_mesh, loft_rings, ring_perp
from rig_mixamo import HOLD_MAT_LEFT, HOLD_MAT_RIGHT
from weapons import WEAPON_META


def _add_octa_puff(bm, center, rx, ry, rz, mat_idx):
    """Low-poly 8-triangle diamond puff polyhedron centered at `center`."""
    cx, cy, cz = center
    rings = [
        [(cx + rx * 0.25, cy, cz - rz), (cx, cy + ry * 0.25, cz - rz),
         (cx - rx * 0.25, cy, cz - rz), (cx, cy - ry * 0.25, cz - rz)],
        [(cx + rx, cy, cz), (cx, cy + ry, cz), (cx - rx, cy, cz), (cx, cy - ry, cz)],
        [(cx + rx * 0.25, cy, cz + rz), (cx, cy + ry * 0.25, cz + rz),
         (cx - rx * 0.25, cy, cz + rz), (cx, cy - ry * 0.25, cz + rz)],
    ]
    return loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_idx)


def _add_star_petals(bm, origin, count, length, r_base, spread_deg, mat_idx, roll_deg=0.0):
    """Radial star of sharp low-poly flame cones fanning around +Z."""
    ox, oy, oz = origin
    sp = math.radians(spread_deg)
    for i in range(count):
        ang = math.radians(roll_deg) + (2.0 * math.pi * i) / count
        dx = math.sin(sp) * math.cos(ang)
        dy = math.sin(sp) * math.sin(ang)
        dz = math.cos(sp)
        add_cone(
            bm,
            (ox, oy, oz),
            (ox + dx * length, oy + dy * length, oz + dz * length),
            r_base, segments=4, mat_idx=mat_idx,
        )


def build_vfx_muzzle_pistol(materials, idx_map, collection=None, name="VFX_Muzzle_Pistol"):
    """Crisp handgun muzzle flash: 4-petal cross flame, bright core lance, tiny upper smoke wisp."""
    bm = bmesh.new()
    add_cone(bm, (0.0, 0.0, -0.005), (0.0, 0.0, 0.145), 0.022, segments=5, mat_idx=idx_map["Mat_VfxFlashCore"])
    _add_star_petals(bm, (0.0, 0.0, 0.004), 4, 0.110, 0.024, 58.0, idx_map["Mat_VfxFlashMid"], roll_deg=45.0)
    _add_star_petals(bm, (0.0, 0.0, 0.006), 4, 0.080, 0.016, 40.0, idx_map["Mat_VfxFlashOuter"], roll_deg=0.0)
    _add_octa_puff(bm, (0.0, 0.028, 0.065), 0.020, 0.022, 0.024, idx_map["Mat_VfxSmokeLight"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_vfx_muzzle_rifle(materials, idx_map, collection=None, name="VFX_Muzzle_Rifle"):
    """Tactical carbine/rifle flash: 3-prong spear, 4 compensator side jets, glowing core, smoke wisps."""
    bm = bmesh.new()
    add_cone(bm, (0.0, 0.0, -0.006), (0.0, 0.0, 0.265), 0.028, segments=6, mat_idx=idx_map["Mat_VfxFlashCore"])
    _add_star_petals(bm, (0.0, 0.0, 0.004), 3, 0.215, 0.030, 26.0, idx_map["Mat_VfxFlashMid"], roll_deg=90.0)
    _add_star_petals(bm, (0.0, 0.0, 0.006), 4, 0.125, 0.022, 70.0, idx_map["Mat_VfxFlashOuter"], roll_deg=45.0)
    _add_octa_puff(bm, (-0.018, 0.042, 0.105), 0.026, 0.024, 0.030, idx_map["Mat_VfxSmokeLight"])
    _add_octa_puff(bm, ( 0.020, 0.032, 0.145), 0.020, 0.020, 0.026, idx_map["Mat_VfxSmokeDark"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_vfx_muzzle_shotgun(materials, idx_map, collection=None, name="VFX_Muzzle_Shotgun"):
    """Wide roaring 12-gauge blast bloom: 8 radial flame petals, wide core, ember shards & chunky smoke."""
    bm = bmesh.new()
    add_cone(bm, (0.0, 0.0, -0.008), (0.0, 0.0, 0.340), 0.048, segments=6, mat_idx=idx_map["Mat_VfxFlashCore"])
    _add_star_petals(bm, (0.0, 0.0, 0.004), 6, 0.245, 0.044, 48.0, idx_map["Mat_VfxFlashMid"], roll_deg=0.0)
    _add_star_petals(bm, (0.0, 0.0, 0.006), 8, 0.180, 0.030, 68.0, idx_map["Mat_VfxFlashOuter"], roll_deg=22.5)
    for k in range(4):
        ang = math.radians(35.0 + 90.0 * k)
        dx, dy = math.cos(ang), math.sin(ang)
        add_cone(bm, (dx * 0.06, dy * 0.06, 0.12), (dx * 0.14, dy * 0.14, 0.30),
                 0.008, segments=4, mat_idx=idx_map["Mat_VfxSpark"])
    _add_octa_puff(bm, (0.0, 0.055, 0.160), 0.042, 0.038, 0.048, idx_map["Mat_VfxSmokeLight"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_vfx_muzzle_heavy(materials, idx_map, collection=None, name="VFX_Muzzle_Heavy"):
    """High-velocity Sniper/LMG brake blast: huge twin -X/+X baffle plumes + long central lance."""
    bm = bmesh.new()
    add_cone(bm, (0.0, 0.0, -0.008), (0.0, 0.0, 0.410), 0.032, segments=6, mat_idx=idx_map["Mat_VfxFlashCore"])
    for sx in (1.0, -1.0):
        add_cone(bm, (sx * 0.010, 0.0, 0.005), (sx * 0.235, 0.0, -0.055), 0.042, segments=5, mat_idx=idx_map["Mat_VfxFlashMid"])
        add_cone(bm, (sx * 0.015, 0.0, 0.008), (sx * 0.180, 0.015, 0.035), 0.028, segments=5, mat_idx=idx_map["Mat_VfxFlashOuter"])
        _add_octa_puff(bm, (sx * 0.135, 0.028, 0.025), 0.036, 0.030, 0.034, idx_map["Mat_VfxSmokeDark"])
    _add_star_petals(bm, (0.0, 0.0, 0.010), 4, 0.240, 0.026, 22.0, idx_map["Mat_VfxFlashOuter"], roll_deg=45.0)
    return finalize_mesh(name, bm, materials, collection=collection)


def build_vfx_tracer_bullet(materials, idx_map, collection=None, name="VFX_Tracer_Bullet"):
    """Stylized glowing supersonic bullet tracer streak (550 mm along +Z)."""
    bm = bmesh.new()
    rings = [
        ring_perp((0.0, 0.0, 0.00), (0, 0, 1), r_up=0.003, r_side=0.003, n=4),
        ring_perp((0.0, 0.0, 0.36), (0, 0, 1), r_up=0.009, r_side=0.009, n=4),
        ring_perp((0.0, 0.0, 0.50), (0, 0, 1), r_up=0.011, r_side=0.011, n=4),
        ring_perp((0.0, 0.0, 0.56), (0, 0, 1), r_up=0.002, r_side=0.002, n=4),
    ]
    verts = loft_rings(bm, rings, close_caps=(True, True), mat_idx=idx_map["Mat_VfxTracer"])
    for f in {fa for v in verts for fa in v.link_faces}:
        if f.calc_center_median().z > 0.44:
            f.material_index = idx_map["Mat_VfxFlashCore"]
    return finalize_mesh(name, bm, materials, collection=collection)


def build_vfx_tracer_pellet_spread(materials, idx_map, collection=None, name="VFX_Tracer_Pellet"):
    """6 diverging buckshot pellet tracer streaks fanning in a ~8 degree cone."""
    bm = bmesh.new()
    dirs = [(0.0, 0.0)]
    for k in range(5):
        ang = (2.0 * math.pi * k) / 5.0
        dirs.append((math.cos(ang) * 0.135, math.sin(ang) * 0.135))
    for i, (dx, dy) in enumerate(dirs):
        z0 = 0.03 * (i % 3)
        z1 = z0 + 0.42
        add_cone(bm, (dx * 0.15, dy * 0.15, z0), (dx, dy, z1), 0.008, segments=4,
                 mat_idx=idx_map["Mat_VfxFlashCore" if i == 0 else "Mat_VfxTracer"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_vfx_shell_rifle(materials, idx_map, collection=None, name="VFX_Shell_Rifle"):
    """Faceted hot brass bottlenecked cartridge casing."""
    bm = bmesh.new()
    add_cylinder(bm, (0.0, 0.0, -0.024), (0.0, 0.0, -0.018), 0.0065, 0.0065, segments=6, mat_idx=idx_map["Mat_VfxBrassHot"])
    add_cylinder(bm, (0.0, 0.0, -0.018), (0.0, 0.0,  0.012), 0.0058, 0.0055, segments=6, mat_idx=idx_map["Mat_VfxBrassHot"])
    add_cylinder(bm, (0.0, 0.0,  0.012), (0.0, 0.0,  0.024), 0.0055, 0.0040, segments=6, mat_idx=idx_map["Mat_VfxBrassHot"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_vfx_shell_shotgun(materials, idx_map, collection=None, name="VFX_Shell_Shotgun"):
    """Faceted 12-gauge spent shotgun hull (crimson plastic + hot brass head)."""
    bm = bmesh.new()
    add_cylinder(bm, (0.0, 0.0, -0.032), (0.0, 0.0, -0.014), 0.0105, 0.0102, segments=8, mat_idx=idx_map["Mat_VfxBrassHot"])
    add_cylinder(bm, (0.0, 0.0, -0.014), (0.0, 0.0,  0.032), 0.0098, 0.0098, segments=8, mat_idx=idx_map["Mat_ShellRed"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_vfx_smoke_puff(materials, idx_map, collection=None, name="VFX_Smoke_Puff"):
    """Cluster of 4 stylized low-poly gunsmoke polyhedra drifting upward & forward."""
    bm = bmesh.new()
    for cx, cy, cz, rx, ry, rz, dark in (
        ( 0.000, 0.020, 0.040, 0.032, 0.032, 0.036, False),
        (-0.022, 0.055, 0.095, 0.044, 0.042, 0.046, False),
        ( 0.024, 0.088, 0.145, 0.036, 0.036, 0.040, True),
        (-0.010, 0.125, 0.190, 0.028, 0.030, 0.032, True),
    ):
        _add_octa_puff(bm, (cx, cy, cz), rx, ry, rz,
                       idx_map["Mat_VfxSmokeDark" if dark else "Mat_VfxSmokeLight"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_vfx_arrow_trail(materials, idx_map, collection=None, name="VFX_Arrow_Trail"):
    """Spiraling kinetic wind ribbon & twin air-wake rings trailing behind a launched arrow."""
    bm = bmesh.new()
    n_seg = 12
    ribs0, ribs1 = [], []
    for i in range(n_seg + 1):
        t = i / n_seg
        z = -0.35 + t * 0.65
        ang = t * 2.8 * math.pi
        rad = 0.022 + 0.020 * (1.0 - t)
        w = 0.010 * math.sin(t * math.pi) + 0.003
        cx, cy = rad * math.cos(ang), rad * math.sin(ang)
        ribs0.append((cx, cy, z - w))
        ribs1.append((cx * 1.35, cy * 1.35, z + w))
    for i in range(n_seg):
        v0 = bm.verts.new(ribs0[i])
        v1 = bm.verts.new(ribs0[i + 1])
        v2 = bm.verts.new(ribs1[i + 1])
        v3 = bm.verts.new(ribs1[i])
        f = bm.faces.new((v0, v1, v2, v3))
        f.material_index = idx_map["Mat_VfxSlashCore" if i > n_seg // 2 else "Mat_VfxSlashEdge"]

    # Twin hexagonal air-wake shock rings
    for z_r, rad_r, th in ((0.18, 0.042, 0.006), (-0.05, 0.058, 0.005)):
        r_a = ring_perp((0.0, 0.0, z_r - th), (0, 0, 1), r_up=rad_r, r_side=rad_r, n=6)
        r_b = ring_perp((0.0, 0.0, z_r + th), (0, 0, 1), r_up=rad_r * 1.08, r_side=rad_r * 1.08, n=6)
        loft_rings(bm, [r_a, r_b], close_caps=(False, False), mat_idx=idx_map["Mat_VfxSlashCore"])

    return finalize_mesh(name, bm, materials, collection=collection)


def build_vfx_melee_slash(materials, idx_map, collection=None, name="VFX_Melee_Slash"):
    """Sweeping 135-degree crescent kinetic slash arc in XY plane (sharp outer edge + flying sparks)."""
    bm = bmesh.new()
    n_arc = 10
    a0 = math.radians(-105.0)
    a1 = math.radians(35.0)
    r_outer = 0.42
    pts_top, pts_bot, pts_edge = [], [], []
    for i in range(n_arc + 1):
        t = i / n_arc
        ang = a0 + t * (a1 - a0)
        ca, sa = math.cos(ang), math.sin(ang)
        env = math.sin(t * math.pi)
        r_in = r_outer - (0.04 + 0.14 * env)
        thick = 0.014 * env + 0.002
        pts_edge.append((r_outer * ca, r_outer * sa, 0.0))
        pts_top.append((r_in * ca, r_in * sa, thick))
        pts_bot.append((r_in * ca, r_in * sa, -thick))

    v_e = [bm.verts.new(p) for p in pts_edge]
    v_t = [bm.verts.new(p) for p in pts_top]
    v_b = [bm.verts.new(p) for p in pts_bot]
    for i in range(n_arc):
        mat_i = idx_map["Mat_VfxSlashCore" if i >= n_arc // 2 else "Mat_VfxSlashEdge"]
        bm.faces.new((v_t[i], v_t[i + 1], v_e[i + 1], v_e[i])).material_index = mat_i
        bm.faces.new((v_e[i], v_e[i + 1], v_b[i + 1], v_b[i])).material_index = mat_i
        bm.faces.new((v_b[i], v_b[i + 1], v_t[i + 1], v_t[i])).material_index = idx_map["Mat_VfxSlashEdge"]

    for ang_d, r0, r1 in ((18.0, 0.44, 0.56), (32.0, 0.41, 0.52), (-15.0, 0.43, 0.51)):
        rad = math.radians(ang_d)
        add_cone(bm, (r0 * math.cos(rad), r0 * math.sin(rad), 0.01),
                 (r1 * math.cos(rad), r1 * math.sin(rad), 0.02),
                 0.010, segments=4, mat_idx=idx_map["Mat_VfxSpark"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_vfx_impact_spark(materials, idx_map, collection=None, name="VFX_Impact_Spark"):
    """Radial burst of 7 glowing spark needles + central star flash."""
    bm = bmesh.new()
    _add_octa_puff(bm, (0.0, 0.0, 0.015), 0.032, 0.032, 0.032, idx_map["Mat_VfxFlashCore"])
    for k in range(7):
        ang = (2.0 * math.pi * k) / 7.0
        tilt = math.radians(38.0 + 18.0 * (k % 2))
        dx = math.sin(tilt) * math.cos(ang)
        dy = math.sin(tilt) * math.sin(ang)
        dz = math.cos(tilt)
        length = 0.14 + 0.06 * (k % 2)
        add_cone(bm, (dx * 0.02, dy * 0.02, 0.01), (dx * length, dy * length, 0.01 + dz * length),
                 0.010, segments=4, mat_idx=idx_map["Mat_VfxSpark"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_vfx_impact_blood(materials, idx_map, collection=None, name="VFX_Impact_Blood"):
    """Stylized low-poly crimson splatter cone + 6 flying blood droplets."""
    bm = bmesh.new()
    add_cone(bm, (0.0, 0.0, 0.0), (0.0, 0.0, 0.14), 0.055, segments=6, mat_idx=idx_map["Mat_VfxBloodDark"])
    for k in range(6):
        ang = (2.0 * math.pi * k) / 6.0
        sp = math.radians(32.0 + 16.0 * (k % 2))
        dx = math.sin(sp) * math.cos(ang)
        dy = math.sin(sp) * math.sin(ang)
        dz = math.cos(sp)
        r = 0.012 + 0.005 * (k % 2)
        _add_octa_puff(bm, (dx * 0.14, dy * 0.14, 0.04 + dz * 0.14), r, r, r * 1.4, idx_map["Mat_VfxBloodFresh"])
    return finalize_mesh(name, bm, materials, collection=collection)


ALL_VFX_BUILDERS = [
    ("muzzle_pistol",  build_vfx_muzzle_pistol),
    ("muzzle_rifle",   build_vfx_muzzle_rifle),
    ("muzzle_shotgun", build_vfx_muzzle_shotgun),
    ("muzzle_heavy",   build_vfx_muzzle_heavy),
    ("tracer_bullet",  build_vfx_tracer_bullet),
    ("tracer_pellet",  build_vfx_tracer_pellet_spread),
    ("shell_rifle",    build_vfx_shell_rifle),
    ("shell_shotgun",  build_vfx_shell_shotgun),
    ("smoke_puff",     build_vfx_smoke_puff),
    ("arrow_trail",    build_vfx_arrow_trail),
    ("melee_slash",    build_vfx_melee_slash),
    ("impact_spark",   build_vfx_impact_spark),
    ("impact_blood",   build_vfx_impact_blood),
]


def get_equipped_weapon_world_matrix(arm_obj, weapon_id):
    """Return posed world 4x4 matrix of the weapon currently bound to Hand (`+Z`=muzzle, `+Y`=up)."""
    bpy.context.view_layer.update()
    pb = arm_obj.pose.bones
    if weapon_id == "compound_bow":
        b_hand = pb["mixamorig:LeftHand"]
        grip_rest = tuple(arm_obj["left_grip_rest"])
        hold_mat = HOLD_MAT_LEFT
    elif weapon_id == "arrow":
        b_hand = pb["mixamorig:RightHand"]
        grip_rest = tuple(arm_obj.get("arrow_grip_rest", arm_obj["right_grip_rest"]))
        hold_mat = HOLD_MAT_RIGHT
    else:
        b_hand = pb["mixamorig:RightHand"]
        grip_rest = tuple(arm_obj["right_grip_rest"])
        hold_mat = HOLD_MAT_RIGHT

    return (
        arm_obj.matrix_world
        @ b_hand.matrix
        @ b_hand.bone.matrix_local.inverted()
        @ Matrix.Translation(Vector(grip_rest))
        @ hold_mat
    )


def _place_vfx(obj, world_mat, scale=1.0):
    obj.matrix_world = world_mat @ Matrix.Scale(scale, 4)


def spawn_weapon_vfx(arm_obj, weapon_id, materials, idx_map, collection, add_light=True):
    """Spawn weapon-matched VFX (muzzle flash, tracer, brass shell, smoke, bow trail, slash) in pose."""
    meta = WEAPON_META.get(weapon_id, WEAPON_META["m4"])
    profile = meta["vfx_profile"]
    spawned = []

    if profile == "bow":
        M_arr = get_equipped_weapon_world_matrix(arm_obj, "arrow")
        trail, _ = build_vfx_arrow_trail(materials, idx_map, collection=collection, name="Live_VFX_ArrowTrail")
        _place_vfx(trail, M_arr @ Matrix.Translation((0.0, 0.0, 0.34)))
        spawned.append(trail)
        return spawned

    M_wep = get_equipped_weapon_world_matrix(arm_obj, weapon_id)
    R_wep = M_wep.to_3x3().to_4x4()

    if profile == "melee":
        slash, _ = build_vfx_melee_slash(materials, idx_map, collection=collection, name="Live_VFX_Slash")
        jaw_w = M_wep @ Vector(meta["muzzle"])
        grip_w = M_wep.to_translation()
        swing_fwd = Vector((jaw_w.x - grip_w.x, jaw_w.y - grip_w.y, 0.0))
        if swing_fwd.length < 1e-4:
            swing_fwd = Vector((0.6, -0.8, 0.0))
        swing_fwd.normalize()
        sc = 0.95
        yaw = math.atan2(swing_fwd.y, swing_fwd.x) - math.radians(15.0)
        R_sl = Euler((math.radians(48.0), math.radians(-18.0), yaw), "XYZ").to_matrix().to_4x4()
        lead_local = Vector((0.42 * sc, 0.0, 0.0))
        slash_cen = jaw_w - (R_sl.to_3x3() @ lead_local)
        _place_vfx(slash, Matrix.Translation(slash_cen) @ R_sl, scale=sc)
        spawned.append(slash)

        spark, _ = build_vfx_impact_spark(materials, idx_map, collection=collection, name="Live_VFX_ImpactSpark")
        _place_vfx(spark, Matrix.Translation(jaw_w) @ R_wep, scale=0.95)
        spawned.append(spark)
        return spawned

    # Firearm VFX: muzzle flash, tracer, smoke puff, spent shell, dynamic bounce light
    flash_builders = {
        "pistol":  build_vfx_muzzle_pistol,
        "rifle":   build_vfx_muzzle_rifle,
        "shotgun": build_vfx_muzzle_shotgun,
        "heavy":   build_vfx_muzzle_heavy,
    }
    muzzle_w = M_wep @ Vector(meta["muzzle"])
    M_muzzle = Matrix.Translation(muzzle_w) @ R_wep

    flash_obj, _ = flash_builders[profile](materials, idx_map, collection=collection, name=f"Live_VFX_Flash_{weapon_id}")
    _place_vfx(flash_obj, M_muzzle)
    spawned.append(flash_obj)

    tracer_fn = build_vfx_tracer_pellet_spread if profile == "shotgun" else build_vfx_tracer_bullet
    tracer_obj, _ = tracer_fn(materials, idx_map, collection=collection, name=f"Live_VFX_Tracer_{weapon_id}")
    _place_vfx(tracer_obj, M_muzzle @ Matrix.Translation((0.0, 0.0, 0.24)))
    spawned.append(tracer_obj)

    smoke_obj, _ = build_vfx_smoke_puff(materials, idx_map, collection=collection, name=f"Live_VFX_Smoke_{weapon_id}")
    _place_vfx(smoke_obj, M_muzzle @ Matrix.Translation((0.0, 0.015, 0.04)) @ Euler((-0.25, 0.0, 0.0), "XYZ").to_matrix().to_4x4(),
               scale=1.15 if profile in ("shotgun", "heavy") else 0.85)
    spawned.append(smoke_obj)

    if meta.get("shell_type") and meta.get("ejection"):
        ej_w = M_wep @ Vector(meta["ejection"])
        sh_fn = build_vfx_shell_shotgun if meta["shell_type"] == "shotgun" else build_vfx_shell_rifle
        sh_obj, _ = sh_fn(materials, idx_map, collection=collection, name=f"Live_VFX_Shell_{weapon_id}")
        sh_off = (M_wep.to_3x3() @ Vector((-0.09, 0.08, -0.02)))
        M_sh = Matrix.Translation(ej_w + sh_off) @ R_wep @ Euler((0.6, 0.9, 0.4), "XYZ").to_matrix().to_4x4()
        _place_vfx(sh_obj, M_sh, scale=1.35)
        spawned.append(sh_obj)

    if add_light:
        ldata = bpy.data.lights.new(name=f"MuzzleLight_{weapon_id}", type="POINT")
        ldata.energy = 140.0 if profile in ("shotgun", "heavy") else (110.0 if profile == "rifle" else 75.0)
        ldata.color = (1.0, 0.68, 0.25)
        ldata.shadow_soft_size = 0.08
        lobj = bpy.data.objects.new(name=f"MuzzleLight_{weapon_id}", object_data=ldata)
        collection.objects.link(lobj)
        lobj.location = muzzle_w + (M_wep.to_3x3() @ Vector((0.0, 0.02, 0.06)))
        spawned.append(lobj)

    return spawned
