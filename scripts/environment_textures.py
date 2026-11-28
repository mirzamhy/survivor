"""Seamless 512x512 procedural PBR textures for the Zombie Apocalypse Environment Kit."""
import bpy
import numpy as np

from mutant_textures import (
    _c,
    _domain_warp,
    _height_to_normal_rgba,
    _mix,
    _periodic_fbm,
    _periodic_value_noise,
    _periodic_voronoi,
)

ENV_GROUND_TEX_SIZE = 512
ENV_PROP_TEX_SIZE = 256
_ENV_TEX_CACHE = {}


def _ensure_packed_env_image(name, rgba_2d, tex_size, colorspace="sRGB"):
    img = bpy.data.images.get(name)
    if img is not None:
        if img.size[0] == tex_size and img.size[1] == tex_size:
            return img
        bpy.data.images.remove(img)
    img = bpy.data.images.new(
        name=name,
        width=tex_size,
        height=tex_size,
        alpha=False,
        float_buffer=False,
    )
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(rgba_2d.ravel())
    img.pack()
    return img


def _generate_env_archetype(arch, mat_name, base_hex, base_roughness):
    n = ENV_GROUND_TEX_SIZE if arch == "mud_wet" else ENV_PROP_TEX_SIZE
    cache_key = (arch, mat_name, n)
    if cache_key in _ENV_TEX_CACHE:
        return _ENV_TEX_CACHE[cache_key]

    lin = np.linspace(0.0, 1.0, n, endpoint=False, dtype=np.float32)
    gy, gx = np.meshgrid(lin, lin, indexing="ij")

    if arch == "asphalt_cracked":
        # Cracked weathered asphalt road with sharp dark fissures & gravel grit
        fbm_coarse = _periodic_fbm(n, 4, seed=101)
        fbm_grit = _periodic_fbm(n, 6, seed=107)
        wx = _periodic_fbm(n, 4, seed=113)
        wy = _periodic_fbm(n, 4, seed=127)
        _, v_edge, v_cell = _periodic_voronoi(n, 14, seed=131)
        edge_w = _domain_warp(v_edge, wx, wy, 14.0)

        # Primary deep fissures + hairline branching cracks
        fissure = np.clip(1.0 - edge_w / 0.055, 0.0, 1.0) ** 1.3
        crack_lip = np.clip(1.0 - np.abs(edge_w - 0.058) / 0.025, 0.0, 1.0)

        base_rgb = _mix(_c("#262A30"), _c("#363B42"), fbm_coarse * 0.65 + fbm_grit * 0.35)
        # Subtle worn tire track sheen / dust patches
        dust = np.clip((fbm_coarse - 0.55) / 0.45, 0.0, 1.0)
        rgb = _mix(base_rgb, _c("#4A443C"), dust * 0.40)
        rgb = _mix(rgb, _c("#4E473D"), crack_lip * 0.45)
        rgb = _mix(rgb, _c("#141518"), fissure * 0.92)

        height = np.clip(0.65 + 0.14 * fbm_grit - 0.58 * fissure + 0.08 * crack_lip, 0.0, 1.0)
        rough_map = np.clip(0.84 + 0.08 * fbm_grit - 0.08 * fbm_coarse + 0.10 * fissure, 0.68, 0.96)
        norm_rgba = _height_to_normal_rgba(height, strength=3.8)

    elif arch == "soil_cracked":
        # Parched cracked earth with raised sun-baked plates & deep mud trenches
        fbm_a = _periodic_fbm(n, 5, seed=203)
        wx = _periodic_fbm(n, 4, seed=211)
        wy = _periodic_fbm(n, 4, seed=223)
        f1, v_edge, v_cell = _periodic_voronoi(n, 18, seed=229)
        edge_w = _domain_warp(v_edge, wx, wy, 11.0)

        crack = np.clip(1.0 - edge_w / 0.078, 0.0, 1.0) ** 1.25
        plate_dome = np.clip(edge_w / 0.25, 0.0, 1.0)
        dry_moss = np.clip((fbm_a - 0.68) / 0.32, 0.0, 1.0) * (1.0 - crack)

        plate_col = _mix(_c("#4A3B2D"), _c("#685642"), 0.55 * plate_dome + 0.45 * v_cell)
        rgb = _mix(plate_col, _c("#525A30"), dry_moss * 0.48)
        rgb = _mix(rgb, _c("#221912"), crack * 0.94)

        height = np.clip(0.60 + 0.18 * plate_dome + 0.10 * fbm_a - 0.64 * crack, 0.0, 1.0)
        rough_map = np.clip(0.88 + 0.06 * fbm_a + 0.04 * crack, 0.78, 0.97)
        norm_rgba = _height_to_normal_rgba(height, strength=4.2)

    elif arch == "concrete_cracked":
        # Poured weathered architectural concrete with subtle hairline cracks, sand grain & rain grime
        fbm_a = _periodic_fbm(n, 5, seed=307)
        fine_grit = _periodic_value_noise(n, 72, seed=311)
        streak = _periodic_fbm(n, 4, seed=313)
        wx = _periodic_fbm(n, 4, seed=317)
        wy = _periodic_fbm(n, 4, seed=331)
        _, v_edge, _ = _periodic_voronoi(n, 10, seed=337)
        edge_w = _domain_warp(v_edge, wx, wy, 7.5)

        fracture = np.clip(1.0 - edge_w / 0.022, 0.0, 1.0) ** 1.5
        rain_streak = np.sin(gx * 2.0 * np.pi * 4.0 + streak * 3.0)
        rain_mask = np.clip(0.5 + 0.5 * rain_streak, 0.0, 1.0) * np.clip(1.0 - gy, 0.25, 0.85)

        if mat_name == "Mat_Env_ConcreteDark":
            c_lo, c_hi = _c("#3D3F3D"), _c("#585A56")
        elif mat_name == "Mat_Env_PlasterDamaged":
            c_lo, c_hi = _c("#746D5D"), _c("#9A9280")
        else:
            c_lo, c_hi = _c("#62605A"), _c("#828078")

        rgb = _mix(c_lo, c_hi, 0.78 * fbm_a + 0.22 * fine_grit)
        rgb = _mix(rgb, _c("#363830"), rain_mask * 0.22)
        rgb = _mix(rgb, _c("#363530"), fracture * 0.28)

        height = np.clip(0.68 + 0.14 * fbm_a + 0.06 * fine_grit - 0.24 * fracture, 0.0, 1.0)
        rough_map = np.clip(0.88 + 0.06 * fbm_a + 0.03 * fracture, 0.86, 0.97)
        norm_rgba = _height_to_normal_rgba(height, strength=2.2)

    elif arch == "brick_ruined":
        # Running-bond weathered apocalypse masonry with dark mortar & damp soot
        fbm_a = _periodic_fbm(n, 5, seed=401)
        fbm_b = _periodic_fbm(n, 4, seed=409)
        rows = 8.0
        cols = 4.0
        row_idx = np.floor(gy * rows)
        u_shift = gx * cols + 0.5 * (row_idx % 2.0)
        v_in = (gy * rows) % 1.0
        u_in = u_shift % 1.0

        brick_seed = np.sin(row_idx * 12.9898 + np.floor(u_shift) * 78.233) * 43758.5453
        brick_var = brick_seed - np.floor(brick_seed)

        mortar = ((u_in < 0.06) | (u_in > 0.94) | (v_in < 0.10) | (v_in > 0.90)).astype(np.float32)
        wx = _periodic_fbm(n, 4, seed=419)
        wy = _periodic_fbm(n, 4, seed=421)
        mortar_w = np.clip(_domain_warp(mortar, wx, wy, 2.5), 0.0, 1.0)

        brick_col = _mix(_c("#582B21"), _c("#844836"), 0.55 * brick_var + 0.45 * fbm_a)
        soot = np.clip((fbm_b - 0.58) / 0.42, 0.0, 1.0)
        rgb = _mix(brick_col, _c("#28211C"), soot * 0.50)
        rgb = _mix(rgb, _c("#3A3631"), mortar_w * 0.90)

        height = np.clip(0.74 - 0.44 * mortar_w + 0.12 * fbm_a - 0.08 * brick_var, 0.0, 1.0)
        rough_map = np.clip(0.84 + 0.08 * mortar_w + 0.05 * fbm_a, 0.78, 0.96)
        norm_rgba = _height_to_normal_rgba(height, strength=2.6)

    elif arch == "rust_weathered":
        # Weathered oxidized metal & faded dusty paint (matte-to-satin, never mirror plastic)
        fbm_a = _periodic_fbm(n, 5, seed=503)
        fbm_b = _periodic_fbm(n, 4, seed=509)
        rust_mask = np.clip((fbm_a * 0.7 + fbm_b * 0.3 - 0.38) / 0.45, 0.0, 1.0)

        if mat_name == "Mat_Env_CarPaintFaded":
            paint_rgb = _mix(_c("#364752"), _c("#4E6470"), fbm_b)
        elif mat_name == "Mat_Env_BarrelRed":
            paint_rgb = _mix(_c("#6D221B"), _c("#96372D"), fbm_b)
        elif mat_name == "Mat_Env_PoliceWhite":
            paint_rgb = _mix(_c("#AAB2B8"), _c("#CED4D8"), fbm_b)
        elif mat_name == "Mat_Env_CrateGreen":
            paint_rgb = _mix(_c("#313F27"), _c("#4D5F3F"), fbm_b)
        elif mat_name == "Mat_Env_HazardYellow":
            paint_rgb = _mix(_c("#96721A"), _c("#C69B2D"), fbm_b)
        elif mat_name == "Mat_Env_MetalScrap":
            paint_rgb = _mix(_c("#262A30"), _c("#42474E"), fbm_b)
        else:
            paint_rgb = _mix(_c("#4A342B"), _c("#684130"), fbm_b)

        rust_col = _mix(_c("#542818"), _c("#844222"), fbm_a)
        rust_w = 0.90 if mat_name == "Mat_Env_RustHeavy" else (0.42 if mat_name == "Mat_Env_PoliceWhite" else 0.58)
        rgb = _mix(paint_rgb, rust_col, rust_mask * rust_w)
        height = np.clip(0.62 - 0.22 * rust_mask + 0.14 * fbm_a, 0.0, 1.0)
        rough_map = np.clip(0.76 - 0.10 * (1.0 - rust_mask) + 0.14 * rust_mask, 0.64, 0.94)
        norm_rgba = _height_to_normal_rgba(height, strength=2.2)

    elif arch == "fabric_burlap":
        # Fine matte military burlap canvas weave with soft weathered soot blotches (zero coarse checker)
        fbm_a = _periodic_fbm(n, 5, seed=651)
        fine_weave = 0.5 + 0.5 * np.sin(gx * 2.0 * np.pi * 48.0) * np.sin(gy * 2.0 * np.pi * 48.0)
        wx = _periodic_fbm(n, 4, seed=657)
        wy = _periodic_fbm(n, 4, seed=663)
        grime = _domain_warp(np.clip((fbm_a - 0.52) * 2.0, 0.0, 1.0), wx, wy, 6.0)
        c_base = _c(base_hex)
        rgb = c_base * (0.86 + 0.16 * (0.25 * fine_weave + 0.75 * fbm_a))[..., None]
        rgb = _mix(rgb, _c("#443A2E"), grime * 0.34)
        height = np.clip(0.54 + 0.06 * fine_weave + 0.24 * fbm_a - 0.14 * grime, 0.0, 1.0)
        rough_map = np.clip(0.88 + 0.05 * grime - 0.04 * fbm_a, 0.84, 0.96)
        norm_rgba = _height_to_normal_rgba(height, strength=1.4)

    elif arch == "wood_weathered":
        # Weathered splintered barricade timber planks
        fbm_a = _periodic_fbm(n, 5, seed=601)
        wx = _periodic_fbm(n, 4, seed=607)
        wy = _periodic_fbm(n, 4, seed=613)
        grain = _domain_warp(0.5 + 0.5 * np.sin(gx * 2.0 * np.pi * 12.0 + fbm_a * 2.5), wx, wy, 5.0)
        plank_seam = np.clip(1.0 - np.abs((gx * 4.0) % 1.0 - 0.03) / 0.035, 0.0, 1.0)
        rgb = _mix(_c("#483322"), _c("#74583D"), grain * 0.72 + fbm_a * 0.28)
        rgb = _mix(rgb, _c("#261B12"), plank_seam * 0.75)
        height = np.clip(0.64 + 0.16 * grain - 0.35 * plank_seam, 0.0, 1.0)
        rough_map = np.clip(0.82 + 0.10 * (1.0 - grain), 0.72, 0.94)
        norm_rgba = _height_to_normal_rgba(height, strength=2.8)

    elif arch == "mud_wet":
        # Compacted matte war-torn brown soil with damp ruts & dry earth gravel grain (NEVER glossy!)
        fbm_macro = _periodic_fbm(n, 5, seed=809)
        fbm_clump = _periodic_fbm(n, 6, seed=811)
        fine_grit = _periodic_value_noise(n, 96, seed=817)
        wx = _periodic_fbm(n, 4, seed=821)
        wy = _periodic_fbm(n, 4, seed=823)
        rut_wave = 0.5 + 0.5 * np.sin(gy * 2.0 * np.pi * 3.0 + wx * 3.2)
        mud_warp = _domain_warp(fbm_macro, wx, wy, 7.5)
        wet_pocket = np.clip((0.50 - mud_warp) / 0.34, 0.0, 1.0) ** 1.25
        rut_trough = np.clip((0.46 - rut_wave) / 0.38, 0.0, 1.0) * 0.45
        moisture = np.clip(wet_pocket * 0.80 + rut_trough * 0.40, 0.0, 1.0)

        dry_ridge = _mix(_c("#4E3A2A"), _c("#634F3C"), 0.72 * fbm_clump + 0.28 * fine_grit)
        damp_soil = _mix(_c("#2B1E14"), _c("#3C2B1E"), 0.76 * fbm_macro + 0.24 * fine_grit)
        rgb = _mix(dry_ridge, damp_soil, moisture)
        rgb = _mix(rgb, _c("#22170F"), np.clip(moisture - 0.55, 0.0, 1.0) * 0.90)

        height = np.clip(0.64 + 0.16 * fbm_clump + 0.08 * fine_grit - 0.36 * moisture, 0.0, 1.0)
        rough_map = np.clip(0.92 - 0.16 * moisture + 0.05 * fbm_clump, 0.74, 0.97)
        norm_rgba = _height_to_normal_rgba(height, strength=2.2)

    elif arch == "fortress_steel":
        # Weathered matte corrugated scrap-metal wall plates with ribs, welded seams, soot & warm rust
        fbm_a = _periodic_fbm(n, 5, seed=907)
        fbm_b = _periodic_fbm(n, 4, seed=911)
        corr = 0.5 + 0.5 * np.sin(gx * 2.0 * np.pi * 10.0)
        seam_y = np.clip(1.0 - np.abs((gy * 2.0) % 1.0 - 0.03) / 0.028, 0.0, 1.0)
        rust_mask = np.clip((fbm_a * 0.68 + fbm_b * 0.32 - 0.44) / 0.42, 0.0, 1.0)
        soot = np.clip((fbm_b - 0.56) / 0.44, 0.0, 1.0)

        steel_base = _mix(_c("#2E3238"), _c("#474D54"), 0.60 * corr + 0.40 * fbm_b)
        if mat_name == "Mat_Env_BarbedWire":
            steel_base = _mix(_c("#3B3430"), _c("#544942"), 0.55 * corr + 0.45 * fbm_b)
        rgb = _mix(steel_base, _c("#6E3820"), rust_mask * 0.64)
        rgb = _mix(rgb, _c("#1C1D20"), soot * 0.40 + seam_y * 0.50)

        height = np.clip(0.54 + 0.24 * corr - 0.28 * seam_y - 0.14 * rust_mask, 0.0, 1.0)
        rough_map = np.clip(0.64 + 0.24 * rust_mask + 0.08 * soot, 0.58, 0.94)
        norm_rgba = _height_to_normal_rgba(height, strength=2.4)

    elif arch == "hive_organic":
        # Glistening dark bruised chitin & bio-hive tissue with toxic olive veins
        fbm_a = _periodic_fbm(n, 5, seed=953)
        wx = _periodic_fbm(n, 4, seed=967)
        wy = _periodic_fbm(n, 4, seed=971)
        _, v_edge, _ = _periodic_voronoi(n, 11, seed=977)
        edge_w = _domain_warp(v_edge, wx, wy, 10.0)
        vein = np.clip(1.0 - edge_w / 0.068, 0.0, 1.0) ** 1.3

        flesh = _mix(_c("#1B0F18"), _c("#461C27"), fbm_a)
        rgb = _mix(flesh, _c("#546B1E"), vein * 0.72)

        height = np.clip(0.55 + 0.18 * fbm_a + 0.22 * vein, 0.0, 1.0)
        rough_map = np.clip(0.56 - 0.28 * vein - 0.12 * fbm_a, 0.24, 0.66)
        norm_rgba = _height_to_normal_rgba(height, strength=3.6)

    else:  # grass_organic (mottled foliage & dried vegetation without artificial stripe bands)
        fbm_a = _periodic_fbm(n, 5, seed=701)
        fbm_b = _periodic_fbm(n, 4, seed=709)
        f1, v_edge, v_cell = _periodic_voronoi(n, 22, seed=719)
        leaf_spot = np.clip(1.0 - f1 * 1.15, 0.0, 1.0)
        mottle = np.clip(0.55 * fbm_a + 0.25 * v_cell + 0.20 * leaf_spot, 0.0, 1.0)
        if mat_name == "Mat_Env_GrassDry":
            c0, c1, c_tip = _c("#545B29"), _c("#7D8742"), _c("#969A50")
        else:
            c0, c1, c_tip = _c("#243E1C"), _c("#3F662E"), _c("#527C3A")
        rgb = _mix(c0, c1, mottle)
        rgb = _mix(rgb, c_tip, np.clip((fbm_b - 0.55) / 0.45, 0.0, 1.0) * 0.55)
        height = np.clip(0.45 + 0.30 * leaf_spot + 0.18 * fbm_a, 0.0, 1.0)
        rough_map = np.clip(float(base_roughness) - 0.06 * leaf_spot + 0.06 * fbm_a, 0.65, 0.92)
        norm_rgba = _height_to_normal_rgba(height, strength=2.2)

    albedo_rgba = np.empty((n, n, 4), dtype=np.float32)
    albedo_rgba[..., :3] = np.clip(rgb, 0.0, 1.0)
    albedo_rgba[..., 3] = 1.0

    rough_rgba = np.empty((n, n, 4), dtype=np.float32)
    rough_rgba[..., 0] = rough_map
    rough_rgba[..., 1] = rough_map
    rough_rgba[..., 2] = rough_map
    rough_rgba[..., 3] = 1.0

    data = {
        "tex_size": n,
        "albedo_rgba": np.ascontiguousarray(albedo_rgba, dtype=np.float32),
        "rough_rgba": np.ascontiguousarray(rough_rgba, dtype=np.float32),
        "norm_rgba": np.ascontiguousarray(norm_rgba, dtype=np.float32),
    }
    _ENV_TEX_CACHE[cache_key] = data
    return data


