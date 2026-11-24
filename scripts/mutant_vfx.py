"""Modular stylized low-poly Mutant Combat VFX assets (pure-tri flat-shaded PBR, origin=(0,0,0), fwd=+Z)."""
import math
import bmesh
import bpy
from mathutils import Euler, Matrix, Vector

from mesh_utils import add_box, add_cone, add_cylinder, finalize_mesh, loft_rings, ring_perp


def _octa_puff(bm, center, rx, ry, rz, mat_idx):
    cx, cy, cz = center
    rings = [
        [(cx + rx * 0.25, cy, cz - rz), (cx, cy + ry * 0.25, cz - rz),
         (cx - rx * 0.25, cy, cz - rz), (cx, cy - ry * 0.25, cz - rz)],
        [(cx + rx, cy, cz), (cx, cy + ry, cz), (cx - rx, cy, cz), (cx, cy - ry, cz)],
        [(cx + rx * 0.25, cy, cz + rz), (cx, cy + ry * 0.25, cz + rz),
         (cx - rx * 0.25, cy, cz + rz), (cx, cy - ry * 0.25, cz + rz)],
    ]
    return loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_idx)


def _crescent_arc(bm, center, radius, arc_deg, width, thick, tilt_rot, mat_edge, mat_wake, n_seg=9):
    """Build a crisp tapered crescent energy slash blade in local XY arcing around `center` (+Z normal)."""
    c = Vector(center)
    rot_m = Euler(tilt_rot, "XYZ").to_matrix()
    rings = []
    start_a = -0.5 * math.radians(arc_deg)
    end_a = 0.5 * math.radians(arc_deg)
    for k in range(n_seg):
        frac = k / (n_seg - 1)
        ang = start_a + (end_a - start_a) * frac
        taper = math.sin(frac * math.pi)
        w = max(0.008, width * taper)
        h = max(0.004, thick * taper)
        r_dir = Vector((math.sin(ang), math.cos(ang), 0.0))
        mid = c + rot_m @ (r_dir * radius)
        out_v = rot_m @ r_dir
        up_v = rot_m @ Vector((0.0, 0.0, 1.0))
        rings.append([
            tuple(mid + out_v * (w * 0.65)),
            tuple(mid + up_v * h),
            tuple(mid - out_v * (w * 0.35)),
            tuple(mid - up_v * h),
        ])
    verts = loft_rings(bm, rings, close_caps=(True, True), mat_idx=mat_wake)
    for f in {fa for v in verts for fa in v.link_faces}:
        if (f.calc_center_median() - c).length > radius * 1.01:
            f.material_index = mat_edge
    return verts


