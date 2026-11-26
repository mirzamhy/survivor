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


def _set_pelvis_world_offset(pb, world_xyz):
    """Set `Pelvis` pose translation from a world-space XYZ offset (accounting for rest bone orientation)."""
    pelvis = pb.get("Pelvis")
    if pelvis is None:
        return
    m_inv = pelvis.bone.matrix_local.to_3x3().inverted()
    pelvis.location = m_inv @ Vector(world_xyz)


def _gait_foot_curve(ph, duty=0.60, ramp=0.14):
    """C2 smooth cyclic foot trajectory: flat-velocity grounded stance (-1->+1), quintic arc swing (+1->-1)."""
    p = ph % 1.0
    if p < duty:
        u = p / max(1e-5, duty)
        r = max(0.02, min(0.45, ramp))
        if u < r:
            f = (0.5 * u - (r / (2.0 * math.pi)) * math.sin(math.pi * u / r)) / (1.0 - r)
        elif u <= 1.0 - r:
            f = (u - 0.5 * r) / (1.0 - r)
        else:
            t = 1.0 - u
            f = 1.0 - (0.5 * t - (r / (2.0 * math.pi)) * math.sin(math.pi * t / r)) / (1.0 - r)
        return (-1.0 + 2.0 * f, 0.0, True, u)
    q = (p - duty) / max(1e-5, 1.0 - duty)
    sw = q * q * q * (10.0 - 15.0 * q + 6.0 * q * q)
    lift = math.sin(math.pi * q) ** 2
    return (1.0 - 2.0 * sw, lift, False, q)


def _aim_creature_bone_world(arm_obj, bname, desired_dir_world):
    """Rotate `bname` with minimal twist so its armature-space head->tail aligns with `desired_dir_world`."""
    b = arm_obj.pose.bones.get(bname)
    d = Vector(desired_dir_world)
    if b is None or d.length < 1e-6:
        return
    cur_dir = b.tail - b.head
    if cur_dir.length < 1e-6:
        return
    cur_dir.normalize()
    target_dir = d.normalized()
    if b.rotation_mode != "QUATERNION":
        q_cur = b.rotation_euler.to_quaternion()
        b.rotation_mode = "QUATERNION"
        b.rotation_quaternion = q_cur
    r_cur = b.matrix.to_3x3().normalized()
    q_delta_arm = cur_dir.rotation_difference(target_dir)
    q_delta_local = (r_cur.inverted() @ q_delta_arm.to_matrix() @ r_cur).to_quaternion()
    b.rotation_quaternion = (b.rotation_quaternion @ q_delta_local).normalized()


def _aim_creature_chain(arm_obj, bone_names, dir_list):
    """Sequentially orient a connected bone chain along world direction vectors."""
    for bname, dvec in zip(bone_names, dir_list):
        _aim_creature_bone_world(arm_obj, bname, dvec)
        bpy.context.view_layer.update()


def _drape_creature_chain_to_floor(arm_obj, bone_names, xy_dirs, z_targets):
    """Drape a chain's joints downward in world space toward `z_targets` along `xy_dirs`."""
    pb = arm_obj.pose.bones
    for bname, (dx, dy), z_tgt in zip(bone_names, xy_dirs, z_targets):
        b = pb.get(bname)
        if b is None:
            continue
        L = max(1e-4, b.bone.length)
        h_len = math.hypot(dx, dy)
        ux, uy = (dx / h_len, dy / h_len) if h_len > 1e-6 else (0.0, 1.0)
        dz = max(-0.92 * L, min(0.85 * L, z_tgt - b.head.z))
        horiz = math.sqrt(max(1e-6, L * L - dz * dz))
        _aim_creature_bone_world(arm_obj, bname, Vector((ux * horiz, uy * horiz, dz)))
        bpy.context.view_layer.update()


def _solve_creature_2bone_ik(arm_obj, upper_name, lower_name, target_arm, pole_hint_arm):
    """Analytical 2-bone limb IK in armature space with bend-plane pole hint and no hyperextension snap."""
    pb = arm_obj.pose.bones
    u_bone = pb.get(upper_name)
    l_bone = pb.get(lower_name)
    if u_bone is None or l_bone is None:
        return
    hip = u_bone.head.copy()
    tgt = Vector(target_arm)
    L1 = u_bone.bone.length
    L2 = l_bone.bone.length

    vec = tgt - hip
    dist = vec.length
    if dist < 1e-6:
        vec = Vector((0.0, 0.0, -1.0))
        dist = 1e-6
    u = vec / dist
    d = min((L1 + L2) * 0.992, max(abs(L1 - L2) + 1e-3, dist))

    p = Vector(pole_hint_arm)
    p = p - u * p.dot(u)
    if p.length < 1e-5:
        fallback = Vector((0.0, -1.0, 0.0)) if abs(u.y) < 0.9 else Vector((0.0, 0.0, 1.0))
        p = fallback - u * fallback.dot(u)
    p.normalize()

    cos_a = max(-1.0, min(1.0, (L1 * L1 + d * d - L2 * L2) / max(1e-6, 2.0 * L1 * d)))
    sin_a = math.sqrt(max(0.0, 1.0 - cos_a * cos_a))
    knee_pos = hip + u * (L1 * cos_a) + p * (L1 * sin_a)

    _aim_creature_bone_world(arm_obj, upper_name, knee_pos - hip)
    bpy.context.view_layer.update()
    knee_actual = l_bone.head.copy()
    _aim_creature_bone_world(arm_obj, lower_name, tgt - knee_actual)
    bpy.context.view_layer.update()


