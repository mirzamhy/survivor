"""Clean stylized horror PBR textures per mutant: countershading, roughness contrast, SSS & zero visual clutter."""
import bpy
import numpy as np

TEX_SIZE = 512

_ARCHETYPE_CACHE = {}


def _hex_to_rgb01(hex_str):
    h = hex_str.lstrip("#")
    return (
        int(h[0:2], 16) / 255.0,
        int(h[2:4], 16) / 255.0,
        int(h[4:6], 16) / 255.0,
    )


def _c(hex_str):
    return np.array(_hex_to_rgb01(hex_str), dtype=np.float32)[None, None, :]


def _mix(rgb_a, rgb_b, mask):
    m = np.clip(mask, 0.0, 1.0)[..., None]
    return rgb_a * (1.0 - m) + rgb_b * m


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
    vals = rng.random(count, dtype=np.float32)

    lin = np.linspace(0.0, 1.0, size, endpoint=False, dtype=np.float32)
    gy, gx = np.meshgrid(lin, lin, indexing="ij")

    d1 = np.full((size, size), 10.0, dtype=np.float32)
    d2 = np.full((size, size), 10.0, dtype=np.float32)
    cell_id = np.zeros((size, size), dtype=np.float32)
    for idx, (px, py) in enumerate(pts):
        dx = np.abs(gx - px)
        dx = np.minimum(dx, 1.0 - dx)
        dy = np.abs(gy - py)
        dy = np.minimum(dy, 1.0 - dy)
        dist = np.sqrt(dx * dx + dy * dy)
        mask1 = dist < d1
        d2 = np.where(mask1, d1, np.minimum(d2, dist))
        cell_id = np.where(mask1, vals[idx], cell_id)
        d1 = np.where(mask1, dist, d1)

    f1 = np.clip(d1 / max(1e-4, float(d1.max())), 0.0, 1.0)
    edge = d2 - d1
    edge = np.clip(edge / max(1e-4, float(edge.max())), 0.0, 1.0)
    return f1, edge, cell_id


def _domain_warp(field, wx, wy, amp_px):
    n = field.shape[0]
    yy, xx = np.meshgrid(
        np.arange(n, dtype=np.float32),
        np.arange(n, dtype=np.float32),
        indexing="ij",
    )
    sx = (xx + (wx - 0.5) * 2.0 * amp_px) % n
    sy = (yy + (wy - 0.5) * 2.0 * amp_px) % n
    x0 = np.floor(sx).astype(np.int32) % n
    y0 = np.floor(sy).astype(np.int32) % n
    x1 = (x0 + 1) % n
    y1 = (y0 + 1) % n
    fx = sx - np.floor(sx)
    fy = sy - np.floor(sy)
    return (
        field[y0, x0] * (1.0 - fx) * (1.0 - fy)
        + field[y0, x1] * fx * (1.0 - fy)
        + field[y1, x0] * (1.0 - fx) * fy
        + field[y1, x1] * fx * fy
    ).astype(np.float32)


def _height_to_normal_rgba(height, strength=2.6):
    s = float(strength)
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


def _grid_coords(n):
    lin = np.linspace(0.0, 1.0, n, endpoint=False, dtype=np.float32)
    return np.meshgrid(lin, lin, indexing="ij")


