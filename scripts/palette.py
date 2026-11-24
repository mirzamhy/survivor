"""Material palette for the low-poly Zombie Apocalypse Survivor."""
import bpy


def srgb_to_linear(c):
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def rgba(hex_or_rgb, alpha=1.0):
    if isinstance(hex_or_rgb, str):
        h = hex_or_rgb.lstrip("#")
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
    else:
        r, g, b = hex_or_rgb
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), alpha)


# Material definitions: (name, hex_color, roughness, metallic)
MATERIAL_SPECS = [
    # Prototype & base skin/clothing
    ("Mat_Skin",         "#C99674", 0.72, 0.00),
    ("Mat_Lip",          "#B07A5E", 0.72, 0.00),
    ("Mat_Stubble",      "#A4785B", 0.78, 0.00),
    ("Mat_Hair",         "#2B211B", 0.85, 0.00),
    ("Mat_Eye",          "#181A1F", 0.35, 0.00),
    ("Mat_Beanie",       "#7D3229", 0.92, 0.00),
    ("Mat_Jacket",       "#4B533E", 0.84, 0.00),
    ("Mat_JacketTrim",   "#33382A", 0.88, 0.00),
    ("Mat_Shirt",        "#9C9889", 0.86, 0.00),
    ("Mat_Pants",        "#3F3B36", 0.86, 0.00),
    ("Mat_BeltLeather",  "#36251B", 0.68, 0.05),
    ("Mat_Boots",        "#2B1E16", 0.66, 0.04),
    ("Mat_BootSole",     "#171718", 0.90, 0.00),
    ("Mat_KneePad",      "#202226", 0.60, 0.08),
    ("Mat_Bandage",      "#B8AD96", 0.92, 0.00),
    ("Mat_Backpack",     "#585C43", 0.86, 0.00),
    ("Mat_SleepingRoll", "#A88B5E", 0.88, 0.00),
    ("Mat_MetalDark",    "#3A3E44", 0.42, 0.85),
    ("Mat_MetalRust",    "#7A3224", 0.56, 0.55),
    ("Mat_WoodBat",      "#8D5E38", 0.74, 0.00),
    ("Mat_GripTape",     "#1E1F22", 0.88, 0.00),

    # Batch 1: Skin & hair variants
    ("Mat_SkinLight",    "#D2A282", 0.72, 0.00),
    ("Mat_SkinWarm",     "#C6926F", 0.72, 0.00),
    ("Mat_SkinTan",      "#B27D58", 0.72, 0.00),
    ("Mat_SkinMed",      "#9E6B4B", 0.74, 0.00),
    ("Mat_LipWarm",      "#B86660", 0.58, 0.00),
    ("Mat_HairBlack",    "#1A1817", 0.84, 0.00),
    ("Mat_HairBrown",    "#3B281D", 0.84, 0.00),
    ("Mat_HairGrey",     "#6E6A66", 0.84, 0.00),
    ("Mat_Beard",        "#2B2019", 0.88, 0.00),

    # Batch 1: 5 Survivors role & outfit colors
    ("Mat_OliveMil",     "#4B563A", 0.84, 0.00),
    ("Mat_OliveDark",    "#343C28", 0.86, 0.00),
    ("Mat_CoyoteTan",    "#8E7958", 0.84, 0.00),
    ("Mat_ScrubBlue",    "#23466E", 0.82, 0.00),
    ("Mat_ScrubDark",    "#1A3352", 0.86, 0.00),
    ("Mat_FieldJacket",  "#596268", 0.84, 0.00),
    ("Mat_MedWhite",     "#E6E8EA", 0.82, 0.00),
    ("Mat_MedRed",       "#C92828", 0.74, 0.00),
    ("Mat_DenimBlue",    "#2D5280", 0.86, 0.00),
    ("Mat_BandanaRed",   "#BE2A24", 0.84, 0.00),
    ("Mat_OilStain",     "#1E2022", 0.78, 0.00),
    ("Mat_ToolYellow",   "#D8A624", 0.58, 0.10),
    ("Mat_WorkGrey",     "#66696C", 0.86, 0.00),
    ("Mat_HoodGreen",    "#2F5434", 0.85, 0.00),
    ("Mat_ScarfRust",    "#BA4B30", 0.88, 0.00),
    ("Mat_LeatherDark",  "#261E1A", 0.65, 0.04),
    ("Mat_FlannelRed",   "#A42822", 0.86, 0.00),
    ("Mat_FlannelDark",  "#4C1514", 0.88, 0.00),
    ("Mat_FlannelCheck", "#221414", 0.88, 0.00),
    ("Mat_CowboyBrown",  "#603D25", 0.78, 0.00),
    ("Mat_Shearling",    "#DED5C0", 0.92, 0.00),
    ("Mat_VestLeather",  "#7A4B2A", 0.70, 0.04),
    ("Mat_ShellRed",     "#B52320", 0.60, 0.05),
    ("Mat_Brass",        "#C8A248", 0.35, 0.85),

    # Batch 1: Weapons & optics
    ("Mat_GunMetal",     "#2A2D32", 0.40, 0.82),
    ("Mat_GunPolymer",   "#1C1E21", 0.72, 0.00),
    ("Mat_GunSteel",     "#686E75", 0.32, 0.88),
    ("Mat_Walnut",       "#5E371F", 0.68, 0.00),
    ("Mat_WrenchRed",    "#B52A22", 0.48, 0.25),
    ("Mat_SightWhite",   "#F2F2F2", 0.50, 0.00),
    ("Mat_RedDot",       "#E52820", 0.30, 0.10),
    ("Mat_Carbon",       "#222428", 0.45, 0.15),
    ("Mat_BowCam",       "#363A40", 0.42, 0.75),
    ("Mat_VaneRed",      "#CC332A", 0.70, 0.00),
    ("Mat_GlassDark",    "#162228", 0.15, 0.20),

    # Weapon VFX (optional 6-tuple: + emission_hex, emission_strength)
    ("Mat_VfxFlashCore",  "#FFF7CC", 0.20, 0.00, "#FFF6B8", 10.0),
    ("Mat_VfxFlashMid",   "#FFB830", 0.30, 0.00, "#FFA820",  6.5),
    ("Mat_VfxFlashOuter", "#F05A18", 0.40, 0.00, "#E84A10",  3.8),
    ("Mat_VfxTracer",     "#FFE680", 0.20, 0.00, "#FFD95A",  7.5),
    ("Mat_VfxSmokeLight", "#C8CCD2", 0.95, 0.00),
    ("Mat_VfxSmokeDark",  "#6E737A", 0.95, 0.00),
    ("Mat_VfxSpark",      "#FFE066", 0.20, 0.00, "#FFC832",  8.5),
    ("Mat_VfxSlashCore",  "#F2F8FF", 0.20, 0.00, "#D8EEFF",  5.5),
    ("Mat_VfxSlashEdge",  "#7CC4F8", 0.30, 0.00, "#4DA8F0",  3.2),
    ("Mat_VfxBloodFresh", "#8C1616", 0.32, 0.00),
    ("Mat_VfxBloodDark",  "#4A0A0A", 0.45, 0.00),
    ("Mat_VfxBrassHot",   "#E0B850", 0.28, 0.88, "#FFB030",  0.8),
    ("Mat_VfxLaserRed",   "#FF2020", 0.15, 0.00, "#FF1818",  9.0),

    # Batch 2: Undead / Zombie skins, facial trauma & torn outfits
    ("Mat_ZSkinGreen",    "#5A634E", 0.80, 0.00),
    ("Mat_ZSkinPale",     "#7A7A76", 0.78, 0.00),
    ("Mat_ZSkinGrey",     "#7A746A", 0.62, 0.00),
    ("Mat_ZSkinBruised",  "#4E4952", 0.68, 0.00),
    ("Mat_ZSkinToxic",    "#5A6A4E", 0.64, 0.00),
    ("Mat_ZSkinDark",     "#393D33", 0.68, 0.00),
    ("Mat_ZSocket",       "#1A1315", 0.84, 0.00),
    ("Mat_ZEyeCloudy",    "#A4A898", 0.14, 0.00),
    ("Mat_ZEyeBlood",     "#721A18", 0.12, 0.00),
    ("Mat_ZMouth",        "#160508", 0.56, 0.00),
    ("Mat_ZLipDead",      "#4A2A2E", 0.52, 0.00),
    ("Mat_ZBone",         "#C8BCA4", 0.60, 0.00),
    ("Mat_ZFlesh",        "#541417", 0.42, 0.00),
    ("Mat_ZBloodDried",   "#2C0708", 0.54, 0.00),
    ("Mat_ZBloodFresh",   "#640E10", 0.28, 0.00),
    ("Mat_ZShirtTorn",    "#747269", 0.90, 0.00),
    ("Mat_ZTieDark",      "#42181A", 0.86, 0.00),
    ("Mat_ZClothDirty",   "#34322E", 0.90, 0.00),
    ("Mat_ZNurseDress",   "#8E9690", 0.88, 0.00),
    ("Mat_ZCardigan",     "#402B32", 0.90, 0.00),
    ("Mat_ZTrackRed",     "#5E1E1D", 0.86, 0.00),
    ("Mat_ZTrackDark",    "#1B1D21", 0.88, 0.00),
    ("Mat_ZRiotNavy",     "#17202D", 0.74, 0.00),
    ("Mat_ZRiotArmor",    "#1E2228", 0.50, 0.22),
    ("Mat_ZRiotVisor",    "#3C525C", 0.18, 0.25),
    ("Mat_ZHazmatYellow", "#8A721E", 0.74, 0.00),
    ("Mat_ZHazmatTrim",   "#1C1E21", 0.70, 0.00),
    ("Mat_ZAcidGlow",     "#8EE038", 0.25, 0.00, "#78D422", 3.2),
    ("Mat_ZRebar",        "#4A2215", 0.62, 0.72),
    ("Mat_ZBoilDark",     "#3A451B", 0.64, 0.00),
    ("Mat_ZBoilGlow",     "#D4C438", 0.28, 0.00, "#C8B822", 2.6),
    ("Mat_ZShroudDark",   "#221F23", 0.92, 0.00),
    ("Mat_ZVeinDark",     "#2B1621", 0.72, 0.00),
    ("Mat_ZSonicWave",    "#C6D8EE", 0.25, 0.00, "#9EC4F0", 4.0),

    # Mutants Batch: Cordyceps / Fungal Bloom
    ("Mat_ZFungusCap",    "#7A6449", 0.86, 0.00),
    ("Mat_ZFungusPale",   "#A4967B", 0.84, 0.00),
    ("Mat_ZFungusGill",   "#542A1E", 0.82, 0.00),
    ("Mat_ZFungusDark",   "#2B1813", 0.88, 0.00),
    ("Mat_ZFungusRoot",      "#433628", 0.88, 0.00),
    ("Mat_ZSporeMote",       "#C8B874", 0.40, 0.00, "#B8A658", 1.8),

    # Mutant #1 (Rafflesia Carnivorous Blood-Flower Monster)
    ("Mat_ZRaffPetal",       "#7A100F", 0.54, 0.00),
    ("Mat_ZRaffPetalDark",   "#380608", 0.68, 0.00),
    ("Mat_ZRaffSpot",        "#B59B78", 0.82, 0.00),
    ("Mat_ZRaffRing",        "#6E1C16", 0.60, 0.00),
    ("Mat_ZLeafDark",        "#11200E", 0.78, 0.00),
    ("Mat_ZLeafMid",         "#1F3B15", 0.72, 0.00),
    ("Mat_ZVinePale",        "#324D27", 0.74, 0.00),
    ("Mat_ZBarkDark",        "#1E1711", 0.88, 0.00),
    ("Mat_ZHeartGlow",       "#98E042", 0.25, 0.00, "#7CD426", 3.2),
    ("Mat_ZRaffPetalBright", "#9C1814", 0.48, 0.00),
    ("Mat_ZRaffJawFlesh",    "#B88B72", 0.46, 0.00),
    ("Mat_ZRaffStamen",      "#866022", 0.68, 0.00),
    ("Mat_ZBarkMid",         "#34271B", 0.84, 0.00),

    # Mutants #2-#4: Scythe Stalker, Thorn Shroud Seraph & Arachnid Maw
    ("Mat_MChitinDark",      "#221C19", 0.66, 0.00),
    ("Mat_MChitinMid",       "#3E332C", 0.68, 0.00),
    ("Mat_MScytheBone",      "#CBBFA6", 0.54, 0.00),
    ("Mat_MEyeAcid",         "#C8E82C", 0.12, 0.00, "#B2DC1E", 3.4),
    ("Mat_MTongueWet",       "#6A141B", 0.14, 0.00),
    ("Mat_MShroudBone",      "#6E6776", 0.64, 0.00),
    ("Mat_MShroudDark",      "#211C28", 0.76, 0.00),
    ("Mat_MShroudSkin",      "#9E98A6", 0.54, 0.00),
    ("Mat_MArachChitin",     "#14181D", 0.52, 0.14),
    ("Mat_MArachUnder",      "#3B1A1C", 0.62, 0.00),
    ("Mat_MSaliva",          "#CFC6BE", 0.08, 0.00),

    # Modular Mutant Combat VFX Materials
    ("Mat_VfxBloodCore",     "#FF4236", 0.18, 0.00, "#FF261B", 4.6),
    ("Mat_VfxBloodArc",      "#A81016", 0.25, 0.00, "#8E0A10", 2.8),
    ("Mat_VfxSporeGlow",     "#AEF248", 0.20, 0.00, "#8CE024", 4.0),
    ("Mat_VfxSporeMist",     "#46662C", 0.90, 0.00),
    ("Mat_VfxShriekCore",    "#A8DCFF", 0.20, 0.00, "#7EC4FF", 2.8),
    ("Mat_VfxAcidCore",      "#CCFF38", 0.16, 0.00, "#A6F214", 4.8),

    # Mutant #5: Bile Juggernaut Heavy Tank
    ("Mat_MTankSkin",        "#4A453D", 0.78, 0.00),
    ("Mat_MTankBruise",      "#2E222A", 0.66, 0.00),
    ("Mat_MTankArmor",       "#28241D", 0.86, 0.05),
    ("Mat_MBileGlow",        "#D87A14", 0.22, 0.00, "#C8640A", 2.8),
    ("Mat_VfxBileCore",      "#FFB833", 0.16, 0.00, "#FF8C14", 4.6),
]


