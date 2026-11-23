"""Mixamo-compatible humanoid rig, deterministic skinning, and canonical weapon hold()."""
import math
import bpy
from mathutils import Euler, Matrix, Vector

from body_parts import PROPORTIONS


# Maximum bone influences per vertex (standard across glTF / Three.js / Unity / Godot)
MAX_INFLUENCES = 4
MIN_WEIGHT = 0.02


def make_proportions(height=1.80, female=False, shoulder_scale=1.0):
    """Build a Mixamo-aligned proportion dict scaled cleanly to `height`."""
    s = height / 1.80
    sh_s = (0.78 if female else 1.0) * shoulder_scale
    hip_x = (0.104 if female else 0.103) * s

    def P3(x, y, z):
        return (x * s, y * s, z * s)

    def Arm3(x, y, z):
        return (x * s * sh_s, y * s, z * s)

    # Keep arm length proportional even when shoulder width narrows; dainty 0.92x hands on female
    arm_base = 0.185 * sh_s
    hf = 0.91 if female else 1.0
    def Reach(dx, y, z):
        return ((arm_base + dx) * s, y * s, z * s)

    def Hand(dx, y, z):
        lx = 0.530 + (dx - 0.530) * hf
        ly = 0.015 + (y - 0.015) * hf
        lz = 1.425 + (z - 1.425) * hf
        return ((arm_base + lx) * s, ly * s, lz * s)

    return {
        "height": height,
        "female": female,
        "scale": s,
        "shoulder_scale": sh_s,
        "hips": P3(0.0, 0.00, 0.94),
        "spine": P3(0.0, 0.005, 1.04),
        "spine1": P3(0.0, 0.010, 1.18),
        "spine2": P3(0.0, 0.012, 1.33),
        "neck": P3(0.0, 0.012, 1.48),
        "head": P3(0.0, 0.005, 1.565),
        "head_top": P3(0.0, 0.005, 1.80),
        "shoulder_in": Arm3(0.045, 0.012, 1.415),
        "arm": Arm3(0.185, 0.015, 1.425),
        "elbow": Reach(0.265, 0.022, 1.425),
        "wrist": Reach(0.530, 0.015, 1.425),
        "hand_end": Hand(0.614, 0.012, 1.425),
        "thumb": [
            Hand(0.546, -0.016, 1.419),  # CMC (inside thenar eminence)
            Hand(0.573, -0.036, 1.413),  # MCP (knuckle at palm edge)
            Hand(0.596, -0.047, 1.409),  # IP  (mid thumb joint)
            Hand(0.615, -0.051, 1.407),  # Tip
        ],
        "index": [
            Hand(0.610, -0.020, 1.426),
            Hand(0.638, -0.020, 1.424),
            Hand(0.662, -0.020, 1.421),
            Hand(0.684, -0.020, 1.418),
        ],
        "middle": [
            Hand(0.614, -0.003, 1.428),
            Hand(0.644, -0.003, 1.426),
            Hand(0.670, -0.003, 1.423),
            Hand(0.696, -0.003, 1.420),
        ],
        "ring": [
            Hand(0.612,  0.014, 1.426),
            Hand(0.640,  0.014, 1.424),
            Hand(0.665,  0.014, 1.421),
            Hand(0.688,  0.014, 1.418),
        ],
        "pinky": [
            Hand(0.606,  0.030, 1.423),
            Hand(0.629,  0.030, 1.421),
            Hand(0.649,  0.030, 1.418),
            Hand(0.668,  0.030, 1.415),
        ],
        "hip": (hip_x, 0.0, 0.91 * s),
        "knee": (hip_x, -0.006 * s, 0.50 * s),
        "ankle": (hip_x, 0.018 * s, 0.095 * s),
        "ball": (hip_x, -0.072 * s, 0.028 * s),
        "toe": (hip_x, -0.148 * s, 0.025 * s),
    }