ENV_MAT_TEX_MAP = {
    "Mat_Env_AsphaltCracked":  ("asphalt_cracked",  0.80, 0.20),
    "Mat_Env_SoilCracked":     ("soil_cracked",     0.82, 0.16),
    "Mat_Env_ConcreteCracked": ("concrete_cracked", 0.66, 0.18),
    "Mat_Env_ConcreteDark":    ("concrete_cracked", 0.68, 0.18),
    "Mat_Env_PlasterDamaged":  ("concrete_cracked", 0.62, 0.18),
    "Mat_Env_BrickRuined":     ("brick_ruined",     0.72, 0.18),
    "Mat_Env_RustHeavy":       ("rust_weathered",   0.72, 0.24),
    "Mat_Env_CarPaintFaded":   ("rust_weathered",   0.66, 0.26),
    "Mat_Env_BarrelRed":       ("rust_weathered",   0.68, 0.26),
    "Mat_Env_PoliceWhite":     ("rust_weathered",   0.64, 0.28),
    "Mat_Env_CrateGreen":      ("rust_weathered",   0.68, 0.24),
    "Mat_Env_HazardYellow":    ("rust_weathered",   0.66, 0.24),
    "Mat_Env_MetalScrap":      ("rust_weathered",   0.74, 0.36),
    "Mat_Env_WoodPlank":       ("wood_weathered",   0.72, 0.18),
    "Mat_Env_Sandbag":         ("fabric_burlap",    0.38, 0.14),
    "Mat_Env_MedCanvas":       ("fabric_burlap",    0.38, 0.16),
    "Mat_Env_MedCross":        ("fabric_burlap",    0.36, 0.18),
    "Mat_Env_GrassDry":        ("grass_organic",    0.50, 0.20),
    "Mat_Env_GrassLush":       ("grass_organic",    0.50, 0.20),
    "Mat_Env_MudWet":          ("mud_wet",          0.62, 0.20),
    "Mat_Env_FortressSteel":   ("fortress_steel",   0.72, 0.30),
    "Mat_Env_BarbedWire":      ("fortress_steel",   0.68, 0.32),
    "Mat_Env_HiveFlesh":       ("hive_organic",     0.85, 0.32),
}