def _generate_archetype(arch):
    if arch in _ARCHETYPE_CACHE:
        return _ARCHETYPE_CACHE[arch]

    n = TEX_SIZE
    gy, gx = _grid_coords(n)

    # --- MUTANT #1: RAFFLESIA BLOOD-FLOWER ---
    if arch in ("rafflesia_petal", "rafflesia_petal_dark", "rafflesia_petal_bright"):
        fbm_a = _periodic_fbm(n, 5, seed=101)
        fbm_b = _periodic_fbm(n, 6, seed=107)
        wx = _periodic_fbm(n, 4, seed=109)
        wy = _periodic_fbm(n, 4, seed=113)
        # Tactile velvety fleshy petal warts/pores in Normal Map — ZERO loud white polka-dots in Albedo!
        pore_f1, _, cid = _periodic_voronoi(n, 38, seed=127)
        wart = np.clip((0.11 - _domain_warp(pore_f1, wx, wy, 6.0)) / 0.055, 0.0, 1.0)
        vein_f = _domain_warp(np.abs(np.sin((gx * 6.0 + fbm_b * 1.1) * np.pi)), wx, wy, 14.0)
        vein = np.exp(-vein_f * 8.5)

        if arch == "rafflesia_petal_dark":
            rgb = _mix(_c("#350508"), _c("#640C10"), fbm_a * 0.90)
            rgb = _mix(rgb, _c("#200204"), vein * 0.65)
            rgb = _mix(rgb, _c("#882824"), wart * (cid > 0.65).astype(np.float32) * 0.24)
        elif arch == "rafflesia_petal_bright":
            rgb = _mix(_c("#8A1513"), _c("#C82E24"), fbm_a * 0.90)
            rgb = _mix(rgb, _c("#580A0D"), vein * 0.45)
            rgb = _mix(rgb, _c("#DF6B52"), wart * (cid > 0.58).astype(np.float32) * 0.30)
        else:
            rgb = _mix(_c("#5B0A0E"), _c("#9E1A17"), fbm_a * 0.90)
            rgb = _mix(rgb, _c("#360508"), vein * 0.55)
            rgb = _mix(rgb, _c("#BA4E3E"), wart * (cid > 0.62).astype(np.float32) * 0.26)

        height = np.clip(0.50 * fbm_b + 0.34 * wart - 0.22 * vein + 0.16 * fbm_a, 0.0, 1.0)
        rough_map = np.clip(0.50 + 0.18 * (1.0 - fbm_a) - 0.12 * wart, 0.42, 0.72)
        norm_rgba = _height_to_normal_rgba(height, strength=5.0)

    elif arch == "rafflesia_jaw":
        fbm_a = _periodic_fbm(n, 5, seed=179)
        fbm_b = _periodic_fbm(n, 6, seed=181)
        pore_f1, _, _ = _periodic_voronoi(n, 40, seed=183)
        vein = np.exp(-np.abs(fbm_b - 0.5) * 14.0) * (0.35 + 0.65 * fbm_a)
        # Warm pale fleshy beak-maw contrasting cleanly inside the deep crimson flower!
        rgb = _mix(_c("#A67860"), _c("#DCB297"), fbm_a)
        rgb = _mix(rgb, _c("#6E1B1F"), vein * 0.48)
        height = np.clip(0.55 * fbm_a + 0.25 * (1.0 - pore_f1) + 0.20 * vein, 0.0, 1.0)
        rough_map = np.clip(0.40 + 0.18 * fbm_a - 0.10 * vein, 0.34, 0.58)
        norm_rgba = _height_to_normal_rgba(height, strength=4.6)

    elif arch == "rafflesia_bark":
        # High-relief gnarled swamp-root bark (NO high-contrast zebra stripes!)
        fbm_a = _periodic_fbm(n, 5, seed=149)
        fbm_b = _periodic_fbm(n, 6, seed=153)
        wx = _periodic_fbm(n, 4, seed=151)
        wy = _periodic_fbm(n, 4, seed=157)
        grain = _periodic_value_noise(n, 32, seed=159)
        bark_f = _domain_warp(0.60 * fbm_b + 0.40 * grain, wx, wy, 12.0)
        crevice = np.clip((0.42 - bark_f) * 2.4, 0.0, 1.0)
        ridge = np.clip((bark_f - 0.58) * 2.3, 0.0, 1.0)
        moss = np.clip((fbm_a - 0.64) * 2.4 * (0.4 + 0.6 * crevice), 0.0, 1.0)

        rgb = _mix(_c("#2B1E14"), _c("#523B28"), bark_f)
        rgb = _mix(rgb, _c("#6B4F37"), ridge * 0.55)
        rgb = _mix(rgb, _c("#160E09"), crevice * 0.78)
        rgb = _mix(rgb, _c("#335221"), moss * 0.62)
        height = np.clip(0.58 * bark_f + 0.24 * ridge - 0.38 * crevice + 0.14 * grain, 0.0, 1.0)
        rough_map = np.clip(0.74 + 0.16 * fbm_a - 0.06 * ridge, 0.68, 0.92)
        norm_rgba = _height_to_normal_rgba(height, strength=5.6)

    elif arch == "rafflesia_vine":
        fbm_a = _periodic_fbm(n, 5, seed=163)
        fbm_b = _periodic_fbm(n, 6, seed=169)
        fine = _periodic_value_noise(n, 36, seed=173)
        blend = 0.55 * fbm_a + 0.30 * fbm_b + 0.15 * fine
        rgb = _mix(_c("#1E3816"), _c("#446B2C"), blend)
        rgb = _mix(rgb, _c("#5F8940"), np.clip((blend - 0.60) * 2.2, 0.0, 1.0) * 0.48)
        height = np.clip(0.55 * fbm_b + 0.30 * fine + 0.15 * fbm_a, 0.0, 1.0)
        rough_map = np.clip(0.52 + 0.18 * fbm_a, 0.46, 0.74)
        norm_rgba = _height_to_normal_rgba(height, strength=4.8)

    # --- MUTANT #2: SCYTHE STALKER ---
    elif arch in ("stalker_chitin", "stalker_chitin_mid"):
        fbm_a = _periodic_fbm(n, 5, seed=211)
        fbm_b = _periodic_fbm(n, 6, seed=217)
        fine = _periodic_value_noise(n, 40, seed=221)
        pore_f1, _, _ = _periodic_voronoi(n, 36, seed=223)
        # Tactile pitted/brushed dark insectoid exoskeleton (ZERO mirror-chrome Voronoi facets!)
        pit = np.clip((0.08 - pore_f1) / 0.045, 0.0, 1.0)
        crest = np.clip((fbm_b - 0.56) * 2.2, 0.0, 1.0)

        if arch == "stalker_chitin_mid":
            rgb = _mix(_c("#302621"), _c("#54453A"), 0.65 * fbm_b + 0.35 * fbm_a)
            rgb = _mix(rgb, _c("#7A6857"), crest * 0.58)
            rgb = _mix(rgb, _c("#181210"), pit * 0.65)
        else:
            rgb = _mix(_c("#1E1815"), _c("#3A2F28"), 0.65 * fbm_b + 0.35 * fbm_a)
            rgb = _mix(rgb, _c("#5A4C3F"), crest * 0.50)
            rgb = _mix(rgb, _c("#100B0A"), pit * 0.70)

        height = np.clip(0.56 * fbm_b + 0.24 * fine + 0.20 * crest - 0.30 * pit, 0.0, 1.0)
        rough_map = np.clip(0.56 + 0.20 * fbm_a + 0.10 * pit - 0.08 * crest, 0.50, 0.82)
        norm_rgba = _height_to_normal_rgba(height, strength=5.0)

    elif arch == "stalker_flesh":
        fbm_a = _periodic_fbm(n, 5, seed=241)
        fbm_b = _periodic_fbm(n, 6, seed=247)
        wx = _periodic_fbm(n, 4, seed=251)
        wy = _periodic_fbm(n, 4, seed=257)
        pore_f1, _, _ = _periodic_voronoi(n, 42, seed=263)
        cap = np.exp(-np.abs(_domain_warp(fbm_b - 0.5, wx, wy, 12.0)) * 16.0)
        # Countershaded taut corpse hide (ZERO zebra stripes!) contrasting cleanly against dark chitin
        rgb = _mix(_c("#6D665D"), _c("#968E82"), fbm_a)
        rgb = _mix(rgb, _c("#472D33"), np.clip((0.46 - fbm_b) * 2.0, 0.0, 1.0) * 0.60)
        rgb = _mix(rgb, _c("#68181D"), cap * 0.48)
        height = np.clip(0.55 * fbm_b + 0.25 * fbm_a + 0.20 * pore_f1 + 0.14 * cap, 0.0, 1.0)
        rough_map = np.clip(0.48 + 0.18 * fbm_a - 0.10 * cap, 0.42, 0.68)
        norm_rgba = _height_to_normal_rgba(height, strength=4.6)

    elif arch == "stalker_bone":
        fbm_a = _periodic_fbm(n, 5, seed=271)
        fbm_b = _periodic_fbm(n, 6, seed=277)
        fine = _periodic_value_noise(n, 38, seed=281)
        blood_patch = np.clip((fbm_a - 0.70) * 2.8, 0.0, 1.0)
        # Rule #2 Keratin Contrast: carved pale ivory-bone scythe & fangs vs dark chitin
        rgb = _mix(_c("#ABA088"), _c("#E2D7BE"), 0.55 * fbm_a + 0.45 * fbm_b)
        rgb = _mix(rgb, _c("#5C1116"), blood_patch * 0.68)
        height = np.clip(0.52 * fbm_b + 0.32 * fine + 0.16 * fbm_a, 0.0, 1.0)
        rough_map = np.clip(0.46 + 0.20 * fbm_a - 0.16 * blood_patch, 0.30, 0.70)
        norm_rgba = _height_to_normal_rgba(height, strength=4.4)

    # --- MUTANT #3: THORN SHROUD SERAPH (Ref-1 Sculpted Gothic Stone-Bone & Veined Flesh) ---
    elif arch == "shroud_vein_skin":
        fbm_a = _periodic_fbm(n, 5, seed=307)
        fbm_b = _periodic_fbm(n, 6, seed=309)
        wx = _periodic_fbm(n, 4, seed=311)
        wy = _periodic_fbm(n, 4, seed=313)
        r1 = _domain_warp(np.abs(_periodic_fbm(n, 5, seed=317) - 0.5), wx, wy, 16.0)
        trunk_vein = np.exp(-r1 * 20.0)
        # Pale weathered ash-alabaster skin with subtle sculpted veins (harmonious with ash-slate petals!)
        rgb = _mix(_c("#8B8694"), _c("#BAB4C3"), fbm_a)
        rgb = _mix(rgb, _c("#4A4056"), np.exp(-r1 * 8.0) * 0.38)
        rgb = _mix(rgb, _c("#282132"), trunk_vein * 0.72)
        height = np.clip(0.55 * fbm_b + 0.25 * fbm_a + 0.24 * trunk_vein, 0.0, 1.0)
        rough_map = np.clip(0.48 + 0.14 * fbm_a - 0.08 * trunk_vein, 0.42, 0.66)
        norm_rgba = _height_to_normal_rgba(height, strength=4.0)

    elif arch == "shroud_carved_bone":
        # Sculpted medium ash-slate / carved gothic bone petals & filigree (ZERO Voronoi cobblestones!)
        fbm_a = _periodic_fbm(n, 5, seed=331)
        fbm_b = _periodic_fbm(n, 6, seed=337)
        fine = _periodic_value_noise(n, 36, seed=341)
        flute = _domain_warp(np.sin((gx * 5.0 + fbm_b * 0.7) * np.pi) * 0.5 + 0.5, fbm_a, fbm_b, 9.0)
        crest = np.clip((0.55 * flute + 0.45 * fbm_b - 0.52) * 2.2, 0.0, 1.0)
        rgb = _mix(_c("#504959"), _c("#7D7688"), 0.50 * flute + 0.50 * fbm_a)
        rgb = _mix(rgb, _c("#A29BAC"), crest * 0.58)
        height = np.clip(0.50 * flute + 0.32 * fbm_b + 0.18 * fine, 0.0, 1.0)
        rough_map = np.clip(0.56 + 0.18 * (1.0 - fbm_a) - 0.08 * crest, 0.48, 0.76)
        norm_rgba = _height_to_normal_rgba(height, strength=4.8)

    elif arch == "shroud_obsidian_crown":
        # Deep smoked obsidian-slate for inner petal undersides, stilt cores & dark root veins
        fbm_a = _periodic_fbm(n, 5, seed=347)
        fbm_b = _periodic_fbm(n, 6, seed=349)
        flute = _domain_warp(np.sin((gx * 5.0 + fbm_b * 0.8) * np.pi) * 0.5 + 0.5, fbm_a, fbm_b, 8.0)
        rgb = _mix(_c("#181420"), _c("#352E40"), 0.50 * flute + 0.50 * fbm_a)
        rgb = _mix(rgb, _c("#524960"), np.clip((fbm_b - 0.64) * 2.4, 0.0, 1.0) * 0.45)
        height = np.clip(0.52 * flute + 0.38 * fbm_b, 0.0, 1.0)
        rough_map = np.clip(0.64 + 0.18 * (1.0 - fbm_a), 0.58, 0.84)
        norm_rgba = _height_to_normal_rgba(height, strength=4.4)

    # --- MUTANT #4: ARACHNID MAW (Restored Historical Venom-Spot Glossy Beetle Chitin + Deeper Dark Cavities) ---
    elif arch == "arachnid_carapace":
        fbm_a = _periodic_fbm(n, 5, seed=401)
        f1, edge, cid = _periodic_voronoi(n, 32, seed=409)
        pores, _, _ = _periodic_voronoi(n, 85, seed=419)
        # Bold venomous acid-lime spider warning spots ringed in jet-black + glossy blue-black armor
        f1_w = _domain_warp(f1, _periodic_fbm(n, 3, seed=411), _periodic_fbm(n, 3, seed=413), 7.0)
        cell_on = (cid > 0.68).astype(np.float32)
        spot_mask = np.clip((0.14 - f1_w) / 0.04, 0.0, 1.0) * cell_on
        spot_ring = np.clip((0.21 - f1_w) / 0.04, 0.0, 1.0) * cell_on * (1.0 - spot_mask)
        pit = np.clip(1.0 - pores * 2.8, 0.0, 1.0)

        rgb = _mix(_c("#0E131A"), _c("#26313B"), fbm_a * 0.85)
        rgb = _mix(rgb, _c("#05070A"), np.clip(spot_ring + pit * 0.68, 0.0, 1.0))
        rgb = _mix(rgb, _c("#8AE024"), spot_mask * (0.75 + 0.25 * fbm_a))
        height = np.clip(0.55 * fbm_a + 0.30 * spot_mask - 0.40 * pit, 0.0, 1.0)
        rough_map = np.clip(0.26 + 0.24 * fbm_a + 0.16 * pit - 0.06 * spot_mask, 0.22, 0.56)
        norm_rgba = _height_to_normal_rgba(height, strength=5.6)

    elif arch == "arachnid_underbelly":
        fbm_a = _periodic_fbm(n, 5, seed=431)
        fbm_b = _periodic_fbm(n, 6, seed=435)
        wx = _periodic_fbm(n, 4, seed=433)
        wy = _periodic_fbm(n, 4, seed=439)
        seg = np.sin((gy * 4.0 + wx * 0.6) * 2.0 * np.pi) * 0.5 + 0.5
        acid_vein = np.exp(-np.abs(_domain_warp(fbm_a - 0.5, wx, wy, 14.0)) * 22.0)

        rgb = _mix(_c("#260B10"), _c("#581C21"), 0.42 * seg + 0.58 * fbm_b)
        rgb = _mix(rgb, _c("#14060A"), np.clip(1.0 - fbm_b * 1.4, 0.0, 1.0) * 0.72)
        rgb = _mix(rgb, _c("#68BA22"), acid_vein * 0.52)
        height = np.clip(0.45 * seg + 0.45 * fbm_b, 0.0, 1.0)
        rough_map = np.clip(0.32 + 0.24 * (1.0 - fbm_b), 0.26, 0.62)
        norm_rgba = _height_to_normal_rgba(height, strength=5.2)

    # --- MUTANT #5: BILE JUGGERNAUT (Restored Historical Pox-Skin w/ Yellow-Amber Blisters & Stratified Fungal Plates) ---
    elif arch == "juggernaut_pox_skin":
        fbm_a = _periodic_fbm(n, 5, seed=503)
        fbm_b = _periodic_fbm(n, 6, seed=509)
        wx = _periodic_fbm(n, 4, seed=521)
        wy = _periodic_fbm(n, 4, seed=523)

        # Broad purple necrosis bruises + dual-pass veins (wide deep blue-purple + thin crimson capillaries)
        bruise = np.clip((fbm_a - 0.50) * 2.4, 0.0, 1.0)
        deep_vein = np.exp(-np.abs(_domain_warp(fbm_a - 0.5, wx, wy, 20.0)) * 11.0)
        capillary = np.exp(-np.abs(_domain_warp(fbm_b - 0.5, wy, wx, 16.0)) * 22.0)

        # Infected yellow-amber pox lesions + 90-cell fine micro-pores (exact historical look!)
        f1, _, cid = _periodic_voronoi(n, 24, seed=541)
        f1_w = _domain_warp(f1, wx, wy, 8.0)
        pore_f1, _, _ = _periodic_voronoi(n, 90, seed=547)
        cell_on = (cid > 0.80).astype(np.float32)
        sore_core = np.clip((0.092 - f1_w) / 0.030, 0.0, 1.0) * cell_on
        sore_halo = np.clip((0.190 - f1_w) / 0.045, 0.0, 1.0) * cell_on * (1.0 - sore_core)
        skin_pores = np.clip(1.0 - pore_f1 * 2.5, 0.0, 1.0)

        rgb = _mix(_c("#3E3A31"), _c("#605A4D"), fbm_b)
        rgb = _mix(rgb, _c("#2E1D2D"), np.clip(bruise * 0.85 + deep_vein * 0.72, 0.0, 1.0))
        rgb = _mix(rgb, _c("#5A121B"), np.clip(capillary * 0.65 + sore_halo * 0.88, 0.0, 1.0))
        rgb = _mix(rgb, _c("#BA892C"), sore_core * 0.94)
        rgb = _mix(rgb, _c("#1B1414"), skin_pores * 0.45)

        height = np.clip(0.50 * fbm_b + 0.38 * sore_core - 0.16 * sore_halo - 0.25 * skin_pores + 0.16 * deep_vein, 0.0, 1.0)
        rough_map = np.clip(0.78 - 0.46 * sore_core - 0.22 * sore_halo - 0.18 * capillary, 0.26, 0.86)
        norm_rgba = _height_to_normal_rgba(height, strength=6.2)

    elif arch == "juggernaut_fungal_plate":
        fbm_a = _periodic_fbm(n, 5, seed=557)
        fbm_b = _periodic_fbm(n, 6, seed=559)
        wx = _periodic_fbm(n, 4, seed=563)
        wy = _periodic_fbm(n, 4, seed=569)
        f1, edge, cid = _periodic_voronoi(n, 18, seed=571)

        # Historical weathered craggy Bloater fungal crust + crisp edge highlights + amber spore dust
        strata = _domain_warp(np.sin(f1 * 12.0 + fbm_a * 4.5) * 0.5 + 0.5, wx, wy, 14.0)
        crack = np.exp(-edge * 13.0)
        edge_highlight = np.exp(-np.abs(edge - 0.08) * 18.0) * fbm_b
        spore_dust = np.clip((crack * 0.6 + (1.0 - fbm_a) * 0.55 - 0.52) * 2.0, 0.0, 1.0)

        rgb = _mix(_c("#201C16"), _c("#423B2F"), 0.55 * strata + 0.45 * fbm_b)
        rgb = _mix(rgb, _c("#6E634E"), edge_highlight * 0.72)
        rgb = _mix(rgb, _c("#0B0908"), crack * 0.92)
        rgb = _mix(rgb, _c("#825418"), spore_dust * 0.58)
        height = np.clip(0.45 * strata + 0.35 * fbm_b - 0.60 * crack + 0.18 * edge_highlight, 0.0, 1.0)
        rough_map = np.clip(0.54 + 0.30 * crack + 0.18 * fbm_a, 0.46, 0.94)
        norm_rgba = _height_to_normal_rgba(height, strength=6.8)

    elif arch == "juggernaut_cloth":
        # Tactile weathered dark leather/muddy fabric — ZERO sin() plaid checkerboard!
        fbm_a = _periodic_fbm(n, 5, seed=577)
        fbm_b = _periodic_fbm(n, 6, seed=587)
        fine = _periodic_value_noise(n, 40, seed=593)
        fold_hi = np.clip((fbm_b - 0.58) * 2.2, 0.0, 1.0)
        blood = np.clip((fbm_a - 0.54) * 2.8, 0.0, 1.0)

        rgb = _mix(_c("#1F1D19"), _c("#3D372E"), 0.68 * fbm_b + 0.32 * fine)
        rgb = _mix(rgb, _c("#584F42"), fold_hi * 0.48)
        rgb = _mix(rgb, _c("#12100D"), np.clip((0.40 - fbm_b) * 2.0, 0.0, 1.0) * 0.68)
        rgb = _mix(rgb, _c("#3B0A0C"), blood * 0.82)
        height = np.clip(0.62 * fbm_b + 0.32 * fine, 0.0, 1.0)
        rough_map = np.clip(0.82 - 0.28 * blood + 0.08 * fbm_a, 0.48, 0.94)
        norm_rgba = _height_to_normal_rgba(height, strength=4.8)

    elif arch == "void_mouth":
        # Visceral wet ribbed crimson-black pharyngeal gullet (restores Arachnid's ribbed inner throat!)
        fbm_a = _periodic_fbm(n, 5, seed=607)
        wx = _periodic_fbm(n, 4, seed=613)
        wy = _periodic_fbm(n, 4, seed=617)
        fiber = _domain_warp(np.sin((gx * 16.0 + fbm_a * 1.6) * np.pi) * 0.5 + 0.5, wx, wy, 12.0)
        rgb = _mix(_c("#180306"), _c("#580C11"), fiber * 0.72 + 0.28 * fbm_a)
        height = np.clip(0.62 * fiber + 0.28 * fbm_a, 0.0, 1.0)
        rough_map = np.clip(0.18 + 0.20 * fbm_a, 0.16, 0.40)
        norm_rgba = _height_to_normal_rgba(height, strength=5.0)

    else:  # gore_wet (ultra-wet arterial gums, tongues, open wounds)
        fbm_a = _periodic_fbm(n, 5, seed=607)
        wx = _periodic_fbm(n, 4, seed=613)
        wy = _periodic_fbm(n, 4, seed=617)
        fiber = _domain_warp(np.sin((gx * 16.0 + fbm_a * 1.6) * np.pi) * 0.5 + 0.5, wx, wy, 12.0)
        rgb = _mix(_c("#2C0508"), _c("#781116"), fiber * 0.72 + 0.28 * fbm_a)
        height = np.clip(0.60 * fiber + 0.30 * fbm_a, 0.0, 1.0)
        rough_map = np.clip(0.20 + 0.22 * fbm_a, 0.18, 0.44)
        norm_rgba = _height_to_normal_rgba(height, strength=4.8)

    albedo_rgba = np.empty((n, n, 4), dtype=np.float32)
    albedo_rgba[..., :3] = np.clip(rgb * 1.10, 0.0, 1.0)
    albedo_rgba[..., 3] = 1.0

    rough_rgba = np.empty((n, n, 4), dtype=np.float32)
    rough_rgba[..., 0] = rough_map
    rough_rgba[..., 1] = rough_map
    rough_rgba[..., 2] = rough_map
    rough_rgba[..., 3] = 1.0

    data = {
        "albedo_rgba": np.ascontiguousarray(albedo_rgba, dtype=np.float32),
        "rough_rgba": np.ascontiguousarray(rough_rgba, dtype=np.float32),
        "norm_rgba": np.ascontiguousarray(norm_rgba, dtype=np.float32),
    }
    _ARCHETYPE_CACHE[arch] = data
    return data