def _bone_specs(proportions=None):
    """Return Mixamo bone hierarchy: list of (name, head, tail, parent, roll_axis)."""
    P = proportions if proportions is not None else PROPORTIONS
    V = Vector
    fwd = V((0.0, -1.0, 0.0))
    up = V((0.0, 0.0, 1.0))

    specs = [
        ("mixamorig:Hips",        V(P["hips"]),     V(P["spine"]),    None,               fwd),
        ("mixamorig:Spine",       V(P["spine"]),    V(P["spine1"]),   "mixamorig:Hips",   fwd),
        ("mixamorig:Spine1",      V(P["spine1"]),   V(P["spine2"]),   "mixamorig:Spine",  fwd),
        ("mixamorig:Spine2",      V(P["spine2"]),   V(P["neck"]),     "mixamorig:Spine1", fwd),
        ("mixamorig:Neck",        V(P["neck"]),     V(P["head"]),     "mixamorig:Spine2", fwd),
        ("mixamorig:Head",        V(P["head"]),     V(P["head_top"]), "mixamorig:Neck",   fwd),
        ("mixamorig:HeadTop_End", V(P["head_top"]), V(P["head_top"]) + V((0, 0, 0.06)), "mixamorig:Head", fwd),
    ]

    for side_name, sx in (("Left", 1.0), ("Right", -1.0)):
        def M(pt):
            return V((sx * pt[0], pt[1], pt[2]))

        # Shoulder, Arm, ForeArm, ForeArmTwist (sibling leaf), Hand
        elbow_mid = (V(P["elbow"]) + V(P["wrist"])) * 0.5
        specs.extend([
            (f"mixamorig:{side_name}Shoulder",     M(P["shoulder_in"]), M(P["arm"]),      "mixamorig:Spine2",              up),
            (f"mixamorig:{side_name}Arm",          M(P["arm"]),         M(P["elbow"]),    f"mixamorig:{side_name}Shoulder", up),
            (f"mixamorig:{side_name}ForeArm",      M(P["elbow"]),       M(P["wrist"]),    f"mixamorig:{side_name}Arm",      up),
            (f"mixamorig:{side_name}ForeArmTwist", M(elbow_mid),        M(P["wrist"]),    f"mixamorig:{side_name}ForeArm",  up),
            (f"mixamorig:{side_name}Hand",         M(P["wrist"]),       M(P["hand_end"]), f"mixamorig:{side_name}ForeArm",  up),
        ])

        # 5 Individual Fingers (Thumb, Index, Middle, Ring, Pinky)
        for fname in ("thumb", "index", "middle", "ring", "pinky"):
            mname = fname.capitalize()
            pts = P[fname]
            for seg in range(3):
                parent = (
                    f"mixamorig:{side_name}Hand"
                    if seg == 0
                    else f"mixamorig:{side_name}Hand{mname}{seg}"
                )
                specs.append((
                    f"mixamorig:{side_name}Hand{mname}{seg + 1}",
                    M(pts[seg]),
                    M(pts[seg + 1]),
                    parent,
                    up,
                ))

        # Legs (UpLeg, Leg, Foot, ToeBase)
        specs.extend([
            (f"mixamorig:{side_name}UpLeg",   M(P["hip"]),   M(P["knee"]),  "mixamorig:Hips",              fwd),
            (f"mixamorig:{side_name}Leg",     M(P["knee"]),  M(P["ankle"]), f"mixamorig:{side_name}UpLeg",   fwd),
            (f"mixamorig:{side_name}Foot",    M(P["ankle"]), M(P["ball"]),  f"mixamorig:{side_name}Leg",     up),
            (f"mixamorig:{side_name}ToeBase", M(P["ball"]),  M(P["toe"]),   f"mixamorig:{side_name}Foot",    up),
        ])

    return specs