def build_vfx_mutant_rafflesia(materials, idx_map, collection=None, name="VFX_Mutant_Rafflesia"):
    """Bioluminescent spore-mist burst cone + sweeping emerald vine-slash crescents (origin=(0,0,0), fwd=+Z)."""
    bm = bmesh.new()
    # Erupting toxic pollen cloud & spore needles along +Z
    add_cone(bm, (0.0, 0.0, 0.0), (0.0, 0.0, 0.52), 0.085, segments=6, mat_idx=idx_map["Mat_VfxSporeGlow"])
    for k in range(8):
        ang = (2.0 * math.pi * k) / 8.0
        r_m = 0.14 + 0.06 * (k % 2)
        cx, cy = math.cos(ang) * r_m, math.sin(ang) * r_m
        _octa_puff(bm, (cx, cy, 0.22 + 0.12 * (k % 3)), 0.068, 0.062, 0.075, idx_map["Mat_VfxSporeMist"])
        add_cone(
            bm, (cx * 0.35, cy * 0.35, 0.06), (cx * 1.65, cy * 1.65, 0.58 + 0.10 * (k % 2)),
            0.016, segments=4, mat_idx=idx_map["Mat_VfxSporeGlow"],
        )
    # Twin intersecting emerald whip-lash crescent energy trails
    _crescent_arc(bm, (0.0, 0.0, 0.18), 0.34, 130.0, 0.078, 0.018, (0.55, 0.45, 0.2), idx_map["Mat_VfxSporeGlow"], idx_map["Mat_ZLeafMid"])
    _crescent_arc(bm, (0.0, 0.0, 0.24), 0.30, 120.0, 0.072, 0.016, (0.55, -0.45, -0.2), idx_map["Mat_VfxSporeGlow"], idx_map["Mat_ZLeafMid"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_vfx_mutant_scythe(materials, idx_map, collection=None, name="VFX_Mutant_Scythe"):
    """Colossal crimson blood-energy reaper slash arc + kinetic blood-splatter shard spray."""
    bm = bmesh.new()
    # Huge twin-layered crimson cleave crescent sweeping forward along +Z
    _crescent_arc(bm, (0.0, 0.0, 0.04), 0.48, 155.0, 0.165, 0.024, (1.57, 0.32, 0.0), idx_map["Mat_VfxBloodCore"], idx_map["Mat_VfxBloodArc"], n_seg=11)
    _crescent_arc(bm, (0.0, 0.0, 0.12), 0.38, 125.0, 0.095, 0.016, (1.57, -0.22, 0.0), idx_map["Mat_VfxBloodCore"], idx_map["Mat_VfxBloodArc"], n_seg=9)
    # 10 Kinetic blood-shard darts erupting forward along cleave vector
    for k in range(10):
        ang = math.radians(-68.0 + k * 15.0)
        dx, dz = math.sin(ang), math.cos(ang)
        dy = 0.18 * math.sin(k * 1.9)
        r0 = 0.28 + 0.08 * (k % 2)
        add_cone(
            bm, (dx * r0, dy * 0.4, dz * r0), (dx * (r0 + 0.34), dy, dz * (r0 + 0.34)),
            0.016, segments=4, mat_idx=idx_map["Mat_VfxBloodCore" if k % 2 == 0 else "Mat_VfxBloodArc"],
        )
    return finalize_mesh(name, bm, materials, collection=collection)


def build_vfx_mutant_thorn(materials, idx_map, collection=None, name="VFX_Mutant_Thorn"):
    """3 hollow concentric pale-cyan sonic scream shockwave rings + 12 spiraling bone-razor barrage darts."""
    bm = bmesh.new()
    # 3 HOLLOW jagged sonic shockwave rings (open center via close_caps=(False, False)) advancing along +Z
    for r_i, (zz, r_in, r_out, th) in enumerate((
        (0.08, 0.09, 0.14, 0.014),
        (0.26, 0.18, 0.25, 0.016),
        (0.48, 0.29, 0.37, 0.018),
    )):
        n_ring = 12
        profile = (
            (r_in,  zz - th),
            (r_out, zz - th * 0.35),
            (r_out, zz + th * 0.35),
            (r_in,  zz + th),
            (r_in,  zz - th),
        )
        rings = [
            [(math.cos(2.0 * math.pi * i / n_ring) * (rad * (1.0 + 0.10 * ((i % 2) * 2 - 1))),
              math.sin(2.0 * math.pi * i / n_ring) * (rad * (1.0 + 0.10 * ((i % 2) * 2 - 1))),
              zc)
             for i in range(n_ring)]
            for rad, zc in profile
        ]
        loft_rings(
            bm, rings, close_caps=(False, False),
            mat_idx=idx_map["Mat_VfxShriekCore" if r_i < 2 else "Mat_ZSonicWave"],
        )
    # 12 spiraling launched bone-petal razor darts fanning forward & outward around hollow rings
    for k in range(12):
        ang = (2.0 * math.pi * k) / 12.0 + 0.25
        rad = 0.20 + 0.11 * (k % 3)
        px, py = math.cos(ang) * rad, math.sin(ang) * rad
        add_cone(
            bm, (px * 0.50, py * 0.50, 0.05 + 0.06 * (k % 3)),
            (px * 1.48, py * 1.48, 0.58 + 0.12 * (k % 2)),
            0.018, segments=4, mat_idx=idx_map["Mat_MShroudBone" if k % 2 == 0 else "Mat_VfxShriekCore"],
        )
    return finalize_mesh(name, bm, materials, collection=collection)


def build_vfx_mutant_arachnid(materials, idx_map, collection=None, name="VFX_Mutant_Arachnid"):
    """Pressurized neon-green corrosive acid spit lance + spray globules + venom splash."""
    bm = bmesh.new()
    # Central pressurized acid jet beam along +Z
    add_cone(bm, (0.0, 0.0, 0.0), (0.0, 0.0, 0.68), 0.068, segments=6, mat_idx=idx_map["Mat_VfxAcidCore"])
    add_cone(bm, (0.0, 0.0, 0.04), (0.0, 0.0, 0.42), 0.092, segments=6, mat_idx=idx_map["Mat_ZAcidGlow"])
    # Outer caustic splash ribs & 10 flying acid venom droplets
    for k in range(10):
        ang = (2.0 * math.pi * k) / 10.0
        r_d = 0.14 + 0.08 * (k % 2)
        dx, dy = math.cos(ang) * r_d, math.sin(ang) * r_d
        zz = 0.18 + 0.14 * (k % 3)
        _octa_puff(bm, (dx, dy, zz), 0.032, 0.032, 0.046, idx_map["Mat_VfxAcidCore" if k % 2 == 0 else "Mat_ZAcidGlow"])
        add_cone(bm, (dx * 0.35, dy * 0.35, 0.04), (dx * 1.55, dy * 1.55, zz + 0.28), 0.014, segments=4, mat_idx=idx_map["Mat_ZAcidGlow"])
    return finalize_mesh(name, bm, materials, collection=collection)


def build_vfx_mutant_juggernaut(materials, idx_map, collection=None, name="VFX_Mutant_Juggernaut"):
    """Ground-shattering seismic molten-bile crater shockwave + flying armor/stone chunks + geyser spikes."""
    bm = bmesh.new()
    # 2 Hollow jagged ground shockwave rings expanding flat on XY (+Z up)
    for r_i, (zz, r_in, r_out, th) in enumerate((
        (0.05, 0.24, 0.36, 0.035),
        (0.08, 0.48, 0.64, 0.045),
    )):
        n_ring = 14
        profile = (
            (r_in,  zz - th * 0.4),
            (r_out, zz - th * 0.2),
            (r_out, zz + th * 0.6),
            (r_in,  zz + th * 0.9),
            (r_in,  zz - th * 0.4),
        )
        rings = [
            [(math.cos(2.0 * math.pi * i / n_ring) * (rad * (1.0 + 0.14 * ((i % 2) * 2 - 1))),
              math.sin(2.0 * math.pi * i / n_ring) * (rad * (1.0 + 0.14 * ((i % 2) * 2 - 1))),
              max(0.01, zc))
             for i in range(n_ring)]
            for rad, zc in profile
        ]
        loft_rings(bm, rings, close_caps=(False, False), mat_idx=idx_map["Mat_VfxBileCore" if r_i == 0 else "Mat_MBileGlow"])

    # 10 Erupting bile geyser spikes & flying shattered boulder chunks rising outward
    for k in range(10):
        ang = (2.0 * math.pi * k) / 10.0
        r0 = 0.26 + 0.12 * (k % 2)
        dx, dy = math.cos(ang), math.sin(ang)
        add_cone(
            bm, (dx * r0, dy * r0, 0.02), (dx * (r0 + 0.36), dy * (r0 + 0.36), 0.44 + 0.16 * (k % 2)),
            0.032, segments=4, mat_idx=idx_map["Mat_VfxBileCore" if k % 2 == 0 else "Mat_MBileGlow"],
        )
        add_box(
            bm, center=(dx * (r0 + 0.16), dy * (r0 + 0.16), 0.26 + 0.14 * (k % 3)),
            size=(0.085, 0.075, 0.070), rot=(k * 0.5, k * 0.8, ang),
            bevel=0.010, mat_idx=idx_map["Mat_MTankArmor" if k % 2 == 0 else "Mat_MChitinMid"],
        )
    return finalize_mesh(name, bm, materials, collection=collection)


ALL_MUTANT_VFX_BUILDERS = [
    ("mutant_rafflesia",       build_vfx_mutant_rafflesia),
    ("mutant_scythe_stalker",  build_vfx_mutant_scythe),
    ("mutant_thorn_shroud",    build_vfx_mutant_thorn),
    ("mutant_arachnid_maw",    build_vfx_mutant_arachnid),
    ("mutant_bile_juggernaut", build_vfx_mutant_juggernaut),
]

MUTANT_VFX_MAP = {
    "rafflesia":       (build_vfx_mutant_rafflesia, (0.65, 1.00, 0.30)),
    "scythe_stalker":  (build_vfx_mutant_scythe,    (1.00, 0.22, 0.18)),
    "thorn_shroud":    (build_vfx_mutant_thorn,     (0.75, 0.90, 1.00)),
    "arachnid_maw":    (build_vfx_mutant_arachnid,  (0.78, 1.00, 0.22)),
    "bile_juggernaut": (build_vfx_mutant_juggernaut,(1.00, 0.58, 0.14)),
}


def spawn_mutant_vfx(arm_obj, slug, materials, idx_map, collection, add_light=True):
    """Spawn a creature's multi-part Combat VFX aligned directly to its live posed mouth/weapon/tentacle bones."""
    if slug not in MUTANT_VFX_MAP:
        return []
    builder, glow_rgb = MUTANT_VFX_MAP[slug]
    bpy.context.view_layer.update()

    def _bone_pos(bname, tail=False, fallback=(0.0, -0.35, 0.95)):
        pb = arm_obj.pose.bones.get(bname)
        if pb is None:
            return Vector(fallback)
        mat = arm_obj.matrix_world @ pb.matrix
        if tail:
            return mat @ Vector((0.0, pb.length, 0.0))
        return mat.to_translation()

    spawned = []
    # Main VFX burst positioned in front of creature's mouth/weapon pointing along attack forward (-Y / slightly down or up)
    head_p = _bone_pos("Head")
    if slug == "scythe_stalker":
        anchor = _bone_pos("Scythe_Blade") + Vector((-0.04, -0.18, -0.04))
        rot_e = Euler((math.radians(92.0), 0.0, 0.0), "XYZ")
    elif slug == "thorn_shroud":
        anchor = head_p + Vector((0.0, -0.22, -0.02))
        rot_e = Euler((math.radians(82.0), 0.0, 0.0), "XYZ")
    elif slug == "arachnid_maw":
        anchor = head_p + Vector((0.0, -0.24, -0.02))
        rot_e = Euler((math.radians(96.0), 0.0, 0.0), "XYZ")
    elif slug == "bile_juggernaut":
        fist_r = _bone_pos("Arm_R_Hand")
        fist_l = _bone_pos("Arm_L_Hand")
        anchor = Vector((0.5 * (fist_r.x + fist_l.x), min(fist_r.y, fist_l.y) - 0.12, 0.02))
        rot_e = Euler((0.0, 0.0, 0.0), "XYZ")
    else:  # rafflesia
        anchor = head_p + Vector((0.0, -0.24, -0.04))
        rot_e = Euler((math.radians(95.0), 0.0, 0.0), "XYZ")

    vfx_obj, _ = builder(materials, idx_map, collection=collection, name=f"QA_VFX_{slug}")
    vfx_obj.location = anchor
    vfx_obj.rotation_mode = "XYZ"
    vfx_obj.rotation_euler = rot_e
    vfx_obj.scale = Vector((1.15, 1.15, 1.15))
    spawned.append(vfx_obj)

    # Extra creature-specific secondary combat VFX accents on tentacle tips / scorpion stinger / razor wings
    if slug == "rafflesia":
        for vb in ("Vine_Main_L_06", "Vine_Main_R_06"):
            vp = _bone_pos(vb, tail=True)
            v2, _ = build_vfx_mutant_rafflesia(materials, idx_map, collection=collection, name=f"QA_VFX_{vb}")
            v2.location = vp
            v2.rotation_mode = "XYZ"
            v2.rotation_euler = Euler((math.radians(78.0), 0.0, math.radians(-22.0 if "_L_" in vb else 22.0)), "XYZ")
            v2.scale = Vector((0.52, 0.52, 0.52))
            spawned.append(v2)
    elif slug == "arachnid_maw":
        tp = _bone_pos("Tail_04", tail=True)
        v2, _ = build_vfx_mutant_arachnid(materials, idx_map, collection=collection, name="QA_VFX_Stinger")
        v2.location = tp + Vector((0.0, -0.06, -0.02))
        v2.rotation_mode = "XYZ"
        v2.rotation_euler = Euler((math.radians(118.0), 0.0, 0.0), "XYZ")
        v2.scale = Vector((0.55, 0.55, 0.55))
        spawned.append(v2)

    if add_light:
        ldata = bpy.data.lights.new(name=f"QA_VfxLight_{slug}", type="POINT")
        ldata.color = glow_rgb
        ldata.energy = 160.0
        ldata.shadow_soft_size = 0.25
        lobj = bpy.data.objects.new(name=f"QA_VfxLight_{slug}", object_data=ldata)
        lobj.location = anchor + Vector((0.0, -0.15, 0.12))
        collection.objects.link(lobj)
        spawned.append(lobj)

    return spawned
