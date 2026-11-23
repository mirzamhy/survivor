"""Live interactive Blender Control Rig (`Controls` Bone Collection) with IK, Reverse-Foot Roll,
Clavicle auto-follow, ForeArmTwist constraint, Head Look-At, and `use_live_ik` driver switch.
"""
import math
import bpy
from mathutils import Vector


def _bind_ik_driver(constraint, arm_obj, weight=1.0):
    """Drive `constraint.influence` from `arm_obj['use_live_ik'] * weight`."""
    fcurve = constraint.driver_add("influence")
    drv = fcurve.driver
    drv.type = "SCRIPTED"
    var = drv.variables.new()
    var.name = "ik"
    var.type = "SINGLE_PROP"
    tgt = var.targets[0]
    tgt.id_type = "OBJECT"
    tgt.id = arm_obj
    tgt.data_path = '["use_live_ik"]'
    drv.expression = f"ik * {weight:.4f}"


def set_live_ik(arm_obj, enabled=False):
    """Toggle interactive Control Rig constraints on (1.0) or off (0.0 for Actions & GLB)."""
    arm_obj["use_live_ik"] = 1.0 if enabled else 0.0
    bpy.context.view_layer.update()


def build_control_rig(arm_obj, proportions):
    """Add non-deforming `CTRL_*` bones & driven constraints to an existing Mixamo armature."""
    P = proportions
    s = P.get("scale", 1.0)
    V = Vector
    fwd = V((0.0, -1.0, 0.0))
    up = V((0.0, 0.0, 1.0))

    arm_obj["use_live_ik"] = 0.0
    id_props = arm_obj.id_properties_ui("use_live_ik")
    id_props.update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0,
                    description="Blend 0=Baked Actions/GLB, 1=Interactive Control Rig IK")

    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_obj.data.edit_bones
    bc_ctrl = arm_obj.data.collections.get("Controls") or arm_obj.data.collections.new("Controls")

    def add_ctrl(name, head, tail, parent_name=None, align_bone=None, roll_axis=up):
        b = eb.new(name)
        b.head = V(head)
        b.tail = V(tail)
        b.use_deform = False
        b.use_connect = False
        bc_ctrl.assign(b)
        if parent_name:
            b.parent = eb[parent_name]
        if align_bone and align_bone in eb:
            b.matrix = b.matrix  # keep translation/dir, copy exact roll from target deform bone
            ref = eb[align_bone]
            b.tail = b.head + (ref.tail - ref.head)
            b.roll = ref.roll
        else:
            b.align_roll(roll_axis)
        return b

    # Master Root, Weapon Master & Look-At target
    add_ctrl("CTRL_Root",   (0.0, 0.0, 0.0),                  (0.0, -0.25 * s, 0.0), roll_axis=up)
    add_ctrl("CTRL_Weapon", (0.0, -0.32 * s, 1.35 * s),       (0.0, -0.58 * s, 1.35 * s), "CTRL_Root", roll_axis=up)
    add_ctrl("CTRL_LookAt", (0.0, -1.60 * s, P["head"][2]),   (0.0, -1.78 * s, P["head"][2]), "CTRL_Root", roll_axis=up)

    for side_key, side_name, sx in (("L", "Left", 1.0), ("R", "Right", -1.0)):
        def M(pt):
            return V((sx * pt[0], pt[1], pt[2]))

        hand_def = f"mixamorig:{side_name}Hand"
        foot_def = f"mixamorig:{side_name}Foot"
        toe_def = f"mixamorig:{side_name}ToeBase"

        add_ctrl(f"CTRL_Hand_IK_{side_key}", M(P["wrist"]), M(P["hand_end"]), "CTRL_Root", align_bone=hand_def)
        add_ctrl(f"CTRL_Pole_Elbow_{side_key}",
                 M(P["elbow"]) + V((0.0, 0.42 * s, 0.0)),
                 M(P["elbow"]) + V((0.0, 0.56 * s, 0.0)),
                 "CTRL_Root", roll_axis=up)

        # Reverse-Foot Roll hierarchy (Root -> Foot_IK -> Heel_Roll -> Toe_Roll -> Ball_Pivot -> Ankle_Target)
        hx = sx * P["hip"][0]
        add_ctrl(f"CTRL_Foot_IK_{side_key}", (hx, 0.0, 0.0), (hx, -0.22 * s, 0.0), "CTRL_Root", roll_axis=up)
        add_ctrl(f"CTRL_Heel_Roll_{side_key}", (hx, 0.068 * s, 0.0), (hx, 0.068 * s, 0.08 * s),
                 f"CTRL_Foot_IK_{side_key}", roll_axis=fwd)
        add_ctrl(f"CTRL_Toe_Roll_{side_key}", (hx, -0.158 * s, 0.0), (hx, -0.158 * s, 0.07 * s),
                 f"CTRL_Heel_Roll_{side_key}", align_bone=toe_def)
        add_ctrl(f"CTRL_Ball_Pivot_{side_key}", M(P["ball"]), M(P["ball"]) + V((0.0, 0.08 * s, 0.0)),
                 f"CTRL_Toe_Roll_{side_key}", align_bone=foot_def)
        add_ctrl(f"CTRL_Ankle_Target_{side_key}", M(P["ankle"]), M(P["ankle"]) + V((0.0, -0.08 * s, 0.0)),
                 f"CTRL_Ball_Pivot_{side_key}", roll_axis=up)
        add_ctrl(f"CTRL_Pole_Knee_{side_key}",
                 M(P["knee"]) + V((0.0, -0.45 * s, 0.0)),
                 M(P["knee"]) + V((0.0, -0.59 * s, 0.0)),
                 "CTRL_Root", roll_axis=up)

    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones

    # Wire live constraints driven by `use_live_ik`
    for side_key, side_name in (("L", "Left"), ("R", "Right")):
        # Arm IK (Pole angle calibrated below at runtime so rest T-pose has zero twist)
        b_arm = pb[f"mixamorig:{side_name}Arm"]
        b_fore = pb[f"mixamorig:{side_name}ForeArm"]
        ik_arm = b_fore.constraints.new("IK")
        ik_arm.name = "IK_Hand"
        ik_arm.target = arm_obj
        ik_arm.subtarget = f"CTRL_Hand_IK_{side_key}"
        ik_arm.pole_target = arm_obj
        ik_arm.pole_subtarget = f"CTRL_Pole_Elbow_{side_key}"
        ik_arm.chain_count = 2
        ik_arm.pole_angle = math.pi if side_key == "L" else 0.0
        _bind_ik_driver(ik_arm, arm_obj, 1.0)

        b_hand = pb[f"mixamorig:{side_name}Hand"]
        c_hrot = b_hand.constraints.new("COPY_ROTATION")
        c_hrot.name = "Copy_Hand_Rot"
        c_hrot.target = arm_obj
        c_hrot.subtarget = f"CTRL_Hand_IK_{side_key}"
        c_hrot.target_space = "WORLD"
        c_hrot.owner_space = "WORLD"
        _bind_ik_driver(c_hrot, arm_obj, 1.0)

        b_tw = pb.get(f"mixamorig:{side_name}ForeArmTwist")
        if b_tw is not None:
            c_tw = b_tw.constraints.new("COPY_ROTATION")
            c_tw.name = "Copy_ForeArm_Twist"
            c_tw.target = arm_obj
            c_tw.subtarget = f"mixamorig:{side_name}Hand"
            c_tw.use_x = False
            c_tw.use_y = True
            c_tw.use_z = False
            c_tw.target_space = "LOCAL"
            c_tw.owner_space = "LOCAL"
            _bind_ik_driver(c_tw, arm_obj, 0.55)

        b_sh = pb[f"mixamorig:{side_name}Shoulder"]
        c_sh = b_sh.constraints.new("DAMPED_TRACK")
        c_sh.name = "Clavicle_Follow"
        c_sh.target = arm_obj
        c_sh.subtarget = f"CTRL_Hand_IK_{side_key}"
        c_sh.track_axis = "TRACK_Y"
        _bind_ik_driver(c_sh, arm_obj, 0.22)

        # Leg IK + Reverse-Foot Copy Rotation
        b_leg = pb[f"mixamorig:{side_name}Leg"]
        ik_leg = b_leg.constraints.new("IK")
        ik_leg.name = "IK_Foot"
        ik_leg.target = arm_obj
        ik_leg.subtarget = f"CTRL_Ankle_Target_{side_key}"
        ik_leg.pole_target = arm_obj
        ik_leg.pole_subtarget = f"CTRL_Pole_Knee_{side_key}"
        ik_leg.chain_count = 2
        ik_leg.pole_angle = -math.pi * 0.5
        _bind_ik_driver(ik_leg, arm_obj, 1.0)

        c_lim_k = b_leg.constraints.new("LIMIT_ROTATION")
        c_lim_k.name = "Limit_Knee"
        c_lim_k.owner_space = "LOCAL"
        c_lim_k.use_limit_x = True
        c_lim_k.min_x = math.radians(-135.0)
        c_lim_k.max_x = 0.0
        c_lim_k.use_limit_y = True
        c_lim_k.min_y = math.radians(-5.0)
        c_lim_k.max_y = math.radians(5.0)
        c_lim_k.use_limit_z = True
        c_lim_k.min_z = math.radians(-5.0)
        c_lim_k.max_z = math.radians(5.0)
        c_lim_k.use_transform_limit = False
        _bind_ik_driver(c_lim_k, arm_obj, 1.0)

        b_foot = pb[f"mixamorig:{side_name}Foot"]
        c_foot = b_foot.constraints.new("COPY_ROTATION")
        c_foot.name = "Copy_Foot_Roll"
        c_foot.target = arm_obj
        c_foot.subtarget = f"CTRL_Ball_Pivot_{side_key}"
        c_foot.target_space = "WORLD"
        c_foot.owner_space = "WORLD"
        _bind_ik_driver(c_foot, arm_obj, 1.0)

        b_toe = pb[f"mixamorig:{side_name}ToeBase"]
        c_toe = b_toe.constraints.new("COPY_ROTATION")
        c_toe.name = "Copy_Toe_Roll"
        c_toe.target = arm_obj
        c_toe.subtarget = f"CTRL_Toe_Roll_{side_key}"
        c_toe.target_space = "WORLD"
        c_toe.owner_space = "WORLD"
        _bind_ik_driver(c_toe, arm_obj, 1.0)

    # Head Look-At Damped Track (14% Spine2 -> 38% Neck -> 62% Head) + Limits
    for bname, w in (("mixamorig:Spine2", 0.14), ("mixamorig:Neck", 0.38), ("mixamorig:Head", 0.62)):
        bn = pb[bname]
        dt = bn.constraints.new("DAMPED_TRACK")
        dt.name = "Track_LookAt"
        dt.target = arm_obj
        dt.subtarget = "CTRL_LookAt"
        dt.track_axis = "TRACK_Z"
        _bind_ik_driver(dt, arm_obj, w)

    for bname in ("mixamorig:Neck", "mixamorig:Head"):
        bn = pb[bname]
        lim = bn.constraints.new("LIMIT_ROTATION")
        lim.name = "Limit_Head_Turn"
        lim.owner_space = "LOCAL"
        lim.use_limit_x = True
        lim.min_x = math.radians(-25.0)
        lim.max_x = math.radians(25.0)
        lim.use_limit_y = True
        lim.min_y = math.radians(-45.0)
        lim.max_y = math.radians(45.0)
        lim.use_limit_z = True
        lim.min_z = math.radians(-20.0)
        lim.max_z = math.radians(20.0)
        _bind_ik_driver(lim, arm_obj, 1.0)

    # Auto-calibrate exact IK pole_angle so rest pose has zero twist when use_live_ik=1.0
    set_live_ik(arm_obj, True)
    candidates = (-math.pi, -math.pi * 0.5, 0.0, math.pi * 0.5, math.pi)
    for side_key, side_name in (("L", "Left"), ("R", "Right")):
        for limb_lo, pole_ref, cname in (
            (f"mixamorig:{side_name}ForeArm", f"mixamorig:{side_name}Arm", "IK_Hand"),
            (f"mixamorig:{side_name}Leg",     f"mixamorig:{side_name}UpLeg", "IK_Foot"),
        ):
            con = pb[limb_lo].constraints[cname]
            rest_head = pb[limb_lo].bone.head_local
            best_ang = con.pole_angle
            best_err = 1e9
            for ang in candidates:
                con.pole_angle = ang
                bpy.context.view_layer.update()
                err = (pb[limb_lo].head - rest_head).length
                if err < best_err:
                    best_err = err
                    best_ang = ang
            con.pole_angle = best_ang

    set_live_ik(arm_obj, False)
    bpy.ops.object.mode_set(mode="OBJECT")