def apply_env_pbr_texture(mat, mat_name, base_hex, base_roughness, use_vertex_ao=False):
    """Attach clean seamless BaseColor (optionally Vertex AO multiplied), Roughness, and Normal maps."""
    spec = ENV_MAT_TEX_MAP.get(mat_name)
    if spec is None:
        return False

    arch, norm_strength, spec_ior = spec
    data = _generate_env_archetype(arch, mat_name, base_hex, base_roughness)
    tex_size = data["tex_size"]

    slug = mat_name.replace("Mat_Env_", "").lower()
    img_col = _ensure_packed_env_image(f"Tex_Env_{slug}_BaseColor", data["albedo_rgba"], tex_size, colorspace="sRGB")
    img_rgh = _ensure_packed_env_image(f"Tex_Env_{arch}_Roughness", data["rough_rgba"], tex_size, colorspace="Non-Color")
    img_nrm = _ensure_packed_env_image(f"Tex_Env_{arch}_Normal", data["norm_rgba"], tex_size, colorspace="Non-Color")

    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = float(spec_ior)

    tex_col = nt.nodes.new("ShaderNodeTexImage")
    tex_col.image = img_col
    if use_vertex_ao:
        vcol = nt.nodes.new("ShaderNodeVertexColor")
        vcol.layer_name = "Col"
        mix_col = nt.nodes.new("ShaderNodeMix")
        mix_col.data_type = "RGBA"
        mix_col.blend_type = "MULTIPLY"
        mix_col.inputs["Factor"].default_value = 1.0
        rgba_inputs = [s for s in mix_col.inputs if s.type == "RGBA"]
        rgba_outputs = [s for s in mix_col.outputs if s.type == "RGBA"]
        nt.links.new(tex_col.outputs["Color"], rgba_inputs[0])
        nt.links.new(vcol.outputs["Color"], rgba_inputs[1])
        nt.links.new(rgba_outputs[0], bsdf.inputs["Base Color"])
    else:
        nt.links.new(tex_col.outputs["Color"], bsdf.inputs["Base Color"])

    tex_rgh = nt.nodes.new("ShaderNodeTexImage")
    tex_rgh.image = img_rgh
    nt.links.new(tex_rgh.outputs["Color"], bsdf.inputs["Roughness"])

    tex_nrm = nt.nodes.new("ShaderNodeTexImage")
    tex_nrm.image = img_nrm
    nrm_node = nt.nodes.new("ShaderNodeNormalMap")
    nrm_node.inputs["Strength"].default_value = float(norm_strength)
    nt.links.new(tex_nrm.outputs["Color"], nrm_node.inputs["Color"])
    nt.links.new(nrm_node.outputs["Normal"], bsdf.inputs["Normal"])
    return True