# Material -> (signature_pattern_archetype, normal_strength, specular_ior, sss_weight)
MUTANT_MAT_TEX_MAP = {
    # Mutant #1: Rafflesia Blood-Flower
    "Mat_ZRaffPetal":       ("rafflesia_petal",        0.95, 0.26, 0.34),
    "Mat_ZRaffPetalDark":   ("rafflesia_petal_dark",   0.98, 0.22, 0.22),
    "Mat_ZRaffPetalBright": ("rafflesia_petal_bright", 0.90, 0.28, 0.38),
    "Mat_ZRaffRing":        ("rafflesia_petal_dark",   0.95, 0.24, 0.26),
    "Mat_ZBarkDark":        ("rafflesia_bark",         1.12, 0.18, 0.00),
    "Mat_ZBarkMid":         ("rafflesia_bark",         1.08, 0.20, 0.00),
    "Mat_ZLeafDark":        ("rafflesia_vine",         0.92, 0.22, 0.18),
    "Mat_ZLeafMid":         ("rafflesia_vine",         0.94, 0.24, 0.22),
    "Mat_ZVinePale":        ("rafflesia_vine",         0.96, 0.26, 0.26),
    "Mat_ZRaffJawFlesh":    ("rafflesia_jaw",          0.88, 0.32, 0.32),
    "Mat_ZRaffSpot":        ("stalker_bone",           0.75, 0.24, 0.08),
    "Mat_ZRaffStamen":      ("stalker_bone",           0.78, 0.24, 0.10),

    # Mutant #2: Scythe Stalker
    "Mat_MChitinDark":      ("stalker_chitin",         0.98, 0.22, 0.00),
    "Mat_MChitinMid":       ("stalker_chitin_mid",     0.96, 0.24, 0.00),
    "Mat_ZSkinGrey":        ("stalker_flesh",          0.92, 0.28, 0.28),
    "Mat_MScytheBone":      ("stalker_bone",           0.86, 0.26, 0.10),
    "Mat_ZBone":            ("stalker_bone",           0.82, 0.26, 0.10),

    # Mutant #3: Thorn Shroud Seraph
    "Mat_MShroudSkin":      ("shroud_vein_skin",       0.78, 0.28, 0.26),
    "Mat_MShroudBone":      ("shroud_carved_bone",     0.92, 0.24, 0.06),
    "Mat_MShroudDark":      ("shroud_obsidian_crown",  0.86, 0.20, 0.00),

    # Mutant #4: Arachnid Maw (Historical glossy beetle-chitin + toxic green spots + ribbed throat)
    "Mat_MArachChitin":     ("arachnid_carapace",      1.30, 0.40, 0.00),
    "Mat_MArachUnder":      ("arachnid_underbelly",    1.25, 0.38, 0.20),

    # Mutant #5: Bile Juggernaut (Historical pox-skin w/ yellow blisters + stratified fungal armor)
    "Mat_MTankSkin":        ("juggernaut_pox_skin",     1.30, 0.40, 0.20),
    "Mat_MTankBruise":      ("juggernaut_pox_skin",     1.35, 0.40, 0.18),
    "Mat_ZVeinDark":        ("juggernaut_pox_skin",     1.20, 0.40, 0.18),
    "Mat_MTankArmor":       ("juggernaut_fungal_plate", 1.45, 0.36, 0.00),
    "Mat_ZClothDirty":      ("juggernaut_cloth",        1.10, 0.22, 0.00),
    "Mat_ZRebar":           ("stalker_chitin_mid",      1.15, 0.32, 0.00),

    # Ultra-wet gore & ribbed pharyngeal mouth
    "Mat_ZBloodFresh":      ("gore_wet",   1.15, 0.42, 0.28),
    "Mat_ZBloodDried":      ("gore_wet",   1.20, 0.36, 0.16),
    "Mat_ZFlesh":           ("gore_wet",   1.20, 0.40, 0.26),
    "Mat_MTongueWet":       ("gore_wet",   1.15, 0.44, 0.30),
    "Mat_ZMouth":           ("void_mouth", 0.95, 0.34, 0.00),
    "Mat_ZSocket":          ("void_mouth", 0.50, 0.16, 0.00),
    "Mat_ZLipDead":         ("rafflesia_jaw", 0.85, 0.30, 0.22),
    "Mat_ZSkinDark":        ("stalker_flesh", 0.88, 0.26, 0.24),
    "Mat_ZSkinBruised":     ("juggernaut_pox_skin", 1.25, 0.36, 0.20),
    "Mat_ZSkinGreen":       ("rafflesia_vine", 0.85, 0.24, 0.22),
    "Mat_ZSkinPale":        ("shroud_vein_skin", 0.78, 0.28, 0.26),
    "Mat_ZSkinToxic":       ("rafflesia_vine", 0.85, 0.24, 0.22),
    "Mat_ZFungusCap":       ("juggernaut_fungal_plate", 1.05, 0.20, 0.00),
    "Mat_ZFungusDark":      ("juggernaut_fungal_plate", 1.05, 0.20, 0.00),
    "Mat_ZFungusRoot":      ("rafflesia_bark", 1.00, 0.18, 0.00),
    "Mat_ZFungusPale":      ("stalker_bone", 0.80, 0.24, 0.10),
    "Mat_ZFungusGill":      ("gore_wet", 0.85, 0.38, 0.28),
}


