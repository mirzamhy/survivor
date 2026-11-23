"""Detachable gear and survival weapons for the Low-Poly Survivor.

Built as separate mesh objects positioned accurately in T-pose world space:
  - Gear_Backpack : survival pack, sleeping roll, shoulder straps (attached to Spine2)
  - Weapon_Bat    : spiked baseball bat held in Right Hand (-X) (attached to RightHand)
  - Weapon_Crowbar: red steel crowbar strapped diagonally on backpack (attached to Spine2)
"""
import math
import bmesh
from mesh_utils import add_box, add_cone, add_cylinder, finalize_mesh


def build_backpack(materials, idx_map, collection=None):
    """Build survival backpack + top sleeping roll + shoulder straps."""
    bm = bmesh.new()

    # Main backpack body seated flush behind upper torso (Y = +0.122 to +0.286, Z = 1.02 to 1.44)
    add_box(
        bm,
        center=(0.0, 0.204, 1.235),
        size=(0.275, 0.165, 0.415),
        bevel=0.016,
        taper_top=(0.90, 0.92),
        mat_idx=idx_map["Mat_Backpack"],
    )

    # Top flap lid
    add_box(
        bm,
        center=(0.0, 0.201, 1.425),
        size=(0.258, 0.175, 0.068),
        rot=(-0.10, 0.0, 0.0),
        bevel=0.0,
        mat_idx=idx_map["Mat_JacketTrim"],
    )

    # Rear zippered lower pocket (back face at Y = 0.322)
    add_box(
        bm,
        center=(0.0, 0.294, 1.155),
        size=(0.205, 0.056, 0.165),
        bevel=0.0,
        mat_idx=idx_map["Mat_JacketTrim"],
    )

    # Two side utility pouches
    for sx in (1.0, -1.0):
        add_box(
            bm,
            center=(sx * 0.154, 0.208, 1.185),
            size=(0.050, 0.095, 0.175),
            bevel=0.0,
            mat_idx=idx_map["Mat_Backpack"],
        )

    # Rolled sleeping mat strapped horizontally on top (Z = 1.49, back at Y = 0.268)
    add_cylinder(
        bm,
        p0=(-0.165, 0.218, 1.495),
        p1=(0.165, 0.218, 1.495),
        r0=0.050,
        r1=0.050,
        segments=6,
        mat_idx=idx_map["Mat_SleepingRoll"],
    )
    # Straps holding sleeping roll
    for sx in (1.0, -1.0):
        add_box(
            bm,
            center=(sx * 0.095, 0.218, 1.495),
            size=(0.022, 0.110, 0.110),
            bevel=0.0,
            mat_idx=idx_map["Mat_BeltLeather"],
        )

    # Shoulder straps hugging the jacket shoulders cleanly
    for sx in (1.0, -1.0):
        # Top shoulder arch
        add_box(
            bm,
            center=(sx * 0.102, 0.052, 1.472),
            size=(0.044, 0.185, 0.024),
            rot=(-0.12, 0.0, sx * 0.08),
            bevel=0.0,
            mat_idx=idx_map["Mat_BeltLeather"],
        )
        # Front vertical chest strap
        add_box(
            bm,
            center=(sx * 0.106, -0.072, 1.325),
            size=(0.042, 0.022, 0.265),
            rot=(0.18, 0.0, sx * 0.12),
            bevel=0.0,
            mat_idx=idx_map["Mat_BeltLeather"],
        )
        # Lower side return strap back to pack along waist/ribs
        add_box(
            bm,
            center=(sx * 0.168, 0.062, 1.135),
            size=(0.022, 0.210, 0.032),
            rot=(0.35, 0.0, sx * -0.14),
            bevel=0.0,
            mat_idx=idx_map["Mat_BeltLeather"],
        )

    # Chest sternum strap + metallic buckle
    add_box(
        bm,
        center=(0.0, -0.092, 1.295),
        size=(0.205, 0.022, 0.024),
        bevel=0.0,
        mat_idx=idx_map["Mat_BeltLeather"],
    )
    add_box(
        bm,
        center=(0.0, -0.102, 1.295),
        size=(0.036, 0.016, 0.032),
        bevel=0.0,
        mat_idx=idx_map["Mat_MetalDark"],
    )

    return finalize_mesh("Gear_Backpack", bm, materials, collection=collection)


