"""Deep humanoid & zombie rig mechanics: 5-finger micro-grips, clavicle auto-follow,
forearm twist, gun-first dual-arm IK, grounded foot-roll Leg IK, upper/lower split strafe,
tactical reload, crouch ADS, melee/hit react, zombie shamble/lunge/bite, and 14 Action bakes.
"""
import math
import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

from rig_controls import set_live_ik
from rig_mixamo import HOLD_MAT_LEFT, HOLD_MAT_RIGHT
from weapons import WEAPON_META


# ---------------------------------------------------------------------------
# Low-level bone transform helpers
# ---------------------------------------------------------------------------
def reset_pose(pb):
    """Reset all pose bones to clean rest transform (XYZ Euler 0)."""
    for b in pb:
        b.location = Vector((0.0, 0.0, 0.0))
        b.rotation_mode = "XYZ"
        b.rotation_euler = Euler((0.0, 0.0, 0.0), "XYZ")
        b.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))


def _rot_bone(pb, name, deg_xyz):
    b = pb.get(name)
    if b is None:
        return
    b.rotation_mode = "XYZ"
    b.rotation_euler = Euler(tuple(math.radians(a) for a in deg_xyz), "XYZ")


def _add_rot_bone(pb, name, deg_xyz):
    """Add additive XYZ Euler degrees onto a bone's existing rotation."""
    b = pb.get(name)
    if b is None:
        return
    if b.rotation_mode != "XYZ":
        cur_eul = b.rotation_quaternion.to_euler("XYZ")
        b.rotation_mode = "XYZ"
    else:
        cur_eul = b.rotation_euler.copy()
    add_q = Euler(tuple(math.radians(a) for a in deg_xyz), "XYZ").to_quaternion()
    b.rotation_euler = (cur_eul.to_quaternion() @ add_q).to_euler("XYZ")


def _bone_world_axes_matrix(desired_y, desired_z, roll_axis="Z"):
    """Build orthonormal 3x3 world rotation matrix where column 1 = desired_y."""
    y = desired_y.normalized()
    if roll_axis == "X":
        x = desired_z - y * desired_z.dot(y)
        if x.length < 1e-6:
            fb = Vector((1, 0, 0)) if abs(y.x) < 0.9 else Vector((0, 1, 0))
            x = fb - y * fb.dot(y)
        x.normalize()
        z = x.cross(y).normalized()
    else:
        z = desired_z - y * desired_z.dot(y)
        if z.length < 1e-6:
            fb = Vector((0, 0, 1)) if abs(y.z) < 0.9 else Vector((0, 1, 0))
            z = fb - y * fb.dot(y)
        z.normalize()
        x = y.cross(z).normalized()
        z = x.cross(y).normalized()
    return Matrix((x, y, z)).transposed()


def _set_bone_world_matrix(arm_obj, pb_bone, R_target_world):
    """Set pose bone local quaternion so its world 3x3 orientation equals `R_target_world`."""
    rest_m = pb_bone.bone.matrix_local.to_3x3()
    if pb_bone.parent is not None:
        par_world = (arm_obj.matrix_world @ pb_bone.parent.matrix).to_3x3()
        par_rest_inv = pb_bone.parent.bone.matrix_local.to_3x3().inverted()
        parent_base = par_world @ (par_rest_inv @ rest_m)
    else:
        parent_base = arm_obj.matrix_world.to_3x3() @ rest_m

    R_local = parent_base.inverted() @ R_target_world
    pb_bone.rotation_mode = "QUATERNION"
    pb_bone.rotation_quaternion = R_local.to_quaternion()


def _set_bone_world_y_axis(arm_obj, pb_bone, desired_y, desired_up):
    _set_bone_world_matrix(arm_obj, pb_bone, _bone_world_axes_matrix(desired_y, desired_up, roll_axis="Z"))


def _swing_twist_y(q):
    """Decompose quaternion q into (swing, twist_angle_rad) around local +Y axis."""
    t = Quaternion((q.w, 0.0, q.y, 0.0))
    if t.magnitude < 1e-6:
        return q, 0.0
    t.normalize()
    angle = 2.0 * math.atan2(t.y, t.w)
    if angle > math.pi:
        angle -= 2.0 * math.pi
    elif angle < -math.pi:
        angle += 2.0 * math.pi
    return q @ t.inverted(), angle


# ---------------------------------------------------------------------------
# Individual 5-Finger Micro-Grip Library (9 Tactical & Monster Presets)
# ---------------------------------------------------------------------------
HAND_PRESETS = {
    "trigger_on": {
        "idx":   (-28, -46, -26),
        "mid":   (-74, -82, -62),
        "ring":  (-78, -86, -64),
        "pinky": (-82, -88, -66),
        "th1": (-18, 22, 26), "th2": (-16, 0, 12), "th3": (-14, 0, 0),
    },
    "trigger_off": {
        "idx":   (-6,  -8,  -4),
        "mid":   (-76, -84, -62),
        "ring":  (-80, -86, -64),
        "pinky": (-82, -88, -66),
        "th1": (-18, 22, 26), "th2": (-16, 0, 12), "th3": (-14, 0, 0),
    },
    "support_under": {
        "idx":   (-38, -46, -30),
        "mid":   (-44, -52, -34),
        "ring":  (-50, -56, -38),
        "pinky": (-56, -60, -40),
        "th1": (-10, 12, 18), "th2": (-8, 0, 8), "th3": (-6, 0, 0),
    },
    "support_c_clamp": {
        "idx":   (-52, -58, -38),
        "mid":   (-58, -64, -42),
        "ring":  (-64, -70, -46),
        "pinky": (-68, -74, -50),
        "th1": (-28, 16, 10), "th2": (-12, 0, 6), "th3": (-6, 0, 0),
    },
    "mag_pinch": {
        "idx":   (-38, -44, -22),
        "mid":   (-44, -50, -26),
        "ring":  (-64, -72, -50),
        "pinky": (-72, -78, -56),
        "th1": (-16, 18, 30), "th2": (-22, 0, 14), "th3": (-14, 0, 0),
    },
    "pistol_support": {
        "idx":   (-56, -66, -44),
        "mid":   (-64, -72, -50),
        "ring":  (-68, -76, -54),
        "pinky": (-72, -78, -56),
        "th1": (-4, 8, 14), "th2": (-6, 0, 6), "th3": (-4, 0, 0),
    },
    "fist": {
        "idx":   (-68, -80, -60),
        "mid":   (-72, -84, -64),
        "ring":  (-76, -86, -66),
        "pinky": (-78, -88, -68),
        "th1": (-24, 24, 28), "th2": (-20, 0, 14), "th3": (-16, 0, 0),
    },
    "relaxed": {
        "idx":   (-14, -18, -12),
        "mid":   (-20, -24, -16),
        "ring":  (-28, -32, -20),
        "pinky": (-36, -40, -26),
        "th1": (-8, 8, 12), "th2": (-6, 0, 6), "th3": (-4, 0, 0),
    },
    "claw": {
        "idx":   (-10, -54, -48),
        "mid":   (-12, -58, -50),
        "ring":  (-16, -60, -52),
        "pinky": (-20, -62, -54),
        "th1": (10, -14, -10), "th2": (-28, 0, 6), "th3": (-24, 0, 0),
    },
    "bow_hold": {
        "idx":   (-42, -52, -34),
        "mid":   (-48, -58, -38),
        "ring":  (-54, -64, -42),
        "pinky": (-58, -68, -46),
        "th1": (-14, 16, 18), "th2": (-10, 0, 8), "th3": (-6, 0, 0),
    },
    "bow_draw": {
        "idx":   (-14, -76, -68),
        "mid":   (-16, -80, -70),
        "ring":  (-18, -76, -66),
        "pinky": (-62, -74, -56),
        "th1": (-18, 16, 10), "th2": (-12, 0, 6), "th3": (-8, 0, 0),
    },
}
HAND_PRESETS["trigger"] = HAND_PRESETS["trigger_on"]


def pose_hand_grip(pb, side="Right", mode="relaxed"):
    """Drive all 5 individual fingers (`Thumb`, `Index`, `Middle`, `Ring`, `Pinky`) cleanly."""
    sx = 1.0 if side == "Left" else -1.0
    p = HAND_PRESETS.get(mode, HAND_PRESETS["relaxed"])
    digit_map = (("Index", "idx"), ("Middle", "mid"), ("Ring", "ring"), ("Pinky", "pinky"))
    for seg in (1, 2, 3):
        for mname, key in digit_map:
            _rot_bone(pb, f"mixamorig:{side}Hand{mname}{seg}", (p[key][seg - 1], 0.0, 0.0))
    _rot_bone(pb, f"mixamorig:{side}HandThumb1", (p["th1"][0], sx * p["th1"][1], sx * p["th1"][2]))
    _rot_bone(pb, f"mixamorig:{side}HandThumb2", (p["th2"][0], sx * p["th2"][1], sx * p["th2"][2]))
    _rot_bone(pb, f"mixamorig:{side}HandThumb3", (p["th3"][0], sx * p["th3"][1], sx * p["th3"][2]))


# ---------------------------------------------------------------------------
# Clavicle Auto-Follow + 2-Bone Limb IK + Forearm Twist
# ---------------------------------------------------------------------------
def _apply_clavicle_follow(arm_obj, side, target_world):
    """Apply subtle anatomical Shoulder elevation & forward protraction toward `target_world`."""
    pb = arm_obj.pose.bones
    b_sh = pb.get(f"mixamorig:{side}Shoulder")
    if b_sh is None:
        return
    sx = 1.0 if side == "Left" else -1.0
    sh_pos = (arm_obj.matrix_world @ b_sh.matrix).to_translation()
    delta = (Vector(target_world) - sh_pos)
    if delta.length < 1e-4:
        return
    dn = delta.normalized()
    # Elevation (+X on both Shoulder bones raises outer clavicle) & forward protraction (-Z Left / +Z Right)
    elev = max(-10.0, min(16.0, dn.z * 16.0))
    protract = max(-8.0, min(14.0, -dn.y * 12.0))
    _rot_bone(pb, f"mixamorig:{side}Shoulder", (elev, 0.0, sx * (-protract)))
    bpy.context.view_layer.update()


def _solve_two_bone_limb_ik(arm_obj, upper_name, lower_name, end_name, target_world, pole_world,
                            upper_up_hint, lower_up_hint):
    """Analytically solve a 2-bone IK chain (arm or leg) without duplicating math."""
    bpy.context.view_layer.update()
    pb = arm_obj.pose.bones
    b_up = pb[upper_name]
    b_lo = pb[lower_name]
    b_end = pb[end_name]

    A = (arm_obj.matrix_world @ b_up.matrix).to_translation()
    L1 = b_up.bone.length
    L2 = b_lo.bone.length

    T = Vector(target_world) - A
    d = min(L1 + L2 - 2e-4, max(abs(L1 - L2) + 2e-4, T.length))
    u_T = T.normalized() if T.length > 1e-6 else Vector((0.0, 0.0, -1.0))

    pole_vec = Vector(pole_world) - A
    u_pole = pole_vec - u_T * pole_vec.dot(u_T)
    if u_pole.length < 1e-5:
        u_pole = Vector((0.0, -1.0, 0.0))
    u_pole.normalize()

    cos_a = max(-1.0, min(1.0, (L1 * L1 + d * d - L2 * L2) / (2.0 * L1 * d)))
    sin_a = math.sqrt(max(0.0, 1.0 - cos_a * cos_a))
    J = A + (u_T * cos_a + u_pole * sin_a) * L1

    y1 = (J - A).normalized()
    y2 = (Vector(target_world) - J).normalized()

    _set_bone_world_y_axis(arm_obj, b_up, y1, upper_up_hint)
    bpy.context.view_layer.update()
    _set_bone_world_y_axis(arm_obj, b_lo, y2, lower_up_hint)
    bpy.context.view_layer.update()
    return b_up, b_lo, b_end, y1, y2


def _distribute_forearm_twist(arm_obj, side, target_hand_R_world):
    """Lock Hand orientation to `target_hand_R_world` & blend 55% longitudinal Y-twist onto ForeArmTwist."""
    bpy.context.view_layer.update()
    pb = arm_obj.pose.bones
    b_hand = pb[f"mixamorig:{side}Hand"]
    b_twist = pb.get(f"mixamorig:{side}ForeArmTwist")

    _set_bone_world_matrix(arm_obj, b_hand, target_hand_R_world)
    bpy.context.view_layer.update()

    if b_twist is not None:
        _, twist_rad = _swing_twist_y(b_hand.rotation_quaternion)
        max_tw = math.radians(135.0)
        twist_clamped = max(-max_tw, min(max_tw, twist_rad))
        b_twist.rotation_mode = "XYZ"
        b_twist.rotation_euler = Euler((0.0, 0.55 * twist_clamped, 0.0), "XYZ")
        bpy.context.view_layer.update()


def solve_two_bone_arm_ik(arm_obj, side, target_world, pole_world, target_hand_R_world=None, clavicle=True):
    """Solve Clavicle->Arm->ForeArm IK and orient Hand + smooth ForeArmTwist."""
    if clavicle:
        _apply_clavicle_follow(arm_obj, side, target_world)
    up_hint = Vector((0.0, 0.0, 1.0))
    _, _, _, y1, y2 = _solve_two_bone_limb_ik(
        arm_obj,
        f"mixamorig:{side}Arm",
        f"mixamorig:{side}ForeArm",
        f"mixamorig:{side}Hand",
        target_world,
        pole_world,
        up_hint,
        up_hint,
    )
    if target_hand_R_world is None:
        bend_normal = y1.cross(y2)
        hand_up = Vector((0.0, 0.0, 1.0))
        if side == "Left" and bend_normal.length > 1e-4:
            hand_up = (Vector((0.0, 0.0, 1.0)) + (-bend_normal.normalized()) * 0.45).normalized()
        target_hand_R_world = _bone_world_axes_matrix(y2, hand_up, roll_axis="Z")

    _distribute_forearm_twist(arm_obj, side, target_hand_R_world)


def solve_two_bone_leg_ik(arm_obj, side, ankle_world, knee_pole_world, foot_pitch_deg=0.0,
                          toe_bend_deg=0.0, foot_yaw_deg=0.0):
    """Solve UpLeg->Leg IK to `ankle_world` + world-aligned foot roll (`foot_pitch_deg`, `toe_bend_deg`)."""
    fwd_hint = Vector((0.0, -1.0, 0.0))
    _solve_two_bone_limb_ik(
        arm_obj,
        f"mixamorig:{side}UpLeg",
        f"mixamorig:{side}Leg",
        f"mixamorig:{side}Foot",
        ankle_world,
        knee_pole_world,
        fwd_hint,
        fwd_hint,
    )
    pb = arm_obj.pose.bones
    b_foot = pb[f"mixamorig:{side}Foot"]
    rot_f = Euler((math.radians(foot_pitch_deg), 0.0, math.radians(foot_yaw_deg)), "XYZ").to_matrix()
    foot_fwd = rot_f @ Vector((0.0, -1.0, 0.0))
    foot_up = rot_f @ Vector((0.0, 0.0, 1.0))
    ball_local_y = (0.8 * foot_fwd - 0.6 * foot_up).normalized()
    ball_local_z = (0.6 * foot_fwd + 0.8 * foot_up).normalized()
    _set_bone_world_matrix(arm_obj, b_foot, _bone_world_axes_matrix(ball_local_y, ball_local_z, roll_axis="Z"))
    _rot_bone(pb, f"mixamorig:{side}ToeBase", (toe_bend_deg, 0.0, 0.0))
    bpy.context.view_layer.update()


def _solve_grounded_leg(arm_obj, side, stride_y=0.0, lift_z=0.0, foot_pitch_deg=0.0,
                        toe_bend_deg=0.0, lat_x_off=0.0, foot_yaw_deg=0.0):
    """Place ankle from hip rest X + stride offsets and solve Grounded Foot-Roll IK."""
    pb = arm_obj.pose.bones
    b_hip = pb[f"mixamorig:{side}UpLeg"]
    b_foot = pb[f"mixamorig:{side}Foot"]
    hip_x = b_hip.bone.head_local.x
    ankle_z = b_foot.bone.head_local.z
    # Compensate ankle height when rolling onto heel or ball
    roll_lift = 0.025 * max(0.0, abs(math.sin(math.radians(foot_pitch_deg))))
    ankle_target = Vector((hip_x + lat_x_off, stride_y, ankle_z + lift_z + roll_lift))
    # Knee pole biased straight forward in world (or rotated with foot_yaw_deg)
    pole_dir = Euler((0.0, 0.0, math.radians(foot_yaw_deg)), "XYZ").to_matrix() @ Vector((0.0, -0.55, 0.42))
    knee_pole = Vector((hip_x + lat_x_off, stride_y, ankle_z)) + pole_dir
    solve_two_bone_leg_ik(arm_obj, side, ankle_target, knee_pole,
                          foot_pitch_deg=foot_pitch_deg, toe_bend_deg=toe_bend_deg, foot_yaw_deg=foot_yaw_deg)


