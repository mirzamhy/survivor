"""Fast re-bake & export all 21 existing .blend files (10 Survivors, 6 Zombies, 5 Mutants).

Preserves all sculpted meshes, vertex weights, vertex colors, sockets, and embedded PBR textures
while refreshing Actions cleanly with active QUATERNION rotation playback in glTF/GLB.
"""
import glob
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import bpy

from reexport_animated_glbs import _export_blend_with_actions
from rig_creature import bake_creature_actions
from rig_mechanics import bake_rig_actions, bake_zombie_actions


def _find_body_mesh(arm_obj):
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and "_Weapon_" not in o.name]
    if not meshes:
        raise RuntimeError("No body mesh object found in scene")
    # Prefer the largest non-weapon skinned mesh or explicit Body name
    for m in meshes:
        if "Body" in m.name or "Mutant" in m.name or "Zombie" in m.name:
            return max(meshes, key=lambda o: len(o.data.vertices))
    return max(meshes, key=lambda o: len(o.data.vertices))


def _clear_old_actions_and_nla(arm_obj):
    if arm_obj.animation_data is not None:
        arm_obj.animation_data.action = None
        for tr in list(arm_obj.animation_data.nla_tracks):
            arm_obj.animation_data.nla_tracks.remove(tr)
    for act in list(bpy.data.actions):
        act.use_fake_user = False
        bpy.data.actions.remove(act)


def rebake_single(blend_path, glb_path, unarmed_glb_path=None, kind="survivor", creature_type=None):
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if not arms:
        raise RuntimeError(f"No armature in {blend_path}")
    arm_obj = arms[0]
    body_obj = _find_body_mesh(arm_obj)

    _clear_old_actions_and_nla(arm_obj)

    if kind == "survivor":
        wid = arm_obj.get("weapon_id")
        rg = tuple(arm_obj["right_grip_rest"]) if "right_grip_rest" in arm_obj else None
        bake_rig_actions(arm_obj, body_obj, weapon_id=wid, right_grip_rest=rg)
    elif kind == "zombie":
        bake_zombie_actions(arm_obj, body_obj)
    elif kind == "mutant":
        bake_creature_actions(arm_obj, body_obj, creature_type=creature_type)
    else:
        raise ValueError(f"Unknown kind: {kind}")

    bpy.ops.wm.save_mainfile(filepath=blend_path)
    return _export_blend_with_actions(blend_path, glb_path, unarmed_glb_path=unarmed_glb_path)


def main():
    test_only = "--test" in sys.argv
    out_root = os.path.join(PROJECT_DIR, "output")
    surv_dir = os.path.join(out_root, "survivors")
    zomb_dir = os.path.join(out_root, "zombies")

    jobs = []
    if test_only:
        jobs.append((
            "survivor", None,
            os.path.join(surv_dir, "rico_male.blend"),
            os.path.join(surv_dir, "rico_male.glb"),
            os.path.join(surv_dir, "unarmed", "rico_male_unarmed.glb"),
        ))
        jobs.append((
            "zombie", None,
            os.path.join(zomb_dir, "zombie_crawler_stalker.blend"),
            os.path.join(zomb_dir, "zombie_crawler_stalker.glb"),
            None,
        ))
        jobs.append((
            "mutant", "bile_juggernaut",
            os.path.join(zomb_dir, "mutant_bile_juggernaut.blend"),
            os.path.join(zomb_dir, "mutant_bile_juggernaut.glb"),
            None,
        ))
    else:
        for bp in sorted(glob.glob(os.path.join(surv_dir, "*.blend"))):
            slug = os.path.splitext(os.path.basename(bp))[0]
            jobs.append((
                "survivor", None, bp,
                os.path.join(surv_dir, f"{slug}.glb"),
                os.path.join(surv_dir, "unarmed", f"{slug}_unarmed.glb"),
            ))
        for bp in sorted(glob.glob(os.path.join(zomb_dir, "zombie_*.blend"))):
            slug = os.path.splitext(os.path.basename(bp))[0]
            jobs.append(("zombie", None, bp, os.path.join(zomb_dir, f"{slug}.glb"), None))
        for bp in sorted(glob.glob(os.path.join(zomb_dir, "mutant_*.blend"))):
            slug = os.path.splitext(os.path.basename(bp))[0]
            if slug == "mutant_fungal_bloom":
                continue
            ctype = slug[len("mutant_"):]
            jobs.append(("mutant", ctype, bp, os.path.join(zomb_dir, f"{slug}.glb"), None))

    print("=" * 78)
    print(f"RE-BAKING & EXPORTING {len(jobs)} MODELS (QUATERNION + FLUID COMBAT ACTIONS)")
    print("=" * 78)
    for kind, ctype, bp, gp, up in jobs:
        anims, n_imgs, rot_active, u_anims = rebake_single(
            bp, gp, unarmed_glb_path=up, kind=kind, creature_type=ctype
        )
        if kind == "mutant" and n_imgs < 18:
            raise RuntimeError(f"{os.path.basename(gp)}: expected >= 18 embedded images, got {n_imgs}!")
        extra = f" | unarmed={len(u_anims)} clips" if u_anims is not None else ""
        print(
            f"  [{kind:<8s}] {os.path.basename(gp):<30s} : clips={len(anims):2d} (rot={rot_active:2d}) | images={n_imgs:2d}{extra}"
        )


if __name__ == "__main__":
    main()
