"""Procedural seamless NumPy PBR texture synthesis & packing for horror mutants."""
import bpy
import numpy as np

TEX_SIZE = 512

_ARCHETYPE_CACHE = {}
_ALBEDO_CACHE = {}


def _hex_to_rgb01(hex_str):
    h = hex_str.lstrip("#")
    return (
        int(h[0:2], 16) / 255.0,
        int(h[2:4], 16) / 255.0,
        int(h[4:6], 16) / 255.0,
    )


def _periodic_value_noise(size, cells, seed):
    rng = np.random.default_rng(seed)
    grid = rng.random((cells, cells), dtype=np.float32)

    coords = np.linspace(0.0, float(cells), size, endpoint=False, dtype=np.float32)
    i0 = np.floor(coords).astype(np.int32) % cells
    i1 = (i0 + 1) % cells
    f = coords - np.floor(coords)
    u = f * f * (3.0 - 2.0 * f)

    ux = u[None, :]
    uy = u[:, None]
    g00 = grid[i0[:, None], i0[None, :]]
    g10 = grid[i0[:, None], i1[None, :]]
    g01 = grid[i1[:, None], i0[None, :]]
    g11 = grid[i1[:, None], i1[None, :]]

    nx0 = g00 * (1.0 - ux) + g10 * ux
    nx1 = g01 * (1.0 - ux) + g11 * ux
    return (nx0 * (1.0 - uy) + nx1 * uy).astype(np.float32)