# ---------------------------------------------------------------------------
# Gun-First Dual-Arm IK (`ik_hand_gun` workflow) + Reload Choreography
# ---------------------------------------------------------------------------
def _make_rifle_world_matrix(arm_obj, weapon_id, mode="aim", recoil_pitch_deg=0.0,
                             kick_m=0.0, cant_deg=0.0):
    """Compute shoulder-pocket or canted weapon world matrix for rifles/shotguns/SMGs/LMGs."""
    pb = arm_obj.pose.bones
    sh_r = (arm_obj.matrix_world @ pb["mixamorig:RightArm"].matrix).to_translation()
    head_p = (arm_obj.matrix_world @ pb["mixamorig:Head"].matrix).to_translation()
    aw = arm_obj.matrix_world.to_3x3()

    if mode == "ready":
        grip_w = sh_r + aw @ Vector((-0.055, -0.265, -0.155))
        eul = Euler((math.radians(-24.0), math.radians(-10.0), math.radians(28.0)), "XYZ")
    elif mode == "reload":
        # Canted inward/upward near chest so magwell & ejection port face LeftHand cleanly
        grip_w = sh_r + aw @ Vector((-0.030, -0.265, -0.075))
        eul = Euler((math.radians(-14.0), math.radians(cant_deg), math.radians(26.0)), "XYZ")
    else:
        z_eye = head_p.z - 0.075
        x_pocket = sh_r.x + 0.072
        grip_w = Vector((x_pocket, sh_r.y - 0.285 + kick_m, z_eye - 0.028 + 0.014 * (recoil_pitch_deg / 8.5)))
        eul = Euler((math.radians(recoil_pitch_deg), math.radians(-4.0 + cant_deg), math.radians(3.0)), "XYZ")

    m_base = Euler((math.pi * 0.5, 0.0, 0.0), "XYZ").to_matrix()
    M = (eul.to_matrix() @ m_base).to_4x4()
    M.translation = grip_w
    return arm_obj.matrix_world @ M if arm_obj.matrix_world != Matrix.Identity(4) else M


def _make_pistol_world_matrix(arm_obj, recoil_pitch_deg=0.0, kick_m=0.0, cant_deg=0.0):
    """Compute two-handed combat pistol ADS world transform."""
    pb = arm_obj.pose.bones
    sh_r = (arm_obj.matrix_world @ pb["mixamorig:RightArm"].matrix).to_translation()
    head_p = (arm_obj.matrix_world @ pb["mixamorig:Head"].matrix).to_translation()
    grip_w = Vector((0.025, sh_r.y - 0.455 + kick_m, head_p.z - 0.115 + 0.012 * (recoil_pitch_deg / 8.5)))
    eul = Euler((math.radians(recoil_pitch_deg), math.radians(cant_deg), math.radians(2.0)), "XYZ")
    m_base = Euler((math.pi * 0.5, 0.0, 0.0), "XYZ").to_matrix()
    M = (eul.to_matrix() @ m_base).to_4x4()
    M.translation = grip_w
    return M


def _compute_hand_target_for_weapon(arm_obj, right_grip_rest, weapon_world_mat):
    b_rhand = arm_obj.pose.bones["mixamorig:RightHand"]
    M_hand_rest = arm_obj.matrix_world @ b_rhand.bone.matrix_local
    M_wep_rest = arm_obj.matrix_world @ Matrix.Translation(Vector(right_grip_rest)) @ HOLD_MAT_RIGHT
    M_wep_in_hand = M_hand_rest.inverted() @ M_wep_rest
    return weapon_world_mat @ M_wep_in_hand.inverted()


def solve_gun_first_weapon_ik(arm_obj, weapon_id, right_grip_rest, weapon_world_mat,
                              style="aim", trigger_discipline=False, support_grip=None):
    """Place weapon first at `weapon_world_mat`, then solve BOTH arms via Clavicle+IK+ForeArmTwist."""
    bpy.context.view_layer.update()
    pb = arm_obj.pose.bones
    M_rhand_target = _compute_hand_target_for_weapon(arm_obj, right_grip_rest, weapon_world_mat)

    sh_r = (arm_obj.matrix_world @ pb["mixamorig:RightArm"].matrix).to_translation()
    pole_R = sh_r + Vector((-0.26, 0.18, -0.45))

    solve_two_bone_arm_ik(arm_obj, "Right", M_rhand_target.to_translation(), pole_R,
                          target_hand_R_world=M_rhand_target.to_3x3())
    pose_hand_grip(pb, "Right", "trigger_off" if trigger_discipline else "trigger_on")

    meta = WEAPON_META.get(weapon_id, {"hold_type": "rifle", "foregrip": (0.0, 0.02, 0.24)})
    htype = meta["hold_type"]

    if htype == "rifle":
        fg_world = weapon_world_mat @ Vector(meta["foregrip"])
        R_w = weapon_world_mat.to_3x3()
        w_left = R_w @ Vector((1.0, 0.0, 0.0))
        w_up = R_w @ Vector((0.0, 1.0, 0.0))
        w_fwd = R_w @ Vector((0.0, 0.0, 1.0))

        lh_y = (0.48 * w_fwd - 0.84 * w_left + 0.24 * w_up).normalized()
        lh_palm_up = (0.88 * w_up + 0.46 * w_left).normalized()
        R_lhand = _bone_world_axes_matrix(lh_y, -lh_palm_up, roll_axis="Z")

        wrist_l_target = fg_world - lh_y * 0.044 - w_up * 0.024 + w_left * 0.008
        sh_l = (arm_obj.matrix_world @ pb["mixamorig:LeftArm"].matrix).to_translation()
        pole_L = sh_l + Vector((0.22, 0.16, -0.58))

        solve_two_bone_arm_ik(arm_obj, "Left", wrist_l_target, pole_L, target_hand_R_world=R_lhand)
        pose_hand_grip(pb, "Left", support_grip or "support_under")

    elif htype == "pistol":
        rh_pos = M_rhand_target.to_translation()
        w_fwd = weapon_world_mat.to_3x3() @ Vector((0.0, 0.0, 1.0))
        w_up = weapon_world_mat.to_3x3() @ Vector((0.0, 1.0, 0.0))
        w_right = weapon_world_mat.to_3x3() @ Vector((-1.0, 0.0, 0.0))

        lh_y = (0.68 * w_fwd + 0.72 * w_right - 0.12 * w_up).normalized()
        lh_z_dorsal = (0.28 * w_up - 0.94 * w_right).normalized()
        R_lhand = _bone_world_axes_matrix(lh_y, lh_z_dorsal, roll_axis="Z")

        wrist_l_target = rh_pos - w_right * 0.028 - w_fwd * 0.015 - w_up * 0.014
        sh_l = (arm_obj.matrix_world @ pb["mixamorig:LeftArm"].matrix).to_translation()
        pole_L = sh_l + Vector((0.28, 0.14, -0.52))
        solve_two_bone_arm_ik(arm_obj, "Left", wrist_l_target, pole_L, target_hand_R_world=R_lhand)
        pose_hand_grip(pb, "Left", "pistol_support")


# ---------------------------------------------------------------------------
# Anatomical Head Look-At (38% Neck + 62% Head + 14% Spine2 follow)
# ---------------------------------------------------------------------------
def apply_head_look_at(pb, yaw_deg=0.0, pitch_deg=0.0, roll_deg=0.0, torso_follow=True):
    """Additive anatomical head turn (clamped ±70° yaw, ±35° pitch)."""
    yaw = max(-70.0, min(70.0, yaw_deg))
    pitch = max(-35.0, min(35.0, pitch_deg))
    roll = max(-25.0, min(25.0, roll_deg))

    if torso_follow and abs(yaw) > 15.0:
        sp_yaw = 0.14 * yaw
        _add_rot_bone(pb, "mixamorig:Spine2", (0.0, sp_yaw, 0.0))
        rem_yaw = yaw - sp_yaw
    else:
        rem_yaw = yaw

    _add_rot_bone(pb, "mixamorig:Neck", (pitch * 0.38, rem_yaw * 0.38, roll * 0.35))
    _add_rot_bone(pb, "mixamorig:Head", (pitch * 0.62, rem_yaw * 0.62, roll * 0.65))


