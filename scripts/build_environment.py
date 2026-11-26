"""Build & export 14 modular Apocalypse Environment assets + assembled Street Battleground Diorama."""
import json
import os
import struct
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import bpy

from build_survivor import clear_scene, export_glb, make_collection, world_bounds
from environment_apocalypse import ALL_ENV_BUILDERS, build_apocalypse_street_scene
from palette import create_materials


def _assert_pure_tris(mesh_objs):
    for m in mesh_objs:
        non_tris = sum(1 for p in m.data.polygons if len(p.vertices) != 3)
        if non_tris:
            raise RuntimeError(f"Non-triangle faces on {m.name}: {non_tris}")


def _inspect_static_glb(glb_path):
    with open(glb_path, "rb") as f:
        raw = f.read()
    jlen = struct.unpack("<I", raw[12:16])[0]
    g = json.loads(raw[20:20 + jlen].decode("utf-8"))
    return {
        "bytes": len(raw),
        "meshes": len(g.get("meshes", [])),
        "nodes": len(g.get("nodes", [])),
        "materials": len(g.get("materials", [])),
        "images": len(g.get("images", [])),
    }


def build_modular_assets(env_dir):
    os.makedirs(env_dir, exist_ok=True)
    print("=" * 74)
    print(f"BUILDING {len(ALL_ENV_BUILDERS)} MODULAR APOCALYPSE ENVIRONMENT ASSETS (PBR Textured)")
    total_tris = 0
    for slug, builder_fn, category in ALL_ENV_BUILDERS:
        clear_scene()
        col = make_collection("Environment")
        materials, idx_map = create_materials(with_env_textures=True)
        obj, tris = builder_fn(materials, idx_map, collection=col, name=f"Env_{slug}")
        _assert_pure_tris([obj])
        mins, maxs = world_bounds([obj])
        dx = maxs[0] - mins[0]
        dy = maxs[1] - mins[1]
        dz = maxs[2] - mins[2]
        if mins[2] < -0.15 or mins[2] > 0.05:
            raise RuntimeError(f"{slug} min_z={mins[2]:.3f}m out of grounded range [-0.15, 0.05]")

        blend_path = os.path.join(env_dir, f"env_{slug}.blend")
        glb_path = os.path.join(env_dir, f"env_{slug}.glb")
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        export_glb(glb_path, selected_only=False, export_animations=False)
        info = _inspect_static_glb(glb_path)
        if info["images"] < 3:
            raise RuntimeError(f"env_{slug}.glb missing packed PBR textures (images={info['images']})")
        total_tris += tris
        print(
            f"  [{category:<8s}] env_{slug:<22s} : {tris:4d} tris | "
            f"{dx:4.1f}x{dy:4.1f}x{dz:4.1f}m | z=[{mins[2]:+.2f},{maxs[2]:.2f}] | "
            f"imgs={info['images']:2d} | {info['bytes'] // 1024:4d} KB"
        )
    print(f"  TOTAL MODULAR TRIS: {total_tris}")


def build_diorama_scene(env_dir):
    os.makedirs(env_dir, exist_ok=True)
    print("=" * 74)
    print("BUILDING ASSEMBLED APOCALYPSE STREET BATTLEGROUND DIORAMA")
    clear_scene()
    col = make_collection("ApocalypseStreet")
    materials, idx_map = create_materials(with_env_textures=True)
    objs, total_tris = build_apocalypse_street_scene(materials, idx_map, collection=col)
    _assert_pure_tris(objs)

    mins, maxs = world_bounds(objs)
    blend_path = os.path.join(env_dir, "apocalypse_street_scene.blend")
    glb_path = os.path.join(env_dir, "apocalypse_street_scene.glb")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    export_glb(glb_path, selected_only=False, export_animations=False)
    info = _inspect_static_glb(glb_path)
    if info["images"] < 12:
        raise RuntimeError(f"apocalypse_street_scene.glb expected >= 12 PBR images, got {info['images']}")
    print(
        f"  DIORAMA : {len(objs)} meshes | {total_tris} tris | "
        f"span {maxs[0]-mins[0]:.1f}x{maxs[1]-mins[1]:.1f}x{maxs[2]-mins[2]:.1f}m | "
        f"imgs={info['images']} | {info['bytes'] / (1024*1024):.2f} MB -> {os.path.basename(glb_path)}"
    )


def main():
    env_dir = os.path.join(PROJECT_DIR, "output", "environment")
    if "--diorama-only" not in sys.argv:
        build_modular_assets(env_dir)
    build_diorama_scene(env_dir)
    print("=" * 74)
    print("APOCALYPSE ENVIRONMENT KIT BUILD COMPLETE")


if __name__ == "__main__":
    main()
