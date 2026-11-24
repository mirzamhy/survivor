"""Master build script: builds the Low-Poly Survivor, rigs it, exports .blend/.glb, and verifies."""
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import bpy

from palette import create_materials
from body_parts import build_survivor_body
from gear_parts import build_backpack, build_spiked_bat, build_crowbar
from rig_mixamo import create_mixamo_armature, skin_body_to_armature, attach_gear_to_bone


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_collection(name, parent=None):
    col = bpy.data.collections.new(name)
    if parent is None:
        bpy.context.scene.collection.children.link(col)
    else:
        parent.children.link(col)
    return col


def verify_body_weights(body_obj):
    unweighted = []
    over_max = []
    for v in body_obj.data.vertices:
        groups = [g for g in v.groups if g.weight > 1e-5]
        if not groups:
            unweighted.append(v.index)
        elif len(groups) > 4:
            over_max.append((v.index, len(groups)))
    if unweighted:
        raise RuntimeError(f"{len(unweighted)} unweighted vertices on {body_obj.name}")
    if over_max:
        raise RuntimeError(f"{len(over_max)} vertices exceed 4 weights on {body_obj.name}")


def world_bounds(objs):
    mins = [1e9, 1e9, 1e9]
    maxs = [-1e9, -1e9, -1e9]
    dg = bpy.context.evaluated_depsgraph_get()
    for obj in objs:
        if obj.type != "MESH":
            continue
        eval_obj = obj.evaluated_get(dg)
        me = eval_obj.to_mesh()
        mat = obj.matrix_world
        for v in me.vertices:
            co = mat @ v.co
            for i in range(3):
                mins[i] = min(mins[i], co[i])
                maxs[i] = max(maxs[i], co[i])
        eval_obj.to_mesh_clear()
    return mins, maxs


def mesh_centroid(obj):
    """Compute centroid over unique vertex positions (invariant to glTF material-primitive splits)."""
    dg = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(dg)
    me = eval_obj.to_mesh()
    mat = obj.matrix_world
    seen = set()
    acc = [0.0, 0.0, 0.0]
    for v in me.vertices:
        co = mat @ v.co
        key = (round(co[0], 4), round(co[1], 4), round(co[2], 4))
        if key not in seen:
            seen.add(key)
            acc[0] += co[0]
            acc[1] += co[1]
            acc[2] += co[2]
    eval_obj.to_mesh_clear()
    n = max(1, len(seen))
    return tuple(a / n for a in acc)


def export_glb(filepath, selected_only=False):
    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format="GLB",
        use_selection=selected_only,
        export_apply=False,
        export_yup=True,
        export_normals=True,
        export_texcoords=True,
        export_materials="EXPORT",
        export_skins=True,
        export_all_influences=False,
        export_def_bones=True,
        export_animations=False,
    )