# ---------------------------------------------------------------------------
# Floor Snap
# ---------------------------------------------------------------------------
def snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0):
    """Shift Hips Z so the lowest evaluated vertex of `body_obj` touches `floor_z`."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    eval_obj = body_obj.evaluated_get(dg)
    me = eval_obj.to_mesh()
    mat = body_obj.matrix_world
    min_z = min((mat @ v.co).z for v in me.vertices)
    eval_obj.to_mesh_clear()

    hips = arm_obj.pose.bones["mixamorig:Hips"]
    hips.location = Vector((hips.location.x, hips.location.y, hips.location.z + (floor_z - min_z)))
    bpy.context.view_layer.update()


# ---------------------------------------------------------------------------
# Pose Library (Combat, Locomotion, Reload, Crouch, Strafe, Melee, Hit, Zombie)
# ---------------------------------------------------------------------------
def _apply_combat_lower_body(pb, stance="bladed"):
    if stance == "bladed":
        pb["mixamorig:Hips"].location = Vector((0.0, 0.0, -0.045))
        _rot_bone(pb, "mixamorig:Hips",   (4, -14, 0))
        _rot_bone(pb, "mixamorig:Spine",  (4, 5, 0))
        _rot_bone(pb, "mixamorig:Spine1", (4, 5, 0))
        _rot_bone(pb, "mixamorig:Spine2", (4, 6, 0))

        _rot_bone(pb, "mixamorig:LeftUpLeg",    (22, 6, 4))
        _rot_bone(pb, "mixamorig:LeftLeg",      (-28, 0, 0))
        _rot_bone(pb, "mixamorig:LeftFoot",     (8, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg",   (-14, -8, -4))
        _rot_bone(pb, "mixamorig:RightLeg",     (-18, 0, 0))
        _rot_bone(pb, "mixamorig:RightFoot",    (14, 0, 0))
        _rot_bone(pb, "mixamorig:RightToeBase", (18, 0, 0))
    else:
        pb["mixamorig:Hips"].location = Vector((0.0, 0.0, -0.025))
        _rot_bone(pb, "mixamorig:Hips",   (3, -10, 0))
        _rot_bone(pb, "mixamorig:Spine",  (3, 4, 0))
        _rot_bone(pb, "mixamorig:Spine1", (2, 4, 0))
        _rot_bone(pb, "mixamorig:Spine2", (2, 4, 0))

        _rot_bone(pb, "mixamorig:LeftUpLeg",    (14, 4, 3))
        _rot_bone(pb, "mixamorig:LeftLeg",      (-18, 0, 0))
        _rot_bone(pb, "mixamorig:LeftFoot",     (5, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg",   (-10, -6, -3))
        _rot_bone(pb, "mixamorig:RightLeg",     (-14, 0, 0))
        _rot_bone(pb, "mixamorig:RightFoot",    (10, 0, 0))
        _rot_bone(pb, "mixamorig:RightToeBase", (12, 0, 0))


def apply_bow_draw_pose(arm_obj, body_obj, right_grip_rest=None, draw_factor=1.0, release_follow=False):
    """Authentic right-handed bladed archery draw: extended Left bow arm + high-elbow cheek anchor."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)

    s = max(0.70, pb["mixamorig:Head"].bone.head_local.z / 1.565)

    # Right-handed archery stance: negative Y yaw puts Left shoulder forward (-Y) & Right shoulder back (+Y)
    pb["mixamorig:Hips"].location = Vector((0.0, 0.0, -0.035))
    _rot_bone(pb, "mixamorig:Hips",   (2.0, -38.0, 0.0))
    _rot_bone(pb, "mixamorig:Spine",  (2.0,  -6.0, 0.0))
    _rot_bone(pb, "mixamorig:Spine1", (1.5,  -6.0, 0.0))
    _rot_bone(pb, "mixamorig:Spine2", (1.5,  -8.0, 0.0))
    _rot_bone(pb, "mixamorig:Neck",   (-1.0, 22.0, 0.0))
    _rot_bone(pb, "mixamorig:Head",   (-2.0, 34.0, 2.0))
    bpy.context.view_layer.update()

    _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.16, lift_z=0.0, lat_x_off=0.02,  foot_yaw_deg=-48.0)
    _solve_grounded_leg(arm_obj, "Right", stride_y=0.18,  lift_z=0.0, lat_x_off=-0.04, foot_yaw_deg=-58.0)

    # Left bow arm: athletic extended reach forward along -Y holding vertical compound bow riser
    b_larm = pb["mixamorig:LeftArm"].bone
    b_lfa = pb["mixamorig:LeftForeArm"].bone
    b_lhand = pb["mixamorig:LeftHand"]
    L_arm_L = (b_lfa.head_local - b_larm.head_local).length + (b_lhand.bone.head_local - b_lfa.head_local).length

    aim_z = 0.035 if draw_factor >= 0.85 else -0.08
    aim_dir = Vector((-0.05, -0.998, aim_z)).normalized()
    sh_l = (arm_obj.matrix_world @ pb["mixamorig:LeftArm"].matrix).to_translation()
    bow_grip_w = sh_l + aim_dir * (0.91 * L_arm_L) + Vector((0.0, 0.0, 0.025 * s))

    bow_x = Vector((0.0, 0.0, 1.0)).cross(aim_dir).normalized()
    bow_y = aim_dir.cross(bow_x).normalized()
    M_bow_w = Matrix((bow_x, bow_y, aim_dir)).transposed().to_4x4()
    M_bow_w.translation = bow_grip_w

    left_grip_rest = tuple(arm_obj["left_grip_rest"]) if "left_grip_rest" in arm_obj else tuple(b_lhand.bone.head_local)
    M_lh_rest = arm_obj.matrix_world @ b_lhand.bone.matrix_local
    M_bow_rest = arm_obj.matrix_world @ Matrix.Translation(Vector(left_grip_rest)) @ HOLD_MAT_LEFT
    M_lh_target = M_bow_w @ (M_lh_rest.inverted() @ M_bow_rest).inverted()

    solve_two_bone_arm_ik(
        arm_obj, "Left", M_lh_target.to_translation(),
        sh_l + Vector((0.40, 0.06, -0.16)),
        target_hand_R_world=M_lh_target.to_3x3(), clavicle=True,
    )
    pose_hand_grip(pb, "Left", "bow_hold")

    # Right drawing arm: gently retract scapula back + high rear elbow anchoring arrow nock by cheek/jaw
    _rot_bone(pb, "mixamorig:RightShoulder", (4.0, 0.0, -10.0))
    bpy.context.view_layer.update()

    sh_r = (arm_obj.matrix_world @ pb["mixamorig:RightArm"].matrix).to_translation()
    head_p = (arm_obj.matrix_world @ pb["mixamorig:Head"].matrix).to_translation()
    rest_w = M_bow_w @ Vector((0.018, 0.042, 0.025))

    nock_full = head_p + Vector((-0.088 * s, -0.135 * s, -0.025 * s))
    nock_ready = rest_w - aim_dir * (0.34 * s) + Vector((0.0, 0.0, -0.02 * s))
    if release_follow:
        nock_w = nock_full + Vector((-0.035 * s, 0.085 * s, 0.010 * s))
    else:
        nock_w = nock_ready.lerp(nock_full, max(0.0, min(1.0, draw_factor)))

    arr_dir = (rest_w - nock_w).normalized()
    arr_x = Vector((0.0, 0.0, 1.0)).cross(arr_dir).normalized()
    arr_y = arr_dir.cross(arr_x).normalized()
    b_rhand = pb["mixamorig:RightHand"]
    nock_off = float(arm_obj.get("arrow_nock_offset", 0.115 * s))
    M_arr_w = Matrix((arr_x, arr_y, arr_dir)).transposed().to_4x4()
    M_arr_w.translation = nock_w + arr_dir * nock_off

    if "arrow_grip_rest" in arm_obj:
        rg = tuple(arm_obj["arrow_grip_rest"])
    elif right_grip_rest is not None:
        rg = (right_grip_rest[0] - nock_off, right_grip_rest[1], right_grip_rest[2])
    elif "right_grip_rest" in arm_obj:
        r0 = tuple(arm_obj["right_grip_rest"])
        rg = (r0[0] - nock_off, r0[1], r0[2])
    else:
        rg = tuple(b_rhand.bone.head_local)
    M_rh_rest = arm_obj.matrix_world @ b_rhand.bone.matrix_local
    M_arr_rest = arm_obj.matrix_world @ Matrix.Translation(Vector(rg)) @ HOLD_MAT_RIGHT
    M_rh_target = M_arr_w @ (M_rh_rest.inverted() @ M_arr_rest).inverted()

    pole_R = sh_r + Vector((-0.42, 0.45, 0.22))
    solve_two_bone_arm_ik(
        arm_obj, "Right", M_rh_target.to_translation(), pole_R,
        target_hand_R_world=M_rh_target.to_3x3(), clavicle=False,
    )
    pose_hand_grip(pb, "Right", "relaxed" if release_follow else "bow_draw")

    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_aim_ads_pose(arm_obj, body_obj, weapon_id=None, right_grip_rest=None,
                       recoil_pitch_deg=0.0, kick_m=0.0, mode="aim", trigger_discipline=False):
    """Shouldered ADS / Shoot Recoil / Two-handed Pistol pose using Gun-First Dual-Arm IK."""
    if weapon_id and WEAPON_META.get(weapon_id, {}).get("hold_type") == "arrow":
        apply_bow_draw_pose(arm_obj, body_obj, right_grip_rest=right_grip_rest,
                            draw_factor=1.0, release_follow=(kick_m > 0.015))
        return

    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)

    _apply_combat_lower_body(pb, stance="bladed")
    _rot_bone(pb, "mixamorig:Spine2", (6.0 - recoil_pitch_deg * 0.45, 6.0, 2.0))
    _rot_bone(pb, "mixamorig:Neck",   (-4.0 - recoil_pitch_deg * 0.25, -2.0, 4.0))
    _rot_bone(pb, "mixamorig:Head",   (-4.0 - recoil_pitch_deg * 0.25, -4.0, 5.0))
    bpy.context.view_layer.update()

    if weapon_id and right_grip_rest is not None:
        htype = WEAPON_META.get(weapon_id, {}).get("hold_type", "rifle")
        if htype == "pistol":
            M_wep = _make_pistol_world_matrix(arm_obj, recoil_pitch_deg=recoil_pitch_deg, kick_m=kick_m)
        else:
            M_wep = _make_rifle_world_matrix(arm_obj, weapon_id, mode=mode,
                                             recoil_pitch_deg=recoil_pitch_deg, kick_m=kick_m)
        solve_gun_first_weapon_ik(arm_obj, weapon_id, right_grip_rest, M_wep, style=mode,
                                  trigger_discipline=trigger_discipline)

    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_reload_pose(arm_obj, body_obj, stage="mag_pinch", weapon_id=None, right_grip_rest=None):
    """5-stage Tactical Reload choreography: cant -> mag_pinch -> pouch_reach -> mag_insert -> bolt_slap."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)

    _apply_combat_lower_body(pb, stance="bladed")
    _rot_bone(pb, "mixamorig:Spine2", (8.0, 10.0, 3.0))
    _rot_bone(pb, "mixamorig:Neck",   (6.0, -4.0, 2.0))
    _rot_bone(pb, "mixamorig:Head",   (8.0, -6.0, 4.0))
    bpy.context.view_layer.update()

    if not (weapon_id and right_grip_rest is not None):
        snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)
        return

    htype = WEAPON_META.get(weapon_id, {}).get("hold_type", "rifle")
    if htype == "pistol":
        M_wep = _make_pistol_world_matrix(arm_obj, recoil_pitch_deg=12.0, cant_deg=34.0)
    else:
        M_wep = _make_rifle_world_matrix(arm_obj, weapon_id, mode="reload", cant_deg=36.0)

    # 1. Right hand keeps canted control with strict trigger_off discipline
    M_rh = _compute_hand_target_for_weapon(arm_obj, right_grip_rest, M_wep)
    sh_r = (arm_obj.matrix_world @ pb["mixamorig:RightArm"].matrix).to_translation()
    solve_two_bone_arm_ik(arm_obj, "Right", M_rh.to_translation(),
                          sh_r + Vector((-0.24, 0.22, -0.42)), target_hand_R_world=M_rh.to_3x3())
    pose_hand_grip(pb, "Right", "trigger_off")

    # 2. Support arm targets magazine well, chest mag pouch, or bolt release
    sh_l = (arm_obj.matrix_world @ pb["mixamorig:LeftArm"].matrix).to_translation()
    R_w = M_wep.to_3x3()
    w_fwd = R_w @ Vector((0.0, 0.0, 1.0))
    w_up = R_w @ Vector((0.0, 1.0, 0.0))
    w_left = R_w @ Vector((1.0, 0.0, 0.0))

    if stage == "cant":
        fg_w = M_wep @ Vector(WEAPON_META.get(weapon_id, {}).get("foregrip", (0.0, 0.02, 0.24)))
        lh_y = (0.45 * w_fwd - 0.85 * w_left + 0.25 * w_up).normalized()
        R_lh = _bone_world_axes_matrix(lh_y, -(0.85 * w_up + 0.50 * w_left).normalized(), "Z")
        solve_two_bone_arm_ik(arm_obj, "Left", fg_w - lh_y * 0.045 - w_up * 0.024,
                              sh_l + Vector((0.24, 0.18, -0.52)), target_hand_R_world=R_lh)
        pose_hand_grip(pb, "Left", "support_under")

    elif stage in ("mag_pinch", "mag_insert"):
        # Wrap palm around bottom-side of curved magazine cleanly outside mag body
        mag_local = Vector((0.036, -0.118 if htype == "rifle" else -0.065, 0.072 if htype == "rifle" else 0.015))
        if stage == "mag_pinch":
            mag_local.y -= 0.024
        mag_w = M_wep @ mag_local
        lh_y = (-0.72 * w_left - 0.52 * w_fwd + 0.35 * w_up).normalized()
        R_lh = _bone_world_axes_matrix(lh_y, -(0.82 * w_up + 0.50 * w_left).normalized(), "Z")
        solve_two_bone_arm_ik(arm_obj, "Left", mag_w - lh_y * 0.058,
                              sh_l + Vector((0.26, 0.14, -0.58)), target_hand_R_world=R_lh)
        pose_hand_grip(pb, "Left", "mag_pinch")

    elif stage == "pouch_reach":
        # Left chest/belly magazine pouch grab
        pouch_w = (arm_obj.matrix_world @ pb["mixamorig:Spine1"].matrix).to_translation() + Vector((0.08, -0.18, -0.05))
        R_lh = _bone_world_axes_matrix(Vector((-0.85, -0.25, 0.45)).normalized(),
                                       Vector((0.0, -0.7, 0.7)).normalized(), "Z")
        solve_two_bone_arm_ik(arm_obj, "Left", pouch_w, sh_l + Vector((0.36, 0.25, -0.35)),
                              target_hand_R_world=R_lh)
        pose_hand_grip(pb, "Left", "mag_pinch")

    elif stage == "bolt_slap":
        bolt_w = M_wep @ Vector((0.032, 0.048, 0.055))
        lh_y = (-0.75 * w_left + 0.55 * w_fwd - 0.25 * w_up).normalized()
        R_lh = _bone_world_axes_matrix(lh_y, (0.35 * w_up + 0.88 * w_left).normalized(), "Z")
        solve_two_bone_arm_ik(arm_obj, "Left", bolt_w - lh_y * 0.035,
                              sh_l + Vector((0.28, 0.20, -0.45)), target_hand_R_world=R_lh)
        pose_hand_grip(pb, "Left", "relaxed")

    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_crouch_aim_pose(arm_obj, body_obj, weapon_id=None, right_grip_rest=None):
    """Low kneeling tactical firing stance with grounded Foot-Roll IK & shouldered ADS."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)

    pb["mixamorig:Hips"].location = Vector((0.0, 0.0, -0.34))
    _rot_bone(pb, "mixamorig:Hips",   (12, -16, 0))
    _rot_bone(pb, "mixamorig:Spine",  (4, 6, 0))
    _rot_bone(pb, "mixamorig:Spine1", (4, 6, 0))
    _rot_bone(pb, "mixamorig:Spine2", (4, 6, 0))
    _rot_bone(pb, "mixamorig:Neck",   (-10, -2, 3))
    _rot_bone(pb, "mixamorig:Head",   (-10, -4, 4))
    bpy.context.view_layer.update()

    # Front Left boot flat on ground; Back Right knee dropped low with toes propped on ground
    _solve_grounded_leg(arm_obj, "Left", stride_y=-0.32, lift_z=0.0,
                        foot_pitch_deg=0.0, toe_bend_deg=0.0, lat_x_off=0.02, foot_yaw_deg=6.0)
    _solve_grounded_leg(arm_obj, "Right", stride_y=0.30, lift_z=0.04,
                        foot_pitch_deg=-36.0, toe_bend_deg=40.0, lat_x_off=-0.02, foot_yaw_deg=-10.0)

    if weapon_id and right_grip_rest is not None:
        htype = WEAPON_META.get(weapon_id, {}).get("hold_type", "rifle")
        M_wep = _make_pistol_world_matrix(arm_obj) if htype == "pistol" else _make_rifle_world_matrix(arm_obj, weapon_id, mode="aim")
        solve_gun_first_weapon_ik(arm_obj, weapon_id, right_grip_rest, M_wep, style="aim")

    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_walk_pose(arm_obj, body_obj, phase=0.0, weapon_id=None, right_grip_rest=None):
    """Grounded Walk Cycle (`phase` in [0, 1)) via Foot-Roll Leg IK + Pelvis Bob/Yaw + Counter-Rotation."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)

    ang = 2.0 * math.pi * phase
    bob = -0.028 * math.cos(2.0 * ang) - 0.028
    lat_x = 0.028 * math.sin(ang)
    pelv_yaw = -11.0 * math.cos(ang)
    pelv_roll = 4.5 * math.sin(ang)

    pb["mixamorig:Hips"].location = Vector((lat_x, 0.0, bob))
    _rot_bone(pb, "mixamorig:Hips",   (5.0, pelv_yaw, pelv_roll))
    _rot_bone(pb, "mixamorig:Spine",  (2.5, -pelv_yaw * 0.48, -pelv_roll * 0.4))
    _rot_bone(pb, "mixamorig:Spine1", (2.5, -pelv_yaw * 0.48, -pelv_roll * 0.35))
    _rot_bone(pb, "mixamorig:Spine2", (2.5, -pelv_yaw * 0.48, -pelv_roll * 0.25))
    _rot_bone(pb, "mixamorig:Neck",   (-2.5, -pelv_yaw * 0.15, 0.0))
    _rot_bone(pb, "mixamorig:Head",   (-3.5,  pelv_yaw * 0.25, 0.0))
    bpy.context.view_layer.update()

    # Grounded Leg IK foot trajectory per side (energetic athletic stride)
    for side, p_off in (("Right", 0.0), ("Left", 0.5)):
        ph = (phase + p_off) % 1.0
        a = 2.0 * math.pi * ph
        stride_y = -0.32 * math.cos(a)  # -Y forward contact -> +Y rear push-off
        lift_z = 0.095 * max(0.0, -math.sin(a - 0.25)) ** 1.25
        if ph < 0.14:
            foot_pitch, toe_bend = 24.0 * (1.0 - ph / 0.14), -5.0
        elif ph < 0.40:
            foot_pitch, toe_bend = 0.0, 0.0
        elif ph < 0.58:
            t_p = (ph - 0.40) / 0.18
            foot_pitch, toe_bend = -26.0 * math.sin(t_p * math.pi * 0.8), 32.0 * math.sin(t_p * math.pi * 0.8)
        else:
            foot_pitch, toe_bend = -12.0 + 28.0 * ((ph - 0.58) / 0.42), 10.0
        _solve_grounded_leg(arm_obj, side, stride_y=stride_y, lift_z=lift_z,
                            foot_pitch_deg=foot_pitch, toe_bend_deg=toe_bend)

    if weapon_id == "melee":
        # Natural melee carry: left arm swings counterbalanced, right weapon arm held clear at low combat ready
        sw_l = 28.0 * math.cos(ang)
        sw_r = 16.0 * math.cos(ang + math.pi)
        _rot_bone(pb, "mixamorig:LeftArm",      (-70.0, 0.0, -sw_l))
        _rot_bone(pb, "mixamorig:LeftForeArm",  (0.0, 0.0, -(20.0 + 18.0 * max(0.0, math.cos(ang)))))
        pose_hand_grip(pb, "Left", "relaxed")

        _rot_bone(pb, "mixamorig:RightShoulder", (0.0, -3.0, -4.0))
        _rot_bone(pb, "mixamorig:RightArm",      (-48.0, -14.0, 32.0 + sw_r * 0.6))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0.0, 0.0, 56.0 + 10.0 * math.sin(ang)))
        _rot_bone(pb, "mixamorig:RightHand",     (0.0, 22.0, 6.0))
        pose_hand_grip(pb, "Right", "fist")
    elif weapon_id and right_grip_rest is not None and WEAPON_META.get(weapon_id, {}).get("hold_type") == "rifle":
        M_wep = _make_rifle_world_matrix(arm_obj, weapon_id, mode="ready",
                                         recoil_pitch_deg=2.2 * math.sin(2.0 * ang),
                                         cant_deg=3.0 * math.sin(ang))
        solve_gun_first_weapon_ik(arm_obj, weapon_id, right_grip_rest, M_wep, style="ready", trigger_discipline=True)
    else:
        for side, sx, p_off in (("Left", 1.0, 0.0), ("Right", -1.0, 0.5)):
            a = 2.0 * math.pi * ((phase + p_off) % 1.0)
            swing = 28.0 * math.cos(a)
            elb_bend = 18.0 + 16.0 * max(0.0, math.cos(a))
            _rot_bone(pb, f"mixamorig:{side}Arm",     (-72.0, 0.0, sx * (-swing)))
            _rot_bone(pb, f"mixamorig:{side}ForeArm", (0.0, 0.0, sx * (-elb_bend)))
            pose_hand_grip(pb, side, "relaxed")

    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_run_pose(arm_obj, body_obj, phase=0.0, weapon_id=None, right_grip_rest=None):
    """Dynamic Run Cycle (`phase` in [0, 1)) with forward lean, high knee drive, pumping arms & flight."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)

    ang = 2.0 * math.pi * phase
    flight_lift = 0.052 * math.sin(2.0 * ang - 0.7) - 0.072
    pelv_yaw = -15.0 * math.cos(ang)

    pb["mixamorig:Hips"].location = Vector((0.022 * math.sin(ang), 0.0, flight_lift))
    _rot_bone(pb, "mixamorig:Hips",   (15.0, pelv_yaw, 5.5 * math.sin(ang)))
    _rot_bone(pb, "mixamorig:Spine",  (6.0, -pelv_yaw * 0.48, 0.0))
    _rot_bone(pb, "mixamorig:Spine1", (6.0, -pelv_yaw * 0.48, 0.0))
    _rot_bone(pb, "mixamorig:Spine2", (5.0, -pelv_yaw * 0.48, 0.0))
    _rot_bone(pb, "mixamorig:Neck",   (-12.0, 0.0, 0.0))
    _rot_bone(pb, "mixamorig:Head",   (-14.0, pelv_yaw * 0.25, 0.0))

    for side, p_off in (("Right", 0.0), ("Left", 0.5)):
        ph = (phase + p_off) % 1.0
        a = 2.0 * math.pi * ph
        hip_x = 52.0 * math.cos(a) + 10.0
        knee_flex = -(24.0 + 70.0 * (0.5 - 0.5 * math.sin(a + 0.55)))
        if ph < 0.25:
            foot_x, toe_x = 12.0 - 28.0 * (ph / 0.25), 14.0
        elif ph < 0.45:
            foot_x, toe_x = -32.0, 36.0
        else:
            foot_x, toe_x = -16.0 + 28.0 * ((ph - 0.45) / 0.55), 8.0

        _rot_bone(pb, f"mixamorig:{side}UpLeg",   (hip_x, 0.0, 0.0))
        _rot_bone(pb, f"mixamorig:{side}Leg",     (knee_flex, 0.0, 0.0))
        _rot_bone(pb, f"mixamorig:{side}Foot",    (foot_x, 0.0, 0.0))
        _rot_bone(pb, f"mixamorig:{side}ToeBase", (toe_x, 0.0, 0.0))

    bpy.context.view_layer.update()
    if weapon_id == "melee":
        # Battle sprint: left arm pumps aggressively, right weapon arm carried out/back clear of torso
        sw_l = 48.0 * math.cos(ang)
        elb_l = 84.0 + 20.0 * max(0.0, math.cos(ang))
        _rot_bone(pb, "mixamorig:LeftArm",     (-66.0, 12.0, -sw_l - 8.0))
        _rot_bone(pb, "mixamorig:LeftForeArm", (0.0, 0.0, -elb_l))
        pose_hand_grip(pb, "Left", "fist")

        sw_r = 22.0 * math.cos(ang + math.pi)
        _rot_bone(pb, "mixamorig:RightShoulder", (4.0, -6.0, -8.0))
        _rot_bone(pb, "mixamorig:RightArm",      (-32.0, -24.0, 12.0 - sw_r))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0.0, 0.0, 52.0))
        _rot_bone(pb, "mixamorig:RightHand",     (0.0, 24.0, -8.0))
        pose_hand_grip(pb, "Right", "fist")
    elif weapon_id and right_grip_rest is not None and WEAPON_META.get(weapon_id, {}).get("hold_type") == "rifle":
        M_wep = _make_rifle_world_matrix(arm_obj, weapon_id, mode="ready",
                                         recoil_pitch_deg=3.2 * math.sin(2.0 * ang),
                                         cant_deg=4.5 * math.sin(ang))
        solve_gun_first_weapon_ik(arm_obj, weapon_id, right_grip_rest, M_wep, style="ready", trigger_discipline=True)
    else:
        for side, sx, p_off in (("Left", 1.0, 0.0), ("Right", -1.0, 0.5)):
            a = 2.0 * math.pi * ((phase + p_off) % 1.0)
            swing = 48.0 * math.cos(a)
            elb_bend = 86.0 + 20.0 * max(0.0, math.cos(a))
            _rot_bone(pb, f"mixamorig:{side}Arm",     (-68.0, sx * 10.0, sx * (-swing - 8.0)))
            _rot_bone(pb, f"mixamorig:{side}ForeArm", (0.0, 0.0, sx * (-elb_bend)))
            pose_hand_grip(pb, side, "fist")

    is_flight = (0.28 < phase < 0.44) or (0.78 < phase < 0.94)
    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.05 if is_flight else 0.0)