def create_mixamo_armature(collection=None, proportions=None):
    """Create and return the Mixamo-named Armature object."""
    arm_data = bpy.data.armatures.new("Mixamo_Armature")
    arm_obj = bpy.data.objects.new("Armature", arm_data)
    if collection is None:
        bpy.context.scene.collection.objects.link(arm_obj)
    else:
        collection.objects.link(arm_obj)

    arm_data.display_type = "OCTAHEDRAL"
    arm_obj.show_in_front = True

    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones

    specs = _bone_specs(proportions=proportions)
    for name, head, tail, _, _ in specs:
        b = eb.new(name)
        b.head = head
        b.tail = tail

    bc_def = arm_data.collections.get("Deform") or arm_data.collections.new("Deform")
    for name, _, _, parent, roll_axis in specs:
        b = eb[name]
        b.use_deform = True
        bc_def.assign(b)
        if parent:
            b.parent = eb[parent]
            b.use_connect = (eb[parent].tail - b.head).length < 1e-4
        b.align_roll(roll_axis)

    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_obj, specs


def _point_seg_dist(p, a, b):
    """Shortest distance from point p to line segment a-b."""
    ab = b - a
    len_sq = ab.length_squared
    if len_sq < 1e-10:
        return (p - a).length
    t = max(0.0, min(1.0, (p - a).dot(ab) / len_sq))
    proj = a + t * ab
    return (p - proj).length


def _region_bone_map():
    """Map each body region tag to its allowed bone names and effective radii."""
    # Rigid parts use a single bone with weight 1.0
    rigid = {
        "head":         "mixamorig:Head",
        "hips_rigid":   "mixamorig:Hips",
        "thigh_rigid_L": "mixamorig:LeftUpLeg",
        "thigh_rigid_R": "mixamorig:RightUpLeg",
        "shin_rigid_L":  "mixamorig:LeftLeg",
        "shin_rigid_R":  "mixamorig:RightLeg",
    }

    # Soft/deforming parts: list of (bone_name, radius_for_falloff)
    soft = {
        "neck": [
            ("mixamorig:Spine2", 0.065),
            ("mixamorig:Neck",   0.048),
            ("mixamorig:Head",   0.055),
        ],
        "torso": [
            ("mixamorig:Hips",          0.095),
            ("mixamorig:Spine",         0.095),
            ("mixamorig:Spine1",        0.105),
            ("mixamorig:Spine2",        0.110),
            ("mixamorig:LeftShoulder",  0.046),
            ("mixamorig:RightShoulder", 0.046),
            ("mixamorig:Neck",          0.045),
        ],
        "hips_soft": [
            ("mixamorig:Hips",       0.100),
            ("mixamorig:LeftUpLeg",  0.062),
            ("mixamorig:RightUpLeg", 0.062),
        ],
        "arm_L": [
            ("mixamorig:Spine2",           0.058),
            ("mixamorig:LeftShoulder",     0.048),
            ("mixamorig:LeftArm",          0.048),
            ("mixamorig:LeftForeArm",      0.044),
            ("mixamorig:LeftForeArmTwist", 0.036),
            ("mixamorig:LeftHand",         0.024),
        ],
        "arm_R": [
            ("mixamorig:Spine2",            0.058),
            ("mixamorig:RightShoulder",     0.048),
            ("mixamorig:RightArm",          0.048),
            ("mixamorig:RightForeArm",      0.044),
            ("mixamorig:RightForeArmTwist", 0.036),
            ("mixamorig:RightHand",         0.024),
        ],
        "hand_L": [
            ("mixamorig:LeftForeArmTwist", 0.024),
            ("mixamorig:LeftHand",         0.045),
        ],
        "hand_R": [
            ("mixamorig:RightForeArmTwist", 0.024),
            ("mixamorig:RightHand",         0.045),
        ],
        "leg_L": [
            ("mixamorig:Hips",      0.075),
            ("mixamorig:LeftUpLeg", 0.068),
            ("mixamorig:LeftLeg",   0.066),
            ("mixamorig:LeftFoot",  0.040),
        ],
        "leg_R": [
            ("mixamorig:Hips",       0.075),
            ("mixamorig:RightUpLeg", 0.068),
            ("mixamorig:RightLeg",   0.066),
            ("mixamorig:RightFoot",  0.040),
        ],
        "boot_shaft_L": [
            ("mixamorig:LeftLeg",  0.058),
            ("mixamorig:LeftFoot", 0.055),
        ],
        "boot_shaft_R": [
            ("mixamorig:RightLeg",  0.058),
            ("mixamorig:RightFoot", 0.055),
        ],
        "foot_L": [
            ("mixamorig:LeftFoot",    0.060),
            ("mixamorig:LeftToeBase", 0.048),
        ],
        "foot_R": [
            ("mixamorig:RightFoot",    0.060),
            ("mixamorig:RightToeBase", 0.048),
        ],
    }

    # Continuous soft chain weighting for all 5 individual fingers (no adjacent-digit bleed)
    finger_defs = (
        ("thumb",  "Thumb"),
        ("index",  "Index"),
        ("middle", "Middle"),
        ("ring",   "Ring"),
        ("pinky",  "Pinky"),
    )
    for side_key, side_name in (("L", "Left"), ("R", "Right")):
        for fname, mname in finger_defs:
            soft[f"{fname}_{side_key}"] = [
                (f"mixamorig:{side_name}Hand",          0.012),
                (f"mixamorig:{side_name}Hand{mname}1", 0.011),
                (f"mixamorig:{side_name}Hand{mname}2", 0.010),
                (f"mixamorig:{side_name}Hand{mname}3", 0.009),
            ]
            # Keep backward compatibility if per-segment tags exist
            for seg in (1, 2, 3):
                soft[f"{fname}_{side_key}_{seg}"] = soft[f"{fname}_{side_key}"]

    return rigid, soft