def _clamp_creature_floor(arm_obj, body_obj, floor_z=0.0):
    """Correct Pelvis Z only if evaluated mesh penetrates below floor or floats ungrounded."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    eval_obj = body_obj.evaluated_get(dg)
    me = eval_obj.to_mesh()
    mat = body_obj.matrix_world
    min_z = min((mat @ v.co).z for v in me.vertices)
    eval_obj.to_mesh_clear()

    if min_z < floor_z - 0.004 or min_z > floor_z + 0.022:
        dz = floor_z - min_z
        pelvis = arm_obj.pose.bones.get("Pelvis")
        if pelvis is not None:
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
        _set_pelvis_world_offset(pb, (0.018 * math.sin(tau), 0.0, -0.032 - 0.010 * math.cos(2.0 * tau)))
        _rot_bone_world(pb, "Pelvis",   (6.0, 2.0 * stride, 4.0 * stride))
        _rot_bone_world(pb, "Stalk_01", (13.0, -1.5 * stride, -3.5 * stride))
        _rot_bone_world(pb, "Stalk_02", (11.0, -0.8 * stride, 2.5 * stride))
        _rot_bone_world(pb, "Neck",     (-15.0, 1.5 * stride, 2.0 * stride))
        _rot_bone_world(pb, "Head",     (-12.0, 0.0, 5.0 * stride))

        _rot_bone_world(pb, "Jaw_Top", (-18.0 - 4.0 * abs(stride), 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_Bot", ( 22.0 + 4.0 * abs(stride), 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_L",   (0.0, 0.0,  16.0))
        _rot_bone_world(pb, "Jaw_R",   (0.0, 0.0, -16.0))

        for side, sx in (("L", 1.0), ("R", -1.0)):
            _pose_vine_chain(pb, f"Vine_Main_{side}", 6, sx,
                             base_deg=(12.0, -6.0, 16.0),
                             wave_deg=(14.0 * stride, -10.0 * lift, 16.0 * stride),
                             curl_deg=(10.0, -16.0, 12.0))
            _pose_vine_chain(pb, f"Vine_Mid_{side}", 5, sx,
                             base_deg=(12.0, -4.0, 18.0),
                             wave_deg=(14.0 * lift, -8.0, 14.0 * stride),
                             curl_deg=(6.0, -12.0, 12.0))
            _pose_vine_chain(pb, f"Vine_Back_{side}", 4, sx,
                             base_deg=(10.0, -4.0, 10.0),
                             wave_deg=(10.0 * stride, -8.0, 10.0),
                             curl_deg=(8.0, -10.0, 8.0))

        bpy.context.view_layer.update()
        # 4-beat lateral-sequence quadruped crawl IK (BL -> FL -> BR -> FR)
        for leg, p_off, sx, fy in (
            ("Leg_BL", 0.00,  1.0, -1.0),
            ("Leg_FL", 0.25,  1.0,  1.0),
            ("Leg_BR", 0.50, -1.0, -1.0),
            ("Leg_FR", 0.75, -1.0,  1.0),
        ):
            str_n, lift_n, _, _ = _gait_foot_curve((phase + p_off) % 1.0, duty=0.72)
            rest_ankle = pb[f"{leg}_Shin"].bone.tail_local.copy()
            rest_foot_vec = pb[f"{leg}_Foot"].bone.tail_local - pb[f"{leg}_Foot"].bone.head_local
            p_ankle = rest_ankle + Vector((0.0, 0.25 * str_n, 0.13 * lift_n))
            _solve_creature_2bone_ik(arm_obj, f"{leg}_Thigh", f"{leg}_Shin",
                                     p_ankle, pole_hint_arm=(0.35 * sx, -0.25 * fy, 1.0))
            _aim_creature_bone_world(arm_obj, f"{leg}_Foot",
                                     rest_foot_vec + Vector((0.0, 0.0, -0.025 * lift_n)))

    elif stage == "bite_windup":
        _rot_bone_world(pb, "Pelvis",   (-10.0, 0.0, -8.0))
        _rot_bone_world(pb, "Stalk_01", (-12.0, 0.0, -6.0))
        _rot_bone_world(pb, "Stalk_02", (-8.0, 0.0, -4.0))
        _rot_bone_world(pb, "Neck",     (12.0, 0.0, 6.0))
        _rot_bone_world(pb, "Head",     (10.0, 0.0, 8.0))
        _rot_bone_world(pb, "Jaw_Top", (-12.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_Bot", ( 14.0, 0.0, 0.0))
        for side, sx in (("L", 1.0), ("R", -1.0)):
            _pose_vine_chain(pb, f"Vine_Main_{side}", 6, sx, (-12.0, -14.0, -10.0), (6.0, -6.0, 6.0), (4.0, -12.0, -8.0))
            _pose_vine_chain(pb, f"Vine_Mid_{side}",  5, sx, (-10.0, -12.0, -8.0),  (6.0, -6.0, 6.0), (4.0, -10.0, -6.0))
            _pose_vine_chain(pb, f"Vine_Back_{side}", 4, sx, (-8.0, -10.0, -6.0),   (4.0, -4.0, 4.0), (4.0, -8.0, -4.0))

    elif stage == "lunge_bite":
        # Explosive forward crouch with 4-lobed fanged beak-maw gaping WIDE OPEN
        _rot_bone_world(pb, "Pelvis",   (18.0, 0.0, 4.0))
        _rot_bone_world(pb, "Stalk_01", (24.0, 0.0, 4.0))
        _rot_bone_world(pb, "Stalk_02", (20.0, 0.0, 2.0))
        _rot_bone_world(pb, "Neck",     (-18.0, 0.0, -4.0))
        _rot_bone_world(pb, "Head",     (-26.0, 0.0, -4.0))

        _rot_bone_world(pb, "Jaw_Top", (-32.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_Bot", ( 36.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_L",   (0.0, 0.0,  28.0))
        _rot_bone_world(pb, "Jaw_R",   (0.0, 0.0, -28.0))

        for leg, sx in (("Leg_FL", 1.0), ("Leg_FR", -1.0)):
            _rot_bone_world(pb, f"{leg}_Thigh", (-14.0, -12.0 * sx, -16.0 * sx))
            _rot_bone_world(pb, f"{leg}_Shin",  ( 10.0,  16.0 * sx,   8.0 * sx))
        for leg, sx in (("Leg_BL", 1.0), ("Leg_BR", -1.0)):
            _rot_bone_world(pb, f"{leg}_Thigh", (-18.0,  12.0 * sx,  12.0 * sx))
            _rot_bone_world(pb, f"{leg}_Shin",  ( 16.0, -14.0 * sx,  -6.0 * sx))

        for side, sx in (("L", 1.0), ("R", -1.0)):
            _pose_vine_chain(pb, f"Vine_Main_{side}", 6, sx,
                             base_deg=(18.0, -4.0, 26.0),
                             wave_deg=(14.0, -8.0, 14.0),
                             curl_deg=(10.0, -14.0, 18.0))
            _pose_vine_chain(pb, f"Vine_Mid_{side}", 5, sx,
                             base_deg=(20.0, -4.0, 26.0),
                             wave_deg=(12.0, -6.0, 12.0),
                             curl_deg=(8.0, -10.0, 16.0))
            _pose_vine_chain(pb, f"Vine_Back_{side}", 4, sx,
                             base_deg=(14.0, -6.0, 16.0),
                             wave_deg=(8.0, -6.0, 10.0),
                             curl_deg=(10.0, -10.0, 10.0))

    elif stage == "bite_follow":
        _rot_bone_world(pb, "Pelvis",   (12.0, 0.0, 10.0))
        _rot_bone_world(pb, "Stalk_01", (14.0, 0.0, 8.0))
        _rot_bone_world(pb, "Stalk_02", (10.0, 0.0, 6.0))
        _rot_bone_world(pb, "Neck",     (-8.0, 0.0, -8.0))
        _rot_bone_world(pb, "Head",     (6.0, 0.0, -10.0))
        _rot_bone_world(pb, "Jaw_Top", (-4.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_Bot", ( 6.0, 0.0, 0.0))
        for side, sx in (("L", 1.0), ("R", -1.0)):
            _pose_vine_chain(pb, f"Vine_Main_{side}", 6, sx, (8.0, -10.0, 12.0), (10.0, -6.0, 10.0), (6.0, -12.0, 8.0))
            _pose_vine_chain(pb, f"Vine_Mid_{side}",  5, sx, (10.0, -8.0, 14.0), (8.0, -4.0, 8.0),  (6.0, -10.0, 8.0))
            _pose_vine_chain(pb, f"Vine_Back_{side}", 4, sx, (6.0, -6.0, 8.0),   (6.0, -4.0, 6.0),  (4.0, -8.0, 6.0))

    elif stage == "thrash_windup":
        _rot_bone_world(pb, "Pelvis",   (-10.0, 0.0, -10.0))
        _rot_bone_world(pb, "Stalk_01", (-10.0, 0.0, -8.0))
        _rot_bone_world(pb, "Head",     (12.0, 0.0, 10.0))
        _rot_bone_world(pb, "Jaw_Top", (-16.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_Bot", ( 18.0, 0.0, 0.0))
        for side, sx in (("L", 1.0), ("R", -1.0)):
            _pose_vine_chain(pb, f"Vine_Main_{side}", 6, sx, (-16.0, -16.0, -18.0), (8.0, -8.0, -8.0), (6.0, -14.0, -12.0))
            _pose_vine_chain(pb, f"Vine_Mid_{side}",  5, sx, (-14.0, -14.0, -16.0), (6.0, -6.0, -6.0), (6.0, -12.0, -10.0))
            _pose_vine_chain(pb, f"Vine_Back_{side}", 4, sx, (-10.0, -12.0, -12.0), (6.0, -4.0, -4.0), (4.0, -10.0, -8.0))

    elif stage == "vine_thrash":
        # Massive predatory rear-up + 6 thorny tentacles whipping violently forward & flaring around roaring maw
        _rot_bone_world(pb, "Pelvis",   (-8.0, 0.0, 8.0))
        _rot_bone_world(pb, "Stalk_01", (18.0, 0.0, 8.0))
        _rot_bone_world(pb, "Stalk_02", (16.0, 0.0, 6.0))
        _rot_bone_world(pb, "Neck",     (-20.0, 0.0, -8.0))
        _rot_bone_world(pb, "Head",     (-16.0, 0.0, -8.0))

        _rot_bone_world(pb, "Jaw_Top", (-32.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_Bot", ( 36.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_L",   (0.0, 0.0,  30.0))
        _rot_bone_world(pb, "Jaw_R",   (0.0, 0.0, -30.0))

        for leg, sx in (("Leg_FL", 1.0), ("Leg_FR", -1.0)):
            _rot_bone_world(pb, f"{leg}_Thigh", ( 8.0,  10.0 * sx, 20.0 * sx))
            _rot_bone_world(pb, f"{leg}_Shin",  (-6.0, -12.0 * sx, -8.0 * sx))
        for leg, sx in (("Leg_BL", 1.0), ("Leg_BR", -1.0)):
            _rot_bone_world(pb, f"{leg}_Thigh", (-14.0, -10.0 * sx, -16.0 * sx))
            _rot_bone_world(pb, f"{leg}_Shin",  ( 12.0, 12.0 * sx,   6.0 * sx))

        for side, sx in (("L", 1.0), ("R", -1.0)):
            _pose_vine_chain(pb, f"Vine_Main_{side}", 6, sx,
                             base_deg=(28.0, -8.0, 30.0),
                             wave_deg=(16.0, -8.0, 14.0),
                             curl_deg=(12.0, -16.0, 16.0))
            _pose_vine_chain(pb, f"Vine_Mid_{side}", 5, sx,
                             base_deg=(28.0, -6.0, 26.0),
                             wave_deg=(14.0, -6.0, 12.0),
                             curl_deg=(10.0, -14.0, 14.0))
            _pose_vine_chain(pb, f"Vine_Back_{side}", 4, sx,
                             base_deg=(20.0, -6.0, 26.0),
                             wave_deg=(12.0, -4.0, 14.0),
                             curl_deg=(8.0, -12.0, 14.0))

    elif stage == "thrash_follow":
        _rot_bone_world(pb, "Pelvis",   (10.0, 0.0, 14.0))
        _rot_bone_world(pb, "Stalk_01", (14.0, 0.0, 10.0))
        _rot_bone_world(pb, "Head",     (-8.0, 0.0, -12.0))
        _rot_bone_world(pb, "Jaw_Top", (-18.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_Bot", ( 20.0, 0.0, 0.0))
        for side, sx in (("L", 1.0), ("R", -1.0)):
            _pose_vine_chain(pb, f"Vine_Main_{side}", 6, sx, (16.0, -12.0, 14.0), (10.0, -6.0, 10.0), (8.0, -12.0, 10.0))
            _pose_vine_chain(pb, f"Vine_Mid_{side}",  5, sx, (14.0, -10.0, 12.0), (8.0, -4.0, 8.0),   (6.0, -10.0, 8.0))
            _pose_vine_chain(pb, f"Vine_Back_{side}", 4, sx, (10.0, -8.0, 10.0),  (6.0, -4.0, 6.0),   (6.0, -8.0, 6.0))

    elif stage == "death_stagger":
        _rot_bone_world(pb, "Pelvis",   (-12.0, -8.0, 10.0))
        _rot_bone_world(pb, "Stalk_01", (-14.0, -4.0, 6.0))
        _rot_bone_world(pb, "Stalk_02", (-10.0, 0.0, 4.0))
        _rot_bone_world(pb, "Neck",     (10.0, 0.0, -6.0))
        _rot_bone_world(pb, "Head",     (-14.0, 6.0, -8.0))
        _rot_bone_world(pb, "Jaw_Top",  (-24.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_Bot",  ( 28.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_L",    (0.0, 0.0,  20.0))
        _rot_bone_world(pb, "Jaw_R",    (0.0, 0.0, -20.0))
        for side, sx in (("L", 1.0), ("R", -1.0)):
            _pose_vine_chain(pb, f"Vine_Main_{side}", 6, sx, (8.0, -14.0, 14.0), (8.0, -6.0, 8.0), (6.0, -12.0, 8.0))
            _pose_vine_chain(pb, f"Vine_Mid_{side}",  5, sx, (8.0, -12.0, 12.0), (6.0, -6.0, 6.0), (6.0, -10.0, 6.0))
            _pose_vine_chain(pb, f"Vine_Back_{side}", 4, sx, (6.0, -10.0, 8.0),  (4.0, -4.0, 4.0), (4.0, -8.0, 4.0))

    elif stage == "death_kneel":
        _rot_bone_world(pb, "Pelvis",   (24.0, 10.0, -4.0))
        _rot_bone_world(pb, "Stalk_01", (28.0, 6.0, 0.0))
        _rot_bone_world(pb, "Stalk_02", (24.0, 4.0, 0.0))
        _rot_bone_world(pb, "Neck",     (12.0, 4.0, 0.0))
        _rot_bone_world(pb, "Head",     (10.0, 8.0, 12.0))
        for leg, sx, fy in (("Leg_FL", 1.0, -1.0), ("Leg_FR", -1.0, -1.0), ("Leg_BL", 1.0, 1.0), ("Leg_BR", -1.0, 1.0)):
            _rot_bone_world(pb, f"{leg}_Thigh", (0.0, -34.0 * sx, -12.0 * sx * fy))
            _rot_bone_world(pb, f"{leg}_Shin",  (0.0,  36.0 * sx, 0.0))
        for side, sx in (("L", 1.0), ("R", -1.0)):
            _pose_vine_chain(pb, f"Vine_Main_{side}", 6, sx, (12.0, -16.0, 8.0), (4.0, -6.0, 4.0), (4.0, -10.0, 2.0))
            _pose_vine_chain(pb, f"Vine_Mid_{side}",  5, sx, (12.0, -14.0, 8.0), (4.0, -4.0, 4.0), (4.0, -8.0, 2.0))
            _pose_vine_chain(pb, f"Vine_Back_{side}", 4, sx, (10.0, -12.0, 0.0), (4.0, -4.0, 0.0), (4.0, -8.0, 0.0))

    else:  # death / death_flat / death_settle
        z_off = 0.0 if stage == "death_settle" else 0.015
        pel_x = 72.0 if stage == "death_settle" else 69.0
        pel_y = 12.0 if stage == "death_settle" else 10.0
        _rot_bone_world(pb, "Pelvis",   (pel_x, pel_y, -4.0))
        _rot_bone_world(pb, "Stalk_01", (2.0, 2.0, 0.0))
        _rot_bone_world(pb, "Stalk_02", (0.0, 2.0, 0.0))
        _rot_bone_world(pb, "Neck",     (-2.0, 2.0, 0.0))
        _rot_bone_world(pb, "Head",     (-14.0, 14.0, 12.0))
        _rot_bone_world(pb, "Jaw_Top",  (-6.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_Bot",  ( 6.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_L",    (0.0, 0.0,  6.0))
        _rot_bone_world(pb, "Jaw_R",    (0.0, 0.0, -6.0))
        bpy.context.view_layer.update()
        # Phase A: lift all 4 roots & 6 vines horizontally clear BEFORE floor snap so torso drops to Z=0
        for leg, sx, fy in (("Leg_FL", 1.0, -1.0), ("Leg_FR", -1.0, -1.0), ("Leg_BL", 1.0, 1.0), ("Leg_BR", -1.0, 1.0)):
            _aim_creature_chain(arm_obj, (f"{leg}_Thigh", f"{leg}_Shin", f"{leg}_Foot"), (
                (0.84 * sx, 0.50 * fy, 0.14), (0.86 * sx, 0.48 * fy, 0.10), (0.88 * sx, 0.46 * fy, 0.08),
            ))
        for side, sx in (("L", 1.0), ("R", -1.0)):
            _aim_creature_chain(arm_obj, [f"Vine_Main_{side}_{k:02d}" for k in range(1, 7)], [
                (sx * 0.88, -0.35 + 0.22 * (k / 5.0), 0.14) for k in range(6)
            ])
            _aim_creature_chain(arm_obj, [f"Vine_Mid_{side}_{k:02d}" for k in range(1, 6)], [
                (sx * 0.90, 0.08 + 0.22 * (k / 4.0), 0.12) for k in range(5)
            ])
            _aim_creature_chain(arm_obj, [f"Vine_Back_{side}_{k:02d}" for k in range(1, 5)], [
                (sx * 0.80, 0.50 + 0.16 * (k / 3.0), 0.12) for k in range(4)
            ])
        # Phase B: seat flattened torso & head directly on asphalt
        snap_creature_to_floor(arm_obj, body_obj, floor_z=0.0)
        # Phase C: drape limbs gently down onto road without propping up torso
        for leg, sx, fy in (("Leg_FL", 1.0, -1.0), ("Leg_FR", -1.0, -1.0), ("Leg_BL", 1.0, 1.0), ("Leg_BR", -1.0, 1.0)):
            _drape_creature_chain_to_floor(
                arm_obj,
                (f"{leg}_Thigh", f"{leg}_Shin", f"{leg}_Foot"),
                ((0.84 * sx, 0.50 * fy), (0.86 * sx, 0.48 * fy), (0.88 * sx, 0.46 * fy)),
                (0.14 + z_off, 0.09 + z_off, 0.07 + z_off * 0.5),
            )
        for side, sx in (("L", 1.0), ("R", -1.0)):
            _drape_creature_chain_to_floor(
                arm_obj,
                [f"Vine_Main_{side}_{k:02d}" for k in range(1, 7)],
                [(sx * 0.88, -0.35 + 0.22 * (k / 5.0)) for k in range(6)],
                [0.14 - 0.08 * (k / 5.0) + z_off for k in range(6)],
            )
            _drape_creature_chain_to_floor(
                arm_obj,
                [f"Vine_Mid_{side}_{k:02d}" for k in range(1, 6)],
                [(sx * 0.90, 0.08 + 0.22 * (k / 4.0)) for k in range(5)],
                [0.13 - 0.07 * (k / 4.0) + z_off for k in range(5)],
            )
            _drape_creature_chain_to_floor(
                arm_obj,
                [f"Vine_Back_{side}_{k:02d}" for k in range(1, 5)],
                [(sx * 0.80, 0.50 + 0.16 * (k / 3.0)) for k in range(4)],
                [0.12 - 0.06 * (k / 3.0) + z_off for k in range(4)],
            )

    if stage == "stalk":
        _clamp_creature_floor(arm_obj, body_obj, floor_z=0.0)
    else:
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
        _set_pelvis_world_offset(pb, (0.024 * math.sin(tau - 0.35), 0.0, -0.068 - 0.026 * math.cos(2.0 * tau - 0.5)))
        _rot_bone_world(pb, "Pelvis",          (12.0 + 3.0 * abs(sway), 2.5 * sway, 7.0 * br))
        _rot_bone_world(pb, "Spine_01",        (12.0, -1.8 * sway, -5.0 * br))
        _rot_bone_world(pb, "Spine_02",        (12.0, -0.8 * sway, -2.0 * br))
        _rot_bone_world(pb, "Hunch_Neck",      (-18.0, 1.8 * sway, 6.0))
        _rot_bone_world(pb, "Head",            (-12.0 + 3.0 * abs(br), 0.0, 8.0 * sway))
        _rot_bone_world(pb, "Mandible_L",      (0.0, 0.0,  22.0 + 6.0 * br))
        _rot_bone_world(pb, "Mandible_R",      (0.0, 0.0, -22.0 - 6.0 * br))
        _rot_bone_world(pb, "Jaw_Bot",         (22.0 + 6.0 * abs(sway), 0.0, 0.0))
        _rot_bone_world(pb, "Tongue_01",       (12.0, 0.0, 12.0 * sway))
        # Asymmetric counter-swinging scythe & clutch arms (phase 0 = Left leg front -> Right Scythe forward)
        arm_sw = math.cos(tau - 0.25)
        _rot_bone_world(pb, "Scythe_Upper",    (-16.0 - 24.0 * arm_sw, -12.0, 18.0))
        _rot_bone_world(pb, "Scythe_Fore",     (-22.0 + 8.0 * math.sin(tau), 10.0, 24.0))
        _rot_bone_world(pb, "Scythe_Blade",    (-18.0, 6.0, 16.0))
        _rot_bone_world(pb, "Clutch_Upper",    (-24.0 + 20.0 * arm_sw, 14.0, -20.0))
        _rot_bone_world(pb, "Clutch_Fore",     (-34.0, 10.0, -24.0))

        bpy.context.view_layer.update()
        # 3-segment digitigrade raptor IK (Thigh -> Shin -> Hock -> Ankle -> Ball -> Toe)
        for leg, sx, p_off in (("Leg_L", 1.0, 0.0), ("Leg_R", -1.0, 0.5)):
            str_n, lift_n, is_stance, u = _gait_foot_curve((phase + p_off) % 1.0, duty=0.52)
            p_ball = Vector((0.235 * sx, -0.080 + 0.40 * str_n, 0.020 + 0.15 * lift_n))
            if is_stance:
                pitch_deg = -10.0 * math.sin(math.pi * u) + 16.0 * max(0.0, (u - 0.65) / 0.35)
            else:
                pitch_deg = -12.0 * math.sin(math.pi * u)
            hock_ang = math.radians(52.0 + pitch_deg)
            l_ank = pb[f"{leg}_Ankle"].bone.length
            p_hock = p_ball + Vector((0.020 * sx, l_ank * math.cos(hock_ang), l_ank * math.sin(hock_ang)))
            _solve_creature_2bone_ik(arm_obj, f"{leg}_Thigh", f"{leg}_Shin",
                                     p_hock, pole_hint_arm=(0.15 * sx, -1.0, 0.25))
            _aim_creature_bone_world(arm_obj, f"{leg}_Ankle", p_ball - pb[f"{leg}_Ankle"].head)
            bpy.context.view_layer.update()
            _aim_creature_bone_world(arm_obj, f"{leg}_Toe",
                                     Vector((0.0, -1.0, 0.0 if is_stance else -0.35 * lift_n)))
    elif stage == "cleave_windup":
        _rot_bone_world(pb, "Pelvis",          (-4.0, 0.0, -24.0))
        _rot_bone_world(pb, "Spine_01",        (-6.0, -6.0, -18.0))
        _rot_bone_world(pb, "Spine_02",        (-6.0, -8.0, -14.0))
        _rot_bone_world(pb, "Hunch_Neck",      (6.0, 8.0, 26.0))
        _rot_bone_world(pb, "Head",            (4.0, 12.0, 28.0))
        _rot_bone_world(pb, "Leg_L_Thigh",     (-12.0, 0.0, 6.0))
        _rot_bone_world(pb, "Leg_R_Thigh",     (18.0, 0.0, -6.0))
        _rot_bone_world(pb, "Leg_R_Shin",      (-22.0, 0.0, 0.0))
        _rot_bone_world(pb, "Scythe_Shoulder", (6.0, 16.0, -28.0))
        _rot_bone_world(pb, "Scythe_Upper",    (24.0, -28.0, -36.0))
        _rot_bone_world(pb, "Scythe_Fore",     (-14.0, -16.0, -24.0))
        _rot_bone_world(pb, "Scythe_Blade",    (-8.0, -10.0, -12.0))
        _rot_bone_world(pb, "Clutch_Upper",    (-30.0, 14.0, -28.0))
        _rot_bone_world(pb, "Clutch_Fore",     (-38.0, 10.0, -24.0))
    elif stage == "slash":
        _rot_bone_world(pb, "Pelvis",          (14.0, 0.0, 24.0))
        _rot_bone_world(pb, "Spine_01",        (14.0, 6.0, 18.0))
        _rot_bone_world(pb, "Spine_02",        (14.0, 8.0, 16.0))
        _rot_bone_world(pb, "Hunch_Neck",      (-20.0, 0.0, -26.0))
        _rot_bone_world(pb, "Head",            (-14.0, 8.0, -22.0))
        _rot_bone_world(pb, "Leg_L_Thigh",     (24.0, 0.0, 8.0))
        _rot_bone_world(pb, "Leg_L_Shin",      (-22.0, 0.0, 0.0))
        _rot_bone_world(pb, "Leg_R_Thigh",     (-18.0, 0.0, -8.0))
        _rot_bone_world(pb, "Mandible_L",      (0.0, 0.0,  34.0))
        _rot_bone_world(pb, "Mandible_R",      (0.0, 0.0, -34.0))
        _rot_bone_world(pb, "Jaw_Bot",         (30.0, 0.0, 0.0))
        _rot_bone_world(pb, "Tongue_01",       (20.0, 0.0, 14.0))
        _rot_bone_world(pb, "Tongue_02",       (18.0, 0.0, -16.0))
        _rot_bone_world(pb, "Scythe_Shoulder", (0.0, -16.0, 32.0))
        _rot_bone_world(pb, "Scythe_Upper",    (-52.0, 14.0, 38.0))
        _rot_bone_world(pb, "Scythe_Fore",     (-32.0, 18.0, 28.0))
        _rot_bone_world(pb, "Scythe_Blade",    (-24.0, 12.0, 20.0))
        _rot_bone_world(pb, "Clutch_Upper",    (-32.0, 18.0, -28.0))
        _rot_bone_world(pb, "Clutch_Fore",     (-36.0, 12.0, -20.0))
    elif stage == "cleave_follow":
        _rot_bone_world(pb, "Pelvis",          (10.0, 0.0, 14.0))
        _rot_bone_world(pb, "Spine_01",        (10.0, 4.0, 10.0))
        _rot_bone_world(pb, "Spine_02",        (10.0, 4.0, 8.0))
        _rot_bone_world(pb, "Hunch_Neck",      (-14.0, 0.0, -14.0))
        _rot_bone_world(pb, "Head",            (-10.0, 4.0, -12.0))
        _rot_bone_world(pb, "Scythe_Shoulder", (0.0, -10.0, 20.0))
        _rot_bone_world(pb, "Scythe_Upper",    (-38.0, 24.0, 44.0))
        _rot_bone_world(pb, "Scythe_Fore",     (-22.0, 14.0, 20.0))
        _rot_bone_world(pb, "Clutch_Upper",    (-26.0, 12.0, -18.0))
    elif stage == "lunge_windup":
        _rot_bone_world(pb, "Pelvis",          (22.0, 0.0, -10.0))
        _rot_bone_world(pb, "Spine_01",        (16.0, 0.0, -6.0))
        _rot_bone_world(pb, "Spine_02",        (14.0, 0.0, -4.0))
        _rot_bone_world(pb, "Hunch_Neck",      (-24.0, 0.0, 8.0))
        _rot_bone_world(pb, "Head",            (-20.0, 0.0, 10.0))
        _rot_bone_world(pb, "Leg_L_Thigh",     (34.0, 0.0, 8.0))
        _rot_bone_world(pb, "Leg_L_Shin",      (-48.0, 0.0, 0.0))
        _rot_bone_world(pb, "Leg_R_Thigh",     (28.0, 0.0, -8.0))
        _rot_bone_world(pb, "Leg_R_Shin",      (-44.0, 0.0, 0.0))
        _rot_bone_world(pb, "Scythe_Upper",    (14.0, -24.0, -24.0))
        _rot_bone_world(pb, "Scythe_Fore",     (-12.0, -14.0, -16.0))
        _rot_bone_world(pb, "Clutch_Upper",    (-18.0, 18.0, -24.0))
    elif stage == "reaper_lunge":
        _rot_bone_world(pb, "Pelvis",          (18.0, 0.0, -22.0))
        _rot_bone_world(pb, "Spine_01",        (16.0, -8.0, -16.0))
        _rot_bone_world(pb, "Spine_02",        (14.0, -6.0, -12.0))
        _rot_bone_world(pb, "Hunch_Neck",      (-22.0, 0.0, 26.0))
        _rot_bone_world(pb, "Head",            (-18.0, -8.0, 22.0))
        _rot_bone_world(pb, "Mandible_L",      (0.0, 0.0,  36.0))
        _rot_bone_world(pb, "Mandible_R",      (0.0, 0.0, -36.0))
        _rot_bone_world(pb, "Jaw_Bot",         (34.0, 0.0, 0.0))
        _rot_bone_world(pb, "Tongue_01",       (20.0, 0.0, -10.0))
        _rot_bone_world(pb, "Tongue_02",       (18.0, 0.0, 14.0))
        _rot_bone_world(pb, "Leg_L_Thigh",     (-26.0, 0.0, 12.0))
        _rot_bone_world(pb, "Leg_L_Shin",      (22.0, 0.0, 0.0))
        _rot_bone_world(pb, "Leg_R_Thigh",     (28.0, 0.0, -12.0))
        _rot_bone_world(pb, "Leg_R_Shin",      (-20.0, 0.0, 0.0))
        _rot_bone_world(pb, "Scythe_Shoulder", (0.0, -18.0, -26.0))
        _rot_bone_world(pb, "Scythe_Upper",    (-62.0, -14.0, -26.0))
        _rot_bone_world(pb, "Scythe_Fore",     (-38.0, 10.0, 16.0))
        _rot_bone_world(pb, "Scythe_Blade",    (-26.0, 8.0, 20.0))
        _rot_bone_world(pb, "Clutch_Upper",    (-38.0, 18.0, -30.0))
        _rot_bone_world(pb, "Clutch_Fore",     (-38.0, 12.0, -22.0))
    elif stage == "lunge_follow":
        _rot_bone_world(pb, "Pelvis",          (14.0, 0.0, 16.0))
        _rot_bone_world(pb, "Spine_01",        (12.0, 4.0, 12.0))
        _rot_bone_world(pb, "Head",            (-12.0, 6.0, -14.0))
        _rot_bone_world(pb, "Leg_L_Thigh",     (24.0, 0.0, 6.0))
        _rot_bone_world(pb, "Leg_L_Shin",      (-24.0, 0.0, 0.0))
        _rot_bone_world(pb, "Leg_R_Thigh",     (-16.0, 0.0, -6.0))
        _rot_bone_world(pb, "Scythe_Upper",    (-36.0, 18.0, 32.0))
        _rot_bone_world(pb, "Scythe_Fore",     (-24.0, 12.0, 20.0))
        _rot_bone_world(pb, "Clutch_Upper",    (-22.0, 12.0, -18.0))
    elif stage == "death_stagger":
        _rot_bone_world(pb, "Pelvis",          (-12.0, -10.0, -14.0))
        _rot_bone_world(pb, "Spine_01",        (-8.0, -4.0, -10.0))
        _rot_bone_world(pb, "Spine_02",        (-6.0, 0.0, -6.0))
        _rot_bone_world(pb, "Hunch_Neck",      (-10.0, 6.0, 12.0))
        _rot_bone_world(pb, "Head",            (-12.0, 8.0, 14.0))
        _rot_bone_world(pb, "Mandible_L",      (0.0, 0.0,  26.0))
        _rot_bone_world(pb, "Mandible_R",      (0.0, 0.0, -26.0))
        _rot_bone_world(pb, "Jaw_Bot",         (22.0, 0.0, 0.0))
        _rot_bone_world(pb, "Leg_L_Thigh",     (-14.0, 0.0, 6.0))
        _rot_bone_world(pb, "Leg_L_Shin",      (18.0, 0.0, 0.0))
        _rot_bone_world(pb, "Scythe_Upper",    (-22.0, -18.0, -22.0))
        _rot_bone_world(pb, "Scythe_Fore",     (-16.0, 10.0, 18.0))
        _rot_bone_world(pb, "Clutch_Upper",    (-26.0, 16.0, -22.0))
    elif stage == "death_kneel":
        _rot_bone_world(pb, "Pelvis",          (42.0, -14.0, 8.0))
        _rot_bone_world(pb, "Spine_01",        (12.0, -4.0, 4.0))
        _rot_bone_world(pb, "Spine_02",        (8.0, -2.0, 2.0))
        _rot_bone_world(pb, "Hunch_Neck",      (-16.0, 6.0, 8.0))
        _rot_bone_world(pb, "Head",            (-18.0, 10.0, 14.0))
        _rot_bone_world(pb, "Leg_L_Thigh",     (-44.0, 0.0, 8.0))
        _rot_bone_world(pb, "Leg_L_Shin",      (72.0, 0.0, 0.0))
        _rot_bone_world(pb, "Leg_R_Thigh",     (-42.0, 0.0, -8.0))
        _rot_bone_world(pb, "Leg_R_Shin",      (70.0, 0.0, 0.0))
        _rot_bone_world(pb, "Scythe_Upper",    (-30.0, -20.0, 18.0))
        _rot_bone_world(pb, "Scythe_Fore",     (-14.0, 8.0, 14.0))
        _rot_bone_world(pb, "Clutch_Upper",    (-28.0, 22.0, -22.0))
    else:  # death / death_flat / death_settle
        z_off = 0.0 if stage == "death_settle" else 0.015
        pel_x = 67.0 if stage == "death_settle" else 65.0
        _rot_bone_world(pb, "Pelvis",          (pel_x, -10.0, 6.0))
        _rot_bone_world(pb, "Spine_01",        (-2.0, -2.0, 2.0))
        _rot_bone_world(pb, "Spine_02",        (-2.0, -2.0, 2.0))
        _rot_bone_world(pb, "Hunch_Neck",      (-12.0, 10.0, 12.0))
        _rot_bone_world(pb, "Head",            (-20.0, 16.0, 14.0))
        _rot_bone_world(pb, "Mandible_L",      (0.0, 0.0,  2.0))
        _rot_bone_world(pb, "Mandible_R",      (0.0, 0.0, -2.0))
        _rot_bone_world(pb, "Jaw_Bot",         (-4.0, 0.0, 0.0))
        _rot_bone_world(pb, "Tongue_01",       (-35.0, 0.0, 0.0))
        _rot_bone_world(pb, "Tongue_02",       (-35.0, 0.0, 0.0))
        bpy.context.view_layer.update()
        _aim_creature_chain(arm_obj, ("Leg_L_Thigh", "Leg_L_Shin", "Leg_L_Ankle", "Leg_L_Toe"), (
            (0.32, 0.94, 0.14), (0.14, 0.98, 0.10), (0.22, 0.97, 0.08), (0.18, 0.98, 0.06),
        ))
        _aim_creature_chain(arm_obj, ("Leg_R_Thigh", "Leg_R_Shin", "Leg_R_Ankle", "Leg_R_Toe"), (
            (-0.24, 0.97, 0.14), (-0.36, 0.93, 0.10), (-0.18, 0.98, 0.08), (-0.15, 0.98, 0.06),
        ))
        _aim_creature_chain(arm_obj, ("Clutch_Upper", "Clutch_Fore", "Clutch_Hand"), (
            (0.80, -0.58, 0.14), (0.64, -0.76, 0.10), (0.50, -0.86, 0.08),
        ))
        _aim_creature_chain(arm_obj, ("Scythe_Upper", "Scythe_Fore", "Scythe_Blade", "Scythe_Hook"), (
            (-0.82, -0.54, 0.14), (-0.62, -0.77, 0.10), (-0.38, -0.91, 0.08), (-0.20, -0.97, 0.06),
        ))
        snap_creature_to_floor(arm_obj, body_obj, floor_z=0.0)
        _drape_creature_chain_to_floor(
            arm_obj, ("Leg_L_Thigh", "Leg_L_Shin", "Leg_L_Ankle", "Leg_L_Toe"),
            ((0.32, 0.94), (0.14, 0.98), (0.22, 0.97), (0.18, 0.98)),
            (0.14 + z_off, 0.11 + z_off, 0.09, 0.08),
        )
        _drape_creature_chain_to_floor(
            arm_obj, ("Leg_R_Thigh", "Leg_R_Shin", "Leg_R_Ankle", "Leg_R_Toe"),
            ((-0.24, 0.97), (-0.36, 0.93), (-0.18, 0.98), (-0.15, 0.98)),
            (0.15 + z_off, 0.11 + z_off, 0.09, 0.08),
        )
        _drape_creature_chain_to_floor(
            arm_obj, ("Clutch_Upper", "Clutch_Fore", "Clutch_Hand"),
            ((0.80, -0.58), (0.64, -0.76), (0.50, -0.86)),
            (0.10 + z_off, 0.08, 0.07),
        )
        _drape_creature_chain_to_floor(
            arm_obj, ("Scythe_Upper", "Scythe_Fore", "Scythe_Blade", "Scythe_Hook"),
            ((-0.82, -0.54), (-0.62, -0.77), (-0.38, -0.91), (-0.20, -0.97)),
            (0.13 + z_off, 0.10 + z_off, 0.08, 0.07),
        )

    if stage == "stalk":
        _clamp_creature_floor(arm_obj, body_obj, floor_z=0.0)
    else:
        snap_creature_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_thorn_shroud_pose(arm_obj, body_obj, stage="idle", phase=0.0):
    """Apply eerie tri-stilt Thorn Shroud Seraph poses (`idle`, `stalk`, `sweep*`, `razor_bloom*`, `death`)."""
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
        _set_pelvis_world_offset(pb, (0.018 * math.sin(tau), 0.0, -0.135 + 0.010 * math.sin(3.0 * tau)))
        _rot_bone_world(pb, "Pelvis",        (7.0, 2.0 * sway, 5.5 * br))
        _rot_bone_world(pb, "Spine_01",      (7.0, -1.5 * sway, -3.5 * br))
        _rot_bone_world(pb, "Spine_02",      (7.0, -0.6 * sway, 2.5 * br))
        _rot_bone_world(pb, "Head",          (-16.0, 0.0, 8.0 * sway))
        _rot_bone_world(pb, "Jaw_Scream",    (24.0 + 5.0 * abs(sway), 0.0, 0.0))
        _rot_bone_world(pb, "Arm_L_Upper",   (32.0 + 16.0 * sway, -18.0, 26.0))
        _rot_bone_world(pb, "Arm_L_Fore",    (36.0, 0.0, -22.0))
        _rot_bone_world(pb, "Arm_R_Upper",   (32.0 - 16.0 * sway, 18.0, -26.0))
        _rot_bone_world(pb, "Arm_R_Fore",    (36.0, 0.0, 22.0))
        wing_b = 11.0 * br

        bpy.context.view_layer.update()
        # 3-phase tripod stilt gait: Stilt_FL (0.000) -> Stilt_FR (0.333) -> Stilt_Rear (0.667)
        for stilt, p_off, rest_tip, (out_x, out_y), pole in (
            ("Stilt_FL",   0.000, Vector(( 0.24, -0.20, 0.015)), ( 0.03, -0.02), ( 0.75, -0.65, 0.20)),
            ("Stilt_FR",   0.333, Vector((-0.24, -0.20, 0.015)), (-0.03, -0.02), (-0.75, -0.65, 0.20)),
            ("Stilt_Rear", 0.667, Vector(( 0.00,  0.24, 0.015)), ( 0.00,  0.04), ( 0.00,  1.00, 0.20)),
        ):
            str_n, lift_n, _, _ = _gait_foot_curve((phase + p_off) % 1.0, duty=0.68)
            p_tip = rest_tip + Vector((0.0, 0.21 * str_n, 0.13 * lift_n))
            l3 = pb[f"{stilt}_03"].bone.length
            dz3 = math.sqrt(max(0.01, l3 * l3 - out_x * out_x - out_y * out_y))
            p_ankle = p_tip + Vector((out_x, out_y, dz3))
            _solve_creature_2bone_ik(arm_obj, f"{stilt}_01", f"{stilt}_02", p_ankle, pole_hint_arm=pole)
            _aim_creature_bone_world(arm_obj, f"{stilt}_03", p_tip - pb[f"{stilt}_03"].head)
    elif stage == "sweep_windup":
        _rot_bone_world(pb, "Pelvis",      (-4.0, 0.0, 20.0))
        _rot_bone_world(pb, "Spine_01",    (-4.0, 0.0, 16.0))
        _rot_bone_world(pb, "Spine_02",    (-6.0, 0.0, 14.0))
        _rot_bone_world(pb, "Head",        (-8.0, 0.0, -20.0))
        _rot_bone_world(pb, "Arm_L_Upper", (18.0, -34.0, -18.0))
        _rot_bone_world(pb, "Arm_L_Fore",  (22.0, -14.0, -24.0))
        _rot_bone_world(pb, "Arm_R_Upper", (18.0, 34.0, 18.0))
        _rot_bone_world(pb, "Arm_R_Fore",  (22.0, 14.0, 24.0))
        wing_b = -8.0
    elif stage == "sweep":
        _rot_bone_world(pb, "Pelvis",      (10.0, 0.0, -24.0))
        _rot_bone_world(pb, "Spine_01",    (10.0, 0.0, -18.0))
        _rot_bone_world(pb, "Spine_02",    (12.0, 0.0, -16.0))
        _rot_bone_world(pb, "Head",        (-18.0, 8.0, 24.0))
        _rot_bone_world(pb, "Jaw_Scream",  (34.0, 0.0, 0.0))
        _rot_bone_world(pb, "Stilt_FL_01", (18.0, 0.0, 0.0))
        _rot_bone_world(pb, "Stilt_FR_01", (-16.0, 0.0, 0.0))
        _rot_bone_world(pb, "Arm_L_Upper", (60.0, -34.0, 38.0))
        _rot_bone_world(pb, "Arm_L_Fore",  (44.0, -12.0, 26.0))
        _rot_bone_world(pb, "Arm_R_Upper", (52.0, 34.0, -38.0))
        _rot_bone_world(pb, "Arm_R_Fore",  (40.0, 12.0, -24.0))
        wing_b = 18.0
    elif stage == "sweep_follow":
        _rot_bone_world(pb, "Pelvis",      (6.0, 0.0, -14.0))
        _rot_bone_world(pb, "Spine_01",    (6.0, 0.0, -10.0))
        _rot_bone_world(pb, "Head",        (-12.0, 4.0, 14.0))
        _rot_bone_world(pb, "Arm_L_Upper", (46.0, -16.0, 48.0))
        _rot_bone_world(pb, "Arm_R_Upper", (42.0, 16.0, -48.0))
        wing_b = 10.0
    elif stage == "bloom_windup":
        _rot_bone_world(pb, "Pelvis",      (10.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_01",    (12.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_02",    (14.0, 0.0, 0.0))
        _rot_bone_world(pb, "Head",        (14.0, 0.0, 0.0))
        _rot_bone_world(pb, "Crown_L",     (12.0, 8.0, -8.0))
        _rot_bone_world(pb, "Crown_C",     (14.0, 0.0, 0.0))
        _rot_bone_world(pb, "Crown_R",     (12.0, -8.0, 8.0))
        _rot_bone_world(pb, "Arm_L_Upper", (28.0, 14.0, -32.0))
        _rot_bone_world(pb, "Arm_R_Upper", (28.0, -14.0, 32.0))
        wing_b = -16.0
    elif stage == "razor_bloom":
        _rot_bone_world(pb, "Pelvis",      (-8.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_01",    (-10.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_02",    (-14.0, 0.0, 0.0))
        _rot_bone_world(pb, "Neck",        (-12.0, 0.0, 0.0))
        _rot_bone_world(pb, "Head",        (-26.0, 0.0, 8.0))
        _rot_bone_world(pb, "Jaw_Scream",  (38.0, 0.0, 0.0))
        _rot_bone_world(pb, "Crown_L",     (-14.0, -26.0, 22.0))
        _rot_bone_world(pb, "Crown_C",     (-22.0, 0.0, 0.0))
        _rot_bone_world(pb, "Crown_R",     (-14.0, 26.0, -22.0))
        _rot_bone_world(pb, "Arm_L_Upper", (54.0, -48.0, 34.0))
        _rot_bone_world(pb, "Arm_L_Fore",  (28.0, -18.0, 22.0))
        _rot_bone_world(pb, "Arm_R_Upper", (54.0, 48.0, -34.0))
        _rot_bone_world(pb, "Arm_R_Fore",  (28.0, 18.0, -22.0))
        wing_b = 30.0
    elif stage == "bloom_rebound":
        _rot_bone_world(pb, "Pelvis",      (4.0, 0.0, 4.0))
        _rot_bone_world(pb, "Spine_01",    (4.0, 0.0, -4.0))
        _rot_bone_world(pb, "Head",        (-14.0, 0.0, -8.0))
        _rot_bone_world(pb, "Arm_L_Upper", (34.0, -24.0, 22.0))
        _rot_bone_world(pb, "Arm_R_Upper", (34.0, 24.0, -22.0))
        wing_b = 14.0
    elif stage == "death_stagger":
        _rot_bone_world(pb, "Pelvis",      (-10.0, 8.0, -8.0))
        _rot_bone_world(pb, "Spine_01",    (-8.0, 4.0, -4.0))
        _rot_bone_world(pb, "Spine_02",    (-10.0, 4.0, 0.0))
        _rot_bone_world(pb, "Neck",        (-10.0, 0.0, 6.0))
        _rot_bone_world(pb, "Head",        (-18.0, -6.0, 12.0))
        _rot_bone_world(pb, "Jaw_Scream",  (38.0, 0.0, 0.0))
        _rot_bone_world(pb, "Arm_L_Upper", (46.0, -28.0, 26.0))
        _rot_bone_world(pb, "Arm_R_Upper", (46.0, 28.0, -26.0))
        wing_b = 26.0
    elif stage == "death_kneel":
        _rot_bone_world(pb, "Pelvis",      (42.0, 12.0, -6.0))
        _rot_bone_world(pb, "Spine_01",    (16.0, 4.0, 0.0))
        _rot_bone_world(pb, "Spine_02",    (12.0, 4.0, 0.0))
        _rot_bone_world(pb, "Head",        (-8.0, 10.0, 12.0))
        _rot_bone_world(pb, "Jaw_Scream",  (24.0, 0.0, 0.0))
        _rot_bone_world(pb, "Stilt_FL_01", (-42.0, 0.0, 12.0))
        _rot_bone_world(pb, "Stilt_FL_02", (54.0, 0.0, 0.0))
        _rot_bone_world(pb, "Stilt_FR_01", (-42.0, 0.0, -12.0))
        _rot_bone_world(pb, "Stilt_FR_02", (54.0, 0.0, 0.0))
        _rot_bone_world(pb, "Stilt_Rear_01", (44.0, 0.0, 0.0))
        _rot_bone_world(pb, "Arm_L_Upper", (28.0, -20.0, 22.0))
        _rot_bone_world(pb, "Arm_R_Upper", (28.0, 20.0, -22.0))
        wing_b = -12.0
    else:  # death / death_flat / death_settle
        z_off = 0.0 if stage == "death_settle" else 0.015
        pel_x = 90.0 if stage == "death_settle" else 88.0
        _rot_bone_world(pb, "Pelvis",      (pel_x, 6.0, -6.0))
        _rot_bone_world(pb, "Spine_01",    (2.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_02",    (0.0, 0.0, 0.0))
        _rot_bone_world(pb, "Neck",        (-22.0, 10.0, 10.0))
        _rot_bone_world(pb, "Head",        (-28.0, 24.0, 16.0))
        _rot_bone_world(pb, "Crown_L",     (12.0, -8.0, 10.0))
        _rot_bone_world(pb, "Crown_C",     (18.0, 0.0, 0.0))
        _rot_bone_world(pb, "Crown_R",     (12.0, 8.0, -10.0))
        _rot_bone_world(pb, "Jaw_Scream",  (6.0, 0.0, 0.0))
        wing_b = -18.0
        bpy.context.view_layer.update()
        _aim_creature_chain(arm_obj, ("Stilt_FL_01", "Stilt_FL_02", "Stilt_FL_03"), ((0.35, 0.94, 0.12), (0.30, 0.95, 0.08), (0.28, 0.96, 0.06)))
        _aim_creature_chain(arm_obj, ("Stilt_FR_01", "Stilt_FR_02", "Stilt_FR_03"), ((-0.35, 0.94, 0.12), (-0.30, 0.95, 0.08), (-0.28, 0.96, 0.06)))
        _aim_creature_chain(arm_obj, ("Stilt_Rear_01", "Stilt_Rear_02", "Stilt_Rear_03"), ((0.05, 0.99, 0.14), (0.04, 0.99, 0.10), (0.03, 0.99, 0.06)))
        _aim_creature_chain(arm_obj, ("Arm_L_Upper", "Arm_L_Fore", "Arm_L_Hand"), ((0.76, -0.64, 0.12), (0.58, -0.81, 0.08), (0.48, -0.88, 0.06)))
        _aim_creature_chain(arm_obj, ("Arm_R_Upper", "Arm_R_Fore", "Arm_R_Hand"), ((-0.76, -0.64, 0.12), (-0.58, -0.81, 0.08), (-0.48, -0.88, 0.06)))
        for side, sx in (("L", 1.0), ("R", -1.0)):
            for wi in (1, 2, 3):
                wy = 0.42 + 0.14 * wi
                _aim_creature_chain(arm_obj, [f"Wing_{side}{wi}_01", f"Wing_{side}{wi}_02", f"Wing_{side}{wi}_03"], (
                    (0.84 * sx, wy, 0.14), (0.80 * sx, wy + 0.12, 0.10), (0.76 * sx, wy + 0.22, 0.08),
                ))
        snap_creature_to_floor(arm_obj, body_obj, floor_z=0.0)
        _drape_creature_chain_to_floor(
            arm_obj, ("Stilt_FL_01", "Stilt_FL_02", "Stilt_FL_03"),
            ((0.35, 0.94), (0.30, 0.95), (0.28, 0.96)),
            (0.10 + z_off, 0.07 + z_off * 0.5, 0.05),
        )
        _drape_creature_chain_to_floor(
            arm_obj, ("Stilt_FR_01", "Stilt_FR_02", "Stilt_FR_03"),
            ((-0.35, 0.94), (-0.30, 0.95), (-0.28, 0.96)),
            (0.10 + z_off, 0.07 + z_off * 0.5, 0.05),
        )
        _drape_creature_chain_to_floor(
            arm_obj, ("Stilt_Rear_01", "Stilt_Rear_02", "Stilt_Rear_03"),
            ((0.05, 0.99), (0.04, 0.99), (0.03, 0.99)),
            (0.12 + z_off, 0.08 + z_off * 0.5, 0.05),
        )
        _drape_creature_chain_to_floor(
            arm_obj, ("Arm_L_Upper", "Arm_L_Fore", "Arm_L_Hand"),
            ((0.76, -0.64), (0.58, -0.81), (0.48, -0.88)),
            (0.10 + z_off, 0.07 + z_off * 0.5, 0.05),
        )
        _drape_creature_chain_to_floor(
            arm_obj, ("Arm_R_Upper", "Arm_R_Fore", "Arm_R_Hand"),
            ((-0.76, -0.64), (-0.58, -0.81), (-0.48, -0.88)),
            (0.10 + z_off, 0.07 + z_off * 0.5, 0.05),
        )
        for side, sx in (("L", 1.0), ("R", -1.0)):
            for wi in (1, 2, 3):
                wy = 0.42 + 0.14 * wi
                _drape_creature_chain_to_floor(
                    arm_obj,
                    [f"Wing_{side}{wi}_01", f"Wing_{side}{wi}_02", f"Wing_{side}{wi}_03"],
                    ((0.84 * sx, wy), (0.80 * sx, wy + 0.12), (0.76 * sx, wy + 0.22)),
                    (0.11 + z_off, 0.08 + z_off * 0.5, 0.05),
                )

    if stage not in ("death", "death_flat", "death_settle"):
        for side, sx in (("L", 1.0), ("R", -1.0)):
            for wi, z_ang in ((1, 18.0), (2, 10.0), (3, 4.0)):
                if stage == "stalk":
                    w1 = 11.0 * math.sin(tau - 0.60 * wi - 0.50 * 0)
                    w2 = 11.0 * math.sin(tau - 0.60 * wi - 0.50 * 1)
                    w3 = 11.0 * math.sin(tau - 0.60 * wi - 0.50 * 2)
                    _rot_bone_world(pb, f"Wing_{side}{wi}_01", (0.4 * w1, -0.5 * w1 * sx, (z_ang + 0.6 * w1) * sx))
                    _rot_bone_world(pb, f"Wing_{side}{wi}_02", (0.4 * w2, -0.4 * w2 * sx, 0.4 * w2 * sx))
                    _rot_bone_world(pb, f"Wing_{side}{wi}_03", (0.3 * w3, -0.3 * w3 * sx, 0.3 * w3 * sx))
                else:
                    _rot_bone_world(pb, f"Wing_{side}{wi}_01", (0.4 * wing_b, -0.5 * wing_b * sx, (z_ang + 0.6 * wing_b) * sx))
                    _rot_bone_world(pb, f"Wing_{side}{wi}_02", (0.4 * wing_b, -0.4 * wing_b * sx, 0.4 * wing_b * sx))
                    _rot_bone_world(pb, f"Wing_{side}{wi}_03", (0.3 * wing_b, -0.3 * wing_b * sx, 0.3 * wing_b * sx))

    if stage == "stalk":
        _clamp_creature_floor(arm_obj, body_obj, floor_z=0.0)
    else:
        snap_creature_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_arachnid_maw_pose(arm_obj, body_obj, stage="idle", phase=0.0):
    """Apply 6-legged Arachnid Maw poses (`idle`, `scuttle`, `bite*`, `pounce*`/`acid_pounce`, `death`)."""
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
        _set_pelvis_world_offset(pb, (0.016 * math.sin(tau), 0.0, -0.025 + 0.008 * math.sin(2.0 * tau)))
        _rot_bone_world(pb, "Pelvis",   (3.0 + 2.0 * br, 3.0 * sway, 4.0 * sway))
        _rot_bone_world(pb, "Abdomen",  (10.0 + 3.0 * br, 0.0, -5.0 * sway))
        _rot_bone_world(pb, "Head",     (-5.0, 0.0, 4.0 * sway))
        _rot_bone_world(pb, "Maw_Top",  (-20.0 - 4.0 * abs(sway), 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Bot",  ( 24.0 + 4.0 * abs(sway), 0.0, 0.0))
        _rot_bone_world(pb, "Palp_L_01", (0.0, 0.0,  16.0 + 8.0 * sway))
        _rot_bone_world(pb, "Palp_R_01", (0.0, 0.0, -16.0 + 8.0 * sway))
        for ti, td in enumerate((12.0, 16.0, 18.0, 20.0), start=1):
            _rot_bone_world(pb, f"Tail_{ti:02d}", (td + 8.0 * math.sin(tau - 0.65 * ti), 0.0, -9.0 * math.cos(tau - 0.65 * ti)))

        bpy.context.view_layer.update()
        # Alternating tripod hexapod IK (Tripod A: FL/MR/BL -> Tripod B: FR/ML/BR)
        for lname, p_off in (
            ("Leg_FL", 0.00), ("Leg_MR", 0.04), ("Leg_BL", 0.08),
            ("Leg_FR", 0.50), ("Leg_ML", 0.54), ("Leg_BR", 0.58),
        ):
            sx = 1.0 if lname.endswith("L") else -1.0
            str_n, lift_n, _, _ = _gait_foot_curve((phase + p_off) % 1.0, duty=0.56)
            rest_tip = pb[f"{lname}_Tarsus"].bone.tail_local.copy()
            tarsus_up = pb[f"{lname}_Tarsus"].bone.head_local - rest_tip
            p_tip = rest_tip + Vector((0.0, 0.34 * str_n, 0.16 * lift_n))
            p_tarsus_head = p_tip + tarsus_up + Vector((-0.025 * sx * lift_n, 0.0, 0.025 * lift_n))
            _solve_creature_2bone_ik(arm_obj, f"{lname}_Coxa", f"{lname}_Femur",
                                     p_tarsus_head, pole_hint_arm=(0.25 * sx, 0.0, 1.0))
            _aim_creature_bone_world(arm_obj, f"{lname}_Tarsus", p_tip - pb[f"{lname}_Tarsus"].head)
    elif stage == "bite_windup":
        _rot_bone_world(pb, "Pelvis",    (-10.0, 0.0, 0.0))
        _rot_bone_world(pb, "Head",      (8.0, 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Top",   (-10.0, 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Bot",   ( 12.0, 0.0, 0.0))
        for ti, td in enumerate((18.0, 24.0, 26.0, 28.0), start=1):
            _rot_bone_world(pb, f"Tail_{ti:02d}", (td, 0.0, 0.0))
    elif stage == "bite":
        _rot_bone_world(pb, "Pelvis",    (14.0, 0.0, 4.0))
        _rot_bone_world(pb, "Head",      (-14.0, 0.0, -4.0))
        _rot_bone_world(pb, "Maw_Top",   (-34.0, 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Bot",   ( 38.0, 0.0, 0.0))
        _rot_bone_world(pb, "Palp_L_01", (0.0, 0.0,  30.0))
        _rot_bone_world(pb, "Palp_L_02", (0.0, 0.0, -28.0))
        _rot_bone_world(pb, "Palp_R_01", (0.0, 0.0, -30.0))
        _rot_bone_world(pb, "Palp_R_02", (0.0, 0.0,  28.0))
        for ti, td in enumerate((14.0, 18.0, 22.0, 24.0), start=1):
            _rot_bone_world(pb, f"Tail_{ti:02d}", (td, 0.0, 0.0))
    elif stage == "bite_follow":
        _rot_bone_world(pb, "Pelvis",    (6.0, 0.0, -4.0))
        _rot_bone_world(pb, "Head",      (4.0, 0.0, 6.0))
        _rot_bone_world(pb, "Maw_Top",   (-4.0, 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Bot",   ( 6.0, 0.0, 0.0))
        for ti, td in enumerate((10.0, 14.0, 16.0, 18.0), start=1):
            _rot_bone_world(pb, f"Tail_{ti:02d}", (td, 0.0, 0.0))
    elif stage == "pounce_windup":
        _rot_bone_world(pb, "Pelvis",    (14.0, 0.0, 0.0))
        _rot_bone_world(pb, "Abdomen",   (16.0, 0.0, 0.0))
        for lname, sx in (("Leg_FL", 1.0), ("Leg_ML", 1.0), ("Leg_BL", 1.0), ("Leg_FR", -1.0), ("Leg_MR", -1.0), ("Leg_BR", -1.0)):
            _rot_bone_world(pb, f"{lname}_Coxa",  (0.0, -24.0 * sx, 0.0))
            _rot_bone_world(pb, f"{lname}_Femur", (0.0,  26.0 * sx, 0.0))
        for ti, td in enumerate((22.0, 28.0, 30.0, 30.0), start=1):
            _rot_bone_world(pb, f"Tail_{ti:02d}", (td, 0.0, 0.0))
    elif stage == "acid_pounce":
        _rot_bone_world(pb, "Pelvis",    (-22.0, 0.0, 0.0))
        _rot_bone_world(pb, "Abdomen",   (14.0, 0.0, 0.0))
        _rot_bone_world(pb, "Head",      (-18.0, 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Top",   (-34.0, 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Bot",   ( 38.0, 0.0, 0.0))
        _rot_bone_world(pb, "Palp_L_01", (0.0, 0.0,  32.0))
        _rot_bone_world(pb, "Palp_R_01", (0.0, 0.0, -32.0))
        for lname, sx in (("Leg_FL", 1.0), ("Leg_FR", -1.0)):
            _rot_bone_world(pb, f"{lname}_Coxa",  (-18.0, -30.0 * sx, -22.0 * sx))
            _rot_bone_world(pb, f"{lname}_Femur", ( 14.0,  22.0 * sx, 0.0))
        for ti, td in enumerate((-8.0, -12.0, -14.0, -16.0), start=1):
            _rot_bone_world(pb, f"Tail_{ti:02d}", (td, 0.0, 0.0))
    elif stage == "pounce_follow":
        _rot_bone_world(pb, "Pelvis",    (8.0, 0.0, 0.0))
        _rot_bone_world(pb, "Head",      (-6.0, 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Top",   (-12.0, 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Bot",   ( 14.0, 0.0, 0.0))
        for ti, td in enumerate((10.0, 14.0, 18.0, 20.0), start=1):
            _rot_bone_world(pb, f"Tail_{ti:02d}", (td, 0.0, 0.0))
    elif stage == "death_stagger":
        _rot_bone_world(pb, "Pelvis",    (-14.0, 38.0, 6.0))
        _rot_bone_world(pb, "Abdomen",   (8.0, 10.0, 0.0))
        _rot_bone_world(pb, "Head",      (-12.0, 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Top",   (-24.0, 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Bot",   ( 28.0, 0.0, 0.0))
        for lname, sx in (("Leg_FL", 1.0), ("Leg_ML", 1.0), ("Leg_BL", 1.0)):
            _rot_bone_world(pb, f"{lname}_Coxa",  (0.0, -34.0 * sx, 0.0))
            _rot_bone_world(pb, f"{lname}_Femur", (0.0,  28.0 * sx, 0.0))
        for ti, td in enumerate((14.0, 18.0, 18.0, 16.0), start=1):
            _rot_bone_world(pb, f"Tail_{ti:02d}", (td, 0.0, 8.0))
    elif stage == "death_kneel":
        _rot_bone_world(pb, "Pelvis",    (0.0, 108.0, 8.0))
        _rot_bone_world(pb, "Abdomen",   (6.0, 8.0, 0.0))
        _rot_bone_world(pb, "Maw_Top",   (-12.0, 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Bot",   ( 18.0, 0.0, 0.0))
        bpy.context.view_layer.update()
        for lname, sx, y_bias in (
            ("Leg_FL", 1.0, -0.45), ("Leg_ML", 1.0, 0.05), ("Leg_BL", 1.0, 0.50),
            ("Leg_FR", -1.0, -0.45), ("Leg_MR", -1.0, 0.05), ("Leg_BR", -1.0, 0.50),
        ):
            _aim_creature_chain(arm_obj, (f"{lname}_Coxa", f"{lname}_Femur", f"{lname}_Tarsus"), (
                (0.60 * sx, y_bias, 0.55),
                (0.10 * sx, y_bias * 0.5, 0.90),
                (-0.45 * sx, y_bias * 0.3, 0.40),
            ))
        _aim_creature_chain(arm_obj, ("Tail_01", "Tail_02", "Tail_03", "Tail_04"), (
            (0.15, 0.95, 0.15), (0.15, 0.92, 0.32), (0.10, 0.86, 0.46), (0.05, 0.80, 0.54),
        ))
    else:  # death / death_flat / death_settle
        roll = 176.0 if stage == "death_settle" else 174.0
        curl_in = -0.82 if stage == "death_settle" else -0.72
        _rot_bone_world(pb, "Pelvis",    (4.0, roll, 8.0))
        _rot_bone_world(pb, "Abdomen",   (6.0, 0.0, 0.0))
        _rot_bone_world(pb, "Head",      (-6.0, 0.0, 6.0))
        _rot_bone_world(pb, "Maw_Top",   (-6.0, 0.0, 0.0))
        _rot_bone_world(pb, "Maw_Bot",   ( 10.0, 0.0, 0.0))
        _rot_bone_world(pb, "Palp_L_01", (0.0, 0.0,  22.0))
        _rot_bone_world(pb, "Palp_R_01", (0.0, 0.0, -22.0))
        bpy.context.view_layer.update()
        # Phase A: curl all 6 legs up & aim Tail horizontally BEFORE snap so carapace drops flush to Z=0
        for lname, sx, y_bias in (
            ("Leg_FL", 1.0, -0.42), ("Leg_ML", 1.0, 0.05), ("Leg_BL", 1.0, 0.44),
            ("Leg_FR", -1.0, -0.42), ("Leg_MR", -1.0, 0.05), ("Leg_BR", -1.0, 0.44),
        ):
            _aim_creature_chain(arm_obj, (f"{lname}_Coxa", f"{lname}_Femur", f"{lname}_Tarsus"), (
                (0.84 * sx, y_bias * 0.45, 0.36),
                (-0.70 * sx, y_bias * 0.25, 0.60),
                (-0.56 * sx, y_bias * 0.15, curl_in),
            ))
        _aim_creature_chain(arm_obj, ("Tail_01", "Tail_02", "Tail_03", "Tail_04"), (
            (0.18, 0.94, 0.16), (0.20, 0.94, 0.14), (0.16, 0.95, 0.12), (0.10, 0.96, 0.10),
        ))
        # Phase B: seat inverted carapace on asphalt
        snap_creature_to_floor(arm_obj, body_obj, floor_z=0.0)
        # Phase C: drape tail gently onto asphalt without lifting carapace
        _drape_creature_chain_to_floor(
            arm_obj, ("Tail_01", "Tail_02", "Tail_03", "Tail_04"),
            ((0.18, 0.94), (0.20, 0.94), (0.16, 0.95), (0.10, 0.96)),
            (0.14, 0.11, 0.09, 0.08),
        )

    if stage == "scuttle":
        _clamp_creature_floor(arm_obj, body_obj, floor_z=0.0)
    else:
        snap_creature_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_bile_juggernaut_pose(arm_obj, body_obj, stage="idle", phase=0.0):
    """Apply slow ponderous tank poses (`idle`, `walk_stomp`, `roar`, `swipe*`, `slam_windup`, `seismic_slam`, `slam_rebound`, `death`)."""
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
        _set_pelvis_world_offset(pb, (0.015 * math.sin(tau - 0.45), 0.0, -0.095 - 0.024 * math.cos(2.0 * tau - 0.4)))
        _rot_bone_world(pb, "Pelvis",        (8.0,  1.2 * math.sin(tau - 0.45), -3.5 * math.cos(tau)))
        _rot_bone_world(pb, "Belly_Gut",     (7.0 + 2.5 * math.cos(2.0 * tau), -0.8 * math.sin(tau - 0.45), 2.5 * math.cos(tau - 0.25)))
        _rot_bone_world(pb, "Belly_Maw_Top", (-16.0 - 3.0 * math.cos(2.0 * tau), 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Maw_Bot", ( 18.0 + 3.0 * math.cos(2.0 * tau), 0.0, 0.0))
        _rot_bone_world(pb, "Spine_01",      (10.0, -0.8 * math.sin(tau - 0.45), 3.0 * math.cos(tau - 0.25)))
        _rot_bone_world(pb, "Spine_02",      (10.0, -0.4 * math.sin(tau - 0.65), 2.0 * math.cos(tau - 0.45)))
        _rot_bone_world(pb, "Head",          (-12.0, 0.0, -2.0 * math.sin(tau - 0.85)))
        _rot_bone_world(pb, "Jaw_L",         (18.0 + 4.0 * abs(br), 0.0,  16.0))
        _rot_bone_world(pb, "Jaw_R",         (18.0 + 4.0 * abs(br), 0.0, -16.0))
        # Contralateral heavy arms: phase 0 = Left leg front -> Right arm forward (-X), Left arm back (+X)
        arm_sw = math.cos(tau - 0.35)
        arm_fa = math.cos(tau - 0.75)
        _rot_bone_world(pb, "Arm_L_Upper",   (-14.0 + 26.0 * arm_sw, -10.0, -4.0))
        _rot_bone_world(pb, "Arm_L_Fore",    (-26.0 - 10.0 * arm_fa, 0.0, -12.0))
        _rot_bone_world(pb, "Arm_R_Upper",   (-14.0 - 26.0 * arm_sw,  10.0,  4.0))
        _rot_bone_world(pb, "Arm_R_Fore",    (-26.0 + 10.0 * arm_fa, 0.0,  12.0))

        bpy.context.view_layer.update()
        # Grounded 2-bone leg IK (duty=0.65, zero knee snap/hyperextension)
        for leg, sx, p_off in (("Leg_L", 1.0, 0.0), ("Leg_R", -1.0, 0.5)):
            str_n, lift_n, is_stance, u = _gait_foot_curve((phase + p_off) % 1.0, duty=0.65)
            p_ankle = Vector((0.260 * sx, 0.020 + 0.26 * str_n, 0.120 + 0.09 * lift_n))
            _solve_creature_2bone_ik(arm_obj, f"{leg}_Thigh", f"{leg}_Shin",
                                     p_ankle, pole_hint_arm=(0.18 * sx, -1.0, 0.05))
            if is_stance:
                if u < 0.16:
                    pitch_z = 0.032 * (1.0 - u / 0.16)
                elif u < 0.72:
                    pitch_z = 0.0
                else:
                    pitch_z = -0.028 * ((u - 0.72) / 0.28)
            else:
                pitch_z = -0.024 * (1.0 - u) + 0.026 * u
            _aim_creature_bone_world(arm_obj, f"{leg}_Foot", Vector((0.0, -0.080, -0.100 + pitch_z)))
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
    elif stage == "swipe_windup":
        _rot_bone_world(pb, "Pelvis",        (-4.0, 0.0, -24.0))
        _rot_bone_world(pb, "Spine_01",      (-4.0, 0.0, -18.0))
        _rot_bone_world(pb, "Spine_02",      (-4.0, 0.0, -16.0))
        _rot_bone_world(pb, "Head",          (6.0, 0.0, 26.0))
        _rot_bone_world(pb, "Arm_R_Shoulder",(6.0, 14.0, -26.0))
        _rot_bone_world(pb, "Arm_R_Upper",   (18.0, -28.0, -34.0))
        _rot_bone_world(pb, "Arm_R_Fore",    (-24.0, -10.0, -20.0))
        _rot_bone_world(pb, "Arm_L_Upper",   (-26.0, 12.0, 14.0))
    elif stage == "swipe":
        _rot_bone_world(pb, "Pelvis",        (12.0, 0.0, 26.0))
        _rot_bone_world(pb, "Spine_01",      (12.0, 0.0, 20.0))
        _rot_bone_world(pb, "Spine_02",      (12.0, 0.0, 18.0))
        _rot_bone_world(pb, "Head",          (-14.0, 0.0, -28.0))
        _rot_bone_world(pb, "Jaw_L",         (26.0, 0.0,  22.0))
        _rot_bone_world(pb, "Jaw_R",         (26.0, 0.0, -22.0))
        _rot_bone_world(pb, "Belly_Maw_Top", (-24.0, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Maw_Bot", ( 26.0, 0.0, 0.0))
        _rot_bone_world(pb, "Arm_R_Shoulder",(0.0, -16.0, 30.0))
        _rot_bone_world(pb, "Arm_R_Upper",   (-62.0, 20.0, 40.0))
        _rot_bone_world(pb, "Arm_R_Fore",    (-36.0, 10.0, 24.0))
        _rot_bone_world(pb, "Arm_L_Upper",   (-22.0, -18.0, -22.0))
    elif stage == "swipe_follow":
        _rot_bone_world(pb, "Pelvis",        (8.0, 0.0, 16.0))
        _rot_bone_world(pb, "Spine_01",      (8.0, 0.0, 12.0))
        _rot_bone_world(pb, "Head",          (-8.0, 0.0, -16.0))
        _rot_bone_world(pb, "Arm_R_Upper",   (-42.0, 26.0, 48.0))
        _rot_bone_world(pb, "Arm_R_Fore",    (-24.0, 8.0, 16.0))
    elif stage == "slam_windup":
        _rot_bone_world(pb, "Pelvis",        (-8.0, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Gut",     (-8.0, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Maw_Top", (-28.0, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Maw_Bot", ( 32.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_01",      (-10.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_02",      (-10.0, 0.0, 0.0))
        _rot_bone_world(pb, "Head",          (-18.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_L",         (30.0, 0.0,  28.0))
        _rot_bone_world(pb, "Jaw_R",         (30.0, 0.0, -28.0))
        _rot_bone_world(pb, "Arm_L_Shoulder",(10.0, 0.0, 12.0))
        _rot_bone_world(pb, "Arm_L_Upper",   (-148.0, -18.0, -14.0))
        _rot_bone_world(pb, "Arm_L_Fore",    (-18.0, 0.0, -12.0))
        _rot_bone_world(pb, "Arm_R_Shoulder",(10.0, 0.0, -12.0))
        _rot_bone_world(pb, "Arm_R_Upper",   (-148.0,  18.0,  14.0))
        _rot_bone_world(pb, "Arm_R_Fore",    (-18.0, 0.0,  12.0))
    elif stage == "seismic_slam":
        # Heavy forward smash slamming both boulder fists violently down at ground crater
        _rot_bone_world(pb, "Pelvis",        (22.0, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Gut",     (12.0, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Maw_Top", (-28.0, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Maw_Bot", ( 30.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_01",      (18.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_02",      (16.0, 0.0, 0.0))
        _rot_bone_world(pb, "Head",          (-20.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_L",         (30.0, 0.0,  28.0))
        _rot_bone_world(pb, "Jaw_R",         (30.0, 0.0, -28.0))
        _rot_bone_world(pb, "Tongue_01",     (18.0, 0.0, 0.0))
        _rot_bone_world(pb, "Leg_L_Thigh",   (-30.0, 0.0, 10.0))
        _rot_bone_world(pb, "Leg_L_Shin",    ( 34.0, 0.0, 0.0))
        _rot_bone_world(pb, "Leg_R_Thigh",   (-30.0, 0.0, -10.0))
        _rot_bone_world(pb, "Leg_R_Shin",    ( 34.0, 0.0, 0.0))
        _rot_bone_world(pb, "Arm_L_Upper",   (-54.0, -10.0, -18.0))
        _rot_bone_world(pb, "Arm_L_Fore",    (-24.0, 0.0, -10.0))
        _rot_bone_world(pb, "Arm_R_Upper",   (-56.0, 10.0, 18.0))
        _rot_bone_world(pb, "Arm_R_Fore",    (-24.0, 0.0, 10.0))
    elif stage == "slam_rebound":
        _rot_bone_world(pb, "Pelvis",        (12.0, 0.0, 4.0))
        _rot_bone_world(pb, "Spine_01",      (10.0, 0.0, -4.0))
        _rot_bone_world(pb, "Head",          (-12.0, 0.0, 6.0))
        _rot_bone_world(pb, "Arm_L_Upper",   (-32.0, -16.0, -12.0))
        _rot_bone_world(pb, "Arm_R_Upper",   (-32.0, 16.0, 12.0))
    elif stage == "death_stagger":
        _rot_bone_world(pb, "Pelvis",        (-6.0, -8.0, 10.0))
        _rot_bone_world(pb, "Belly_Gut",     (-4.0, -4.0, 4.0))
        _rot_bone_world(pb, "Belly_Maw_Top", (-26.0, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Maw_Bot", ( 28.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_01",      (-8.0, -4.0, 4.0))
        _rot_bone_world(pb, "Spine_02",      (-6.0, 0.0, 0.0))
        _rot_bone_world(pb, "Head",          (-16.0, -4.0, -10.0))
        _rot_bone_world(pb, "Jaw_L",         (28.0, 0.0,  26.0))
        _rot_bone_world(pb, "Jaw_R",         (28.0, 0.0, -26.0))
        _rot_bone_world(pb, "Arm_L_Upper",   (-28.0, -26.0, 16.0))
        _rot_bone_world(pb, "Arm_R_Upper",   (-28.0,  26.0, -16.0))
    elif stage == "death_kneel":
        _rot_bone_world(pb, "Pelvis",        (40.0, 10.0, -4.0))
        _rot_bone_world(pb, "Belly_Gut",     (8.0, 2.0, 0.0))
        _rot_bone_world(pb, "Spine_01",      (12.0, 4.0, 0.0))
        _rot_bone_world(pb, "Spine_02",      (8.0, 2.0, 0.0))
        _rot_bone_world(pb, "Head",          (-24.0, 12.0, 12.0))
        _rot_bone_world(pb, "Jaw_L",         (18.0, 0.0,  16.0))
        _rot_bone_world(pb, "Jaw_R",         (18.0, 0.0, -16.0))
        _rot_bone_world(pb, "Leg_L_Thigh",   (-42.0, 0.0, 10.0))
        _rot_bone_world(pb, "Leg_L_Shin",    ( 74.0, 0.0, 0.0))
        _rot_bone_world(pb, "Leg_R_Thigh",   (-42.0, 0.0, -10.0))
        _rot_bone_world(pb, "Leg_R_Shin",    ( 74.0, 0.0, 0.0))
        _rot_bone_world(pb, "Arm_L_Upper",   (-36.0, -34.0, -10.0))
        _rot_bone_world(pb, "Arm_R_Upper",   (-36.0,  34.0,  10.0))
    else:  # death / death_flat / death_settle
        z_off = 0.0 if stage == "death_settle" else 0.01
        pel_x = 73.0 if stage == "death_settle" else 71.0
        _rot_bone_world(pb, "Pelvis",        (pel_x, 6.0, -4.0))
        _rot_bone_world(pb, "Belly_Gut",     (4.0, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Maw_Top", (0.0, 0.0, 0.0))
        _rot_bone_world(pb, "Belly_Maw_Bot", (0.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_01",      (4.0, 0.0, 0.0))
        _rot_bone_world(pb, "Spine_02",      (4.0, 0.0, 0.0))
        _rot_bone_world(pb, "Head",          (-28.0, 16.0, 14.0))
        _rot_bone_world(pb, "Jaw_L",         (0.0, 0.0, 0.0))
        _rot_bone_world(pb, "Jaw_R",         (0.0, 0.0, 0.0))
        _rot_bone_world(pb, "Tongue_01",     (-42.0, 0.0, 0.0))
        _rot_bone_world(pb, "Tongue_02",     (-32.0, 0.0, 0.0))
        bpy.context.view_layer.update()
        # Phase A: orient limbs horizontally clear BEFORE floor snap so heavy belly rests flat at Z=0
        _aim_creature_chain(arm_obj, ("Leg_L_Thigh", "Leg_L_Shin", "Leg_L_Foot"), (
            (0.28, 0.96, 0.18), (0.18, 0.98, 0.16), (0.14, 0.98, 0.14),
        ))
        _aim_creature_chain(arm_obj, ("Leg_R_Thigh", "Leg_R_Shin", "Leg_R_Foot"), (
            (-0.30, 0.95, 0.18), (-0.22, 0.96, 0.16), (-0.16, 0.98, 0.14),
        ))
        _aim_creature_chain(arm_obj, ("Arm_L_Upper", "Arm_L_Fore", "Arm_L_Hand"), (
            (0.84, -0.52, 0.18), (0.64, -0.76, 0.16), (0.50, -0.86, 0.14),
        ))
        _aim_creature_chain(arm_obj, ("Arm_R_Upper", "Arm_R_Fore", "Arm_R_Hand"), (
            (-0.82, -0.54, 0.18), (-0.66, -0.74, 0.16), (-0.54, -0.84, 0.14),
        ))
        # Phase B: seat massive belly & hips directly onto asphalt
        snap_creature_to_floor(arm_obj, body_obj, floor_z=0.0)
        # Phase C: match thick limb flesh radius (0.19-0.24m) so fists/feet meet road flush with belly
        _drape_creature_chain_to_floor(
            arm_obj, ("Leg_L_Thigh", "Leg_L_Shin", "Leg_L_Foot"),
            ((0.28, 0.96), (0.18, 0.98), (0.14, 0.98)),
            (0.25 + z_off, 0.22 + z_off, 0.20),
        )
        _drape_creature_chain_to_floor(
            arm_obj, ("Leg_R_Thigh", "Leg_R_Shin", "Leg_R_Foot"),
            ((-0.30, 0.95), (-0.22, 0.96), (-0.16, 0.98)),
            (0.26 + z_off, 0.22 + z_off, 0.20),
        )
        _drape_creature_chain_to_floor(
            arm_obj, ("Arm_L_Upper", "Arm_L_Fore", "Arm_L_Hand"),
            ((0.84, -0.52), (0.64, -0.76), (0.50, -0.86)),
            (0.24 + z_off, 0.21 + z_off, 0.19),
        )
        _drape_creature_chain_to_floor(
            arm_obj, ("Arm_R_Upper", "Arm_R_Fore", "Arm_R_Hand"),
            ((-0.82, -0.54), (-0.66, -0.74), (-0.54, -0.84)),
            (0.25 + z_off, 0.22 + z_off, 0.20),
        )

    if stage == "walk_stomp":
        _clamp_creature_floor(arm_obj, body_obj, floor_z=0.0)
    else:
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


def _keyframe_creature_pose(arm_obj, frame, prev_quats=None):
    bpy.context.view_layer.update()
    for b in arm_obj.pose.bones:
        if not b.bone.use_deform:
            continue
        if b.rotation_mode != "QUATERNION":
            q = b.rotation_euler.to_quaternion()
            b.rotation_mode = "QUATERNION"
            b.rotation_quaternion = q
        if prev_quats is not None and b.name in prev_quats:
            if b.rotation_quaternion.dot(prev_quats[b.name]) < 0.0:
                b.rotation_quaternion.negate()
        if prev_quats is not None:
            prev_quats[b.name] = b.rotation_quaternion.copy()
        b.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        if b.name == "Pelvis":
            b.keyframe_insert(data_path="location", frame=frame)


CREATURE_ACTION_SPECS = {
    "rafflesia": (
        ("Idle_Sway",         "loop", "idle",        36, 1),
        ("Crawl_Stalk",       "loop", "stalk",       22, 1),
        ("Attack_Lunge_Bite", "seq",  [(1, "idle"), (7, "bite_windup"), (13, "lunge_bite"), (19, "bite_follow"), (26, "idle")], 0.0, None),
        ("Skill_Vine_Thrash", "seq",  [(1, "idle"), (8, "thrash_windup"), (15, "vine_thrash"), (23, "thrash_follow"), (32, "idle")], 0.25, None),
        ("Death_Wilt",        "seq",  [(1, "idle"), (8, "death_stagger"), (17, "death_kneel"), (28, "death_flat"), (38, "death_settle")], 0.0, None),
    ),
    "scythe_stalker": (
        ("Idle_Hunch",         "loop", "idle",        36, 1),
        ("Run_Limp_Stalk",     "loop", "stalk",       20, 1),
        ("Attack_Scythe_Clef", "seq",  [(1, "idle"), (6, "cleave_windup"), (11, "slash"), (17, "cleave_follow"), (24, "idle")], 0.0, None),
        ("Skill_Reaper_Lunge", "seq",  [(1, "idle"), (8, "lunge_windup"), (14, "reaper_lunge"), (22, "lunge_follow"), (30, "idle")], 0.0, None),
        ("Death_Collapse",     "seq",  [(1, "idle"), (7, "death_stagger"), (16, "death_kneel"), (27, "death_flat"), (36, "death_settle")], 0.0, None),
    ),
    "thorn_shroud": (
        ("Idle_Veil_Sway",    "loop", "idle",         36, 1),
        ("Glide_Stilt_Stalk", "loop", "stalk",        24, 1),
        ("Attack_Blade_Sweep","seq",  [(1, "idle"), (7, "sweep_windup"), (13, "sweep"), (20, "sweep_follow"), (27, "idle")], 0.0, None),
        ("Skill_Razor_Bloom", "seq",  [(1, "idle"), (8, "bloom_windup"), (15, "razor_bloom"), (23, "bloom_rebound"), (32, "idle")], 0.0, None),
        ("Death_Shatter",     "seq",  [(1, "idle"), (8, "death_stagger"), (17, "death_kneel"), (28, "death_flat"), (38, "death_settle")], 0.0, None),
    ),
    "arachnid_maw": (
        ("Idle_Acid_Throb",   "loop", "idle",         32, 1),
        ("Skitter_Scuttle",   "loop", "scuttle",      16, 1),
        ("Attack_Mandible",   "seq",  [(1, "idle"), (5, "bite_windup"), (10, "bite"), (16, "bite_follow"), (22, "idle")], 0.0, None),
        ("Skill_Acid_Pounce", "seq",  [(1, "idle"), (7, "pounce_windup"), (13, "acid_pounce"), (21, "pounce_follow"), (29, "idle")], 0.0, None),
        ("Death_Curl",        "seq",  [(1, "idle"), (7, "death_stagger"), (15, "death_kneel"), (26, "death_flat"), (36, "death_settle")], 0.0, None),
    ),
    "bile_juggernaut": (
        ("Idle_Lumber",           "loop", "idle",         40, 1),
        ("Walk_Stomp_Slow",       "loop", "walk_stomp",   32, 1),
        ("Attack_Crusher_Swipe",  "seq",  [(1, "idle"), (9, "swipe_windup"), (16, "swipe"), (24, "swipe_follow"), (34, "idle")], 0.0, None),
        ("Skill_Seismic_Bile_Slam","seq", [(1, "idle"), (10, "slam_windup"), (18, "seismic_slam"), (27, "slam_rebound"), (38, "idle")], 0.0, None),
        ("Death_Timber",          "seq",  [(1, "idle"), (9, "death_stagger"), (20, "death_kneel"), (33, "death_flat"), (44, "death_settle")], 0.0, None),
    ),
}


def _clamp_creature_action_floor(arm_obj, body_obj, act, floor_z=0.0):
    """Ensure every evaluated frame of a non-cyclic collapse stays >= `floor_z` without floor sink."""
    fr0, fr1 = int(round(act.frame_range[0])), int(round(act.frame_range[1]))
    pelvis = arm_obj.pose.bones.get("Pelvis")
    if pelvis is None:
        return
    m_inv = pelvis.bone.matrix_local.to_3x3().inverted()
    dg = bpy.context.evaluated_depsgraph_get()
    mat = body_obj.matrix_world
    adjusted = []
    for f in range(fr0, fr1 + 1):
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        ev = body_obj.evaluated_get(dg)
        me = ev.to_mesh()
        min_z = min((mat @ v.co).z for v in me.vertices)
        ev.to_mesh_clear()
        loc = pelvis.location.copy()
        if min_z < floor_z - 0.006:
            dz = (floor_z - min_z)
            loc = loc + (m_inv @ Vector((0.0, 0.0, dz)))
        adjusted.append((f, loc))

    for f, loc in adjusted:
        bpy.context.scene.frame_set(f)
        pelvis.location = loc
        pelvis.keyframe_insert(data_path="location", frame=f)


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
        prev_quats = {}
        if spec[1] == "loop":
            _, _, stg, steps, step_f = spec
            for idx in range(steps + 1):
                pose_fn(arm_obj, body_obj, stage=stg, phase=(idx % steps) / float(steps))
                _keyframe_creature_pose(arm_obj, 1 + idx * step_f, prev_quats=prev_quats)
        else:
            _, _, keys, ph, _ = spec
            for frame, stg in keys:
                pose_fn(arm_obj, body_obj, stage=stg, phase=ph)
                _keyframe_creature_pose(arm_obj, frame, prev_quats=prev_quats)
            if aname.startswith("Death_"):
                _clamp_creature_action_floor(arm_obj, body_obj, act, floor_z=0.0)

    arm_obj.animation_data.action = None
    reset_creature_pose(arm_obj.pose.bones)
    bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode="OBJECT")
