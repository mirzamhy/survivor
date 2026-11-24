"""Custom non-humanoid Creature Armature, smooth multi-bone chain skinning & animation system."""
import math
import bpy
from mathutils import Euler, Matrix, Quaternion, Vector


def create_creature_armature(name, bone_specs, collection=None):
    """Build a custom hierarchy armature from `[(bone_name, parent_name, head_xyz, tail_xyz, use_deform), ...]`."""
    arm_data = bpy.data.armatures.new(f"{name}_Data")
    arm_data.display_type = "STICK"
    arm_obj = bpy.data.objects.new(name, arm_data)
    target_col = collection if collection is not None else bpy.context.scene.collection
    target_col.objects.link(arm_obj)
    arm_obj["rig_type"] = "creature"
    arm_obj.show_in_front = True

    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    created = {}

    for bname, pname, head_xyz, tail_xyz, use_deform in bone_specs:
        b = eb.new(bname)
        h = Vector(head_xyz)
        t = Vector(tail_xyz)
        if (t - h).length < 1e-4:
            t = h + Vector((0.0, 0.0, 0.05))
        b.head = h
        b.tail = t
        b.use_connect = False
        b.use_deform = use_deform
        if pname is not None and pname in created:
            b.parent = created[pname]
        created[bname] = b

    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_obj


def _project_point_segment(pt, a, b):
    ab = b - a
    len_sq = ab.length_squared
    if len_sq < 1e-10:
        return 0.0, (pt - a).length
    u = max(0.0, min(1.0, (pt - a).dot(ab) / len_sq))
    closest = a + ab * u
    return u, (pt - closest).length


def skin_creature_to_armature(
    body_obj, arm_obj, chain_assignments, single_bone_assignments, fallback_bone="Pelvis",
):
    """Bind `body_obj` cleanly to `arm_obj` using smooth multi-bone chain blending & strict <=4 weights."""
    vgroups = {
        b.name: body_obj.vertex_groups.new(name=b.name)
        for b in arm_obj.data.bones
        if b.use_deform
    }
    bone_segs = {
        b.name: (b.head_local.copy(), b.tail_local.copy())
        for b in arm_obj.data.bones
        if b.use_deform
    }

    mesh_verts = body_obj.data.vertices
    assigned = set()

    # 1. Rigid single-bone clusters first (jaws, head cranium/crown) so split jaws stay sharp
    for bname, v_indices in single_bone_assignments.items():
        vg = vgroups.get(bname)
        if vg is None:
            continue
        for vi in v_indices:
            if vi in assigned:
                continue
            vg.add([vi], 1.0, "REPLACE")
            assigned.add(vi)

    # 2. Smooth flexible multi-bone chain skinning (legs, stalk spine, sinuous plant whip vines)
    blend_band = 0.24
    for bone_chain, v_indices in chain_assignments:
        segs = [bone_segs[bn] for bn in bone_chain if bn in bone_segs]
        names = [bn for bn in bone_chain if bn in bone_segs]
        if not segs:
            continue
        m = len(segs)
        for vi in v_indices:
            if vi in assigned:
                continue
            co = mesh_verts[vi].co
            best_k = 0
            best_u = 0.0
            best_d = 1e9
            for k, (ha, tb) in enumerate(segs):
                u, d = _project_point_segment(co, ha, tb)
                if d < best_d:
                    best_d = d
                    best_k = k
                    best_u = u

            weights = {names[best_k]: 1.0}
            if m > 1:
                if best_u < blend_band and best_k > 0:
                    w_prev = 0.5 * (1.0 - best_u / blend_band)
                    weights[names[best_k]] = 1.0 - w_prev
                    weights[names[best_k - 1]] = w_prev
                elif best_u > (1.0 - blend_band) and best_k < (m - 1):
                    w_next = 0.5 * ((best_u - (1.0 - blend_band)) / blend_band)
                    weights[names[best_k]] = 1.0 - w_next
                    weights[names[best_k + 1]] = w_next

            tot = sum(weights.values())
            for bn, wt in weights.items():
                if wt > 1e-4:
                    vgroups[bn].add([vi], wt / tot, "REPLACE")
            assigned.add(vi)

    # 3. Guarantee 100% vertex coverage
    fb_vg = vgroups.get(fallback_bone) or next(iter(vgroups.values()))
    for v in mesh_verts:
        if v.index not in assigned:
            fb_vg.add([v.index], 1.0, "REPLACE")

    body_obj.parent = arm_obj
    mod = body_obj.modifiers.new(name="Armature", type="ARMATURE")
    mod.object = arm_obj


def reset_creature_pose(pb):
    """Reset all pose bones to rest transform."""
    for b in pb:
        b.location = Vector((0.0, 0.0, 0.0))
        b.rotation_mode = "XYZ"
        b.rotation_euler = Euler((0.0, 0.0, 0.0), "XYZ")
        b.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))


def _rot_bone_world(pb, name, deg_xyz):
    """Apply an XYZ Euler rotation defined in armature world orientation around bone rest head pivot."""
    b = pb.get(name)
    if b is None:
        return
    rx, ry, rz = (math.radians(a) for a in deg_xyz)
    r_world = Euler((rx, ry, rz), "XYZ").to_matrix()
    m_local = b.bone.matrix_local.to_3x3()
    r_local = m_local.inverted() @ r_world @ m_local
    b.rotation_mode = "QUATERNION"
    b.rotation_quaternion = r_local.to_quaternion()


