"""Render T-pose 5-view studio sheet and posed hero render of the Survivor."""
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Euler, Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)


def configure_renderer(scene, samples=32):
    """Use BLENDER_EEVEE by default; fall back to CYCLES CPU if needed."""
    scene.render.engine = "BLENDER_EEVEE"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    return scene.render.engine


def add_studio_lights(bg_color=(0.14, 0.15, 0.17)):
    scene = bpy.context.scene
    if scene.world is None:
        scene.world = bpy.data.worlds.new("StudioWorld")
    scene.world.use_nodes = True
    nt = scene.world.node_tree
    bg = nt.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (*bg_color, 1.0)
        bg.inputs["Strength"].default_value = 0.75

    def add_area(name, loc, target, energy, size, color=(1.0, 1.0, 1.0)):
        ldata = bpy.data.lights.new(name=name, type="AREA")
        ldata.energy = energy
        ldata.size = size
        ldata.color = color
        lobj = bpy.data.objects.new(name=name, object_data=ldata)
        scene.collection.objects.link(lobj)
        aim_camera(lobj, loc, target)
        return lobj

    # Key (warm front-right), Fill (soft cool front-left), Rim + BackFill (clear back view)
    add_area("KeyLight",  (-2.6, -2.8, 2.7), (0.0,  0.0, 1.05), 260, 2.2, (1.00, 0.94, 0.86))
    add_area("FillLight", ( 2.8, -2.2, 1.8), (0.0,  0.0, 1.00), 125, 3.0, (0.82, 0.90, 1.00))
    add_area("RimLight",  ( 0.4,  2.8, 2.5), (0.0,  0.0, 1.15), 180, 2.0, (0.78, 0.88, 1.00))
    add_area("BackFill",  (-0.5,  3.6, 1.35), (0.0, 0.1, 1.05), 175, 2.8, (0.94, 0.96, 1.00))


def add_ground_disc(radius=1.8):
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=0.04, location=(0, 0, -0.021))
    disc = bpy.context.active_object
    disc.name = "_RenderFloor"
    mat = bpy.data.materials.new("_FloorMat")
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.045, 0.048, 0.055, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.85
    disc.data.materials.append(mat)
    return disc


def aim_camera(cam, location, target):
    cam.location = Vector(location)
    direction = Vector(target) - Vector(location)
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def render_image(scene, out_path, width, height):
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.filepath = out_path
    try:
        bpy.ops.render.render(write_still=True)
    except Exception as exc:
        print(f"EEVEE render failed ({exc}), switching to CYCLES CPU...")
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 32
        scene.cycles.use_denoising = True
        bpy.ops.render.render(write_still=True)


def load_rgba_np(path):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size[0], img.size[1]
    arr = np.array(img.pixels[:], dtype=np.float32).reshape((h, w, 4))
    bpy.data.images.remove(img)
    return arr