def apply_strafe_pose(arm_obj, body_obj, phase=0.25, weapon_id=None, right_grip_rest=None):
    """Upper/Lower Body Split Strafe Right: legs step laterally while torso counter-rotates & ADS stays locked -Y."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)

    ang = 2.0 * math.pi * phase
    # Hips yawed -32 deg (turned toward step), Spine+Chest twist back +34 deg toward forward target!
    pb["mixamorig:Hips"].location = Vector((-0.03 * math.cos(ang), 0.0, -0.045 - 0.015 * abs(math.cos(ang))))
    _rot_bone(pb, "mixamorig:Hips",   (5.0, -34.0, 0.0))
    _rot_bone(pb, "mixamorig:Spine",  (3.0,  11.0, 0.0))
    _rot_bone(pb, "mixamorig:Spine1", (3.0,  12.0, 0.0))
    _rot_bone(pb, "mixamorig:Spine2", (4.0,  14.0, 2.0))
    _rot_bone(pb, "mixamorig:Neck",   (-3.0, -4.0, 3.0))
    _rot_bone(pb, "mixamorig:Head",   (-4.0, -5.0, 4.0))
    bpy.context.view_layer.update()

    # Sidestepping lateral leg stride (Right moves right -X, Left crosses/catches)
    step = math.cos(ang)
    r_lat = -0.14 * (1.0 + step)
    l_lat =  0.04 + 0.14 * (-step)
    r_lift = 0.065 * max(0.0, -math.sin(ang))
    l_lift = 0.065 * max(0.0, math.sin(ang))

    _solve_grounded_leg(arm_obj, "Right", stride_y=0.04, lift_z=r_lift,
                        foot_pitch_deg=8.0, lat_x_off=r_lat, foot_yaw_deg=-24.0)
    _solve_grounded_leg(arm_obj, "Left", stride_y=-0.06, lift_z=l_lift,
                        foot_pitch_deg=4.0, lat_x_off=l_lat, foot_yaw_deg=-18.0)

    if weapon_id and right_grip_rest is not None:
        htype = WEAPON_META.get(weapon_id, {}).get("hold_type", "rifle")
        M_wep = _make_pistol_world_matrix(arm_obj) if htype == "pistol" else _make_rifle_world_matrix(arm_obj, weapon_id, mode="aim")
        solve_gun_first_weapon_ik(arm_obj, weapon_id, right_grip_rest, M_wep, style="aim")

    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_melee_idle_pose(arm_obj, body_obj, phase=0.0):
    """Animated athletic melee guard stance (`phase` in [0, 1)) with weight shift & breathing weapon sway."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)

    ang = 2.0 * math.pi * phase
    sway = math.sin(ang)
    br = math.cos(ang)

    pb["mixamorig:Hips"].location = Vector((0.015 * sway, 0.0, -0.045 - 0.008 * br))
    _rot_bone(pb, "mixamorig:Hips",   (6.0, -18.0 + 3.0 * sway, 1.5 * sway))
    _rot_bone(pb, "mixamorig:Spine",  (4.0 + 1.5 * br, 6.0, 0.0))
    _rot_bone(pb, "mixamorig:Spine1", (4.0 + 1.5 * br, 6.0, 0.0))
    _rot_bone(pb, "mixamorig:Spine2", (4.0 + 2.0 * br, 8.0 - 2.0 * sway, 0.0))
    _rot_bone(pb, "mixamorig:Neck",   (-5.0 - 1.5 * br, -6.0 + 2.0 * sway, 0.0))
    _rot_bone(pb, "mixamorig:Head",   (-6.0 - 1.5 * br, -8.0 + 4.0 * sway, 0.0))
    bpy.context.view_layer.update()

    _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.16, lift_z=0.0, lat_x_off=0.02,  foot_yaw_deg=8.0)
    _solve_grounded_leg(arm_obj, "Right", stride_y=0.16,  lift_z=0.0, lat_x_off=-0.02, foot_yaw_deg=-18.0)

    _rot_bone(pb, "mixamorig:LeftShoulder",  (2.0, 4.0, 2.0))
    _rot_bone(pb, "mixamorig:LeftArm",       (-52.0 + 3.0 * br, 14.0, -28.0 + 4.0 * sway))
    _rot_bone(pb, "mixamorig:LeftForeArm",   (0.0, 0.0, -64.0 - 6.0 * br))
    pose_hand_grip(pb, "Left", "fist")

    _rot_bone(pb, "mixamorig:RightShoulder", (0.0, -4.0, -4.0))
    _rot_bone(pb, "mixamorig:RightArm",      (-32.0 - 4.0 * br, -18.0, 46.0 + 5.0 * sway))
    _rot_bone(pb, "mixamorig:RightForeArm",  (0.0, 0.0, 74.0 + 6.0 * br))
    _rot_bone(pb, "mixamorig:RightHand",     (0.0, 24.0, 6.0))
    pose_hand_grip(pb, "Right", "fist")

    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_melee_swing_pose(arm_obj, body_obj, stage="impact"):
    """Grounded 5-beat horizontal power melee slash (`ready`, `windup`, `mid_snap`, `impact`, `follow`)."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)

    if stage == "ready":
        apply_melee_idle_pose(arm_obj, body_obj, phase=0.0)
        return
    elif stage == "windup":
        pb["mixamorig:Hips"].location = Vector((0.02, 0.04, -0.06))
        _rot_bone(pb, "mixamorig:Hips",   (8, -42, -3))
        _rot_bone(pb, "mixamorig:Spine",  (3, -10, 0))
        _rot_bone(pb, "mixamorig:Spine2", (3, -14, -4))
        _rot_bone(pb, "mixamorig:Neck",   (-3, 24, 0))
        _rot_bone(pb, "mixamorig:Head",   (-4, 42, 0))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.16, lift_z=0.02, foot_pitch_deg=10.0, foot_yaw_deg=12.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.22,  lift_z=0.0,  foot_yaw_deg=-26.0)
        _rot_bone(pb, "mixamorig:RightShoulder", (8, -16, -18))
        _rot_bone(pb, "mixamorig:RightArm",      (22, 26, -54))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 98))
        _rot_bone(pb, "mixamorig:RightHand",     (0, 12, 16))
        _rot_bone(pb, "mixamorig:LeftArm",       (-48, 12, -38))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -56))
        pose_hand_grip(pb, "Right", "fist")
        pose_hand_grip(pb, "Left", "fist")
    elif stage == "mid_snap":
        pb["mixamorig:Hips"].location = Vector((0.0, -0.05, -0.09))
        _rot_bone(pb, "mixamorig:Hips",   (12, 4, 2))
        _rot_bone(pb, "mixamorig:Spine",  (6, 6, 0))
        _rot_bone(pb, "mixamorig:Spine2", (8, 8, -4))
        _rot_bone(pb, "mixamorig:Neck",   (-6, -8, 0))
        _rot_bone(pb, "mixamorig:Head",   (-8, -14, 2))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.28, lift_z=0.03, foot_pitch_deg=12.0, foot_yaw_deg=8.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.24,  lift_z=0.02, foot_pitch_deg=-18.0, toe_bend_deg=22.0)
        _rot_bone(pb, "mixamorig:RightShoulder", (6, 4, 8))
        _rot_bone(pb, "mixamorig:RightArm",      (-22, 34, 26))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 34))
        _rot_bone(pb, "mixamorig:RightHand",     (0, 26, -12))
        _rot_bone(pb, "mixamorig:LeftArm",       (-54, -8, 8))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -72))
        pose_hand_grip(pb, "Right", "fist")
        pose_hand_grip(pb, "Left", "fist")
    elif stage == "impact":
        pb["mixamorig:Hips"].location = Vector((-0.02, -0.09, -0.10))
        _rot_bone(pb, "mixamorig:Hips",   (16, 38, 4))
        _rot_bone(pb, "mixamorig:Spine",  (8, 14, 0))
        _rot_bone(pb, "mixamorig:Spine2", (10, 20, -6))
        _rot_bone(pb, "mixamorig:Neck",   (-8, -20, 0))
        _rot_bone(pb, "mixamorig:Head",   (-10, -34, 4))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.34, lift_z=0.0, foot_pitch_deg=0.0, foot_yaw_deg=10.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.28,  lift_z=0.03, foot_pitch_deg=-24.0, toe_bend_deg=28.0)
        _rot_bone(pb, "mixamorig:RightShoulder", (10, 14, 18))
        _rot_bone(pb, "mixamorig:RightArm",      (-28, 30, 82))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 28))
        _rot_bone(pb, "mixamorig:RightHand",     (0, 22, -16))
        _rot_bone(pb, "mixamorig:LeftArm",       (-62, -16, 22))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -68))
        pose_hand_grip(pb, "Right", "fist")
        pose_hand_grip(pb, "Left", "fist")
    else:  # follow
        pb["mixamorig:Hips"].location = Vector((-0.01, -0.04, -0.06))
        _rot_bone(pb, "mixamorig:Hips",   (10, 26, 2))
        _rot_bone(pb, "mixamorig:Spine2", (5, 16, -4))
        _rot_bone(pb, "mixamorig:Head",   (-5, -28, 0))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.24, lift_z=0.0, foot_yaw_deg=8.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.18,  lift_z=0.0, foot_yaw_deg=-14.0)
        _rot_bone(pb, "mixamorig:RightArm",     (-36, 20, 102))
        _rot_bone(pb, "mixamorig:RightForeArm", (0, 0, 48))
        _rot_bone(pb, "mixamorig:LeftArm",      (-60, 8, -16))
        _rot_bone(pb, "mixamorig:LeftForeArm",  (0, 0, -52))
        pose_hand_grip(pb, "Right", "fist")
        pose_hand_grip(pb, "Left", "relaxed")

    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_melee_heavy_slash_pose(arm_obj, body_obj, stage="impact_low"):
    """5-beat overhead-to-diagonal heavy cleave (`ready`, `windup_high`, `cleave_mid`, `impact_low`, `follow_low`)."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)

    if stage == "ready":
        apply_melee_idle_pose(arm_obj, body_obj, phase=0.25)
        return
    elif stage == "windup_high":
        pb["mixamorig:Hips"].location = Vector((0.02, 0.04, -0.04))
        _rot_bone(pb, "mixamorig:Hips",   (-6, -28, -4))
        _rot_bone(pb, "mixamorig:Spine",  (-6, -8, 0))
        _rot_bone(pb, "mixamorig:Spine2", (-8, -10, 0))
        _rot_bone(pb, "mixamorig:Neck",   (6, 14, 0))
        _rot_bone(pb, "mixamorig:Head",   (8, 22, 0))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.12, lift_z=0.03, foot_pitch_deg=12.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.22,  lift_z=0.0,  foot_yaw_deg=-24.0)
        _rot_bone(pb, "mixamorig:RightShoulder", (14, -10, -16))
        _rot_bone(pb, "mixamorig:RightArm",      (56, 22, 16))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 82))
        _rot_bone(pb, "mixamorig:RightHand",     (0, 14, 24))
        _rot_bone(pb, "mixamorig:LeftArm",       (-36, -12, -48))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -70))
        pose_hand_grip(pb, "Right", "fist")
        pose_hand_grip(pb, "Left", "fist")
    elif stage == "cleave_mid":
        pb["mixamorig:Hips"].location = Vector((0.0, -0.05, -0.08))
        _rot_bone(pb, "mixamorig:Hips",   (14, 6, 0))
        _rot_bone(pb, "mixamorig:Spine",  (8, 6, 0))
        _rot_bone(pb, "mixamorig:Spine2", (10, 8, -4))
        _rot_bone(pb, "mixamorig:Head",   (-10, -10, 0))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.30, lift_z=0.02, foot_pitch_deg=8.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.26,  lift_z=0.02, foot_pitch_deg=-18.0, toe_bend_deg=20.0)
        _rot_bone(pb, "mixamorig:RightShoulder", (10, 12, 10))
        _rot_bone(pb, "mixamorig:RightArm",      (-2, 36, 48))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 26))
        _rot_bone(pb, "mixamorig:RightHand",     (0, 22, -20))
        _rot_bone(pb, "mixamorig:LeftArm",       (-52, -14, 14))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -68))
        pose_hand_grip(pb, "Right", "fist")
        pose_hand_grip(pb, "Left", "fist")
    elif stage == "impact_low":
        pb["mixamorig:Hips"].location = Vector((-0.02, -0.10, -0.13))
        _rot_bone(pb, "mixamorig:Hips",   (22, 32, 6))
        _rot_bone(pb, "mixamorig:Spine",  (10, 12, 0))
        _rot_bone(pb, "mixamorig:Spine2", (12, 16, -6))
        _rot_bone(pb, "mixamorig:Neck",   (-12, -16, 0))
        _rot_bone(pb, "mixamorig:Head",   (-14, -26, 4))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.38, lift_z=0.0, foot_pitch_deg=0.0, foot_yaw_deg=12.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.30,  lift_z=0.03, foot_pitch_deg=-26.0, toe_bend_deg=30.0)
        _rot_bone(pb, "mixamorig:RightShoulder", (6, 16, 18))
        _rot_bone(pb, "mixamorig:RightArm",      (-54, 18, 68))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 20))
        _rot_bone(pb, "mixamorig:RightHand",     (0, 18, -28))
        _rot_bone(pb, "mixamorig:LeftArm",       (-64, -18, 28))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -60))
        pose_hand_grip(pb, "Right", "fist")
        pose_hand_grip(pb, "Left", "fist")
    else:  # follow_low
        pb["mixamorig:Hips"].location = Vector((-0.01, -0.05, -0.08))
        _rot_bone(pb, "mixamorig:Hips",   (14, 24, 3))
        _rot_bone(pb, "mixamorig:Spine2", (8, 14, -4))
        _rot_bone(pb, "mixamorig:Head",   (-8, -22, 0))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.26, lift_z=0.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.20,  lift_z=0.0)
        _rot_bone(pb, "mixamorig:RightArm",     (-68, 12, 84))
        _rot_bone(pb, "mixamorig:RightForeArm", (0, 0, 42))
        _rot_bone(pb, "mixamorig:LeftArm",      (-62, 6, -12))
        _rot_bone(pb, "mixamorig:LeftForeArm",  (0, 0, -48))
        pose_hand_grip(pb, "Right", "fist")
        pose_hand_grip(pb, "Left", "relaxed")

    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_hit_react_pose(arm_obj, body_obj, stage="peak"):
    """Impact flinch / stagger reaction (`peak` -> `follow` -> `recover`)."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)

    if stage == "peak":
        pb["mixamorig:Hips"].location = Vector((-0.02, 0.08, -0.06))
        _rot_bone(pb, "mixamorig:Hips",   (-8, -16, -5))
        _rot_bone(pb, "mixamorig:Spine",  (-6, -6, -2))
        _rot_bone(pb, "mixamorig:Spine1", (-7, -6, -3))
        _rot_bone(pb, "mixamorig:Spine2", (-8, -8, -4))
        _rot_bone(pb, "mixamorig:Neck",   (-8, -14, -5))
        _rot_bone(pb, "mixamorig:Head",   (-10, -18, -8))
        bpy.context.view_layer.update()

        _solve_grounded_leg(arm_obj, "Left", stride_y=-0.18, lift_z=0.0, foot_pitch_deg=0.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.20, lift_z=0.03, foot_pitch_deg=-12.0, toe_bend_deg=14.0)

        _rot_bone(pb, "mixamorig:LeftShoulder",  (12, 0, 8))
        _rot_bone(pb, "mixamorig:LeftArm",       (-24, -18, -56))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -92))
        _rot_bone(pb, "mixamorig:RightShoulder", (10, 0, -8))
        _rot_bone(pb, "mixamorig:RightArm",      (-32, 14, 34))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 74))
        pose_hand_grip(pb, "Left", "relaxed")
        pose_hand_grip(pb, "Right", "fist")
    elif stage == "follow":
        pb["mixamorig:Hips"].location = Vector((-0.01, 0.03, -0.05))
        _rot_bone(pb, "mixamorig:Hips",   (4, -6, 0))
        _rot_bone(pb, "mixamorig:Spine2", (4, 4, 0))
        _rot_bone(pb, "mixamorig:Head",   (-4, -6, 0))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left", stride_y=-0.14, lift_z=0.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.14, lift_z=0.0)
        _rot_bone(pb, "mixamorig:LeftArm",      (-54, 4, -34))
        _rot_bone(pb, "mixamorig:LeftForeArm",  (0, 0, -56))
        _rot_bone(pb, "mixamorig:RightArm",     (-50, -4, 32))
        _rot_bone(pb, "mixamorig:RightForeArm", (0, 0, 56))
        pose_hand_grip(pb, "Left", "relaxed")
        pose_hand_grip(pb, "Right", "fist")
    else:
        _apply_combat_lower_body(pb, stance="neutral")
        pose_hand_grip(pb, "Left", "relaxed")
        pose_hand_grip(pb, "Right", "relaxed")

    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_zombie_idle_pose(arm_obj, body_obj, phase=0.0):
    """Eerie hunched zombie idle sway (`phase` in [0, 1)): uneven shoulders, twitching lolled head, claws."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)

    s = max(0.75, pb["mixamorig:Head"].bone.head_local.z / 1.565)
    ang = 2.0 * math.pi * phase
    sway = math.sin(ang)

    pb["mixamorig:Hips"].location = Vector((0.024 * s * sway, 0.0, (-0.055 - 0.008 * abs(math.cos(ang))) * s))
    _rot_bone(pb, "mixamorig:Hips",   (10.0, -8.0 + 6.0 * sway, 4.0 * sway))
    _rot_bone(pb, "mixamorig:Spine",  (10.0 + 3.0 * math.cos(ang), 2.0, -3.0))
    _rot_bone(pb, "mixamorig:Spine1", (10.0 + 2.5 * math.cos(ang), 3.0, -4.0))
    _rot_bone(pb, "mixamorig:Spine2", (9.0, 4.0, -5.0))
    _rot_bone(pb, "mixamorig:Neck",   (-10.0, -8.0 + 8.0 * sway, 14.0))
    _rot_bone(pb, "mixamorig:Head",   (-12.0, -10.0 + 10.0 * sway, 16.0))
    bpy.context.view_layer.update()

    _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.08 * s, lift_z=0.0, lat_x_off=0.02 * s, foot_yaw_deg=8.0)
    _solve_grounded_leg(arm_obj, "Right", stride_y=0.07 * s,  lift_z=0.0, lat_x_off=-0.03 * s, foot_yaw_deg=-14.0)

    _rot_bone(pb, "mixamorig:LeftShoulder",  (4.0, 0.0, 8.0))
    _rot_bone(pb, "mixamorig:LeftArm",       (-28.0 + 6.0 * sway, -12.0, -64.0))
    _rot_bone(pb, "mixamorig:LeftForeArm",   (0.0, 0.0, -28.0 - 6.0 * math.cos(ang)))
    _rot_bone(pb, "mixamorig:RightShoulder", (-6.0, 0.0, -12.0))
    _rot_bone(pb, "mixamorig:RightArm",      (-48.0 - 6.0 * sway, 10.0, 44.0))
    _rot_bone(pb, "mixamorig:RightForeArm",  (0.0, 0.0, 34.0 + 6.0 * math.cos(ang)))
    pose_hand_grip(pb, "Left", "claw")
    pose_hand_grip(pb, "Right", "claw")
    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_zombie_shamble_pose(arm_obj, body_obj, phase=0.25):
    """Asymmetric zombie shambling walk (`phase` in [0, 1)): lateral lurch, lolled head, dragging limp leg."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)

    s = max(0.75, pb["mixamorig:Head"].bone.head_local.z / 1.565)
    ang = 2.0 * math.pi * phase
    pb["mixamorig:Hips"].location = Vector(((0.048 * math.sin(ang) - 0.015) * s, 0.0, (-0.068 - 0.024 * abs(math.cos(ang))) * s))
    _rot_bone(pb, "mixamorig:Hips",   (17.0, -13.0 * math.cos(ang) - 8.0, 9.0 * math.sin(ang) + 5.0))
    _rot_bone(pb, "mixamorig:Spine",  (11.0, 8.0 * math.cos(ang), -4.0))
    _rot_bone(pb, "mixamorig:Spine1", (13.0, 8.0 * math.cos(ang), -4.0))
    _rot_bone(pb, "mixamorig:Spine2", (11.0, 10.0, -6.0))
    _rot_bone(pb, "mixamorig:Neck",   (-14.0, -8.0 + 5.0 * math.sin(ang), 16.0))
    _rot_bone(pb, "mixamorig:Head",   (-16.0, -10.0 + 6.0 * math.sin(ang), 18.0))
    bpy.context.view_layer.update()

    l_str = -0.27 * s * math.cos(ang + math.pi)
    l_lift = 0.072 * s * max(0.0, -math.sin(ang + math.pi))
    r_str = (-0.18 * math.cos(ang) + 0.08) * s
    r_lift = 0.036 * s * max(0.0, -math.sin(ang))
    _solve_grounded_leg(arm_obj, "Left", stride_y=l_str, lift_z=l_lift, foot_pitch_deg=14.0 * math.cos(ang + math.pi))
    _solve_grounded_leg(arm_obj, "Right", stride_y=r_str, lift_z=r_lift,
                        foot_pitch_deg=-14.0, lat_x_off=-0.025 * s, foot_yaw_deg=-14.0)

    sw = 18.0 * math.sin(ang)
    _rot_bone(pb, "mixamorig:LeftShoulder",  (6, 0, 10))
    _rot_bone(pb, "mixamorig:LeftArm",       (-22, -14, -68 + sw))
    _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -24 - 8.0 * math.cos(ang)))
    _rot_bone(pb, "mixamorig:RightShoulder", (-4, 0, -14))
    _rot_bone(pb, "mixamorig:RightArm",      (-44, 10, 48 - sw))
    _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 28 + 8.0 * math.cos(ang)))
    pose_hand_grip(pb, "Left", "claw")
    pose_hand_grip(pb, "Right", "claw")
    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_zombie_run_pose(arm_obj, body_obj, phase=0.14):
    """Feral aggressive zombie sprint (`phase` in [0, 1)): heavy forward pitch, outstretched claws."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)

    s = max(0.75, pb["mixamorig:Head"].bone.head_local.z / 1.565)
    ang = 2.0 * math.pi * phase
    pelv_yaw = -16.0 * math.cos(ang)

    pb["mixamorig:Hips"].location = Vector((0.026 * s * math.sin(ang), 0.0, (-0.088 + 0.044 * math.sin(2.0 * ang - 0.6)) * s))
    _rot_bone(pb, "mixamorig:Hips",   (26.0, pelv_yaw, 6.0 * math.sin(ang)))
    _rot_bone(pb, "mixamorig:Spine",  (11.0, -pelv_yaw * 0.48, 0.0))
    _rot_bone(pb, "mixamorig:Spine1", (11.0, -pelv_yaw * 0.48, 0.0))
    _rot_bone(pb, "mixamorig:Spine2", (9.0,  -pelv_yaw * 0.48, 0.0))
    _rot_bone(pb, "mixamorig:Neck",   (-22.0, 0.0, 4.0))
    _rot_bone(pb, "mixamorig:Head",   (-24.0, pelv_yaw * 0.22, 6.0))

    for side, p_off in (("Right", 0.0), ("Left", 0.5)):
        ph = (phase + p_off) % 1.0
        a = 2.0 * math.pi * ph
        hip_x = 54.0 * math.cos(a) + 12.0
        knee_flex = -(26.0 + 68.0 * (0.5 - 0.5 * math.sin(a + 0.55)))
        foot_x = -24.0 if ph < 0.45 else (-12.0 + 24.0 * ((ph - 0.45) / 0.55))
        _rot_bone(pb, f"mixamorig:{side}UpLeg",   (hip_x, 0.0, 0.0))
        _rot_bone(pb, f"mixamorig:{side}Leg",     (knee_flex, 0.0, 0.0))
        _rot_bone(pb, f"mixamorig:{side}Foot",    (foot_x, 0.0, 0.0))
        _rot_bone(pb, f"mixamorig:{side}ToeBase", (20.0, 0.0, 0.0))

    sw = 32.0 * math.cos(ang)
    _rot_bone(pb, "mixamorig:LeftShoulder",  (8, 0, 12))
    _rot_bone(pb, "mixamorig:LeftArm",       (-12, -16, -68 - sw))
    _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -28))
    _rot_bone(pb, "mixamorig:RightShoulder", (8, 0, -12))
    _rot_bone(pb, "mixamorig:RightArm",      (-12, 16, 68 - sw))
    _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 28))
    pose_hand_grip(pb, "Left", "claw")
    pose_hand_grip(pb, "Right", "claw")
    is_flight = (0.30 < phase < 0.44) or (0.80 < phase < 0.94)
    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.045 * s if is_flight else 0.0)