def snap_creature_to_floor(arm_obj, body_obj, floor_z=0.0):
    """Drop/lift Pelvis Z so lowest deformed mesh vertex sits cleanly on `floor_z`."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    eval_obj = body_obj.evaluated_get(dg)
    me = eval_obj.to_mesh()
    mat = body_obj.matrix_world
    min_z = min((mat @ v.co).z for v in me.vertices)
    eval_obj.to_mesh_clear()

    dz = floor_z - min_z
    pelvis = arm_obj.pose.bones.get("Pelvis")
    if pelvis is not None:
        # Transform world Z shift into Pelvis parent/rest space (Pelvis has parent=None, vertical +Z rest)
        m_inv = pelvis.bone.matrix_local.to_3x3().inverted()
        pelvis.location = pelvis.location + (m_inv @ Vector((0.0, 0.0, dz)))
    bpy.context.view_layer.update()


def _pose_vine_chain(pb, prefix, n_bones, sx, base_deg, wave_deg, curl_deg):
    """Apply progressive S-wave rotation down a flexible multi-bone tentacle chain."""
    for k in range(1, n_bones + 1):
        bname = f"{prefix}_{k:02d}"
        frac = (k - 1) / max(1, n_bones - 1)
        px = base_deg[0] * (1.0 - 0.35 * frac) + wave_deg[0] * math.sin(frac * math.pi * 1.4) + curl_deg[0] * frac
        py = (base_deg[1] + wave_deg[1] * math.cos(frac * math.pi * 1.2) + curl_deg[1] * frac) * sx
        pz = (base_deg[2] + wave_deg[2] * math.sin(frac * math.pi) + curl_deg[2] * frac) * sx
        _rot_bone_world(pb, bname, (px, py, pz))


def apply_rafflesia_creature_pose(arm_obj, body_obj, stage="idle", phase=0.0):
    """Apply non-humanoid quadruped plant-beast poses (`idle`, `stalk`, `lunge_bite`, `vine_thrash`, `death`)."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_creature_pose(pb)
    tau = 2.0 * math.pi * phase

    if stage == "idle":
        sway = math.sin(tau)
        breathe = math.cos(tau)
        _rot_bone_world(pb, "Pelvis",   (3.0 * breathe, 2.5 * sway, 3.0 * sway))
        _rot_bone_world(pb, "Stalk_01", (6.0 + 3.0 * breathe, -3.0 * sway, 2.0 * sway))
        _rot_bone_world(pb, "Stalk_02", (6.0 + 2.5 * breathe, -2.0 * sway, -3.0 * sway))
        _rot_bone_world(pb, "Neck",     (-8.0 - 2.0 * breathe, 3.0 * sway, -3.0 * sway))
        _rot_bone_world(pb, "Head",     (-6.0 + 3.0 * sway, 2.0 * breathe, 6.0 * sway))

        # Threatening rhythmic gape on the 4-lobed beak-maw even in idle
        jaw_open = 10.0 + 5.0 * (0.5 + 0.5 * breathe)
        _rot_bone_world(pb, "Jaw_Top", (-jaw_open * 0.85, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_Bot", ( jaw_open * 1.05, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_L",   (0.0, 0.0,  jaw_open * 0.80))
        _rot_bone_world(pb, "Jaw_R",   (0.0, 0.0, -jaw_open * 0.80))

        for side, sx in (("L", 1.0), ("R", -1.0)):
            # Negative Y rotation lifts +X tentacles UP into dramatic U-shaped thorny arms
            _pose_vine_chain(pb, f"Vine_Main_{side}", 6, sx,
                             base_deg=(4.0 * breathe, -6.0, 8.0),
                             wave_deg=(8.0 * sway, -6.0 * breathe, 10.0 * sway),
                             curl_deg=(6.0, -14.0 - 5.0 * breathe, -10.0))
            _pose_vine_chain(pb, f"Vine_Mid_{side}", 5, sx,
                             base_deg=(-6.0, -4.0, 10.0),
                             wave_deg=(10.0 * breathe, -5.0 * sway, 8.0 * breathe),
                             curl_deg=(-6.0, -10.0, 6.0))
            _pose_vine_chain(pb, f"Vine_Back_{side}", 4, sx,
                             base_deg=(6.0 * sway, -4.0, -6.0),
                             wave_deg=(6.0 * breathe, -4.0 * sway, 6.0),
                             curl_deg=(6.0, -10.0, -8.0))

    elif stage == "stalk":
        stride = math.sin(tau)
        lift = max(0.0, math.cos(tau))
        _rot_bone_world(pb, "Pelvis",   (6.0, 4.0 * stride, 5.0 * stride))
        _rot_bone_world(pb, "Stalk_01", (14.0, -4.0 * stride, -4.0 * stride))
        _rot_bone_world(pb, "Stalk_02", (12.0, -3.0 * stride, 3.0 * stride))
        _rot_bone_world(pb, "Neck",     (-16.0, 4.0 * stride, 2.0 * stride))
        _rot_bone_world(pb, "Head",     (-12.0, 0.0, 8.0 * stride))

        _rot_bone_world(pb, "Jaw_Top", (-18.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_Bot", ( 22.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_L",   (0.0, 0.0,  16.0))
        _rot_bone_world(pb, "Jaw_R",   (0.0, 0.0, -16.0))

        # Diagonal gait across all 4 crawling root legs (FL+BR vs FR+BL)
        for leg, s_sgn, fy in (("Leg_FL", 1.0, 1.0), ("Leg_BR", 1.0, -1.0), ("Leg_FR", -1.0, 1.0), ("Leg_BL", -1.0, -1.0)):
            step = stride * s_sgn
            l_up = max(0.0, math.cos(tau) * s_sgn)
            sx = 1.0 if leg.endswith("L") else -1.0
            _rot_bone_world(pb, f"{leg}_Thigh", (12.0 * l_up * fy, -14.0 * l_up * sx, 16.0 * step))
            _rot_bone_world(pb, f"{leg}_Shin",  (8.0 * l_up * fy, 16.0 * l_up * sx, -6.0 * step))
            _rot_bone_world(pb, f"{leg}_Foot",  (-14.0 * l_up * fy, 0.0, 0.0))

        for side, sx in (("L", 1.0), ("R", -1.0)):
            _pose_vine_chain(pb, f"Vine_Main_{side}", 6, sx,
                             base_deg=(12.0, 6.0, 14.0),
                             wave_deg=(10.0 * stride, 8.0 * lift, 12.0 * stride),
                             curl_deg=(8.0, 14.0, 10.0))
            _pose_vine_chain(pb, f"Vine_Mid_{side}", 5, sx,
                             base_deg=(10.0, 4.0, 18.0),
                             wave_deg=(12.0 * lift, 6.0, 10.0 * stride),
                             curl_deg=(4.0, 12.0, 12.0))
            _pose_vine_chain(pb, f"Vine_Back_{side}", 4, sx,
                             base_deg=(8.0, 2.0, 8.0),
                             wave_deg=(8.0 * stride, 8.0, 8.0),
                             curl_deg=(6.0, 10.0, 6.0))

    elif stage == "lunge_bite":
        # Explosive forward crouch with 4-lobed fanged beak-maw gaping WIDE OPEN
        _rot_bone_world(pb, "Pelvis",   (16.0, 0.0, 0.0))
        _rot_bone_world(pb, "Stalk_01", (20.0, 0.0, 0.0))
        _rot_bone_world(pb, "Stalk_02", (18.0, 0.0, 0.0))
        _rot_bone_world(pb, "Neck",     (-14.0, 0.0, 0.0))
        _rot_bone_world(pb, "Head",     (-22.0, 0.0, 0.0))

        _rot_bone_world(pb, "Jaw_Top", (-28.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_Bot", ( 34.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_L",   (0.0, 0.0,  26.0))
        _rot_bone_world(pb, "Jaw_R",   (0.0, 0.0, -26.0))

        for leg, sx in (("Leg_FL", 1.0), ("Leg_FR", -1.0)):
            _rot_bone_world(pb, f"{leg}_Thigh", (-10.0, -10.0 * sx, -12.0 * sx))
            _rot_bone_world(pb, f"{leg}_Shin",  (  8.0,  14.0 * sx,   6.0 * sx))
        for leg, sx in (("Leg_BL", 1.0), ("Leg_BR", -1.0)):
            _rot_bone_world(pb, f"{leg}_Thigh", (-16.0,  10.0 * sx,  10.0 * sx))
            _rot_bone_world(pb, f"{leg}_Shin",  ( 14.0, -12.0 * sx,  -6.0 * sx))

        for side, sx in (("L", 1.0), ("R", -1.0)):
            _pose_vine_chain(pb, f"Vine_Main_{side}", 6, sx,
                             base_deg=(10.0, 4.0, 20.0),
                             wave_deg=(12.0, 10.0, 14.0),
                             curl_deg=(8.0, 16.0, 16.0))
            _pose_vine_chain(pb, f"Vine_Mid_{side}", 5, sx,
                             base_deg=(14.0, 6.0, 22.0),
                             wave_deg=(10.0, 8.0, 12.0),
                             curl_deg=(6.0, 12.0, 14.0))
            _pose_vine_chain(pb, f"Vine_Back_{side}", 4, sx,
                             base_deg=(12.0, -6.0, 14.0),
                             wave_deg=(8.0, 6.0, 10.0),
                             curl_deg=(10.0, 10.0, 10.0))

    elif stage == "vine_thrash":
        # Massive predatory rear-up + 6 thorny tentacles whipping violently forward & flaring around roaring maw
        _rot_bone_world(pb, "Pelvis",   (-8.0, 0.0, 0.0))
        _rot_bone_world(pb, "Stalk_01", (16.0, 0.0, -6.0))
        _rot_bone_world(pb, "Stalk_02", (14.0, 0.0, -4.0))
        _rot_bone_world(pb, "Neck",     (-18.0, 0.0, 6.0))
        _rot_bone_world(pb, "Head",     (-12.0, 0.0, 6.0))

        _rot_bone_world(pb, "Jaw_Top", (-30.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_Bot", ( 34.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_L",   (0.0, 0.0,  28.0))
        _rot_bone_world(pb, "Jaw_R",   (0.0, 0.0, -28.0))

        for leg, sx in (("Leg_FL", 1.0), ("Leg_FR", -1.0)):
            _rot_bone_world(pb, f"{leg}_Thigh", ( 6.0,  8.0 * sx, 18.0 * sx))
            _rot_bone_world(pb, f"{leg}_Shin",  (-4.0, -10.0 * sx, -6.0 * sx))
        for leg, sx in (("Leg_BL", 1.0), ("Leg_BR", -1.0)):
            _rot_bone_world(pb, f"{leg}_Thigh", (-12.0, -8.0 * sx, -14.0 * sx))
            _rot_bone_world(pb, f"{leg}_Shin",  ( 10.0, 10.0 * sx,   4.0 * sx))

        for side, sx in (("L", 1.0), ("R", -1.0)):
            _pose_vine_chain(pb, f"Vine_Main_{side}", 6, sx,
                             base_deg=(24.0, -8.0, 26.0),
                             wave_deg=(14.0, -8.0, 12.0),
                             curl_deg=(10.0, -14.0, 14.0))
            _pose_vine_chain(pb, f"Vine_Mid_{side}", 5, sx,
                             base_deg=(26.0, -6.0, 22.0),
                             wave_deg=(12.0, -6.0, 10.0),
                             curl_deg=(8.0, -12.0, 12.0))
            _pose_vine_chain(pb, f"Vine_Back_{side}", 4, sx,
                             base_deg=(18.0, -6.0, 24.0),
                             wave_deg=(10.0, -4.0, 12.0),
                             curl_deg=(6.0, -10.0, 14.0))

    else:  # death
        _rot_bone_world(pb, "Pelvis",   (22.0, 8.0, 0.0))
        _rot_bone_world(pb, "Stalk_01", (28.0, 10.0, 0.0))
        _rot_bone_world(pb, "Stalk_02", (26.0, 8.0, 0.0))
        _rot_bone_world(pb, "Neck",     (14.0, 6.0, 0.0))
        _rot_bone_world(pb, "Head",     (12.0, 8.0, 14.0))
        for leg, sx in (("Leg_FL", 1.0), ("Leg_FR", -1.0), ("Leg_BL", 1.0), ("Leg_BR", -1.0)):
            _rot_bone_world(pb, f"{leg}_Thigh", (0.0, -24.0 * sx, 0.0))
            _rot_bone_world(pb, f"{leg}_Shin",  (0.0,  28.0 * sx, 0.0))
        for side, sx in (("L", 1.0), ("R", -1.0)):
            _pose_vine_chain(pb, f"Vine_Main_{side}", 6, sx, (10.0, -18.0, 4.0), (4.0, -6.0, 4.0), (4.0, -12.0, 0.0))
            _pose_vine_chain(pb, f"Vine_Mid_{side}", 5, sx,  (12.0, -16.0, 6.0), (4.0, -4.0, 4.0), (6.0, -10.0, 0.0))
            _pose_vine_chain(pb, f"Vine_Back_{side}", 4, sx, (10.0, -16.0, -4.0), (4.0, -4.0, 0.0), (6.0, -10.0, 0.0))

    snap_creature_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_scythe_stalker_pose(arm_obj, body_obj, stage="idle", phase=0.0):
    """Apply hunched digitigrade Scythe Stalker poses (`idle`, `stalk`, `slash`, `reaper_lunge`, `death`)."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_creature_pose(pb)
    tau = 2.0 * math.pi * phase
    sway = math.sin(tau)
    br = math.cos(tau)

    if stage == "idle":
        _rot_bone_world(pb, "Pelvis",          (4.0, 2.0 * sway, 3.0 * sway))
        _rot_bone_world(pb, "Spine_01",        (6.0 + 3.0 * br, 0.0, 2.0 * sway))
        _rot_bone_world(pb, "Spine_02",        (8.0 + 3.0 * br, 2.0 * sway, -4.0))
        _rot_bone_world(pb, "Hunch_Neck",      (-10.0, 4.0 * sway, 8.0))
        _rot_bone_world(pb, "Head",            (-6.0, 6.0 * sway, 10.0))
        _rot_bone_world(pb, "Mandible_L",      (0.0, 0.0,  10.0 + 6.0 * br))
        _rot_bone_world(pb, "Mandible_R",      (0.0, 0.0, -10.0 - 6.0 * br))
        _rot_bone_world(pb, "Jaw_Bot",         (12.0 + 5.0 * br, 0.0, 0.0))
        _rot_bone_world(pb, "Tongue_01",       (8.0 + 6.0 * sway, 0.0, 6.0 * sway))
        _rot_bone_world(pb, "Tongue_02",       (12.0 * br, 0.0, -8.0 * sway))
        # Negative X swings downward limb (-Z) FORWARD (-Y)
        _rot_bone_world(pb, "Scythe_Shoulder", (0.0, -6.0, -6.0))
        _rot_bone_world(pb, "Scythe_Upper",    (-14.0 - 6.0 * br, -8.0, 12.0))
        _rot_bone_world(pb, "Scythe_Fore",     (-16.0, 10.0, 18.0))
        _rot_bone_world(pb, "Scythe_Blade",    (-12.0, 6.0, 12.0))
        _rot_bone_world(pb, "Scythe_Hook",     (-8.0, 0.0, 8.0))
        _rot_bone_world(pb, "Clutch_Shoulder", (0.0, 6.0, 8.0))
        _rot_bone_world(pb, "Clutch_Upper",    (-22.0, 10.0, -14.0))
        _rot_bone_world(pb, "Clutch_Fore",     (-28.0 - 6.0 * br, 6.0, -18.0))
        _rot_bone_world(pb, "Clutch_Hand",     (-18.0, 0.0, -12.0))
    elif stage == "stalk":
        for leg, s_s in (("Leg_L", 1.0), ("Leg_R", -1.0)):
            step = sway * s_s
            lift = max(0.0, br * s_s)
            _rot_bone_world(pb, f"{leg}_Thigh", (18.0 * step + 10.0 * lift, 0.0, 0.0))
            _rot_bone_world(pb, f"{leg}_Shin",  (-12.0 * step - 14.0 * lift, 0.0, 0.0))
            _rot_bone_world(pb, f"{leg}_Ankle", (12.0 * lift, 0.0, 0.0))
        _rot_bone_world(pb, "Pelvis",          (8.0, 4.0 * sway, 6.0 * sway))
        _rot_bone_world(pb, "Spine_01",        (10.0, -4.0 * sway, -4.0 * sway))
        _rot_bone_world(pb, "Spine_02",        (10.0, -3.0 * sway, 0.0))
        _rot_bone_world(pb, "Hunch_Neck",      (-16.0, 0.0, 6.0))
        _rot_bone_world(pb, "Head",            (-10.0, 0.0, 12.0 * sway))
        _rot_bone_world(pb, "Mandible_L",      (0.0, 0.0,  22.0))
        _rot_bone_world(pb, "Mandible_R",      (0.0, 0.0, -22.0))
        _rot_bone_world(pb, "Jaw_Bot",         (22.0, 0.0, 0.0))
        _rot_bone_world(pb, "Tongue_01",       (12.0, 0.0, 10.0 * sway))
        _rot_bone_world(pb, "Scythe_Upper",    (-18.0 * sway - 14.0, -10.0, 16.0))
        _rot_bone_world(pb, "Scythe_Fore",     (-18.0, 8.0, 22.0))
        _rot_bone_world(pb, "Scythe_Blade",    (-16.0, 4.0, 14.0))
        _rot_bone_world(pb, "Clutch_Upper",    (-24.0, 12.0, -18.0))
        _rot_bone_world(pb, "Clutch_Fore",     (-30.0, 8.0, -22.0))
    elif stage == "slash":
        _rot_bone_world(pb, "Pelvis",          (10.0, 0.0, 18.0))
        _rot_bone_world(pb, "Spine_01",        (10.0, 4.0, 14.0))
        _rot_bone_world(pb, "Spine_02",        (10.0, 6.0, 12.0))
        _rot_bone_world(pb, "Hunch_Neck",      (-18.0, 0.0, -22.0))
        _rot_bone_world(pb, "Head",            (-12.0, 6.0, -18.0))
        _rot_bone_world(pb, "Mandible_L",      (0.0, 0.0,  32.0))
        _rot_bone_world(pb, "Mandible_R",      (0.0, 0.0, -32.0))
        _rot_bone_world(pb, "Jaw_Bot",         (28.0, 0.0, 0.0))
        _rot_bone_world(pb, "Tongue_01",       (18.0, 0.0, 12.0))
        _rot_bone_world(pb, "Tongue_02",       (16.0, 0.0, -14.0))
        _rot_bone_world(pb, "Scythe_Shoulder", (0.0, -14.0, 28.0))
        _rot_bone_world(pb, "Scythe_Upper",    (-44.0, 10.0, 32.0))
        _rot_bone_world(pb, "Scythe_Fore",     (-28.0, 14.0, 24.0))
        _rot_bone_world(pb, "Scythe_Blade",    (-22.0, 10.0, 16.0))
        _rot_bone_world(pb, "Clutch_Upper",    (-28.0, 16.0, -24.0))
        _rot_bone_world(pb, "Clutch_Fore",     (-32.0, 10.0, -18.0))
    elif stage == "reaper_lunge":
        _rot_bone_world(pb, "Pelvis",          (16.0, 0.0, -20.0))
        _rot_bone_world(pb, "Spine_01",        (14.0, -6.0, -14.0))
        _rot_bone_world(pb, "Spine_02",        (12.0, -6.0, -12.0))
        _rot_bone_world(pb, "Hunch_Neck",      (-20.0, 0.0, 24.0))
        _rot_bone_world(pb, "Head",            (-16.0, -8.0, 20.0))
        _rot_bone_world(pb, "Mandible_L",      (0.0, 0.0,  34.0))
        _rot_bone_world(pb, "Mandible_R",      (0.0, 0.0, -34.0))
        _rot_bone_world(pb, "Jaw_Bot",         (32.0, 0.0, 0.0))
        _rot_bone_world(pb, "Tongue_01",       (20.0, 0.0, -10.0))
        _rot_bone_world(pb, "Tongue_02",       (18.0, 0.0, 14.0))
        _rot_bone_world(pb, "Leg_L_Thigh",     (-22.0, 0.0, 10.0))
        _rot_bone_world(pb, "Leg_L_Shin",      (18.0, 0.0, 0.0))
        _rot_bone_world(pb, "Leg_R_Thigh",     (24.0, 0.0, -10.0))
        _rot_bone_world(pb, "Leg_R_Shin",      (-16.0, 0.0, 0.0))
        _rot_bone_world(pb, "Scythe_Shoulder", (0.0, -18.0, -24.0))
        _rot_bone_world(pb, "Scythe_Upper",    (-58.0, -12.0, -24.0))
        _rot_bone_world(pb, "Scythe_Fore",     (-36.0, 8.0, 14.0))
        _rot_bone_world(pb, "Scythe_Blade",    (-24.0, 6.0, 18.0))
        _rot_bone_world(pb, "Clutch_Upper",    (-34.0, 16.0, -28.0))
        _rot_bone_world(pb, "Clutch_Fore",     (-36.0, 10.0, -20.0))
    else:  # death
        _rot_bone_world(pb, "Pelvis",          (36.0, 14.0, 0.0))
        _rot_bone_world(pb, "Spine_01",        (24.0, 8.0, 0.0))
        _rot_bone_world(pb, "Spine_02",        (22.0, 6.0, 0.0))
        _rot_bone_world(pb, "Head",            (16.0, 10.0, 18.0))
        _rot_bone_world(pb, "Leg_L_Thigh",     (-38.0, 0.0, 0.0))
        _rot_bone_world(pb, "Leg_L_Shin",      (44.0, 0.0, 0.0))
        _rot_bone_world(pb, "Leg_R_Thigh",     (-34.0, 0.0, 0.0))
        _rot_bone_world(pb, "Leg_R_Shin",      (42.0, 0.0, 0.0))
        _rot_bone_world(pb, "Scythe_Upper",    (-18.0, -24.0, 0.0))

    snap_creature_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_thorn_shroud_pose(arm_obj, body_obj, stage="idle", phase=0.0):
    """Apply eerie tri-stilt Thorn Shroud Seraph poses (`idle`, `stalk`, `sweep`, `razor_bloom`, `death`)."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_creature_pose(pb)
    tau = 2.0 * math.pi * phase
    sway = math.sin(tau)
    br = math.cos(tau)

    if stage == "idle":
        _rot_bone_world(pb, "Pelvis",      (-2.0, 3.0 * sway, 4.0 * sway))
        _rot_bone_world(pb, "Spine_01",    (-4.0, -2.0 * sway, 0.0))
        _rot_bone_world(pb, "Spine_02",    (-6.0 + 3.0 * br, 3.0 * sway, -4.0))
        _rot_bone_world(pb, "Neck",        (-8.0, 4.0, 12.0))
        _rot_bone_world(pb, "Head",        (-10.0, -8.0, 16.0))
        _rot_bone_world(pb, "Jaw_Scream",  (18.0 + 6.0 * br, 0.0, 0.0))
        _rot_bone_world(pb, "Crown_L",     (6.0 * br, -8.0, 6.0))
        _rot_bone_world(pb, "Crown_C",     (8.0 * sway, 0.0, 4.0 * sway))
        _rot_bone_world(pb, "Crown_R",     (-6.0 * br, 8.0, -6.0))
        # Iconic pale arm raised lightly against filigree ribs (Ref Image 1 silhouette)
        _rot_bone_world(pb, "Arm_L_Upper", (12.0, -14.0, 16.0))
        _rot_bone_world(pb, "Arm_L_Fore",  (22.0, 0.0, -14.0))
        _rot_bone_world(pb, "Arm_R_Upper", (36.0, 18.0, -34.0))
        _rot_bone_world(pb, "Arm_R_Fore",  (62.0, 12.0, -56.0))
        _rot_bone_world(pb, "Arm_R_Hand",  (18.0, -12.0, -22.0))
        wing_b = 4.0 * br
    elif stage == "stalk":
        _rot_bone_world(pb, "Pelvis",      (6.0, 4.0 * sway, 8.0 * sway))
        _rot_bone_world(pb, "Spine_01",    (6.0, -4.0 * sway, -4.0 * sway))
        _rot_bone_world(pb, "Spine_02",    (6.0, 0.0, 0.0))
        _rot_bone_world(pb, "Head",        (-14.0, 0.0, 12.0 * sway))
        _rot_bone_world(pb, "Jaw_Scream",  (24.0, 0.0, 0.0))
        _rot_bone_world(pb, "Stilt_FL_01", (16.0 * sway, 0.0, 0.0))
        _rot_bone_world(pb, "Stilt_FR_01", (-16.0 * sway, 0.0, 0.0))
        _rot_bone_world(pb, "Stilt_Rear_01", (-12.0 * br, 0.0, 0.0))
        _rot_bone_world(pb, "Arm_L_Upper", (28.0, -16.0, 22.0))
        _rot_bone_world(pb, "Arm_L_Fore",  (32.0, 0.0, -18.0))
        _rot_bone_world(pb, "Arm_R_Upper", (28.0, 16.0, -22.0))
        _rot_bone_world(pb, "Arm_R_Fore",  (32.0, 0.0, 18.0))
        wing_b = 8.0 * br
    elif stage == "sweep":
        _rot_bone_world(pb, "Pelvis",      (8.0, 0.0, -18.0))
        _rot_bone_world(pb, "Spine_01",    (8.0, 0.0, -14.0))
        _rot_bone_world(pb, "Spine_02",    (10.0, 0.0, -12.0))
        _rot_bone_world(pb, "Head",        (-16.0, 6.0, 22.0))
        _rot_bone_world(pb, "Jaw_Scream",  (32.0, 0.0, 0.0))
        _rot_bone_world(pb, "Arm_L_Upper", (54.0, -28.0, 32.0))
        _rot_bone_world(pb, "Arm_L_Fore",  (40.0, -10.0, 22.0))
        _rot_bone_world(pb, "Arm_R_Upper", (46.0, 28.0, -32.0))
        _rot_bone_world(pb, "Arm_R_Fore",  (36.0, 10.0, -20.0))
        wing_b = 14.0
    elif stage == "razor_bloom":
        _rot_bone_world(pb, "Pelvis",      (-6.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_01",    (-8.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_02",    (-12.0, 0.0, 0.0))
        _rot_bone_world(pb, "Neck",        (-10.0, 0.0, 0.0))
        _rot_bone_world(pb, "Head",        (-22.0, 0.0, 8.0))
        _rot_bone_world(pb, "Jaw_Scream",  (36.0, 0.0, 0.0))
        _rot_bone_world(pb, "Crown_L",     (-12.0, -22.0, 18.0))
        _rot_bone_world(pb, "Crown_C",     (-18.0, 0.0, 0.0))
        _rot_bone_world(pb, "Crown_R",     (-12.0, 22.0, -18.0))
        _rot_bone_world(pb, "Arm_L_Upper", (48.0, -44.0, 28.0))
        _rot_bone_world(pb, "Arm_L_Fore",  (24.0, -16.0, 18.0))
        _rot_bone_world(pb, "Arm_R_Upper", (48.0, 44.0, -28.0))
        _rot_bone_world(pb, "Arm_R_Fore",  (24.0, 16.0, -18.0))
        wing_b = 26.0
    else:  # death
        _rot_bone_world(pb, "Pelvis",      (32.0, 12.0, 0.0))
        _rot_bone_world(pb, "Spine_01",    (22.0, 8.0, 0.0))
        _rot_bone_world(pb, "Spine_02",    (24.0, 6.0, 0.0))
        _rot_bone_world(pb, "Head",        (20.0, 12.0, 16.0))
        _rot_bone_world(pb, "Stilt_FL_01", (-28.0, 0.0, 0.0))
        _rot_bone_world(pb, "Stilt_FR_01", (-28.0, 0.0, 0.0))
        _rot_bone_world(pb, "Stilt_Rear_01", (28.0, 0.0, 0.0))
        wing_b = -18.0

    for side, sx in (("L", 1.0), ("R", -1.0)):
        for wi, z_ang in ((1, 18.0), (2, 10.0), (3, 4.0)):
            _rot_bone_world(pb, f"Wing_{side}{wi}_01", (0.4 * wing_b, -0.5 * wing_b * sx, (z_ang + 0.6 * wing_b) * sx))
            _rot_bone_world(pb, f"Wing_{side}{wi}_02", (0.4 * wing_b, -0.4 * wing_b * sx, 0.4 * wing_b * sx))
            _rot_bone_world(pb, f"Wing_{side}{wi}_03", (0.3 * wing_b, -0.3 * wing_b * sx, 0.3 * wing_b * sx))

    snap_creature_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_arachnid_maw_pose(arm_obj, body_obj, stage="idle", phase=0.0):
    """Apply 6-legged Arachnid Maw poses (`idle`, `scuttle`, `bite`, `acid_pounce`, `death`)."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_creature_pose(pb)
    tau = 2.0 * math.pi * phase
    sway = math.sin(tau)
    br = math.cos(tau)

    if stage == "idle":
        _rot_bone_world(pb, "Pelvis",   (3.0 * br, 2.0 * sway, 3.0 * sway))
        _rot_bone_world(pb, "Abdomen",  (6.0 + 4.0 * br, 0.0, 4.0 * sway))
        _rot_bone_world(pb, "Head",     (-4.0 + 3.0 * br, 0.0, 4.0 * sway))
        gape = 12.0 + 6.0 * (0.5 + 0.5 * br)
        _rot_bone_world(pb, "Maw_Top",  (-gape, 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Bot",  ( gape * 1.15, 0.0, 0.0))
        _rot_bone_world(pb, "Palp_L_01", (0.0, 0.0,  10.0 + 6.0 * sway))
        _rot_bone_world(pb, "Palp_R_01", (0.0, 0.0, -10.0 - 6.0 * sway))
        for ti, td in enumerate((8.0, 12.0, 14.0, 16.0), start=1):
            _rot_bone_world(pb, f"Tail_{ti:02d}", (td + 4.0 * br, 0.0, 3.0 * sway))
    elif stage == "scuttle":
        _rot_bone_world(pb, "Pelvis",   (4.0, 3.0 * sway, 5.0 * sway))
        _rot_bone_world(pb, "Abdomen",  (8.0, 0.0, -5.0 * sway))
        _rot_bone_world(pb, "Maw_Top",  (-18.0, 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Bot",  ( 22.0, 0.0, 0.0))
        for ti, td in enumerate((10.0, 14.0, 16.0, 18.0), start=1):
            _rot_bone_world(pb, f"Tail_{ti:02d}", (td, 0.0, -4.0 * sway))
        for lname, sgn in (("Leg_FL", 1.0), ("Leg_MR", 1.0), ("Leg_BL", 1.0), ("Leg_FR", -1.0), ("Leg_ML", -1.0), ("Leg_BR", -1.0)):
            sx = 1.0 if lname.endswith("L") else -1.0
            lift = max(0.0, br * sgn)
            step = sway * sgn
            _rot_bone_world(pb, f"{lname}_Coxa",  (0.0, -14.0 * lift * sx, 16.0 * step))
            _rot_bone_world(pb, f"{lname}_Femur", (0.0,  12.0 * lift * sx, 0.0))
    elif stage == "bite":
        _rot_bone_world(pb, "Pelvis",    (10.0, 0.0, 0.0))
        _rot_bone_world(pb, "Head",      (-10.0, 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Top",   (-30.0, 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Bot",   ( 34.0, 0.0, 0.0))
        _rot_bone_world(pb, "Palp_L_01", (0.0, 0.0,  26.0))
        _rot_bone_world(pb, "Palp_L_02", (0.0, 0.0, -24.0))
        _rot_bone_world(pb, "Palp_R_01", (0.0, 0.0, -26.0))
        _rot_bone_world(pb, "Palp_R_02", (0.0, 0.0,  24.0))
        for ti, td in enumerate((14.0, 18.0, 22.0, 24.0), start=1):
            _rot_bone_world(pb, f"Tail_{ti:02d}", (td, 0.0, 0.0))
    elif stage == "acid_pounce":
        _rot_bone_world(pb, "Pelvis",    (-18.0, 0.0, 0.0))
        _rot_bone_world(pb, "Abdomen",   (12.0, 0.0, 0.0))
        _rot_bone_world(pb, "Head",      (-14.0, 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Top",   (-32.0, 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Bot",   ( 36.0, 0.0, 0.0))
        _rot_bone_world(pb, "Palp_L_01", (0.0, 0.0,  28.0))
        _rot_bone_world(pb, "Palp_R_01", (0.0, 0.0, -28.0))
        for lname, sx in (("Leg_FL", 1.0), ("Leg_FR", -1.0)):
            _rot_bone_world(pb, f"{lname}_Coxa",  (-16.0, -26.0 * sx, -18.0 * sx))
            _rot_bone_world(pb, f"{lname}_Femur", ( 12.0,  18.0 * sx, 0.0))
        for ti, td in enumerate((18.0, 24.0, 26.0, 26.0), start=1):
            _rot_bone_world(pb, f"Tail_{ti:02d}", (td, 0.0, 0.0))
    else:  # death
        _rot_bone_world(pb, "Pelvis",    (14.0, 12.0, 0.0))
        _rot_bone_world(pb, "Maw_Bot",   (24.0, 0.0, 0.0))
        for lname, sx in (("Leg_FL", 1.0), ("Leg_ML", 1.0), ("Leg_BL", 1.0), ("Leg_FR", -1.0), ("Leg_MR", -1.0), ("Leg_BR", -1.0)):
            _rot_bone_world(pb, f"{lname}_Coxa",  (0.0, -28.0 * sx, 0.0))
            _rot_bone_world(pb, f"{lname}_Femur", (0.0,  22.0 * sx, 0.0))
        for ti, td in enumerate((-12.0, -14.0, -12.0, -10.0), start=1):
            _rot_bone_world(pb, f"Tail_{ti:02d}", (td, 0.0, 0.0))

    snap_creature_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_bile_juggernaut_pose(arm_obj, body_obj, stage="idle", phase=0.0):
    """Apply slow ponderous tank poses (`idle`, `walk_stomp`, `roar`, `swipe`, `seismic_slam`, `death`)."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_creature_pose(pb)
    tau = 2.0 * math.pi * phase
    sway = math.sin(tau)
    br = math.cos(tau)

    if stage == "idle":
        _rot_bone_world(pb, "Pelvis",        (4.0, 2.0 * sway, 2.0 * sway))
        _rot_bone_world(pb, "Belly_Gut",     (4.0 + 3.0 * br, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Maw_Top", (-8.0 - 4.0 * br, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Maw_Bot", (10.0 + 5.0 * br, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_01",      (6.0 + 3.0 * br, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_02",      (8.0 + 2.0 * br, 2.0 * sway, 2.0 * sway))
        _rot_bone_world(pb, "Head",          (-8.0, 0.0, 4.0 * sway))
        _rot_bone_world(pb, "Jaw_L",         (12.0 + 4.0 * br, 0.0,  10.0))
        _rot_bone_world(pb, "Jaw_R",         (12.0 + 4.0 * br, 0.0, -10.0))
        _rot_bone_world(pb, "Tongue_01",     (8.0 + 4.0 * br, 0.0, 4.0 * sway))
        _rot_bone_world(pb, "Arm_L_Upper",   (-14.0, -6.0, 0.0))
        _rot_bone_world(pb, "Arm_L_Fore",    (-18.0, 0.0, -10.0))
        _rot_bone_world(pb, "Arm_R_Upper",   (-16.0, 6.0, 0.0))
        _rot_bone_world(pb, "Arm_R_Fore",    (-20.0, 0.0, 12.0))
    elif stage == "walk_stomp":
        # Ponderous waddling tank march
        _rot_bone_world(pb, "Pelvis",        (6.0, 7.0 * sway, 8.0 * sway))
        _rot_bone_world(pb, "Belly_Gut",     (6.0 + 3.0 * abs(sway), -4.0 * sway, -5.0 * sway))
        _rot_bone_world(pb, "Belly_Maw_Top", (-14.0, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Maw_Bot", ( 16.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_01",      (8.0, -4.0 * sway, -6.0 * sway))
        _rot_bone_world(pb, "Spine_02",      (8.0, -3.0 * sway, -4.0 * sway))
        _rot_bone_world(pb, "Head",          (-10.0, 0.0, 6.0 * sway))
        _rot_bone_world(pb, "Jaw_L",         (16.0, 0.0,  14.0))
        _rot_bone_world(pb, "Jaw_R",         (16.0, 0.0, -14.0))
        for leg, s_s in (("Leg_L", 1.0), ("Leg_R", -1.0)):
            step = sway * s_s
            lift = max(0.0, br * s_s)
            _rot_bone_world(pb, f"{leg}_Thigh", (-18.0 * step - 12.0 * lift, 0.0, 0.0))
            _rot_bone_world(pb, f"{leg}_Shin",  (14.0 * step + 16.0 * lift, 0.0, 0.0))
            _rot_bone_world(pb, f"{leg}_Foot",  (-10.0 * lift, 0.0, 0.0))
        _rot_bone_world(pb, "Arm_L_Upper",   (-16.0 - 18.0 * sway, -8.0, 0.0))
        _rot_bone_world(pb, "Arm_L_Fore",    (-22.0, 0.0, -10.0))
        _rot_bone_world(pb, "Arm_R_Upper",   (-16.0 + 18.0 * sway, 8.0, 0.0))
        _rot_bone_world(pb, "Arm_R_Fore",    (-24.0, 0.0, 12.0))
    elif stage == "roar":
        _rot_bone_world(pb, "Pelvis",        (-4.0, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Gut",     (-4.0, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Maw_Top", (-26.0, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Maw_Bot", ( 30.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_01",      (-6.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_02",      (-6.0, 0.0, 0.0))
        _rot_bone_world(pb, "Head",          (-16.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_L",         (28.0, 0.0,  26.0))
        _rot_bone_world(pb, "Jaw_R",         (28.0, 0.0, -26.0))
        _rot_bone_world(pb, "Tongue_01",     (16.0, 0.0, 0.0))
        _rot_bone_world(pb, "Tongue_02",     (18.0, 0.0, 0.0))
        _rot_bone_world(pb, "Arm_L_Upper",   (-28.0, -22.0, 16.0))
        _rot_bone_world(pb, "Arm_R_Upper",   (-28.0,  22.0, -16.0))
    elif stage == "swipe":
        _rot_bone_world(pb, "Pelvis",        (10.0, 0.0, 22.0))
        _rot_bone_world(pb, "Spine_01",      (10.0, 0.0, 18.0))
        _rot_bone_world(pb, "Spine_02",      (10.0, 0.0, 16.0))
        _rot_bone_world(pb, "Head",          (-12.0, 0.0, -24.0))
        _rot_bone_world(pb, "Jaw_L",         (24.0, 0.0,  20.0))
        _rot_bone_world(pb, "Jaw_R",         (24.0, 0.0, -20.0))
        _rot_bone_world(pb, "Belly_Maw_Top", (-22.0, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Maw_Bot", ( 24.0, 0.0, 0.0))
        _rot_bone_world(pb, "Arm_R_Shoulder",(0.0, -14.0, 26.0))
        _rot_bone_world(pb, "Arm_R_Upper",   (-54.0, 18.0, 34.0))
        _rot_bone_world(pb, "Arm_R_Fore",    (-32.0, 8.0, 22.0))
        _rot_bone_world(pb, "Arm_L_Upper",   (-20.0, -16.0, -18.0))
    elif stage == "seismic_slam":
        # Heavy forward smash slamming both boulder fists violently down at ground crater
        _rot_bone_world(pb, "Pelvis",        (18.0, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Gut",     (10.0, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Maw_Top", (-26.0, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Maw_Bot", ( 28.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_01",      (16.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_02",      (14.0, 0.0, 0.0))
        _rot_bone_world(pb, "Head",          (-18.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_L",         (28.0, 0.0,  26.0))
        _rot_bone_world(pb, "Jaw_R",         (28.0, 0.0, -26.0))
        _rot_bone_world(pb, "Tongue_01",     (18.0, 0.0, 0.0))
        _rot_bone_world(pb, "Leg_L_Thigh",   (-26.0, 0.0, 8.0))
        _rot_bone_world(pb, "Leg_L_Shin",    ( 28.0, 0.0, 0.0))
        _rot_bone_world(pb, "Leg_R_Thigh",   (-26.0, 0.0, -8.0))
        _rot_bone_world(pb, "Leg_R_Shin",    ( 28.0, 0.0, 0.0))
        _rot_bone_world(pb, "Arm_L_Upper",   (-48.0, -10.0, -18.0))
        _rot_bone_world(pb, "Arm_L_Fore",    (-22.0, 0.0, -10.0))
        _rot_bone_world(pb, "Arm_R_Upper",   (-52.0, 10.0, 18.0))
        _rot_bone_world(pb, "Arm_R_Fore",    (-22.0, 0.0, 10.0))
    else:  # death
        _rot_bone_world(pb, "Pelvis",        (48.0, 8.0, 0.0))
        _rot_bone_world(pb, "Spine_01",      (22.0, 6.0, 0.0))
        _rot_bone_world(pb, "Head",          (14.0, 8.0, 14.0))
        _rot_bone_world(pb, "Leg_L_Thigh",   (-36.0, 0.0, 0.0))
        _rot_bone_world(pb, "Leg_L_Shin",    ( 44.0, 0.0, 0.0))
        _rot_bone_world(pb, "Leg_R_Thigh",   (-36.0, 0.0, 0.0))
        _rot_bone_world(pb, "Leg_R_Shin",    ( 44.0, 0.0, 0.0))
        _rot_bone_world(pb, "Arm_L_Upper",   (-24.0, -18.0, 0.0))
        _rot_bone_world(pb, "Arm_R_Upper",   (-24.0,  18.0, 0.0))

    snap_creature_to_floor(arm_obj, body_obj, floor_z=0.0)


CREATURE_POSE_DISPATCH = {
    "rafflesia":       apply_rafflesia_creature_pose,
    "scythe_stalker":  apply_scythe_stalker_pose,
    "thorn_shroud":    apply_thorn_shroud_pose,
    "arachnid_maw":    apply_arachnid_maw_pose,
    "bile_juggernaut": apply_bile_juggernaut_pose,
}


def apply_creature_pose(arm_obj, body_obj, creature_type, stage="idle", phase=0.0):
    fn = CREATURE_POSE_DISPATCH[creature_type]
    fn(arm_obj, body_obj, stage=stage, phase=phase)


def _keyframe_creature_pose(arm_obj, frame):
    bpy.context.view_layer.update()
    for b in arm_obj.pose.bones:
        if not b.bone.use_deform:
            continue
        if b.rotation_mode != "QUATERNION":
            q = b.rotation_euler.to_quaternion()
            b.rotation_mode = "QUATERNION"
            b.rotation_quaternion = q
        b.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        if b.name == "Pelvis":
            b.keyframe_insert(data_path="location", frame=frame)


CREATURE_ACTION_SPECS = {
    "rafflesia": (
        ("Idle_Sway",         "loop", "idle",        6, 6),
        ("Crawl_Stalk",       "loop", "stalk",       8, 4),
        ("Attack_Lunge_Bite", "seq",  [(1, "idle"), (8, "stalk"), (14, "lunge_bite"), (21, "lunge_bite"), (28, "idle")], 0.0, None),
        ("Skill_Vine_Thrash", "seq",  [(1, "idle"), (10, "stalk"), (18, "vine_thrash"), (28, "vine_thrash"), (36, "idle")], 0.25, None),
        ("Death_Wilt",        "seq",  [(1, "idle"), (10, "stalk"), (20, "death"), (30, "death")], 0.0, None),
    ),
    "scythe_stalker": (
        ("Idle_Hunch",         "loop", "idle",        6, 6),
        ("Run_Limp_Stalk",     "loop", "stalk",       8, 4),
        ("Attack_Scythe_Clef", "seq",  [(1, "idle"), (7, "stalk"), (13, "slash"), (21, "slash"), (28, "idle")], 0.0, None),
        ("Skill_Reaper_Lunge", "seq",  [(1, "idle"), (9, "stalk"), (16, "reaper_lunge"), (26, "reaper_lunge"), (36, "idle")], 0.0, None),
        ("Death_Collapse",     "seq",  [(1, "idle"), (10, "stalk"), (20, "death"), (30, "death")], 0.0, None),
    ),
    "thorn_shroud": (
        ("Idle_Veil_Sway",    "loop", "idle",         6, 6),
        ("Glide_Stilt_Stalk", "loop", "stalk",        8, 4),
        ("Attack_Blade_Sweep","seq",  [(1, "idle"), (8, "stalk"), (15, "sweep"), (23, "sweep"), (30, "idle")], 0.0, None),
        ("Skill_Razor_Bloom", "seq",  [(1, "idle"), (10, "stalk"), (18, "razor_bloom"), (28, "razor_bloom"), (38, "idle")], 0.0, None),
        ("Death_Shatter",     "seq",  [(1, "idle"), (10, "stalk"), (20, "death"), (30, "death")], 0.0, None),
    ),
    "arachnid_maw": (
        ("Idle_Acid_Throb",   "loop", "idle",         6, 6),
        ("Skitter_Scuttle",   "loop", "scuttle",      8, 3),
        ("Attack_Mandible",   "seq",  [(1, "idle"), (6, "scuttle"), (12, "bite"), (19, "bite"), (26, "idle")], 0.0, None),
        ("Skill_Acid_Pounce", "seq",  [(1, "idle"), (9, "scuttle"), (16, "acid_pounce"), (26, "acid_pounce"), (36, "idle")], 0.0, None),
        ("Death_Curl",        "seq",  [(1, "idle"), (10, "scuttle"), (20, "death"), (30, "death")], 0.0, None),
    ),
    "bile_juggernaut": (
        ("Idle_Lumber",           "loop", "idle",         6, 8),
        ("Walk_Stomp_Slow",       "loop", "walk_stomp",   8, 6),
        ("Attack_Crusher_Swipe",  "seq",  [(1, "idle"), (10, "walk_stomp"), (20, "swipe"), (29, "swipe"), (40, "idle")], 0.0, None),
        ("Skill_Seismic_Bile_Slam","seq", [(1, "idle"), (12, "roar"), (24, "seismic_slam"), (36, "seismic_slam"), (48, "idle")], 0.0, None),
        ("Death_Timber",          "seq",  [(1, "idle"), (14, "roar"), (28, "death"), (42, "death")], 0.0, None),
    ),
}


def bake_creature_actions(arm_obj, body_obj, creature_type="rafflesia"):
    """Bake 5 dedicated creature actions onto `arm_obj` (`use_fake_user=True`) and restore rest pose."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    if arm_obj.animation_data is None:
        arm_obj.animation_data_create()

    pose_fn = CREATURE_POSE_DISPATCH[creature_type]
    for spec in CREATURE_ACTION_SPECS[creature_type]:
        aname = spec[0]
        act = bpy.data.actions.new(name=aname)
        act.use_fake_user = True
        arm_obj.animation_data.action = act
        if spec[1] == "loop":
            _, _, stg, steps, step_f = spec
            for idx in range(steps + 1):
                pose_fn(arm_obj, body_obj, stage=stg, phase=(idx % steps) / float(steps))
                _keyframe_creature_pose(arm_obj, 1 + idx * step_f)
        else:
            _, _, keys, ph, _ = spec
            for frame, stg in keys:
                pose_fn(arm_obj, body_obj, stage=stg, phase=ph)
                _keyframe_creature_pose(arm_obj, frame)

    arm_obj.animation_data.action = None
    reset_creature_pose(arm_obj.pose.bones)
    bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode="OBJECT")
