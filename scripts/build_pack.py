"""Batch 1 master builder: builds 7 canonical weapons and 5 rigged Playable Survivors."""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import bpy

from build_survivor import (
    clear_scene,
    export_glb,
    make_collection,
    mesh_centroid,
    verify_body_weights,
    verify_glb_roundtrip,
    world_bounds,
)
from palette import create_materials
from rig_controls import verify_live_ik
from rig_mechanics import bake_rig_actions
from survivors import SURVIVOR_BUILDERS
from weapon_vfx import ALL_VFX_BUILDERS
from weapons import ALL_WEAPON_BUILDERS, WEAPON_META


def assert_pure_tris(mesh_objs):
    for m in mesh_objs:
        non_tris = sum(1 for p in m.data.polygons if len(p.vertices) != 3)
        if non_tris:
            raise RuntimeError(f"Non-triangle faces on {m.name}: {non_tris}")


def build_all_weapons(weapons_dir):
    os.makedirs(weapons_dir, exist_ok=True)
    print("=" * 64)
    print(f"BUILDING {len(ALL_WEAPON_BUILDERS)} CANONICAL WEAPONS (grip=(0,0,0), muzzle=+Z)")
    for wid, builder, expected_z in ALL_WEAPON_BUILDERS:
        clear_scene()
        materials, idx_map = create_materials()
        obj, tris = builder(materials, idx_map)
        assert_pure_tris([obj])
        mins, maxs = world_bounds([obj])
        z_len = maxs[2] - mins[2]
        y_len = maxs[1] - mins[1]

        meta = WEAPON_META[wid]
        muzzle_sock = bpy.data.objects.new("MuzzleSocket", None)
        muzzle_sock.empty_display_type = "ARROWS"
        muzzle_sock.empty_display_size = 0.04
        bpy.context.scene.collection.objects.link(muzzle_sock)
        muzzle_sock.parent = obj
        muzzle_sock.location = meta["muzzle"]

        if meta.get("ejection") is not None:
            ej_sock = bpy.data.objects.new("EjectSocket", None)
            ej_sock.empty_display_type = "ARROWS"
            ej_sock.empty_display_size = 0.03
            bpy.context.scene.collection.objects.link(ej_sock)
            ej_sock.parent = obj
            ej_sock.location = meta["ejection"]

        out_glb = os.path.join(weapons_dir, f"weapon_{wid}.glb")
        export_glb(out_glb, selected_only=False)
        print(f"  weapon_{wid:<14s} : {tris:4d} tris | Z={z_len:.3f}m (spec~{expected_z:.3f}m) | Y={y_len:.3f}m")


def build_all_vfx(vfx_dir):
    os.makedirs(vfx_dir, exist_ok=True)
    print("=" * 64)
    print(f"BUILDING {len(ALL_VFX_BUILDERS)} MODULAR WEAPON VFX ASSETS (origin=(0,0,0), fwd=+Z)")
    for vid, builder in ALL_VFX_BUILDERS:
        clear_scene()
        materials, idx_map = create_materials()
        obj, tris = builder(materials, idx_map)
        assert_pure_tris([obj])
        mins, maxs = world_bounds([obj])
        span_z = maxs[2] - mins[2]
        span_x = maxs[0] - mins[0]
        out_glb = os.path.join(vfx_dir, f"vfx_{vid}.glb")
        export_glb(out_glb, selected_only=False)
        print(f"  vfx_{vid:<18s} : {tris:4d} tris | X={span_x:.3f}m | Z={span_z:.3f}m")


def build_all_survivors(surv_dir):
    unarmed_dir = os.path.join(surv_dir, "unarmed")
    os.makedirs(surv_dir, exist_ok=True)
    os.makedirs(unarmed_dir, exist_ok=True)
    print("=" * 64)
    print(f"BUILDING {len(SURVIVOR_BUILDERS)} RIGGED PLAYABLE SURVIVORS (5 Male + 5 Female Pairs)")
    for name, builder in SURVIVOR_BUILDERS:
        clear_scene()
        col_char = make_collection("Character")
        col_gear = make_collection("Gear")
        col_rig = make_collection("Rig")

        materials, idx_map = create_materials()
        body_obj, body_tris, arm_obj, gear_items = builder(materials, idx_map, col_char, col_gear, col_rig)

        all_meshes = [body_obj] + [g for g, _ in gear_items]
        assert_pure_tris(all_meshes)
        verify_body_weights(body_obj)
        verify_live_ik(arm_obj)

        wid = arm_obj.get("weapon_id")
        rg = tuple(arm_obj["right_grip_rest"]) if "right_grip_rest" in arm_obj else None
        bake_rig_actions(arm_obj, body_obj, weapon_id=wid, right_grip_rest=rg)

        b_mins, b_maxs = world_bounds([body_obj])
        total_gear = sum(t for _, t in gear_items)
        expected_centroids = {m.name: mesh_centroid(m) for m in all_meshes}
        expected_sockets = {
            sn: tuple(bpy.data.objects[sn].matrix_world.to_translation())
            for sn in ("WeaponSocket_R", "WeaponSocket_L")
            if sn in bpy.data.objects
        }

        blend_path = os.path.join(surv_dir, f"{name}.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)

        glb_path = os.path.join(surv_dir, f"{name}.glb")
        export_glb(glb_path, selected_only=False)

        # Export clean unarmed base GLB (body + non-weapon gear + WeaponSocket_R/L, no held _Weapon_)
        unarmed_meshes = [body_obj] + [g for g, _ in gear_items if "_Weapon_" not in g.name]
        unarmed_centroids = {m.name: expected_centroids[m.name] for m in unarmed_meshes}
        bpy.ops.object.select_all(action="DESELECT")
        arm_obj.select_set(True)
        for m in unarmed_meshes:
            m.select_set(True)
        for sn in expected_sockets:
            bpy.data.objects[sn].select_set(True)
        bpy.context.view_layer.objects.active = arm_obj
        unarmed_glb = os.path.join(unarmed_dir, f"{name}_unarmed.glb")
        export_glb(unarmed_glb, selected_only=True)

        n_deform = sum(1 for b in arm_obj.data.bones if b.use_deform)
        n_ctrl = sum(1 for b in arm_obj.data.bones if not b.use_deform)
        n_actions = sum(1 for a in bpy.data.actions if a.use_fake_user)
        print(
            f"  {name.upper():<6s} : body={body_tris:4d} tris, gear={total_gear:4d} tris "
            f"(total={body_tris + total_gear:4d}) | H={b_maxs[2] - b_mins[2]:.3f}m | "
            f"deform={n_deform}, ctrl={n_ctrl} | actions={n_actions}"
        )

        # Round-trip glTF checks (equipped + unarmed sockets)
        verify_glb_roundtrip(glb_path, expected_centroids, expected_sockets=expected_sockets)
        verify_glb_roundtrip(unarmed_glb, unarmed_centroids, expected_sockets=expected_sockets)


def main():
    vfx_only = "--vfx-only" in sys.argv
    out_root = os.path.join(PROJECT_DIR, "output")
    build_all_weapons(os.path.join(out_root, "weapons"))
    build_all_vfx(os.path.join(out_root, "vfx"))
    if not vfx_only:
        build_all_survivors(os.path.join(out_root, "survivors"))
    print("=" * 64)
    print("VFX + WEAPONS BUILD COMPLETE" if vfx_only else "BATCH 1 PACK BUILD COMPLETE")


if __name__ == "__main__":
    main()