def _ensure_packed_image(name, rgba_2d, colorspace="sRGB"):
    img = bpy.data.images.get(name)
    if img is None:
        img = bpy.data.images.new(name=name, width=TEX_SIZE, height=TEX_SIZE, alpha=False, float_buffer=False)
    img.colorspace_settings.name = colorspace
    img.pixels.foreach_set(rgba_2d.ravel())
    img.pack()
    return img


def apply_mutant_pbr_texture(mat, mat_name, base_hex, base_roughness):
    """Attach clean per-mutant Albedo x VertexColor(Col), Roughness, Normal, and warm SSS."""
    spec = MUTANT_MAT_TEX_MAP.get(mat_name)
    if spec is None:
        return False

    arch, norm_strength, spec_ior, sss_w = spec
    data = _generate_archetype(arch)

    img_col = _ensure_packed_image(f"Tex_{arch}_BaseColor", data["albedo_rgba"], colorspace="sRGB")
    img_rgh = _ensure_packed_image(f"Tex_{arch}_Roughness", data["rough_rgba"], colorspace="Non-Color")
    img_nrm = _ensure_packed_image(f"Tex_{arch}_Normal", data["norm_rgba"], colorspace="Non-Color")

    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = float(spec_ior)
    if sss_w > 0.0 and "Subsurface Weight" in bsdf.inputs:
        bsdf.inputs["Subsurface Weight"].default_value = float(sss_w)
        if "Subsurface Scale" in bsdf.inputs:
            bsdf.inputs["Subsurface Scale"].default_value = 0.024
        if "Subsurface Radius" in bsdf.inputs:
            bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.28, 0.16)

    tex_col = nt.nodes.new("ShaderNodeTexImage")
    tex_col.image = img_col

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
