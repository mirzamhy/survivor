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
]


def create_materials():
    """Create or return the survivor material list and index lookup."""
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
        bsdf.inputs["Metallic"].default_value = metallic
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.35
        if len(spec) >= 6 and "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = rgba(spec[4])
            bsdf.inputs["Emission Strength"].default_value = spec[5]
        mat.diffuse_color = col

        mats.append(mat)
        idx_map[name] = i
    return mats, idx_map