def build_spiked_bat(materials, idx_map, collection=None):
    """Build spiked survival baseball bat gripped in Right Hand (-X), pointing forward (-Y)."""
    bm = bmesh.new()

    # Right palm grip center in T-pose:
    gx, gy, gz = -0.775, 0.005, 1.398

    # Pommel knob behind hand (+Y)
    add_cylinder(
        bm,
        p0=(gx, gy + 0.105, gz),
        p1=(gx, gy + 0.078, gz),
        r0=0.024,
        r1=0.016,
        segments=6,
        mat_idx=idx_map["Mat_MetalDark"],
    )
    # Grip-tape handle inside palm
    add_cylinder(
        bm,
        p0=(gx, gy + 0.078, gz),
        p1=(gx, gy - 0.145, gz),
        r0=0.016,
        r1=0.020,
        segments=6,
        mat_idx=idx_map["Mat_GripTape"],
    )
    # Tapered wooden barrel extending forward (-Y)
    add_cylinder(
        bm,
        p0=(gx, gy - 0.145, gz),
        p1=(gx, gy - 0.440, gz),
        r0=0.020,
        r1=0.038,
        segments=6,
        mat_idx=idx_map["Mat_WoodBat"],
    )
    add_cylinder(
        bm,
        p0=(gx, gy - 0.440, gz),
        p1=(gx, gy - 0.655, gz),
        r0=0.038,
        r1=0.034,
        segments=6,
        mat_idx=idx_map["Mat_WoodBat"],
    )
    # Metal reinforcing band near upper barrel
    add_cylinder(
        bm,
        p0=(gx, gy - 0.475, gz),
        p1=(gx, gy - 0.565, gz),
        r0=0.041,
        r1=0.040,
        segments=6,
        mat_idx=idx_map["Mat_MetalDark"],
    )

    # 8 jagged iron spikes piercing the barrel
    spike_specs = [
        (-0.46, 0.0),
        (-0.49, 1.57),
        (-0.52, 3.14),
        (-0.55, 4.71),
        (-0.58, 0.78),
        (-0.61, 2.35),
        (-0.60, 3.92),
        (-0.53, 5.49),
    ]
    for dy, ang in spike_specs:
        nx = math.cos(ang)
        nz = math.sin(ang)
        base = (gx + nx * 0.032, gy + dy, gz + nz * 0.032)
        tip = (gx + nx * 0.092, gy + dy - 0.008, gz + nz * 0.092)
        add_cone(bm, base=base, tip=tip, r_base=0.0085, segments=5, mat_idx=idx_map["Mat_MetalRust"])

    return finalize_mesh("Weapon_Bat", bm, materials, collection=collection)


def build_crowbar(materials, idx_map, collection=None):
    """Build red steel crowbar cleanly mounted behind backpack pocket with zero clipping."""
    bm = bmesh.new()

    # Diagonal line cleanly behind backpack & rear pocket (Y_pocket_max = 0.322, shaft at Y = 0.338..0.346)
    p_bot = (-0.106, 0.346, 1.070)
    p_top = ( 0.106, 0.338, 1.455)

    # Main hex-bar shaft
    add_cylinder(bm, p_bot, p_top, r0=0.012, r1=0.012, segments=6, mat_idx=idx_map["Mat_MetalRust"])

    # Lower chisel end
    add_box(
        bm,
        center=(-0.118, 0.348, 1.046),
        size=(0.026, 0.014, 0.055),
        rot=(0.0, 0.52, 0.0),
        bevel=0.0,
        taper_top=(0.8, 0.8),
        mat_idx=idx_map["Mat_MetalDark"],
    )

    # Top curved claw hook clear of sleeping roll (Y = 0.312..0.338 vs roll Y = 0.268)
    add_cylinder(
        bm,
        p0=p_top,
        p1=(0.148, 0.336, 1.498),
        r0=0.012,
        r1=0.011,
        segments=6,
        mat_idx=idx_map["Mat_MetalRust"],
    )
    add_box(
        bm,
        center=(0.164, 0.312, 1.490),
        size=(0.042, 0.022, 0.016),
        rot=(0.0, 0.65, -0.35),
        bevel=0.0,
        mat_idx=idx_map["Mat_MetalDark"],
    )

    # Dual mounting leather straps bridging from rear pocket/pack cleanly around crowbar shaft
    for t in (0.32, 0.72):
        sx = p_bot[0] + t * (p_top[0] - p_bot[0])
        sy = p_bot[1] + t * (p_top[1] - p_bot[1]) - 0.014
        sz = p_bot[2] + t * (p_top[2] - p_bot[2])
        add_box(
            bm,
            center=(sx, sy, sz),
            size=(0.046, 0.048, 0.024),
            rot=(0.0, -0.50, 0.0),
            bevel=0.0,
            mat_idx=idx_map["Mat_BeltLeather"],
        )

    return finalize_mesh("Weapon_Crowbar", bm, materials, collection=collection)