def create_materials(with_mutant_textures=False):
    """Create or return the survivor material list and index lookup."""
    apply_tex_fn = None
    if with_mutant_textures:
        from mutant_textures import apply_mutant_pbr_texture
        apply_tex_fn = apply_mutant_pbr_texture

    mats = []
    idx_map = {}
    for i, spec in enumerate(MATERIAL_SPECS):
        name, color_hex, roughness, metallic = spec[0], spec[1], spec[2], spec[3]
        mat = bpy.data.materials.get(name)
        if mat is None:
            mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        nt = mat.node_tree
        bsdf = None
        for node in nt.nodes:
            if node.type == "BSDF_PRINCIPLED":
                bsdf = node
                break
        if bsdf is None:
            nt.nodes.clear()
            bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
            out = nt.nodes.new("ShaderNodeOutputMaterial")
            nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

        col = rgba(color_hex)
        bsdf.inputs["Base Color"].default_value = col
        bsdf.inputs["Roughness"].default_value = roughness
        applied_tex = False
        if len(spec) < 6 and apply_tex_fn is not None:
            applied_tex = bool(apply_tex_fn(mat, name, color_hex, roughness))
            for node in mat.node_tree.nodes:
                if node.type == "BSDF_PRINCIPLED":
                    bsdf = node
                    break

        bsdf.inputs["Metallic"].default_value = metallic
        if not applied_tex and "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.35
        if len(spec) >= 6 and "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = rgba(spec[4])
            bsdf.inputs["Emission Strength"].default_value = spec[5]
        mat.diffuse_color = col

        mats.append(mat)
        idx_map[name] = i
    return mats, idx_map