def apply_zombie_swipe_pose(arm_obj, body_obj, stage="impact"):
    """4-stage heavy raking zombie claw swipe (`windup`, `impact`, `follow`, `recover`)."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)
    s = max(0.75, pb["mixamorig:Head"].bone.head_local.z / 1.565)

    if stage == "windup":
        pb["mixamorig:Hips"].location = Vector((0.02 * s, 0.04 * s, -0.08 * s))
        _rot_bone(pb, "mixamorig:Hips",   (14, -38, 0))
        _rot_bone(pb, "mixamorig:Spine",  (6, -10, 0))
        _rot_bone(pb, "mixamorig:Spine2", (8, -14, 0))
        _rot_bone(pb, "mixamorig:Head",   (-8, 38, 10))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.16 * s, lift_z=0.0, foot_yaw_deg=-18.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.20 * s,  lift_z=0.0, foot_yaw_deg=-34.0)
        _rot_bone(pb, "mixamorig:RightShoulder", (10, -14, -18))
        _rot_bone(pb, "mixamorig:RightArm",      (22, 24, -52))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 90))
        _rot_bone(pb, "mixamorig:LeftArm",       (-40, 10, -56))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -44))
    elif stage == "impact":
        pb["mixamorig:Hips"].location = Vector((-0.02 * s, -0.08 * s, -0.10 * s))
        _rot_bone(pb, "mixamorig:Hips",   (24, 36, 0))
        _rot_bone(pb, "mixamorig:Spine",  (10, 14, 0))
        _rot_bone(pb, "mixamorig:Spine2", (12, 20, -6))
        _rot_bone(pb, "mixamorig:Neck",   (-14, -18, 6))
        _rot_bone(pb, "mixamorig:Head",   (-16, -32, 12))
        _rot_bone(pb, "mixamorig:LeftUpLeg",  (40, 8, 6))
        _rot_bone(pb, "mixamorig:LeftLeg",    (-48, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg", (-28, -10, -4))
        _rot_bone(pb, "mixamorig:RightLeg",   (-22, 0, 0))
        _rot_bone(pb, "mixamorig:RightShoulder", (12, 16, 20))
        _rot_bone(pb, "mixamorig:RightArm",      (-26, 28, 82))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 22))
        _rot_bone(pb, "mixamorig:LeftArm",       (-50, -16, -14))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -58))
    elif stage == "follow":
        pb["mixamorig:Hips"].location = Vector((-0.01 * s, -0.04 * s, -0.07 * s))
        _rot_bone(pb, "mixamorig:Hips",   (16, 24, 0))
        _rot_bone(pb, "mixamorig:Spine2", (8, 12, -4))
        _rot_bone(pb, "mixamorig:Head",   (-12, -22, 8))
        _rot_bone(pb, "mixamorig:LeftUpLeg",  (28, 6, 4))
        _rot_bone(pb, "mixamorig:LeftLeg",    (-36, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg", (-18, -6, -4))
        _rot_bone(pb, "mixamorig:RightLeg",   (-20, 0, 0))
        _rot_bone(pb, "mixamorig:RightArm",     (-36, 22, 98))
        _rot_bone(pb, "mixamorig:RightForeArm", (0, 0, 48))
        _rot_bone(pb, "mixamorig:LeftArm",      (-46, 8, -36))
        _rot_bone(pb, "mixamorig:LeftForeArm",  (0, 0, -38))
    else:  # recover
        pb["mixamorig:Hips"].location = Vector((0.0, -0.01 * s, -0.06 * s))
        _rot_bone(pb, "mixamorig:Hips",   (12, -4, 0))
        _rot_bone(pb, "mixamorig:Spine2", (8, 4, -4))
        _rot_bone(pb, "mixamorig:Head",   (-10, -8, 12))
        _rot_bone(pb, "mixamorig:LeftUpLeg",  (18, 4, 4))
        _rot_bone(pb, "mixamorig:LeftLeg",    (-24, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg", (-12, -4, -4))
        _rot_bone(pb, "mixamorig:RightLeg",   (-18, 0, 0))
        _rot_bone(pb, "mixamorig:RightArm",     (-46, 10, 48))
        _rot_bone(pb, "mixamorig:RightForeArm", (0, 0, 32))
        _rot_bone(pb, "mixamorig:LeftArm",      (-26, -12, -62))
        _rot_bone(pb, "mixamorig:LeftForeArm",  (0, 0, -28))

    pose_hand_grip(pb, "Left", "claw")
    pose_hand_grip(pb, "Right", "claw")
    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_zombie_death_pose(arm_obj, body_obj, stage="prone"):
    """4-stage zombie collapse (`stagger`, `knees`, `fall`, `prone`) grounded cleanly at Z=0."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)
    s = max(0.75, pb["mixamorig:Head"].bone.head_local.z / 1.565)

    if stage == "stagger":
        pb["mixamorig:Hips"].location = Vector((0.0, 0.04 * s, -0.08 * s))
        _rot_bone(pb, "mixamorig:Hips",   (-12, 10, 6))
        _rot_bone(pb, "mixamorig:Spine2", (-10, 6, 4))
        _rot_bone(pb, "mixamorig:Head",   (-14, 12, 8))
        _rot_bone(pb, "mixamorig:LeftUpLeg",  (24, 0, 6))
        _rot_bone(pb, "mixamorig:LeftLeg",    (-34, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg", (8, 0, -6))
        _rot_bone(pb, "mixamorig:RightLeg",   (-26, 0, 0))
        _rot_bone(pb, "mixamorig:LeftArm",    (-24, 10, -40))
        _rot_bone(pb, "mixamorig:RightArm",   (-20, -10, 44))
    elif stage == "knees":
        pb["mixamorig:Hips"].location = Vector((0.0, -0.04 * s, -0.44 * s))
        _rot_bone(pb, "mixamorig:Hips",   (26, 8, 4))
        _rot_bone(pb, "mixamorig:Spine2", (18, 4, 4))
        _rot_bone(pb, "mixamorig:Head",   (16, -8, 10))
        _rot_bone(pb, "mixamorig:LeftUpLeg",  (56, 0, 6))
        _rot_bone(pb, "mixamorig:LeftLeg",    (-112, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg", (48, 0, -6))
        _rot_bone(pb, "mixamorig:RightLeg",   (-104, 0, 0))
        _rot_bone(pb, "mixamorig:LeftArm",    (-34, 0, -56))
        _rot_bone(pb, "mixamorig:RightArm",   (-34, 0, 56))
    elif stage == "fall":
        pb["mixamorig:Hips"].location = Vector((0.0, -0.10 * s, -0.62 * s))
        _rot_bone(pb, "mixamorig:Hips",   (62, 12, -8))
        _rot_bone(pb, "mixamorig:Spine2", (14, 0, -6))
        _rot_bone(pb, "mixamorig:Head",   (-16, 12, 14))
        _rot_bone(pb, "mixamorig:LeftUpLeg",  (28, 0, 8))
        _rot_bone(pb, "mixamorig:LeftLeg",    (-58, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg", (14, 0, -8))
        _rot_bone(pb, "mixamorig:RightLeg",   (-38, 0, 0))
        _rot_bone(pb, "mixamorig:LeftArm",    (-20, -14, -76))
        _rot_bone(pb, "mixamorig:RightArm",   (-28, 12, 68))
    else:  # prone
        pb["mixamorig:Hips"].location = Vector((0.0, -0.16 * s, -0.78 * s))
        _rot_bone(pb, "mixamorig:Hips",   (86, 10, -8))
        _rot_bone(pb, "mixamorig:Spine2", (4, 0, -6))
        _rot_bone(pb, "mixamorig:Head",   (-10, 24, 16))
        _rot_bone(pb, "mixamorig:LeftUpLeg",  (8, 0, 12))
        _rot_bone(pb, "mixamorig:LeftLeg",    (-20, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg", (-4, 0, -10))
        _rot_bone(pb, "mixamorig:RightLeg",   (-12, 0, 0))
        _rot_bone(pb, "mixamorig:LeftArm",    (-56, -24, -64))
        _rot_bone(pb, "mixamorig:LeftForeArm",(0, 0, -48))
        _rot_bone(pb, "mixamorig:RightArm",   (-48, 22, 74))
        _rot_bone(pb, "mixamorig:RightForeArm",(0, 0, 56))

    pose_hand_grip(pb, "Left", "claw")
    pose_hand_grip(pb, "Right", "claw")
    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_zombie_shriek_pose(arm_obj, body_obj, stage="peak"):
    """Banshee Sonic Shriek (`inhale`, `peak`, `recover`): arched spine, skyward unhinged jaw, raised claws."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)
    s = max(0.75, pb["mixamorig:Head"].bone.head_local.z / 1.565)

    if stage == "inhale":
        pb["mixamorig:Hips"].location = Vector((0.0, 0.02 * s, -0.09 * s))
        _rot_bone(pb, "mixamorig:Hips",   (16, 0, 0))
        _rot_bone(pb, "mixamorig:Spine",  (12, 0, 0))
        _rot_bone(pb, "mixamorig:Spine2", (14, 0, 0))
        _rot_bone(pb, "mixamorig:Head",   (14, 0, 6))
        _rot_bone(pb, "mixamorig:LeftUpLeg",  (22, 0, 4))
        _rot_bone(pb, "mixamorig:LeftLeg",    (-30, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg", (12, 0, -4))
        _rot_bone(pb, "mixamorig:RightLeg",   (-26, 0, 0))
        _rot_bone(pb, "mixamorig:LeftArm",    (-24, -18, -54))
        _rot_bone(pb, "mixamorig:LeftForeArm",(0, 0, -78))
        _rot_bone(pb, "mixamorig:RightArm",   (-24, 18, 54))
        _rot_bone(pb, "mixamorig:RightForeArm",(0, 0, 78))
    elif stage == "peak":
        pb["mixamorig:Hips"].location = Vector((0.0, 0.0, -0.05 * s))
        _rot_bone(pb, "mixamorig:Hips",   (-8, -6, 0))
        _rot_bone(pb, "mixamorig:Spine",  (-12, 2, 0))
        _rot_bone(pb, "mixamorig:Spine1", (-12, 2, 0))
        _rot_bone(pb, "mixamorig:Spine2", (-14, 2, 0))
        _rot_bone(pb, "mixamorig:Neck",   (-14, 0, -4))
        _rot_bone(pb, "mixamorig:Head",   (-22, 0, -6))
        _rot_bone(pb, "mixamorig:LeftUpLeg",  (16, 4, 5))
        _rot_bone(pb, "mixamorig:LeftLeg",    (-18, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg", (-10, -4, -5))
        _rot_bone(pb, "mixamorig:RightLeg",   (-16, 0, 0))
        _rot_bone(pb, "mixamorig:LeftShoulder",  (14, 0, 12))
        _rot_bone(pb, "mixamorig:LeftArm",       (8, -22, -48))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -96))
        _rot_bone(pb, "mixamorig:RightShoulder", (14, 0, -12))
        _rot_bone(pb, "mixamorig:RightArm",      (8, 22, 48))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 96))
    elif stage == "follow":
        pb["mixamorig:Hips"].location = Vector((0.0, 0.0, -0.06 * s))
        _rot_bone(pb, "mixamorig:Hips",   (-2, 4, 0))
        _rot_bone(pb, "mixamorig:Spine2", (-6, 0, 0))
        _rot_bone(pb, "mixamorig:Head",   (-12, 6, 4))
        _rot_bone(pb, "mixamorig:LeftArm",    (-18, -16, -40))
        _rot_bone(pb, "mixamorig:RightArm",   (-18, 16, 40))
    else:
        pb["mixamorig:Hips"].location = Vector((0.0, 0.0, -0.05 * s))
        _rot_bone(pb, "mixamorig:Hips",   (10, 0, 0))
        _rot_bone(pb, "mixamorig:Spine2", (8, 0, 0))
        _rot_bone(pb, "mixamorig:Head",   (-10, 0, 8))
        _rot_bone(pb, "mixamorig:LeftArm",    (-38, -10, -46))
        _rot_bone(pb, "mixamorig:RightArm",   (-38, 10, 46))

    pose_hand_grip(pb, "Left", "claw")
    pose_hand_grip(pb, "Right", "claw")
    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_zombie_spit_pose(arm_obj, body_obj, stage="spit"):
    """Spitter Acid Spit (`charge`, `spit`, `follow`, `recover`): braced lunge projecting toxic vomit straight forward."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)
    s = max(0.75, pb["mixamorig:Head"].bone.head_local.z / 1.565)

    if stage == "charge":
        pb["mixamorig:Hips"].location = Vector((0.0, 0.04 * s, -0.08 * s))
        _rot_bone(pb, "mixamorig:Hips",   (-6, 0, 0))
        _rot_bone(pb, "mixamorig:Spine",  (-6, 0, 0))
        _rot_bone(pb, "mixamorig:Spine2", (-8, 0, 0))
        _rot_bone(pb, "mixamorig:Neck",   (-14, 0, 0))
        _rot_bone(pb, "mixamorig:Head",   (-18, 0, 0))
        _rot_bone(pb, "mixamorig:LeftArm",    (-28, 18, -32))
        _rot_bone(pb, "mixamorig:RightArm",   (-28, -18, 32))
    elif stage == "spit":
        pb["mixamorig:Hips"].location = Vector((0.0, -0.06 * s, -0.10 * s))
        _rot_bone(pb, "mixamorig:Hips",   (22, -6, 0))
        _rot_bone(pb, "mixamorig:Spine",  (12, 4, 0))
        _rot_bone(pb, "mixamorig:Spine1", (14, 4, 0))
        _rot_bone(pb, "mixamorig:Spine2", (14, 4, 0))
        _rot_bone(pb, "mixamorig:Neck",   (-26, 0, 0))
        _rot_bone(pb, "mixamorig:Head",   (-24, 0, 0))
        _rot_bone(pb, "mixamorig:LeftUpLeg",  (30, 4, 4))
        _rot_bone(pb, "mixamorig:LeftLeg",    (-38, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg", (-18, -4, -4))
        _rot_bone(pb, "mixamorig:RightLeg",   (-22, 0, 0))
        _rot_bone(pb, "mixamorig:LeftShoulder",  (6, -10, -10))
        _rot_bone(pb, "mixamorig:LeftArm",       (-18, 28, -22))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -34))
        _rot_bone(pb, "mixamorig:RightShoulder", (6, 10, 10))
        _rot_bone(pb, "mixamorig:RightArm",      (-18, -28, 22))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 34))
    elif stage == "follow":
        pb["mixamorig:Hips"].location = Vector((0.0, -0.02 * s, -0.07 * s))
        _rot_bone(pb, "mixamorig:Hips",   (14, 0, 0))
        _rot_bone(pb, "mixamorig:Spine2", (10, 0, 0))
        _rot_bone(pb, "mixamorig:Head",   (-4, 0, 6))
        _rot_bone(pb, "mixamorig:LeftArm",  (-32, 10, -36))
        _rot_bone(pb, "mixamorig:RightArm", (-32, -10, 36))
    else:
        pb["mixamorig:Hips"].location = Vector((0.0, 0.0, -0.06 * s))
        _rot_bone(pb, "mixamorig:Hips",   (12, 0, 0))
        _rot_bone(pb, "mixamorig:Spine2", (8, 0, 0))
        _rot_bone(pb, "mixamorig:Head",   (-10, 0, 8))
        _rot_bone(pb, "mixamorig:LeftArm",    (-44, 0, -40))
        _rot_bone(pb, "mixamorig:RightArm",   (-44, 0, 40))

    pose_hand_grip(pb, "Left", "claw")
    pose_hand_grip(pb, "Right", "claw")
    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_zombie_detonate_pose(arm_obj, body_obj, stage="burst"):
    """Bloater Volatile Detonate (`idle`, `swell`, `burst`, `collapse`): arms brace clear of wide gut then explode outward."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)
    s = max(0.75, pb["mixamorig:Head"].bone.head_local.z / 1.565)

    if stage == "idle":
        apply_zombie_idle_pose(arm_obj, body_obj, phase=0.0)
        return
    elif stage == "swell":
        pb["mixamorig:Hips"].location = Vector((0.0, 0.0, -0.10 * s))
        _rot_bone(pb, "mixamorig:Hips",   (12, 0, 0))
        _rot_bone(pb, "mixamorig:Spine",  (10, 0, 0))
        _rot_bone(pb, "mixamorig:Spine2", (10, 0, 0))
        _rot_bone(pb, "mixamorig:Head",   (14, 0, 10))
        _rot_bone(pb, "mixamorig:LeftUpLeg",  (24, 0, 8))
        _rot_bone(pb, "mixamorig:LeftLeg",    (-36, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg", (24, 0, -8))
        _rot_bone(pb, "mixamorig:RightLeg",   (-36, 0, 0))
        _rot_bone(pb, "mixamorig:LeftArm",    (-18, -22, -46))
        _rot_bone(pb, "mixamorig:LeftForeArm",(0, 0, -48))
        _rot_bone(pb, "mixamorig:RightArm",   (-18, 22, 46))
        _rot_bone(pb, "mixamorig:RightForeArm",(0, 0, 48))
    elif stage == "burst":
        pb["mixamorig:Hips"].location = Vector((0.0, 0.0, -0.06 * s))
        _rot_bone(pb, "mixamorig:Hips",   (-6, 0, 0))
        _rot_bone(pb, "mixamorig:Spine",  (-6, 0, 0))
        _rot_bone(pb, "mixamorig:Spine1", (-6, 0, 0))
        _rot_bone(pb, "mixamorig:Spine2", (-8, 0, 0))
        _rot_bone(pb, "mixamorig:Neck",   (-10, 0, 0))
        _rot_bone(pb, "mixamorig:Head",   (-14, 0, 6))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.10 * s, lift_z=0.0, lat_x_off=0.04 * s, foot_yaw_deg=12.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.10 * s,  lift_z=0.0, lat_x_off=-0.04 * s, foot_yaw_deg=-12.0)
        _rot_bone(pb, "mixamorig:LeftShoulder",  (10, -8, -10))
        _rot_bone(pb, "mixamorig:LeftArm",       (-8, 24, -18))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -18))
        _rot_bone(pb, "mixamorig:RightShoulder", (10, 8, 10))
        _rot_bone(pb, "mixamorig:RightArm",      (-8, -24, 18))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 18))
    else:
        pb["mixamorig:Hips"].location = Vector((0.0, 0.02 * s, -0.22 * s))
        _rot_bone(pb, "mixamorig:Hips",   (32, 8, 0))
        _rot_bone(pb, "mixamorig:LeftUpLeg",  (36, 0, 8))
        _rot_bone(pb, "mixamorig:LeftLeg",    (-58, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg", (32, 0, -8))
        _rot_bone(pb, "mixamorig:RightLeg",   (-54, 0, 0))
        _rot_bone(pb, "mixamorig:LeftArm",    (-28, 0, -32))
        _rot_bone(pb, "mixamorig:RightArm",   (-28, 0, 32))

    pose_hand_grip(pb, "Left", "claw")
    pose_hand_grip(pb, "Right", "claw")
    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_zombie_slam_pose(arm_obj, body_obj, stage="impact"):
    """Juggernaut Ground Slam (`windup`, `impact`, `rebound`, `recover`): towering rear-back then crushing fist smash."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)
    s = max(0.75, pb["mixamorig:Head"].bone.head_local.z / 1.565)

    if stage == "windup":
        pb["mixamorig:Hips"].location = Vector((0.0, 0.03 * s, -0.06 * s))
        _rot_bone(pb, "mixamorig:Hips",   (-10, -24, 0))
        _rot_bone(pb, "mixamorig:Spine",  (-8, -8, 0))
        _rot_bone(pb, "mixamorig:Spine2", (-10, -10, 0))
        _rot_bone(pb, "mixamorig:Neck",   (8, 12, 0))
        _rot_bone(pb, "mixamorig:Head",   (6, 20, 4))
        _rot_bone(pb, "mixamorig:LeftUpLeg",  (18, 6, 8))
        _rot_bone(pb, "mixamorig:LeftLeg",    (-24, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg", (-12, -6, -8))
        _rot_bone(pb, "mixamorig:RightLeg",   (-18, 0, 0))
        _rot_bone(pb, "mixamorig:RightShoulder", (18, 0, -14))
        _rot_bone(pb, "mixamorig:RightArm",      (56, 16, 18))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 44))
        _rot_bone(pb, "mixamorig:LeftArm",       (-42, -12, -32))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -40))
    elif stage == "impact":
        pb["mixamorig:Hips"].location = Vector((0.0, -0.05 * s, -0.42 * s))
        _rot_bone(pb, "mixamorig:Hips",   (38, 18, 0))
        _rot_bone(pb, "mixamorig:Spine",  (14, 8, 0))
        _rot_bone(pb, "mixamorig:Spine1", (14, 8, 0))
        _rot_bone(pb, "mixamorig:Spine2", (14, 10, 0))
        _rot_bone(pb, "mixamorig:Neck",   (-20, -14, 0))
        _rot_bone(pb, "mixamorig:Head",   (-24, -18, 6))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.30 * s, lift_z=0.0, lat_x_off=0.08 * s, foot_yaw_deg=18.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.22 * s,  lift_z=0.02 * s, foot_pitch_deg=-18.0, toe_bend_deg=22.0, lat_x_off=-0.08 * s, foot_yaw_deg=-18.0)
        _rot_bone(pb, "mixamorig:RightShoulder", (6, 14, -14))
        _rot_bone(pb, "mixamorig:RightArm",      (-40, 14, 78))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 12))
        _rot_bone(pb, "mixamorig:RightHand",     (0, 0, 22))
        _rot_bone(pb, "mixamorig:LeftShoulder",  (6, 0, 10))
        _rot_bone(pb, "mixamorig:LeftArm",       (-36, -24, -22))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -48))
    elif stage == "rebound":
        pb["mixamorig:Hips"].location = Vector((0.0, -0.03 * s, -0.22 * s))
        _rot_bone(pb, "mixamorig:Hips",   (24, 12, 0))
        _rot_bone(pb, "mixamorig:Spine2", (12, 6, 0))
        _rot_bone(pb, "mixamorig:Head",   (-14, -12, 6))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.24 * s, lift_z=0.0, lat_x_off=0.06 * s)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.18 * s,  lift_z=0.0, lat_x_off=-0.06 * s)
        _rot_bone(pb, "mixamorig:RightArm",     (-34, 16, 54))
        _rot_bone(pb, "mixamorig:RightForeArm", (0, 0, 28))
        _rot_bone(pb, "mixamorig:LeftArm",      (-42, -16, -28))
        _rot_bone(pb, "mixamorig:LeftForeArm",  (0, 0, -42))
    else:
        pb["mixamorig:Hips"].location = Vector((0.0, -0.02 * s, -0.10 * s))
        _rot_bone(pb, "mixamorig:Hips",   (16, 10, 0))
        _rot_bone(pb, "mixamorig:Spine2", (10, 6, 0))
        _rot_bone(pb, "mixamorig:Head",   (-10, -10, 6))
        _rot_bone(pb, "mixamorig:LeftUpLeg",  (24, 0, 6))
        _rot_bone(pb, "mixamorig:LeftLeg",    (-30, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg", (-14, 0, -6))
        _rot_bone(pb, "mixamorig:RightLeg",   (-22, 0, 0))
        _rot_bone(pb, "mixamorig:RightArm",     (-42, 16, 36))
        _rot_bone(pb, "mixamorig:LeftArm",      (-48, -10, -34))

    pose_hand_grip(pb, "Left", "claw")
    pose_hand_grip(pb, "Right", "fist")
    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_zombie_echo_click_pose(arm_obj, body_obj, stage="listen"):
    """Cordyceps Echolocation & Blind Dash (`listen`, `crouch`, `dash`, `grab`)."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)
    s = max(0.75, pb["mixamorig:Head"].bone.head_local.z / 1.565)

    if stage == "crouch":
        pb["mixamorig:Hips"].location = Vector((0.0, 0.04 * s, -0.18 * s))
        _rot_bone(pb, "mixamorig:Hips",   (22, -6, 0))
        _rot_bone(pb, "mixamorig:Spine2", (12, 4, 0))
        _rot_bone(pb, "mixamorig:Head",   (-18, -10, 14))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.20 * s, lift_z=0.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.20 * s,  lift_z=0.0)
        _rot_bone(pb, "mixamorig:LeftArm",      (-28, 12, -48))
        _rot_bone(pb, "mixamorig:LeftForeArm",  (0, 0, -68))
        _rot_bone(pb, "mixamorig:RightArm",     (-28, -12, 48))
        _rot_bone(pb, "mixamorig:RightForeArm", (0, 0, 68))
    elif stage == "listen":
        pb["mixamorig:Hips"].location = Vector((0.0, 0.01 * s, -0.10 * s))
        _rot_bone(pb, "mixamorig:Hips",   (14, -10, 4))
        _rot_bone(pb, "mixamorig:Spine",  (12, 4, -4))
        _rot_bone(pb, "mixamorig:Spine1", (12, 4, -4))
        _rot_bone(pb, "mixamorig:Spine2", (10, 6, -4))
        _rot_bone(pb, "mixamorig:Neck",   (-16, 18, -14))
        _rot_bone(pb, "mixamorig:Head",   (-18, 22, -20))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.16 * s, lift_z=0.0, lat_x_off=0.03 * s, foot_yaw_deg=10.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.14 * s,  lift_z=0.0, lat_x_off=-0.03 * s, foot_yaw_deg=-16.0)
        _rot_bone(pb, "mixamorig:LeftShoulder",  (8, 0, 12))
        _rot_bone(pb, "mixamorig:LeftArm",       (-18, -28, -56))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -58))
        _rot_bone(pb, "mixamorig:LeftHand",      (0, -14, 18))
        _rot_bone(pb, "mixamorig:RightShoulder", (6, 0, -12))
        _rot_bone(pb, "mixamorig:RightArm",      (-28, 24, 48))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 64))
        _rot_bone(pb, "mixamorig:RightHand",     (0, 16, -16))
    elif stage == "dash":
        pb["mixamorig:Hips"].location = Vector((0.0, -0.06 * s, -0.14 * s))
        _rot_bone(pb, "mixamorig:Hips",   (28, -12, 0))
        _rot_bone(pb, "mixamorig:Spine",  (12, 6, 0))
        _rot_bone(pb, "mixamorig:Spine2", (12, 6, 0))
        _rot_bone(pb, "mixamorig:Neck",   (-16, 8, -10))
        _rot_bone(pb, "mixamorig:Head",   (-20, 10, -14))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.30 * s, lift_z=0.02 * s, foot_pitch_deg=10.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.34 * s,  lift_z=0.08 * s, foot_pitch_deg=-26.0, toe_bend_deg=24.0)
        _rot_bone(pb, "mixamorig:LeftShoulder",  (10, 0, 14))
        _rot_bone(pb, "mixamorig:LeftArm",       (-10, -14, -76))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -24))
        _rot_bone(pb, "mixamorig:RightShoulder", (10, 0, -14))
        _rot_bone(pb, "mixamorig:RightArm",      (-10, 14, 76))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 24))
    else:  # grab
        pb["mixamorig:Hips"].location = Vector((0.0, -0.05 * s, -0.10 * s))
        _rot_bone(pb, "mixamorig:Hips",   (22, 8, 0))
        _rot_bone(pb, "mixamorig:Spine2", (14, -4, 0))
        _rot_bone(pb, "mixamorig:Head",   (8, -10, 12))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.22 * s, lift_z=0.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.20 * s,  lift_z=0.0)
        _rot_bone(pb, "mixamorig:LeftArm",       (-16, -24, -64))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -48))
        _rot_bone(pb, "mixamorig:RightArm",      (-16, 24, 64))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 48))

    pose_hand_grip(pb, "Left", "claw")
    pose_hand_grip(pb, "Right", "claw")
    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_zombie_signature_pose(arm_obj, body_obj, pose_name="shamble"):
    """Apply signature zombie showcase pose (`idle`, `shamble`, `run`, `swipe`, `pounce`, `lunge`, `bite`, `shriek`, `spit`, `detonate`, `slam`)."""
    if pose_name == "idle":
        apply_zombie_idle_pose(arm_obj, body_obj, phase=0.20)
    elif pose_name == "run":
        apply_zombie_run_pose(arm_obj, body_obj, phase=0.14)
    elif pose_name == "swipe":
        apply_zombie_swipe_pose(arm_obj, body_obj, stage="impact")
    elif pose_name in ("lunge", "pounce"):
        apply_zombie_lunge_pose(arm_obj, body_obj, stage="lunge")
    elif pose_name == "bite":
        apply_zombie_bite_pose(arm_obj, body_obj, stage="bite")
    elif pose_name == "shriek":
        apply_zombie_shriek_pose(arm_obj, body_obj, stage="peak")
    elif pose_name == "spit":
        apply_zombie_spit_pose(arm_obj, body_obj, stage="spit")
    elif pose_name == "detonate":
        apply_zombie_detonate_pose(arm_obj, body_obj, stage="burst")
    elif pose_name == "slam":
        apply_zombie_slam_pose(arm_obj, body_obj, stage="impact")
    else:
        apply_zombie_shamble_pose(arm_obj, body_obj, phase=0.22)
    bpy.ops.object.mode_set(mode="OBJECT")


def apply_zombie_lunge_pose(arm_obj, body_obj, stage="lunge"):
    """4-stage Zombie Pounce / Lunge mechanic (stage in {'windup', 'launch', 'lunge', 'recover'})."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)

    if stage == "windup":
        pb["mixamorig:Hips"].location = Vector((0.0, 0.05, -0.22))
        _rot_bone(pb, "mixamorig:Hips",   (18, 12, 0))
        _rot_bone(pb, "mixamorig:Spine",  (14, -8, 0))
        _rot_bone(pb, "mixamorig:Spine1", (12, -8, 0))
        _rot_bone(pb, "mixamorig:Spine2", (8, -6, 0))
        _rot_bone(pb, "mixamorig:Neck",   (-18, 6, 0))
        _rot_bone(pb, "mixamorig:Head",   (-22, 8, -4))
        _rot_bone(pb, "mixamorig:LeftUpLeg",   (52, 0, 5))
        _rot_bone(pb, "mixamorig:LeftLeg",     (-84, 0, 0))
        _rot_bone(pb, "mixamorig:LeftFoot",    (26, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg",  (20, 0, -5))
        _rot_bone(pb, "mixamorig:RightLeg",    (-64, 0, 0))
        _rot_bone(pb, "mixamorig:RightFoot",   (26, 0, 0))
        _rot_bone(pb, "mixamorig:LeftArm",      (-48, 20, 32))
        _rot_bone(pb, "mixamorig:LeftForeArm",  (0, 0, -78))
        _rot_bone(pb, "mixamorig:RightArm",     (-42, -20, -28))
        _rot_bone(pb, "mixamorig:RightForeArm", (0, 0, 84))
        pose_hand_grip(pb, "Left", "claw")
        pose_hand_grip(pb, "Right", "claw")
        snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)

    elif stage == "launch":
        pb["mixamorig:Hips"].location = Vector((0.0, -0.04, -0.10))
        _rot_bone(pb, "mixamorig:Hips",   (28, -10, 0))
        _rot_bone(pb, "mixamorig:Spine",  (12, 6, 0))
        _rot_bone(pb, "mixamorig:Spine2", (10, 6, 0))
        _rot_bone(pb, "mixamorig:Neck",   (-24, 0, 0))
        _rot_bone(pb, "mixamorig:Head",   (-26, 0, 4))
        _rot_bone(pb, "mixamorig:LeftUpLeg",    (48, 4, 6))
        _rot_bone(pb, "mixamorig:LeftLeg",      (-64, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg",   (-24, -4, -4))
        _rot_bone(pb, "mixamorig:RightLeg",     (-12, 0, 0))
        _rot_bone(pb, "mixamorig:RightFoot",    (-24, 0, 0))
        _rot_bone(pb, "mixamorig:RightToeBase", (26, 0, 0))
        _rot_bone(pb, "mixamorig:RightArm",     (-30, 14, 62))
        _rot_bone(pb, "mixamorig:RightForeArm", (0, 0, 26))
        _rot_bone(pb, "mixamorig:LeftArm",      (-22, -16, -54))
        _rot_bone(pb, "mixamorig:LeftForeArm",  (0, 0, -34))
        pose_hand_grip(pb, "Left", "claw")
        pose_hand_grip(pb, "Right", "claw")
        snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)

    elif stage == "lunge":
        pb["mixamorig:Hips"].location = Vector((0.0, -0.08, -0.14))
        _rot_bone(pb, "mixamorig:Hips",   (38, -14, 0))
        _rot_bone(pb, "mixamorig:Spine",  (14, 8, 0))
        _rot_bone(pb, "mixamorig:Spine1", (14, 8, 0))
        _rot_bone(pb, "mixamorig:Spine2", (10, 6, 4))
        _rot_bone(pb, "mixamorig:Neck",   (-28, -4, 0))
        _rot_bone(pb, "mixamorig:Head",   (-32, -6, 8))

        _rot_bone(pb, "mixamorig:LeftUpLeg",    (44, 4, 6))
        _rot_bone(pb, "mixamorig:LeftLeg",      (-60, 0, 0))
        _rot_bone(pb, "mixamorig:LeftFoot",     (-14, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg",   (-40, -4, -4))
        _rot_bone(pb, "mixamorig:RightLeg",     (-14, 0, 0))
        _rot_bone(pb, "mixamorig:RightFoot",    (-26, 0, 0))
        _rot_bone(pb, "mixamorig:RightToeBase", (24, 0, 0))

        _rot_bone(pb, "mixamorig:RightShoulder", (4, 12, 12))
        _rot_bone(pb, "mixamorig:RightArm",      (-20, 16, 76))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 16))
        _rot_bone(pb, "mixamorig:RightHand",     (0, 15, -14))

        _rot_bone(pb, "mixamorig:LeftShoulder",  (4, -10, -10))
        _rot_bone(pb, "mixamorig:LeftArm",       (-14, -22, -62))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -28))
        _rot_bone(pb, "mixamorig:LeftHand",      (0, -12, 16))

        pose_hand_grip(pb, "Left", "claw")
        pose_hand_grip(pb, "Right", "claw")
        snap_feet_to_floor(arm_obj, body_obj, floor_z=0.05)

    elif stage == "follow":
        pb["mixamorig:Hips"].location = Vector((0.0, -0.04, -0.09))
        _rot_bone(pb, "mixamorig:Hips",   (24, -10, 0))
        _rot_bone(pb, "mixamorig:Spine2", (8, 4, 0))
        _rot_bone(pb, "mixamorig:Head",   (-14, -4, 6))
        _rot_bone(pb, "mixamorig:LeftUpLeg",  (32, 0, 4))
        _rot_bone(pb, "mixamorig:LeftLeg",    (-44, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg", (-18, 0, -4))
        _rot_bone(pb, "mixamorig:RightLeg",   (-26, 0, 0))
        _rot_bone(pb, "mixamorig:LeftArm",    (-38, 10, -42))
        _rot_bone(pb, "mixamorig:LeftForeArm",(0, 0, -46))
        _rot_bone(pb, "mixamorig:RightArm",   (-36, -10, 46))
        _rot_bone(pb, "mixamorig:RightForeArm",(0, 0, 44))
        pose_hand_grip(pb, "Left", "claw")
        pose_hand_grip(pb, "Right", "claw")
        snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)

    else:  # recover
        pb["mixamorig:Hips"].location = Vector((0.0, 0.0, -0.06))
        _rot_bone(pb, "mixamorig:Hips",   (18, -6, 0))
        _rot_bone(pb, "mixamorig:Spine",  (8, 3, 0))
        _rot_bone(pb, "mixamorig:Spine1", (8, 3, 0))
        _rot_bone(pb, "mixamorig:Spine2", (6, 2, 0))
        _rot_bone(pb, "mixamorig:Neck",   (-14, 0, 0))
        _rot_bone(pb, "mixamorig:Head",   (-14, 0, 0))
        _rot_bone(pb, "mixamorig:LeftUpLeg",  (28, 0, 4))
        _rot_bone(pb, "mixamorig:LeftLeg",    (-38, 0, 0))
        _rot_bone(pb, "mixamorig:RightUpLeg", (-14, 0, -4))
        _rot_bone(pb, "mixamorig:RightLeg",   (-22, 0, 0))
        _rot_bone(pb, "mixamorig:LeftArm",      (-58, 12, -32))
        _rot_bone(pb, "mixamorig:LeftForeArm",  (0, 0, -32))
        _rot_bone(pb, "mixamorig:RightArm",     (-52, -12, 36))
        _rot_bone(pb, "mixamorig:RightForeArm", (0, 0, 34))
        pose_hand_grip(pb, "Left", "claw")
        pose_hand_grip(pb, "Right", "claw")
        snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_zombie_bite_pose(arm_obj, body_obj, stage="bite"):
    """Close-range grapple & neck bite (`reach`, `windup`, `bite`, `follow`)."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)

    pb["mixamorig:Hips"].location = Vector((0.0, -0.04, -0.06))
    _rot_bone(pb, "mixamorig:Hips",   (18, -8, 0))
    _rot_bone(pb, "mixamorig:Spine",  (8, 4, 0))
    _rot_bone(pb, "mixamorig:Spine1", (10, 4, 0))
    _rot_bone(pb, "mixamorig:Spine2", (12, 4, 0))
    _rot_bone(pb, "mixamorig:LeftUpLeg",  (28, 4, 4))
    _rot_bone(pb, "mixamorig:LeftLeg",    (-36, 0, 0))
    _rot_bone(pb, "mixamorig:RightUpLeg", (-18, -4, -4))
    _rot_bone(pb, "mixamorig:RightLeg",   (-24, 0, 0))

    if stage == "windup":
        _rot_bone(pb, "mixamorig:Neck", (-18, 0, -6))
        _rot_bone(pb, "mixamorig:Head", (-22, 0, -8))
        _rot_bone(pb, "mixamorig:LeftArm",      (-12, -26, -78))
        _rot_bone(pb, "mixamorig:LeftForeArm",  (0, 0, -24))
        _rot_bone(pb, "mixamorig:RightArm",     (-12, 26, 78))
        _rot_bone(pb, "mixamorig:RightForeArm", (0, 0, 24))
    elif stage == "bite":
        _rot_bone(pb, "mixamorig:Neck", (22, -6, 10))
        _rot_bone(pb, "mixamorig:Head", (18, -8, 12))
        # Both arms clamped forward gripping prey's shoulders, elbows pulled back slightly
        _rot_bone(pb, "mixamorig:LeftShoulder",  (6, 0, 12))
        _rot_bone(pb, "mixamorig:LeftArm",       (-12, -24, -68))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -54))
        _rot_bone(pb, "mixamorig:LeftHand",      (0, 24, 18))
        _rot_bone(pb, "mixamorig:RightShoulder", (6, 0, -12))
        _rot_bone(pb, "mixamorig:RightArm",      (-12, 24, 68))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 54))
        _rot_bone(pb, "mixamorig:RightHand",     (0, -24, -18))
    elif stage == "follow":
        _rot_bone(pb, "mixamorig:Neck", (-4, 8, -10))
        _rot_bone(pb, "mixamorig:Head", (-8, 10, -12))
        _rot_bone(pb, "mixamorig:LeftArm",      (-24, -12, -52))
        _rot_bone(pb, "mixamorig:LeftForeArm",  (0, 0, -40))
        _rot_bone(pb, "mixamorig:RightArm",     (-24, 12, 52))
        _rot_bone(pb, "mixamorig:RightForeArm", (0, 0, 40))
    else:  # reach
        _rot_bone(pb, "mixamorig:Neck", (-12, 0, 0))
        _rot_bone(pb, "mixamorig:Head", (-12, 0, 6))
        _rot_bone(pb, "mixamorig:LeftArm",      (-10, -18, -74))
        _rot_bone(pb, "mixamorig:LeftForeArm",  (0, 0, -20))
        _rot_bone(pb, "mixamorig:RightArm",     (-10, 18, 74))
        _rot_bone(pb, "mixamorig:RightForeArm", (0, 0, 20))

    pose_hand_grip(pb, "Left", "claw")
    pose_hand_grip(pb, "Right", "claw")
    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_zombie_rafflesia_pose(arm_obj, body_obj, stage="stalk"):
    """Rafflesia Corpse-Flower poses (`stalk`, `windup`, `lash`, `devour`): swaying whip tendrils & snapping bloom."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)
    s = max(0.75, pb["mixamorig:Head"].bone.head_local.z / 1.565)

    if stage == "stalk":
        pb["mixamorig:Hips"].location = Vector((0.0, 0.0, -0.09 * s))
        _rot_bone(pb, "mixamorig:Hips",   (14, -6, 0))
        _rot_bone(pb, "mixamorig:Spine",  (10, 2, -2))
        _rot_bone(pb, "mixamorig:Spine2", (12, 4, -2))
        _rot_bone(pb, "mixamorig:Neck",   (-14, 4, 8))
        _rot_bone(pb, "mixamorig:Head",   (-16, 4, 10))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.16 * s, lift_z=0.0, lat_x_off=0.06 * s, foot_yaw_deg=16.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.14 * s,  lift_z=0.0, lat_x_off=-0.06 * s, foot_yaw_deg=-16.0)
        _rot_bone(pb, "mixamorig:LeftShoulder",  (6, 0, 12))
        _rot_bone(pb, "mixamorig:LeftArm",       (-48, -18, -28))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -28))
        _rot_bone(pb, "mixamorig:RightShoulder", (6, 0, -12))
        _rot_bone(pb, "mixamorig:RightArm",      (-46, 18, 30))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 30))
        pose_hand_grip(pb, "Left", "claw")
        pose_hand_grip(pb, "Right", "claw")
    elif stage == "windup":
        pb["mixamorig:Hips"].location = Vector((0.0, 0.03 * s, -0.08 * s))
        _rot_bone(pb, "mixamorig:Hips",   (-6, 0, 0))
        _rot_bone(pb, "mixamorig:Spine2", (-6, 0, 0))
        _rot_bone(pb, "mixamorig:Head",   (8, 0, -6))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.14 * s, lift_z=0.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.14 * s,  lift_z=0.0)
        _rot_bone(pb, "mixamorig:LeftArm",      (-28, 18, -42))
        _rot_bone(pb, "mixamorig:LeftForeArm",  (0, 0, -48))
        _rot_bone(pb, "mixamorig:RightArm",     (-28, -18, 42))
        _rot_bone(pb, "mixamorig:RightForeArm", (0, 0, 48))
        pose_hand_grip(pb, "Left", "claw")
        pose_hand_grip(pb, "Right", "claw")
    elif stage == "lash":
        pb["mixamorig:Hips"].location = Vector((0.0, -0.07 * s, -0.18 * s))
        _rot_bone(pb, "mixamorig:Hips",   (30, -8, 0))
        _rot_bone(pb, "mixamorig:Spine",  (14, 4, 0))
        _rot_bone(pb, "mixamorig:Spine2", (16, 6, 0))
        _rot_bone(pb, "mixamorig:Neck",   (-26, 0, 4))
        _rot_bone(pb, "mixamorig:Head",   (-26, 0, 6))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.30 * s, lift_z=0.0, lat_x_off=0.05 * s, foot_yaw_deg=14.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.32 * s,  lift_z=0.05 * s, lat_x_off=-0.05 * s, foot_pitch_deg=-22.0, toe_bend_deg=22.0)
        _rot_bone(pb, "mixamorig:LeftShoulder",  (12, -8, -10))
        _rot_bone(pb, "mixamorig:LeftArm",       (-12, -22, -66))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -18))
        _rot_bone(pb, "mixamorig:RightShoulder", (12, 8, 10))
        _rot_bone(pb, "mixamorig:RightArm",      (-12, 22, 66))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 18))
        pose_hand_grip(pb, "Left", "claw")
        pose_hand_grip(pb, "Right", "claw")
    else:  # devour
        pb["mixamorig:Hips"].location = Vector((0.0, -0.03 * s, -0.08 * s))
        _rot_bone(pb, "mixamorig:Hips",   (14, 0, 0))
        _rot_bone(pb, "mixamorig:Spine2", (16, 0, 0))
        _rot_bone(pb, "mixamorig:Neck",   (-10, 0, 0))
        _rot_bone(pb, "mixamorig:Head",   (-12, 0, 0))
        bpy.context.view_layer.update()
        _solve_grounded_leg(arm_obj, "Left",  stride_y=-0.16 * s, lift_z=0.0)
        _solve_grounded_leg(arm_obj, "Right", stride_y=0.16 * s,  lift_z=0.0)
        _rot_bone(pb, "mixamorig:LeftArm",       (-18, -28, -56))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -56))
        _rot_bone(pb, "mixamorig:RightArm",      (-18, 28, 56))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 56))
        pose_hand_grip(pb, "Left", "claw")
        pose_hand_grip(pb, "Right", "claw")

    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)