def skin_body_to_armature(body_obj, arm_obj, specs, region_indices):
    """Assign deterministic, normalized vertex weights and bind body_obj to arm_obj."""
    bone_segs = {name: (head, tail) for name, head, tail, _, _ in specs}
    vgroups = {}
    for name, _, _, _, _ in specs:
        vgroups[name] = body_obj.vertex_groups.new(name=name)

    rigid_map, soft_map = _region_bone_map()

    # Invert region_indices -> per-vertex region list (a vertex belongs to one part)
    vert_to_region = {}
    for rname, indices in region_indices.items():
        for idx in indices:
            vert_to_region[idx] = rname

    for v in body_obj.data.vertices:
        rname = vert_to_region.get(v.index)
        if rname in rigid_map:
            vgroups[rigid_map[rname]].add([v.index], 1.0, "REPLACE")
            continue

        candidates = soft_map.get(rname)
        if not candidates:
            # Fallback to nearest spine/hips bone
            candidates = [("mixamorig:Hips", 0.08), ("mixamorig:Spine1", 0.08)]

        scores = []
        for bname, radius in candidates:
            h, t = bone_segs[bname]
            d = _point_seg_dist(v.co, h, t) / radius
            w = 1.0 / (max(d, 0.015) ** 4)
            scores.append((bname, w))

        # Keep top MAX_INFLUENCES and prune tiny weights
        scores.sort(key=lambda x: x[1], reverse=True)
        scores = scores[:MAX_INFLUENCES]
        total = sum(w for _, w in scores)
        kept = [(b, w / total) for b, w in scores if (w / total) >= MIN_WEIGHT]
        if not kept:
            kept = [(scores[0][0], 1.0)]
        norm = sum(w for _, w in kept)
        for bname, w in kept:
            vgroups[bname].add([v.index], w / norm, "REPLACE")

    body_obj.parent = arm_obj
    mod = body_obj.modifiers.new(name="Armature", type="ARMATURE")
    mod.object = arm_obj
    mod.use_vertex_groups = True


def attach_gear_to_bone(gear_obj, arm_obj, bone_name):
    """Attach a separate detachable gear mesh 100% to a single Mixamo bone.

    Using a single-bone vertex group + ARMATURE modifier keeps each gear piece
    as an independent, easily toggleable/swappable mesh object while ensuring
    zero transform drift across Blender, glTF (.glb), Three.js, Unity, and Godot.
    """
    vg = gear_obj.vertex_groups.new(name=bone_name)
    all_idx = [v.index for v in gear_obj.data.vertices]
    vg.add(all_idx, 1.0, "REPLACE")

    gear_obj.parent = arm_obj
    mod = gear_obj.modifiers.new(name="Armature", type="ARMATURE")
    mod.object = arm_obj
    mod.use_vertex_groups = True