def _periodic_fbm(size, octaves, seed):
    acc = np.zeros((size, size), dtype=np.float32)
    amp = 0.5
    total_amp = 0.0
    for o in range(octaves):
        cells = min(size // 2, 4 * (2 ** o))
        acc += amp * _periodic_value_noise(size, max(2, cells), seed + o * 31)
        total_amp += amp
        amp *= 0.5
    acc /= max(1e-6, total_amp)
    lo, hi = float(acc.min()), float(acc.max())
    if hi - lo > 1e-6:
        acc = (acc - lo) / (hi - lo)
    return acc


def _periodic_voronoi(size, count, seed):
    rng = np.random.default_rng(seed)
    pts = rng.random((count, 2), dtype=np.float32)

    lin = np.linspace(0.0, 1.0, size, endpoint=False, dtype=np.float32)
    gy, gx = np.meshgrid(lin, lin, indexing="ij")

    d1 = np.full((size, size), 10.0, dtype=np.float32)
    d2 = np.full((size, size), 10.0, dtype=np.float32)
    for px, py in pts:
        dx = np.abs(gx - px)
        dx = np.minimum(dx, 1.0 - dx)
        dy = np.abs(gy - py)
        dy = np.minimum(dy, 1.0 - dy)
        dist = np.sqrt(dx * dx + dy * dy)
        mask1 = dist < d1
        d2 = np.where(mask1, d1, np.minimum(d2, dist))
        d1 = np.where(mask1, dist, d1)

    f1 = np.clip(d1 / max(1e-4, float(d1.max())), 0.0, 1.0)
    edge = d2 - d1
    edge = np.clip(edge / max(1e-4, float(edge.max())), 0.0, 1.0)
    return f1, edge


def _height_to_normal_rgba(height, strength=3.0):
    s = float(strength)
    # Periodic Sobel gradients on tileable height map
    tl = np.roll(np.roll(height, 1, axis=0), 1, axis=1)
    tc = np.roll(height, 1, axis=0)
    tr = np.roll(np.roll(height, 1, axis=0), -1, axis=1)
    ml = np.roll(height, 1, axis=1)
    mr = np.roll(height, -1, axis=1)
    bl = np.roll(np.roll(height, -1, axis=0), 1, axis=1)
    bc = np.roll(height, -1, axis=0)
    br = np.roll(np.roll(height, -1, axis=0), -1, axis=1)

    gx = (tr + 2.0 * mr + br) - (tl + 2.0 * ml + bl)
    gy = (bl + 2.0 * bc + br) - (tl + 2.0 * tc + tr)

    nx = -gx * s
    ny = -gy * s
    nz = np.ones_like(height, dtype=np.float32)
    inv_len = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
    nx *= inv_len
    ny *= inv_len
    nz *= inv_len

    rgba = np.empty((height.shape[0], height.shape[1], 4), dtype=np.float32)
    rgba[..., 0] = np.clip(nx * 0.5 + 0.5, 0.0, 1.0)
    rgba[..., 1] = np.clip(ny * 0.5 + 0.5, 0.0, 1.0)
    rgba[..., 2] = np.clip(nz * 0.5 + 0.5, 0.0, 1.0)
    rgba[..., 3] = 1.0
    return rgba


def _generate_archetype(arch):
    if arch in _ARCHETYPE_CACHE:
        return _ARCHETYPE_CACHE[arch]

    n = TEX_SIZE
    if arch == "necrotic_flesh":
        fbm_a = _periodic_fbm(n, 5, seed=101)
        fbm_b = _periodic_fbm(n, 6, seed=137)
        f1, edge = _periodic_voronoi(n, 42, seed=173)
        vein_ridge = np.abs(fbm_b - 0.5) * 2.0
        vein_mask = np.exp(-vein_ridge * 10.0) * (0.35 + 0.65 * fbm_a)
        pit_mask = np.clip(1.0 - f1 * 2.1, 0.0, 1.0) ** 1.3
        crack_scar = np.exp(-edge * 11.0)
        grime_mask = np.clip(0.50 * pit_mask + 0.35 * (1.0 - fbm_a) + 0.30 * crack_scar, 0.0, 1.0)
        shade_mul = np.clip(0.62 + 0.66 * fbm_a - 0.38 * pit_mask - 0.28 * vein_mask - 0.25 * crack_scar, 0.26, 1.32)
        height = np.clip(0.55 * fbm_a + 0.25 * edge - 0.45 * pit_mask - 0.28 * vein_mask, 0.0, 1.0)
        rough_map = np.clip(0.86 - 0.42 * pit_mask - 0.28 * vein_mask - 0.16 * (1.0 - fbm_b), 0.32, 0.92)
        norm_rgba = _height_to_normal_rgba(height, strength=5.6)

    elif arch == "chitin_armor":
        fbm_a = _periodic_fbm(n, 5, seed=211)
        striation = _periodic_value_noise(n, 64, seed=233)
        striation = np.roll(striation, 1, axis=1) * 0.5 + striation * 0.5
        f1, edge = _periodic_voronoi(n, 34, seed=251)
        crack = np.exp(-edge * 10.0)
        grime_mask = np.clip(0.82 * crack + 0.38 * (1.0 - fbm_a), 0.0, 1.0)
        vein_mask = crack
        shade_mul = np.clip(0.68 + 0.58 * fbm_a + 0.18 * striation - 0.55 * crack, 0.24, 1.32)
        height = np.clip(0.46 * fbm_a + 0.28 * edge + 0.20 * striation - 0.55 * crack, 0.0, 1.0)
        rough_map = np.clip(0.42 + 0.38 * fbm_a + 0.40 * crack, 0.38, 0.94)
        norm_rgba = _height_to_normal_rgba(height, strength=6.8)

    elif arch == "gore_wet":
        fbm_a = _periodic_fbm(n, 5, seed=307)
        fiber = np.abs(_periodic_fbm(n, 6, seed=331) - 0.5) * 2.0
        f1, edge = _periodic_voronoi(n, 30, seed=353)
        vein_mask = np.exp(-fiber * 8.0)
        grime_mask = np.clip(0.65 * (1.0 - fbm_a) + 0.45 * (1.0 - f1), 0.0, 1.0)
        shade_mul = np.clip(0.58 + 0.68 * fbm_a - 0.38 * vein_mask, 0.25, 1.32)
        height = np.clip(0.52 * fbm_a + 0.28 * (1.0 - f1) + 0.24 * vein_mask, 0.0, 1.0)
        rough_map = np.clip(0.12 + 0.26 * fbm_a + 0.12 * (1.0 - edge), 0.12, 0.44)
        norm_rgba = _height_to_normal_rgba(height, strength=5.2)

    elif arch == "bark_vine":
        fbm_a = _periodic_fbm(n, 5, seed=409)
        coarse_y = _periodic_value_noise(n, 12, seed=421)
        fine_x = _periodic_value_noise(n, 72, seed=443)
        ridge = 0.55 * coarse_y + 0.45 * fine_x
        furrow = np.clip(1.0 - ridge * 1.65, 0.0, 1.0)
        grime_mask = np.clip(0.75 * furrow + 0.35 * (1.0 - fbm_a), 0.0, 1.0)
        vein_mask = furrow
        shade_mul = np.clip(0.64 + 0.54 * ridge + 0.22 * fbm_a - 0.44 * furrow, 0.26, 1.30)
        height = np.clip(0.60 * ridge + 0.32 * fbm_a - 0.45 * furrow, 0.0, 1.0)
        rough_map = np.clip(0.58 + 0.28 * fbm_a + 0.18 * furrow, 0.52, 0.94)
        norm_rgba = _height_to_normal_rgba(height, strength=6.2)

    elif arch == "bone_stained":
        fbm_a = _periodic_fbm(n, 5, seed=503)
        streak = _periodic_value_noise(n, 48, seed=521)
        f1, edge = _periodic_voronoi(n, 24, seed=547)
        hairline = np.exp(-edge * 12.0)
        grime_mask = np.clip(0.58 * (1.0 - fbm_a) + 0.58 * hairline, 0.0, 1.0)
        vein_mask = hairline
        shade_mul = np.clip(0.72 + 0.40 * fbm_a + 0.16 * streak - 0.44 * hairline, 0.32, 1.24)
        height = np.clip(0.58 * fbm_a + 0.24 * streak - 0.42 * hairline, 0.0, 1.0)
        rough_map = np.clip(0.32 + 0.28 * fbm_a + 0.22 * hairline, 0.30, 0.76)
        norm_rgba = _height_to_normal_rgba(height, strength=4.2)

    else:  # shroud_stone
        fbm_a = _periodic_fbm(n, 5, seed=607)
        marble = np.abs(np.sin((fbm_a * 5.0 + _periodic_fbm(n, 4, seed=631) * 2.0) * np.pi))
        f1, edge = _periodic_voronoi(n, 24, seed=653)
        crack = np.exp(-edge * 11.0)
        grime_mask = np.clip(0.60 * (1.0 - marble) + 0.56 * crack, 0.0, 1.0)
        vein_mask = crack
        shade_mul = np.clip(0.68 + 0.46 * marble - 0.42 * crack, 0.30, 1.24)
        height = np.clip(0.56 * fbm_a + 0.28 * marble - 0.45 * crack, 0.0, 1.0)
        rough_map = np.clip(0.40 + 0.30 * (1.0 - marble) + 0.20 * crack, 0.38, 0.82)
        norm_rgba = _height_to_normal_rgba(height, strength=4.8)

    rough_rgba = np.empty((n, n, 4), dtype=np.float32)
    rough_rgba[..., 0] = rough_map
    rough_rgba[..., 1] = rough_map
    rough_rgba[..., 2] = rough_map
    rough_rgba[..., 3] = 1.0

    data = {
        "shade_mul": shade_mul.astype(np.float32),
        "grime_mask": grime_mask.astype(np.float32),
        "vein_mask": vein_mask.astype(np.float32),
        "rough_rgba": np.ascontiguousarray(rough_rgba, dtype=np.float32),
        "norm_rgba": np.ascontiguousarray(norm_rgba, dtype=np.float32),
    }
    _ARCHETYPE_CACHE[arch] = data
    return data


MUTANT_MAT_TEX_MAP = {
    # Necrotic / bruised / living corpse skin
    "Mat_MTankSkin":        ("necrotic_flesh", "#241E19", "#281218", 0.72),
    "Mat_MTankBruise":      ("necrotic_flesh", "#170F16", "#2E0C14", 0.75),
    "Mat_ZSkinGrey":        ("necrotic_flesh", "#282622", "#2C181C", 0.68),
    "Mat_ZSkinDark":        ("necrotic_flesh", "#1D1F19", "#261416", 0.68),
    "Mat_ZSkinBruised":     ("necrotic_flesh", "#231E26", "#2E121A", 0.68),
    "Mat_ZSkinGreen":       ("necrotic_flesh", "#262B20", "#2A1816", 0.68),
    "Mat_ZSkinPale":        ("necrotic_flesh", "#3B3936", "#361C20", 0.64),
    "Mat_ZSkinToxic":       ("necrotic_flesh", "#252D1E", "#2C1B14", 0.68),
    "Mat_ZRaffJawFlesh":    ("necrotic_flesh", "#3E1B16", "#4D0E12", 0.72),
    "Mat_MArachUnder":      ("necrotic_flesh", "#1E0C0F", "#380A10", 0.72),
    "Mat_ZLipDead":         ("necrotic_flesh", "#241418", "#3B0E12", 0.68),
    "Mat_ZVeinDark":        ("necrotic_flesh", "#180C12", "#2A080F", 0.72),

    # Calcified chitin / fungal armor / ragged cloth / rebar
    "Mat_MTankArmor":       ("chitin_armor",   "#13110E", "#1A1410", 0.85),
    "Mat_MChitinDark":      ("chitin_armor",   "#0B0909", "#18110F", 0.80),
    "Mat_MChitinMid":       ("chitin_armor",   "#181310", "#241914", 0.78),
    "Mat_MArachChitin":     ("chitin_armor",   "#0A0C10", "#181B22", 0.82),
    "Mat_ZFungusCap":       ("chitin_armor",   "#382B1E", "#2B1912", 0.75),
    "Mat_ZFungusDark":      ("chitin_armor",   "#180D0A", "#1E110C", 0.75),
    "Mat_ZFungusRoot":      ("chitin_armor",   "#261E16", "#1D140E", 0.75),
    "Mat_ZClothDirty":      ("chitin_armor",   "#1F1E1B", "#161412", 0.72),
    "Mat_ZRebar":           ("chitin_armor",   "#2B120C", "#3D180E", 0.78),

    # Wet crimson gore / petals / oral cavity
    "Mat_ZBloodFresh":      ("gore_wet",       "#240406", "#3E0609", 0.68),
    "Mat_ZBloodDried":      ("gore_wet",       "#180405", "#290507", 0.72),
    "Mat_ZFlesh":           ("gore_wet",       "#2C0A0C", "#420B0F", 0.72),
    "Mat_MTongueWet":       ("gore_wet",       "#28060B", "#400910", 0.70),
    "Mat_ZMouth":           ("gore_wet",       "#100405", "#1F0608", 0.55),
    "Mat_ZRaffPetal":       ("gore_wet",       "#320608", "#4A090B", 0.75),
    "Mat_ZRaffPetalDark":   ("gore_wet",       "#190304", "#280406", 0.72),
    "Mat_ZRaffPetalBright": ("gore_wet",       "#460A09", "#5C0C0E", 0.72),
    "Mat_ZRaffRing":        ("gore_wet",       "#380D0A", "#4C120E", 0.72),
    "Mat_ZFungusGill":      ("gore_wet",       "#2C130E", "#3B1810", 0.70),

    # Anisotropic swamp bark / thorny leaves / vines
    "Mat_ZBarkDark":        ("bark_vine",      "#0E0A07", "#140F0A", 0.85),
    "Mat_ZBarkMid":         ("bark_vine",      "#19120C", "#21170F", 0.82),
    "Mat_ZLeafDark":        ("bark_vine",      "#0B1409", "#111E0E", 0.72),
    "Mat_ZLeafMid":         ("bark_vine",      "#14240E", "#1D3214", 0.70),
    "Mat_ZVinePale":        ("bark_vine",      "#1D2B17", "#26381D", 0.72),

    # Root-stained bone, claws, spikes, spots
    "Mat_MScytheBone":      ("bone_stained",   "#382E24", "#281C15", 0.72),
    "Mat_ZBone":            ("bone_stained",   "#4D4437", "#362B20", 0.68),
    "Mat_ZRaffSpot":        ("bone_stained",   "#5C4A34", "#423322", 0.62),
    "Mat_ZRaffStamen":      ("bone_stained",   "#4A3412", "#34220B", 0.68),
    "Mat_ZFungusPale":      ("bone_stained",   "#564A38", "#3D3122", 0.65),

    # Darkened ash-marble bone & shroud skin
    "Mat_MShroudBone":      ("shroud_stone",   "#3B3734", "#282326", 0.68),
    "Mat_MShroudDark":      ("shroud_stone",   "#110F14", "#1A151D", 0.75),
    "Mat_MShroudSkin":      ("shroud_stone",   "#28252C", "#1E1922", 0.72),
}


def _get_albedo_rgba(mat_name, base_hex, arch, grime_hex, vein_hex):
    key = (mat_name, base_hex, arch, grime_hex, vein_hex)
    if key in _ALBEDO_CACHE:
        return _ALBEDO_CACHE[key]

    data = _generate_archetype(arch)
    n = TEX_SIZE
    base = np.array(_hex_to_rgb01(base_hex), dtype=np.float32)[None, None, :]
    grime = np.array(_hex_to_rgb01(grime_hex), dtype=np.float32)[None, None, :]
    vein = np.array(_hex_to_rgb01(vein_hex), dtype=np.float32)[None, None, :]

    shaded = np.clip(base * data["shade_mul"][..., None], 0.0, 1.0)
    gm = (data["grime_mask"] * 0.76)[..., None]
    vm = (data["vein_mask"] * 0.82)[..., None]
    rgb = shaded * (1.0 - gm) + grime * gm
    rgb = rgb * (1.0 - vm) + vein * vm

    rgba = np.empty((n, n, 4), dtype=np.float32)
    rgba[..., :3] = np.clip(rgb, 0.0, 1.0)
    rgba[..., 3] = 1.0
    out = np.ascontiguousarray(rgba, dtype=np.float32)
    _ALBEDO_CACHE[key] = out
    return out


def _ensure_packed_image(name, rgba_2d, colorspace="sRGB"):
    img = bpy.data.images.get(name)
    if img is None:
        img = bpy.data.images.new(name=name, width=TEX_SIZE, height=TEX_SIZE, alpha=False, float_buffer=False)
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(rgba_2d.ravel())
    img.pack()
    return img


def apply_mutant_pbr_texture(mat, mat_name, base_hex, base_roughness):
    """Attach packed seamless Albedo, Roughness, and Normal maps onto mapped mutant materials."""
    spec = MUTANT_MAT_TEX_MAP.get(mat_name)
    if spec is None:
        return False

    arch, grime_hex, vein_hex, norm_strength = spec
    data = _generate_archetype(arch)

    albedo_rgba = _get_albedo_rgba(mat_name, base_hex, arch, grime_hex, vein_hex)
    img_col = _ensure_packed_image(f"Tex_{mat_name}_BaseColor", albedo_rgba, colorspace="sRGB")
    img_rgh = _ensure_packed_image(f"Tex_{arch}_Roughness", data["rough_rgba"], colorspace="Non-Color")
    img_nrm = _ensure_packed_image(f"Tex_{arch}_Normal", data["norm_rgba"], colorspace="Non-Color")

    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    # Maintain existing metallic/IOR feel
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.35

    tex_col = nt.nodes.new("ShaderNodeTexImage")
    tex_col.image = img_col
    nt.links.new(tex_col.outputs["Color"], bsdf.inputs["Base Color"])

    tex_rgh = nt.nodes.new("ShaderNodeTexImage")
    tex_rgh.image = img_rgh
    nt.links.new(tex_rgh.outputs["Color"], bsdf.inputs["Roughness"])

    tex_nrm = nt.nodes.new("ShaderNodeTexImage")
    tex_nrm.image = img_nrm
    nrm_node = nt.nodes.new("ShaderNodeNormalMap")
    nrm_node.inputs["Strength"].default_value = float(norm_strength) * 1.45
    nt.links.new(tex_nrm.outputs["Color"], nrm_node.inputs["Color"])
    nt.links.new(nrm_node.outputs["Normal"], bsdf.inputs["Normal"])
    return True