def apply_survivor_pose(arm_obj, body_obj, style="auto", weapon_id=None, right_grip_rest=None):
    """Apply signature or weapon-matched character pose using Gun-First Dual-Arm IK & grounded stance."""
    wid = weapon_id or arm_obj.get("weapon_id")
    rg = right_grip_rest if right_grip_rest is not None else (
        tuple(arm_obj["right_grip_rest"]) if "right_grip_rest" in arm_obj else None
    )
    if style == "auto" and wid:
        htype = WEAPON_META.get(wid, {}).get("hold_type", "melee")
        style = "bow" if htype in ("bow", "arrow") else ("wrench" if htype == "melee" else htype)

    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones
    reset_pose(pb)

    if style in ("rifle", "pistol"):
        apply_aim_ads_pose(arm_obj, body_obj, weapon_id=wid or ("pistol" if style == "pistol" else "m4"),
                           right_grip_rest=rg, mode="aim")
        bpy.ops.object.mode_set(mode="OBJECT")
        return

    _apply_combat_lower_body(pb, stance="neutral")

    if style == "wrench":
        _rot_bone(pb, "mixamorig:LeftShoulder",  (0, 4, 0))
        _rot_bone(pb, "mixamorig:LeftArm",       (-58, 10, -24))
        _rot_bone(pb, "mixamorig:LeftForeArm",   (0, 0, -42))
        pose_hand_grip(pb, "Left", "relaxed")

        _rot_bone(pb, "mixamorig:RightShoulder", (0, -4, -4))
        _rot_bone(pb, "mixamorig:RightArm",      (-34, -18, 42))
        _rot_bone(pb, "mixamorig:RightForeArm",  (0, 0, 74))
        _rot_bone(pb, "mixamorig:RightHand",     (0, 26, 8))
        pose_hand_grip(pb, "Right", "fist")

    elif style == "bow":
        apply_bow_draw_pose(arm_obj, body_obj, right_grip_rest=rg, draw_factor=1.0)
        bpy.ops.object.mode_set(mode="OBJECT")
        return

    snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)
    bpy.ops.object.mode_set(mode="OBJECT")