def verify_live_ik(arm_obj):
    """Verify live Control Rig rest alignment (< 1.5 cm drift) and interactive response."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones

    # 1. Zero-offset rest drift check with live IK enabled
    set_live_ik(arm_obj, True)
    for cname in ("mixamorig:LeftForeArm", "mixamorig:RightForeArm", "mixamorig:LeftLeg", "mixamorig:RightLeg"):
        b = pb[cname]
        drift = (b.head - b.bone.head_local).length
        if drift > 0.015:
            raise RuntimeError(f"Control rig rest drift too high on {cname}: {drift:.4f}m")

    # 2. Functional test: move Left Hand IK & Head LookAt and verify deform bones follow
    ctrl_l = pb["CTRL_Hand_IK_L"]
    ctrl_l.location = Vector((0.0, -0.15, 0.0))
    ctrl_look = pb["CTRL_LookAt"]
    ctrl_look.location = Vector((0.40, 0.0, 0.0))
    bpy.context.view_layer.update()

    hand_delta = (pb["mixamorig:LeftHand"].head - pb["mixamorig:LeftHand"].bone.head_local).length
    head_eul = pb["mixamorig:Head"].matrix.to_euler()
    head_rot = abs(head_eul.x) + abs(head_eul.y) + abs(head_eul.z)
    if hand_delta < 0.08 or head_rot < 0.03:
        raise RuntimeError(f"Control rig did not drive bones (hand_delta={hand_delta:.3f}, head_rot={head_rot:.3f})")

    # 3. Reset controls and switch back to baked Action mode (use_live_ik=0.0)
    ctrl_l.location = Vector((0.0, 0.0, 0.0))
    ctrl_look.location = Vector((0.0, 0.0, 0.0))
    set_live_ik(arm_obj, False)
    bpy.ops.object.mode_set(mode="OBJECT")
