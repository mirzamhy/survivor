"""Re-export existing Survivor, Zombie & Mutant .blend files to .glb with active QUATERNION baked Actions."""
import glob
import json
import os
import struct
import sys

import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import bpy

from build_survivor import export_glb


def _reset_armature_rest_pose(arm_obj):
    if arm_obj.animation_data is not None:
        arm_obj.animation_data.action = None
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm_obj.pose.bones:
        # Must match rotation_quaternion F-curves written by rig_mechanics & rig_creature!
        pb.rotation_mode = "QUATERNION"
        pb.location = (0.0, 0.0, 0.0)
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)
        for c in pb.constraints:
            c.mute = True
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()


def _inspect_glb_header(glb_path):
    with open(glb_path, "rb") as f:
        raw = f.read()
    if len(raw) < 20:
        return [], 0, 0
    jlen = struct.unpack("<I", raw[12:16])[0]
    g = json.loads(raw[20:20 + jlen].decode("utf-8"))
    bin_off = 20 + jlen + 8

    anims = []
    clips_with_active_rot = 0
    for anim in g.get("animations", []):
        anims.append(anim.get("name"))
        has_rot = False
        for ch in anim.get("channels", []):
            if ch["target"]["path"] != "rotation":
                continue
            samp = anim["samplers"][ch["sampler"]]
            acc = g["accessors"][samp["output"]]
            bv = g["bufferViews"][acc["bufferView"]]
            off = bin_off + bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
            arr = np.frombuffer(raw[off:off + acc["count"] * 16], dtype=np.float32).reshape(acc["count"], 4)
            # Non-rest or time-varying quaternion rotation
            if float(arr.std(axis=0).max()) > 1e-3 or float(np.abs(arr[:, :3]).max()) > 1e-3:
                has_rot = True
                break
        if has_rot:
            clips_with_active_rot += 1
    n_imgs = len(g.get("images", []))
    return anims, n_imgs, clips_with_active_rot


def _push_actions_to_nla(arm_obj):
    if arm_obj.animation_data is None:
        arm_obj.animation_data_create()
    for tr in list(arm_obj.animation_data.nla_tracks):
        arm_obj.animation_data.nla_tracks.remove(tr)
    for act in sorted(bpy.data.actions, key=lambda a: a.name):
        if not act.use_fake_user:
            continue
        tr = arm_obj.animation_data.nla_tracks.new()
        tr.name = act.name
        st = int(round(act.frame_range[0]))
        strip = tr.strips.new(act.name, st, act)
        strip.name = act.name
    arm_obj.animation_data.action = None


def _export_blend_with_actions(blend_path, glb_path, unarmed_glb_path=None):
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if not arms:
        raise RuntimeError(f"No armature in {blend_path}")
    arm_obj = arms[0]
    _reset_armature_rest_pose(arm_obj)
    _push_actions_to_nla(arm_obj)
    _reset_armature_rest_pose(arm_obj)

    bpy.ops.export_scene.gltf(
        filepath=glb_path,
        export_format="GLB",
        use_selection=False,
        export_apply=False,
        export_yup=True,
        export_normals=True,
        export_texcoords=True,
        export_materials="EXPORT",
        export_skins=True,
        export_all_influences=False,
        export_def_bones=True,
        export_animations=True,
        export_animation_mode="NLA_TRACKS",
        export_anim_slide_to_zero=True,
        export_bake_animation=True,
        export_anim_single_armature=True,
    )
    anims, n_imgs, rot_active = _inspect_glb_header(glb_path)
    if rot_active < len(anims):
        raise RuntimeError(
            f"{os.path.basename(glb_path)}: only {rot_active}/{len(anims)} clips have active bone rotations!"
        )

    if unarmed_glb_path is not None:
        os.makedirs(os.path.dirname(unarmed_glb_path), exist_ok=True)
        bpy.ops.object.select_all(action="DESELECT")
        arm_obj.select_set(True)
        for obj in bpy.data.objects:
            if obj.type == "MESH" and "_Weapon_" not in obj.name:
                obj.select_set(True)
            elif obj.name in ("WeaponSocket_R", "WeaponSocket_L"):
                obj.select_set(True)
        bpy.context.view_layer.objects.active = arm_obj
        bpy.ops.export_scene.gltf(
            filepath=unarmed_glb_path,
            export_format="GLB",
            use_selection=True,
            export_apply=False,
            export_yup=True,
            export_normals=True,
            export_texcoords=True,
            export_materials="EXPORT",
            export_skins=True,
            export_all_influences=False,
            export_def_bones=True,
            export_animations=True,
            export_animation_mode="NLA_TRACKS",
            export_anim_slide_to_zero=True,
            export_bake_animation=True,
            export_anim_single_armature=True,
        )
        u_anims, _, u_rot = _inspect_glb_header(unarmed_glb_path)
        if u_rot < len(u_anims):
            raise RuntimeError(
                f"{os.path.basename(unarmed_glb_path)}: only {u_rot}/{len(u_anims)} clips have active bone rotations!"
            )
    else:
        u_anims = None

    return anims, n_imgs, rot_active, u_anims


def main():
    test_only = "--test" in sys.argv
    out_root = os.path.join(PROJECT_DIR, "output")
    surv_dir = os.path.join(out_root, "survivors")
    zomb_dir = os.path.join(out_root, "zombies")

    if test_only:
        targets = [
            (
                os.path.join(surv_dir, "jake_male.blend"),
                os.path.join(surv_dir, "jake_male.glb"),
                os.path.join(surv_dir, "unarmed", "jake_male_unarmed.glb"),
            ),
            (
                os.path.join(zomb_dir, "mutant_bile_juggernaut.blend"),
                os.path.join(zomb_dir, "mutant_bile_juggernaut.glb"),
                None,
            ),
        ]
    else:
        targets = []
        for bp in sorted(glob.glob(os.path.join(surv_dir, "*.blend"))):
            slug = os.path.splitext(os.path.basename(bp))[0]
            targets.append((
                bp,
                os.path.join(surv_dir, f"{slug}.glb"),
                os.path.join(surv_dir, "unarmed", f"{slug}_unarmed.glb"),
            ))
        for bp in sorted(glob.glob(os.path.join(zomb_dir, "zombie_*.blend"))):
            slug = os.path.splitext(os.path.basename(bp))[0]
            targets.append((bp, os.path.join(zomb_dir, f"{slug}.glb"), None))
        for bp in sorted(glob.glob(os.path.join(zomb_dir, "mutant_*.blend"))):
            slug = os.path.splitext(os.path.basename(bp))[0]
            if slug == "mutant_fungal_bloom":
                continue
            targets.append((bp, os.path.join(zomb_dir, f"{slug}.glb"), None))

    print("=" * 78)
    print(f"RE-EXPORTING {len(targets)} BLEND FILES WITH QUATERNION BAKED ANIMATIONS")
    print("=" * 78)
    for bp, gp, up in targets:
        anims, n_imgs, rot_active, u_anims = _export_blend_with_actions(bp, gp, up)
        extra = f" | unarmed={len(u_anims)} clips" if u_anims is not None else ""
        print(
            f"  {os.path.basename(gp):<32s} : clips={len(anims):2d} (rot={rot_active:2d}) | images={n_imgs:2d}{extra}"
        )


if __name__ == "__main__":
    main()