# ---------------------------------------------------------------------------
# 14 Production Action Baking (Deform-Only Keyframes, Clean Rest T-Pose After)
# ---------------------------------------------------------------------------
def _keyframe_current_pose(arm_obj, frame):
    """Snapshot deform bone orientations & hip locations at `frame` (`CTRL_*` left unlocked)."""
    bpy.context.view_layer.update()
    for b in arm_obj.pose.bones:
        if not b.bone.use_deform:
            continue
        if b.rotation_mode != "QUATERNION":
            q = b.rotation_euler.to_quaternion()
            b.rotation_mode = "QUATERNION"
            b.rotation_quaternion = q
        b.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        if b.name == "mixamorig:Hips":
            b.keyframe_insert(data_path="location", frame=frame)


def bake_rig_actions(arm_obj, body_obj, weapon_id=None, right_grip_rest=None):
    """Bake 22 universal Actions covering Rifle, Pistol, Bow, Melee, & Zombie sets (`use_fake_user=True`)."""
    set_live_ik(arm_obj, False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    if arm_obj.animation_data is None:
        arm_obj.animation_data_create()

    rg = tuple(arm_obj["right_grip_rest"]) if "right_grip_rest" in arm_obj else right_grip_rest
    arg = tuple(arm_obj["arrow_grip_rest"]) if "arrow_grip_rest" in arm_obj else rg

    def start_action(name):
        act = bpy.data.actions.new(name=name)
        act.use_fake_user = True
        arm_obj.animation_data.action = act
        return act

    # --- A. Rifle / SMG / Shotgun / Sniper / LMG Set (8 Actions) ---
    start_action("Rifle_Idle_Ready")
    for frame, breath, scan in ((1, 0.0, 0.0), (13, 0.5, 6.0), (25, 1.0, 0.0), (37, 0.5, -6.0), (49, 0.0, 0.0)):
        reset_pose(arm_obj.pose.bones)
        pb = arm_obj.pose.bones
        _apply_combat_lower_body(pb, stance="neutral")
        _add_rot_bone(pb, "mixamorig:Spine2", (-2.2 * breath, 0.0, 0.0))
        _add_rot_bone(pb, "mixamorig:Head",   (1.8 * breath, scan, 0.0))
        bpy.context.view_layer.update()
        M_w = _make_rifle_world_matrix(arm_obj, "m4", mode="ready")
        solve_gun_first_weapon_ik(arm_obj, "m4", rg, M_w, style="ready", trigger_discipline=True)
        snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Rifle_Aim_ADS")
    for frame, pitch in ((1, 0.0), (13, 0.9), (25, 0.0)):
        apply_aim_ads_pose(arm_obj, body_obj, weapon_id="m4", right_grip_rest=rg, recoil_pitch_deg=pitch, mode="aim")
        _keyframe_current_pose(arm_obj, frame)

    start_action("Rifle_Shoot_Recoil")
    for frame, pitch, kick in ((1, 0.0, 0.0), (3, 12.5, 0.052), (6, -2.5, 0.004), (9, 1.4, 0.002), (12, 0.0, 0.0)):
        apply_aim_ads_pose(arm_obj, body_obj, weapon_id="m4", right_grip_rest=rg, recoil_pitch_deg=pitch, kick_m=kick, mode="aim")
        _keyframe_current_pose(arm_obj, frame)

    start_action("Rifle_Reload_Tactical")
    for frame, stg in (
        (1, "cant"), (18, "mag_pinch"), (28, "pouch_reach"),
        (40, "mag_insert"), (50, "bolt_slap"), (61, "cant"),
    ):
        apply_reload_pose(arm_obj, body_obj, stage=stg, weapon_id="m4", right_grip_rest=rg)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Rifle_Crouch_Aim")
    for frame in (1, 13, 25):
        apply_crouch_aim_pose(arm_obj, body_obj, weapon_id="m4", right_grip_rest=rg)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Rifle_Walk_Cycle")
    for idx in range(13):
        apply_walk_pose(arm_obj, body_obj, phase=(idx % 12) / 12.0, weapon_id="m4", right_grip_rest=rg)
        _keyframe_current_pose(arm_obj, 1 + idx * 3)

    start_action("Rifle_Run_Cycle")
    for idx in range(13):
        apply_run_pose(arm_obj, body_obj, phase=(idx % 12) / 12.0, weapon_id="m4", right_grip_rest=rg)
        _keyframe_current_pose(arm_obj, 1 + idx * 2)

    start_action("Rifle_Strafe_Right")
    for idx in range(13):
        apply_strafe_pose(arm_obj, body_obj, phase=(idx % 12) / 12.0, weapon_id="m4", right_grip_rest=rg)
        _keyframe_current_pose(arm_obj, 1 + idx * 3)

    # --- B. Pistol / Revolver Set (4 Actions) ---
    start_action("Pistol_Idle_Ready")
    for frame, breath, scan in ((1, 0.0, 0.0), (13, 0.5, 5.0), (25, 1.0, 0.0), (37, 0.5, -5.0), (49, 0.0, 0.0)):
        reset_pose(arm_obj.pose.bones)
        pb = arm_obj.pose.bones
        _apply_combat_lower_body(pb, stance="neutral")
        _add_rot_bone(pb, "mixamorig:Spine2", (-1.8 * breath, 0.0, 0.0))
        _add_rot_bone(pb, "mixamorig:Head",   (1.5 * breath, scan, 0.0))
        bpy.context.view_layer.update()
        M_w = _make_pistol_world_matrix(arm_obj, recoil_pitch_deg=8.0, kick_m=0.04)
        solve_gun_first_weapon_ik(arm_obj, "pistol", rg, M_w, style="aim", trigger_discipline=True)
        snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Pistol_Aim_ADS")
    for frame, pitch in ((1, 0.0), (13, 0.8), (25, 0.0)):
        apply_aim_ads_pose(arm_obj, body_obj, weapon_id="pistol", right_grip_rest=rg, recoil_pitch_deg=pitch, mode="aim")
        _keyframe_current_pose(arm_obj, frame)

    start_action("Pistol_Shoot_Recoil")
    for frame, pitch, kick in ((1, 0.0, 0.0), (3, 15.5, 0.042), (6, -2.5, 0.004), (9, 1.2, 0.002), (12, 0.0, 0.0)):
        apply_aim_ads_pose(arm_obj, body_obj, weapon_id="pistol", right_grip_rest=rg, recoil_pitch_deg=pitch, kick_m=kick, mode="aim")
        _keyframe_current_pose(arm_obj, frame)

    start_action("Pistol_Reload_Tactical")
    for frame, stg in (
        (1, "cant"), (18, "mag_pinch"), (28, "pouch_reach"),
        (40, "mag_insert"), (50, "bolt_slap"), (61, "cant"),
    ):
        apply_reload_pose(arm_obj, body_obj, stage=stg, weapon_id="pistol", right_grip_rest=rg)
        _keyframe_current_pose(arm_obj, frame)

    # --- C. Bow & Arrow Set (3 Actions) ---
    start_action("Bow_Idle_Ready")
    for frame, df in ((1, 0.65), (17, 0.74), (33, 0.65)):
        apply_bow_draw_pose(arm_obj, body_obj, right_grip_rest=arg, draw_factor=df)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Bow_Aim_Draw")
    for frame, df in ((1, 0.65), (9, 0.90), (18, 1.00), (26, 1.00)):
        apply_bow_draw_pose(arm_obj, body_obj, right_grip_rest=arg, draw_factor=df)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Bow_Shoot_Release")
    for frame, df, rel in ((1, 1.00, False), (3, 1.00, True), (10, 0.85, True), (18, 0.65, False)):
        apply_bow_draw_pose(arm_obj, body_obj, right_grip_rest=arg, draw_factor=df, release_follow=rel)
        _keyframe_current_pose(arm_obj, frame)

    # --- D. Melee Set (5 Actions: Guard Idle, Walk, Run, Horizontal Swing, Heavy Cleave) ---
    start_action("Melee_Idle_Ready")
    for idx in range(9):
        apply_melee_idle_pose(arm_obj, body_obj, phase=(idx % 8) / 8.0)
        _keyframe_current_pose(arm_obj, 1 + idx * 6)

    start_action("Melee_Walk_Cycle")
    for idx in range(13):
        apply_walk_pose(arm_obj, body_obj, phase=(idx % 12) / 12.0, weapon_id="melee")
        _keyframe_current_pose(arm_obj, 1 + idx * 3)

    start_action("Melee_Run_Cycle")
    for idx in range(13):
        apply_run_pose(arm_obj, body_obj, phase=(idx % 12) / 12.0, weapon_id="melee")
        _keyframe_current_pose(arm_obj, 1 + idx * 2)

    start_action("Melee_Swing")
    for frame, stg in ((1, "ready"), (6, "windup"), (10, "mid_snap"), (13, "impact"), (19, "follow"), (26, "ready")):
        apply_melee_swing_pose(arm_obj, body_obj, stage=stg)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Melee_Heavy_Slash")
    for frame, stg in ((1, "ready"), (8, "windup_high"), (12, "cleave_mid"), (15, "impact_low"), (22, "follow_low"), (30, "ready")):
        apply_melee_heavy_slash_pose(arm_obj, body_obj, stage=stg)
        _keyframe_current_pose(arm_obj, frame)

    # --- E. Shared Reactions, Look-At & Zombie Set (5 Actions) ---
    start_action("Hit_React")
    for frame, stg in ((1, "recover"), (5, "peak"), (12, "follow"), (19, "recover")):
        apply_hit_react_pose(arm_obj, body_obj, stage=stg)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Head_LookAt")
    for frame, yaw, pitch in (
        (1, 0.0, 0.0), (10, 55.0, 0.0), (20, -55.0, 0.0),
        (30, 0.0, -24.0), (40, 0.0, 22.0), (49, 0.0, 0.0),
    ):
        reset_pose(arm_obj.pose.bones)
        _apply_combat_lower_body(arm_obj.pose.bones, stance="neutral")
        apply_head_look_at(arm_obj.pose.bones, yaw_deg=yaw, pitch_deg=pitch, torso_follow=True)
        snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Zombie_Walk_Shamble")
    for idx in range(13):
        apply_zombie_shamble_pose(arm_obj, body_obj, phase=(idx % 12) / 12.0)
        _keyframe_current_pose(arm_obj, 1 + idx * 3)

    start_action("Zombie_Lunge")
    for frame, stg in ((1, "recover"), (7, "windup"), (11, "launch"), (15, "lunge"), (22, "follow"), (28, "recover")):
        apply_zombie_lunge_pose(arm_obj, body_obj, stage=stg)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Zombie_Bite_Grab")
    for frame, stg in ((1, "reach"), (7, "windup"), (13, "bite"), (20, "follow"), (27, "reach")):
        apply_zombie_bite_pose(arm_obj, body_obj, stage=stg)
        _keyframe_current_pose(arm_obj, frame)

    arm_obj.animation_data.action = None
    reset_pose(arm_obj.pose.bones)
    bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode="OBJECT")