def save_rgba_np(arr, path):
    h, w, _ = arr.shape
    img = bpy.data.images.new("_Composite", width=w, height=h, alpha=True)
    img.pixels.foreach_set(arr.ravel().tolist())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def render_tpose_sheet(blend_path, out_path, tile_size=640):
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene
    configure_renderer(scene)
    add_studio_lights(bg_color=(0.13, 0.14, 0.16))
    add_ground_disc(radius=2.0)

    cam_data = bpy.data.cameras.new("SheetCam")
    cam_data.type = "ORTHO"
    cam_data.clip_start = 0.05
    cam_data.clip_end = 50.0
    cam = bpy.data.objects.new("SheetCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    center = (0.0, 0.03, 0.90)
    views = [
        ("front", (0.0, -5.0, 0.90),  center, 2.05),
        ("34",    (-3.2, -3.8, 1.35), center, 2.05),
        ("right", (-5.0, 0.03, 0.90), center, 2.05),
        ("back",  (0.0,  5.0, 0.90),  center, 2.05),
        ("head",  (-2.0, -3.2, 1.72), (0.0, -0.02, 1.60), 0.52),
    ]

    tmp_dir = os.path.join(PROJECT_DIR, "renders", "_tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    tiles = []
    for name, loc, tgt, ortho_s in views:
        cam_data.ortho_scale = ortho_s
        aim_camera(cam, loc, tgt)
        p = os.path.join(tmp_dir, f"tile_{name}.png")
        render_image(scene, p, tile_size, tile_size)
        tiles.append(load_rgba_np(p))

    # Stitch 5 views horizontally with thin 4px dark divider
    gap = 4
    total_w = tile_size * len(tiles) + gap * (len(tiles) - 1)
    sheet = np.zeros((tile_size, total_w, 4), dtype=np.float32)
    sheet[:, :, :3] = 0.05
    sheet[:, :, 3] = 1.0
    x = 0
    for t in tiles:
        sheet[:, x:x + tile_size, :] = t
        x += tile_size + gap

    save_rgba_np(sheet, out_path)
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    print(f"Saved T-pose 5-view sheet: {out_path}")


def _rot_bone(pose_bones, name, deg_xyz):
    pb = pose_bones.get(name)
    if pb is None:
        return
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = Euler(tuple(math.radians(a) for a in deg_xyz), "XYZ")


def apply_combat_pose(arm_obj):
    """Apply an athletic Zombie Apocalypse survivor combat-ready pose."""
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="POSE")
    pb = arm_obj.pose.bones

    # Lower hips slightly for athletic bend and turn torso toward camera
    hips = pb["mixamorig:Hips"]
    hips.location = Vector((0.0, 0.0, -0.040))
    _rot_bone(pb, "mixamorig:Hips",   (3, 0, -16))
    _rot_bone(pb, "mixamorig:Spine",  (4, 0, 8))
    _rot_bone(pb, "mixamorig:Spine1", (5, 0, 8))
    _rot_bone(pb, "mixamorig:Spine2", (4, 0, 10))
    _rot_bone(pb, "mixamorig:Neck",   (-5, 0, -10))
    _rot_bone(pb, "mixamorig:Head",   (-4, 0, -14))

    # Grounded athletic stance (both boots planted cleanly near Z=0)
    _rot_bone(pb, "mixamorig:LeftUpLeg",  (-18, -4, 6))
    _rot_bone(pb, "mixamorig:LeftLeg",    (26, 0, 0))
    _rot_bone(pb, "mixamorig:LeftFoot",   (-8, 0, 0))

    _rot_bone(pb, "mixamorig:RightUpLeg", (14, 4, -8))
    _rot_bone(pb, "mixamorig:RightLeg",   (18, 0, 0))
    _rot_bone(pb, "mixamorig:RightFoot",  (-24, 0, 0))
    _rot_bone(pb, "mixamorig:RightToeBase", (10, 0, 0))

    # Left arm (bone +Y = +X, +Z = +Z): -X lowers arm DOWN, -Z swings FORWARD (-Y)
    _rot_bone(pb, "mixamorig:LeftShoulder", (-6, 0, -4))
    _rot_bone(pb, "mixamorig:LeftArm",      (-52, 12, -32))
    _rot_bone(pb, "mixamorig:LeftForeArm",  (0, 0, -68))
    _rot_bone(pb, "mixamorig:LeftHand",     (0, 10, -10))
    for seg in (1, 2, 3):
        _rot_bone(pb, f"mixamorig:LeftHandIndex{seg}",  (45, 0, 0))
        _rot_bone(pb, f"mixamorig:LeftHandMiddle{seg}", (48, 0, 0))
        _rot_bone(pb, f"mixamorig:LeftHandThumb{seg}",  (0, 22, 16))

    # Right arm (bone +Y = -X, +Z = +Z): -X lowers arm DOWN, +Z swings FORWARD (-Y)
    _rot_bone(pb, "mixamorig:RightShoulder", (-4, 0, 6))
    _rot_bone(pb, "mixamorig:RightArm",      (-32, -14, 42))
    _rot_bone(pb, "mixamorig:RightForeArm",  (42, 0, 58))
    _rot_bone(pb, "mixamorig:RightHand",     (12, 16, 10))
    # Wrap right fingers cleanly around bat grip
    for seg in (1, 2, 3):
        _rot_bone(pb, f"mixamorig:RightHandIndex{seg}",  (50, 0, 0))
        _rot_bone(pb, f"mixamorig:RightHandMiddle{seg}", (52, 0, 0))
        _rot_bone(pb, f"mixamorig:RightHandThumb{seg}",  (0, -24, -18))

    bpy.ops.object.mode_set(mode="OBJECT")


def render_hero_posed(blend_path, out_path, width=1280, height=1440):
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene
    configure_renderer(scene)
    add_studio_lights(bg_color=(0.08, 0.09, 0.11))
    add_ground_disc(radius=2.2)

    arm_obj = bpy.data.objects["Armature"]
    apply_combat_pose(arm_obj)

    cam_data = bpy.data.cameras.new("HeroCam")
    cam_data.type = "PERSP"
    cam_data.lens = 52.0
    cam = bpy.data.objects.new("HeroCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    aim_camera(cam, (-1.85, -2.55, 1.32), (0.02, -0.02, 0.92))
    render_image(scene, out_path, width, height)
    print(f"Saved posed hero render: {out_path}")


def render_closeup_check(blend_path, out_path, tile_size=640):
    """Render side-by-side close-up of Face 3/4 and Back Head + Backpack/Crowbar."""
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene
    configure_renderer(scene)
    add_studio_lights(bg_color=(0.13, 0.14, 0.16))

    cam_data = bpy.data.cameras.new("CloseCam")
    cam_data.type = "ORTHO"
    cam_data.clip_start = 0.05
    cam_data.clip_end = 50.0
    cam = bpy.data.objects.new("CloseCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    views = [
        ("face_34",    (-1.8, -2.8, 1.72), (0.0, -0.02, 1.62), 0.46),
        ("back_gear",  ( 1.2,  3.2, 1.56), (0.0,  0.14, 1.42), 0.78),
    ]
    tmp_dir = os.path.join(PROJECT_DIR, "renders", "_tmp_close")
    os.makedirs(tmp_dir, exist_ok=True)
    tiles = []
    for name, loc, tgt, ortho_s in views:
        cam_data.ortho_scale = ortho_s
        aim_camera(cam, loc, tgt)
        p = os.path.join(tmp_dir, f"{name}.png")
        render_image(scene, p, tile_size, tile_size)
        tiles.append(load_rgba_np(p))

    gap = 4
    total_w = tile_size * 2 + gap
    sheet = np.zeros((tile_size, total_w, 4), dtype=np.float32)
    sheet[:, :, :3] = 0.05
    sheet[:, :, 3] = 1.0
    sheet[:, 0:tile_size, :] = tiles[0]
    sheet[:, tile_size + gap:, :] = tiles[1]
    save_rgba_np(sheet, out_path)
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    print(f"Saved close-up QA check: {out_path}")


def render_head_sheet(blend_path, out_path, tile_size=640):
    """Render 4-view head turnaround (Front, 3/4, Side, Back) on clean light studio backdrop."""
    bpy.ops.wm.open_mainfile(filepath=blend_path)
    scene = bpy.context.scene
    configure_renderer(scene)
    add_studio_lights(bg_color=(0.76, 0.77, 0.79))

    cam_data = bpy.data.cameras.new("HeadSheetCam")
    cam_data.type = "ORTHO"
    cam_data.clip_start = 0.05
    cam_data.clip_end = 50.0
    cam = bpy.data.objects.new("HeadSheetCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    tgt = (0.0, 0.0, 1.65)
    views = [
        ("front", ( 0.0, -2.8, 1.66)),
        ("34",    (-1.9, -2.1, 1.70)),
        ("side",  (-2.8,  0.0, 1.66)),
        ("back",  ( 0.0,  2.8, 1.66)),
    ]
    tmp_dir = os.path.join(PROJECT_DIR, "renders", "_tmp_head")
    os.makedirs(tmp_dir, exist_ok=True)
    tiles = []
    cam_data.ortho_scale = 0.42
    for name, loc in views:
        aim_camera(cam, loc, tgt)
        p = os.path.join(tmp_dir, f"{name}.png")
        render_image(scene, p, tile_size, tile_size)
        tiles.append(load_rgba_np(p))

    gap = 4
    total_w = tile_size * len(tiles) + gap * (len(tiles) - 1)
    sheet = np.zeros((tile_size, total_w, 4), dtype=np.float32)
    sheet[:, :, :3] = 0.76
    sheet[:, :, 3] = 1.0
    x = 0
    for t in tiles:
        sheet[:, x:x + tile_size, :] = t
        x += tile_size + gap
    save_rgba_np(sheet, out_path)
    for f in os.listdir(tmp_dir):
        os.remove(os.path.join(tmp_dir, f))
    os.rmdir(tmp_dir)
    print(f"Saved 4-view head sheet: {out_path}")


def main():
    blend_path = os.path.join(PROJECT_DIR, "output", "survivor_lowpoly.blend")
    renders_dir = os.path.join(PROJECT_DIR, "renders")
    os.makedirs(renders_dir, exist_ok=True)

    render_tpose_sheet(blend_path, os.path.join(renders_dir, "sheet_tpose.png"))
    render_hero_posed(blend_path, os.path.join(renders_dir, "hero_posed.png"))
    render_closeup_check(blend_path, os.path.join(renders_dir, "closeup_check.png"))
    render_head_sheet(blend_path, os.path.join(renders_dir, "head_sheet.png"))


if __name__ == "__main__":
    main()