def create_weapon_sockets(arm_obj, proportions, collection):
    """Add canonical bone-parented Empty weapon sockets (`WeaponSocket_R` / `WeaponSocket_L`) + metadata."""
    s = proportions.get("scale", 1.0)
    wx, wy, wz = proportions["wrist"]
    grip_r = (-wx - 0.044 * s, wy - 0.004 * s, wz - 0.022 * s)
    grip_l = ( wx + 0.044 * s, wy - 0.004 * s, wz - 0.022 * s)
    nock_offset = 0.115 * s
    arrow_grip_r = (grip_r[0] - nock_offset, grip_r[1], grip_r[2])

    bpy.context.view_layer.update()
    sockets = []
    for sock_name, bone_name, grip_pos, hold_mat in (
        ("WeaponSocket_R", "mixamorig:RightHand", grip_r, HOLD_MAT_RIGHT),
        ("WeaponSocket_L", "mixamorig:LeftHand",  grip_l, HOLD_MAT_LEFT),
    ):
        sock = bpy.data.objects.new(sock_name, None)
        sock.empty_display_type = "ARROWS"
        sock.empty_display_size = 0.06 * s
        collection.objects.link(sock)

        b_pose = arm_obj.pose.bones[bone_name]
        b_tail_mat = arm_obj.matrix_world @ b_pose.matrix @ Matrix.Translation((0.0, b_pose.length, 0.0))
        sock.parent = arm_obj
        sock.parent_type = "BONE"
        sock.parent_bone = bone_name
        sock.matrix_parent_inverse = b_tail_mat.inverted()
        sock.matrix_basis = Matrix.Translation(Vector(grip_pos)) @ hold_mat
        sockets.append(sock)

    arm_obj["right_grip_rest"] = grip_r
    arm_obj["left_grip_rest"] = grip_l
    arm_obj["arrow_grip_rest"] = arrow_grip_r
    arm_obj["arrow_nock_offset"] = nock_offset
    return tuple(sockets)


# Anatomical weapon rest orientations in T-pose hands (canonical +Z=muzzle, +Y=top, +X=weapon left)
HOLD_MAT_RIGHT = Matrix((
    ( 0.0,  0.0, -1.0),
    ( 0.0, -1.0,  0.0),
    (-1.0,  0.0,  0.0),
)).to_4x4()

HOLD_MAT_LEFT = Matrix((
    ( 0.0,  0.0,  1.0),
    ( 0.0, -1.0,  0.0),
    ( 1.0,  0.0,  0.0),
)).to_4x4()


def hold(weapon_obj, arm_obj, bone_name="mixamorig:RightHand",
         grip_world=(0.0, 0.0, 0.0), base_rot=(math.pi * 0.5, 0.0, 0.0),
         extra_rot=(0.0, 0.0, 0.0), hand=None):
    """Place a canonical weapon (grip=0, muzzle=+Z, top=+Y) into a character bone via hold().

    When `hand` is 'Right' or 'Left', uses anatomical palm-crease alignment (`HOLD_MAT_RIGHT` /
    `HOLD_MAT_LEFT`). Otherwise uses `base_rot` (default Rx(+90 deg) for legacy holsters/tests).
    """
    if hand == "Right":
        m_base = HOLD_MAT_RIGHT
    elif hand == "Left":
        m_base = HOLD_MAT_LEFT
    else:
        m_base = Euler(base_rot, "XYZ").to_matrix().to_4x4()
    m_extra = Euler(extra_rot, "XYZ").to_matrix().to_4x4()
    m_tr = Matrix.Translation(Vector(grip_world))
    xform = m_tr @ m_extra @ m_base

    me = weapon_obj.data
    for v in me.vertices:
        v.co = xform @ v.co
    me.update()
    attach_gear_to_bone(weapon_obj, arm_obj, bone_name)
    return xform