def bake_zombie_actions(arm_obj, body_obj):
    """Bake 13 dedicated Zombie & Skill Actions (`use_fake_user=True`) and leave arm_obj in rest T-pose."""
    set_live_ik(arm_obj, False)
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    if arm_obj.animation_data is None:
        arm_obj.animation_data_create()

    def start_action(name):
        act = bpy.data.actions.new(name=name)
        act.use_fake_user = True
        arm_obj.animation_data.action = act
        return act

    start_action("Zombie_Idle_Sway")
    for idx in range(13):
        apply_zombie_idle_pose(arm_obj, body_obj, phase=(idx % 12) / 12.0)
        _keyframe_current_pose(arm_obj, 1 + idx * 4)

    start_action("Zombie_Walk_Shamble")
    for idx in range(13):
        apply_zombie_shamble_pose(arm_obj, body_obj, phase=(idx % 12) / 12.0)
        _keyframe_current_pose(arm_obj, 1 + idx * 3)

    start_action("Zombie_Run_Feral")
    for idx in range(13):
        apply_zombie_run_pose(arm_obj, body_obj, phase=(idx % 12) / 12.0)
        _keyframe_current_pose(arm_obj, 1 + idx * 2)

    start_action("Zombie_Attack_Swipe")
    for frame, stg in ((1, "recover"), (6, "windup"), (11, "impact"), (17, "follow"), (24, "recover")):
        apply_zombie_swipe_pose(arm_obj, body_obj, stage=stg)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Zombie_Lunge")
    for frame, stg in ((1, "recover"), (7, "windup"), (11, "launch"), (15, "lunge"), (22, "follow"), (28, "recover")):
        apply_zombie_lunge_pose(arm_obj, body_obj, stage=stg)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Zombie_Bite_Grab")
    for frame, stg in ((1, "reach"), (7, "windup"), (13, "bite"), (20, "follow"), (27, "reach")):
        apply_zombie_bite_pose(arm_obj, body_obj, stage=stg)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Zombie_Hit_React")
    for frame, stg in ((1, "recover"), (5, "peak"), (12, "follow"), (19, "recover")):
        apply_hit_react_pose(arm_obj, body_obj, stage=stg)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Zombie_Death_Fall")
    for frame, stg in ((1, "stagger"), (8, "knees"), (16, "fall"), (26, "prone")):
        apply_zombie_death_pose(arm_obj, body_obj, stage=stg)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Skill_Sonic_Shriek")
    for frame, stg in ((1, "recover"), (7, "inhale"), (14, "peak"), (23, "follow"), (32, "recover")):
        apply_zombie_shriek_pose(arm_obj, body_obj, stage=stg)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Skill_Acid_Spit")
    for frame, stg in ((1, "recover"), (7, "charge"), (13, "spit"), (21, "follow"), (29, "recover")):
        apply_zombie_spit_pose(arm_obj, body_obj, stage=stg)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Skill_Volatile_Detonate")
    for frame, stg in ((1, "idle"), (8, "swell"), (14, "burst"), (24, "collapse")):
        apply_zombie_detonate_pose(arm_obj, body_obj, stage=stg)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Skill_Ground_Slam")
    for frame, stg in ((1, "recover"), (8, "windup"), (14, "impact"), (22, "rebound"), (32, "recover")):
        apply_zombie_slam_pose(arm_obj, body_obj, stage=stg)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Skill_Echo_Click_Dash")
    for frame, stg in ((1, "listen"), (8, "crouch"), (14, "dash"), (22, "grab"), (32, "listen")):
        apply_zombie_echo_click_pose(arm_obj, body_obj, stage=stg)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Skill_Corpse_Bloom_Lash")
    for frame, stg in ((1, "stalk"), (8, "windup"), (15, "lash"), (23, "devour"), (32, "stalk")):
        apply_zombie_rafflesia_pose(arm_obj, body_obj, stage=stg)
        _keyframe_current_pose(arm_obj, frame)

    start_action("Head_LookAt")
    for frame, yaw, pitch in (
        (1, 0.0, 0.0), (10, 55.0, 0.0), (20, -55.0, 0.0),
        (30, 0.0, -24.0), (40, 0.0, 22.0), (49, 0.0, 0.0),
    ):
        reset_pose(arm_obj.pose.bones)
        _apply_combat_lower_body(arm_obj.pose.bones, stance="neutral")
        apply_head_look_at(arm_obj.pose.bones, yaw_deg=yaw, pitch_deg=pitch, torso_follow=True)
        snap_feet_to_floor(arm_obj, body_obj, floor_z=0.0)
        _keyframe_current_pose(arm_obj, frame)

    arm_obj.animation_data.action = None
    reset_pose(arm_obj.pose.bones)
    bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode="OBJECT")