def verify_glb_roundtrip(
    glb_path, expected_centroids, expected_sockets=None,
    min_h=1.60, max_h=1.95, require_mixamo=True, min_bones=25, min_images=0,
):
    """Import GLB into a clean scene to confirm bones, meshes, sockets, height, and gear alignment."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb_path)

    # Ignore helper bone-shape meshes like Icosphere created by glTF importer
    meshes = [bpy.data.objects[name] for name in expected_centroids if name in bpy.data.objects]
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if not arms:
        raise RuntimeError("GLB round-trip check failed: missing Armature")
    arm = arms[0]
    if require_mixamo:
        rig_bones = [b.name for b in arm.data.bones if b.name.startswith("mixamorig:")]
        bone_label = "Mixamo bones"
    else:
        rig_bones = [b.name for b in arm.data.bones]
        bone_label = "creature bones"
    if len(rig_bones) < min_bones:
        raise RuntimeError(f"GLB round-trip check failed: expected >={min_bones} {bone_label}, got {len(rig_bones)}")

    mins, maxs = world_bounds(meshes)
    height = maxs[2] - mins[2]
    if not (min_h <= height <= max_h):
        raise RuntimeError(f"GLB height out of range: {height:.3f}m (expected {min_h:.2f}..{max_h:.2f})")

    for name, exp_c in expected_centroids.items():
        obj = bpy.data.objects.get(name)
        if obj is None:
            raise RuntimeError(f"GLB missing mesh {name}")
        c = mesh_centroid(obj)
        dist = sum((c[i] - exp_c[i]) ** 2 for i in range(3)) ** 0.5
        if dist > 0.015:
            raise RuntimeError(f"GLB centroid shift on {name}: {dist:.4f}m (expected {exp_c}, got {c})")

    sock_tag = ""
    if expected_sockets:
        bpy.context.view_layer.update()
        for sname, exp_p in expected_sockets.items():
            sobj = bpy.data.objects.get(sname)
            if sobj is None:
                raise RuntimeError(f"GLB missing weapon socket {sname}")
            got_p = sobj.matrix_world.to_translation()
            dist = sum((got_p[i] - exp_p[i]) ** 2 for i in range(3)) ** 0.5
            if dist > 0.015:
                raise RuntimeError(f"GLB socket shift on {sname}: {dist:.4f}m (expected {exp_p}, got {tuple(got_p)})")
        sock_tag = ", sockets=OK"

    if min_images > 0:
        n_imgs = len(bpy.data.images)
        if n_imgs < min_images:
            raise RuntimeError(f"GLB missing embedded images: expected >={min_images}, got {n_imgs}")
    img_tag = f", images={len(bpy.data.images)}" if min_images > 0 else ""

    print(f"[GLB CHECK OK] {os.path.basename(glb_path)}: {len(rig_bones)} {bone_label}, "
          f"meshes={[m.name for m in meshes]}, height={height:.3f}m{sock_tag}{img_tag}, max centroid drift < 1.5cm")


def main():
    out_dir = os.path.join(PROJECT_DIR, "output")
    os.makedirs(out_dir, exist_ok=True)

    clear_scene()
    col_char = make_collection("Character")
    col_gear = make_collection("Gear")
    col_rig = make_collection("Rig")

    materials, idx_map = create_materials()

    # Build character body + detachable gear
    body_obj, body_tris, region_indices = build_survivor_body(materials, idx_map, collection=col_char)
    pack_obj, pack_tris = build_backpack(materials, idx_map, collection=col_gear)
    bat_obj, bat_tris = build_spiked_bat(materials, idx_map, collection=col_gear)
    crow_obj, crow_tris = build_crowbar(materials, idx_map, collection=col_gear)

    # Build Mixamo rig and bind character + gear
    arm_obj, specs = create_mixamo_armature(collection=col_rig)
    skin_body_to_armature(body_obj, arm_obj, specs, region_indices)
    attach_gear_to_bone(pack_obj, arm_obj, "mixamorig:Spine2")
    attach_gear_to_bone(crow_obj, arm_obj, "mixamorig:Spine2")
    attach_gear_to_bone(bat_obj, arm_obj, "mixamorig:RightHand")

    verify_body_weights(body_obj)

    all_meshes = [body_obj, pack_obj, bat_obj, crow_obj]
    for m in all_meshes:
        non_tris = sum(1 for p in m.data.polygons if len(p.vertices) != 3)
        if non_tris:
            raise RuntimeError(f"Expected 100% pure triangles on {m.name}, found {non_tris} non-tri faces")

    mins, maxs = world_bounds(all_meshes)
    b_mins, b_maxs = world_bounds([body_obj])
    total_gear_tris = pack_tris + bat_tris + crow_tris

    print("=" * 60)
    print("LOW-POLY ZOMBIE APOCALYPSE SURVIVOR BUILD SUMMARY")
    print(f"  Survivor_Body  : {body_tris:5d} tris")
    print(f"  Gear_Backpack  : {pack_tris:5d} tris")
    print(f"  Weapon_Bat     : {bat_tris:5d} tris")
    print(f"  Weapon_Crowbar : {crow_tris:5d} tris")
    print(f"  Total Gear     : {total_gear_tris:5d} tris")
    print(f"  Grand Total    : {body_tris + total_gear_tris:5d} tris")
    print(f"  Mixamo Bones   : {len(arm_obj.data.bones)} bones")
    print(f"  Body Bounds Z  : {b_mins[2]:.4f}m .. {b_maxs[2]:.4f}m (H = {b_maxs[2] - b_mins[2]:.4f}m)")
    print(f"  Full Bounds Z  : {mins[2]:.4f}m .. {maxs[2]:.4f}m")
    print("=" * 60)

    expected_centroids = {m.name: mesh_centroid(m) for m in all_meshes}

    blend_path = os.path.join(out_dir, "survivor_lowpoly.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"Saved: {blend_path}")

    glb_full = os.path.join(out_dir, "survivor_lowpoly.glb")
    export_glb(glb_full, selected_only=False)
    print(f"Exported: {glb_full}")

    # Export character-only GLB (Armature + Survivor_Body)
    bpy.ops.object.select_all(action="DESELECT")
    arm_obj.select_set(True)
    body_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj
    glb_body = os.path.join(out_dir, "survivor_character_only.glb")
    export_glb(glb_body, selected_only=True)
    print(f"Exported: {glb_body}")

    # Automated glTF round-trip check
    verify_glb_roundtrip(glb_full, expected_centroids)


if __name__ == "__main__":
    main()
