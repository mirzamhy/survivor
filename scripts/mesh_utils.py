"""Reusable BMesh primitives for faceted low-poly modeling."""
import math
import bmesh
import bpy
from mathutils import Euler, Matrix, Vector


def ring_ellipse(cx, cy, cz, rx, ry, n=8, rot_z=0.0,
                 squash_front=1.0, squash_back=1.0, tilt_y=0.0):
    """Generate a ring of n 3D points in the XY plane around (cx, cy, cz).
    -Y is front, +Y is back.
    """
    pts = []
    cz_cos = math.cos(rot_z)
    cz_sin = math.sin(rot_z)
    for i in range(n):
        ang = (2.0 * math.pi * i) / n
        lx = rx * math.cos(ang)
        ly = ry * math.sin(ang)
        if ly < 0:
            ly *= squash_front
        else:
            ly *= squash_back
        # Rotate around Z
        rxp = lx * cz_cos - ly * cz_sin
        ryp = lx * cz_sin + ly * cz_cos
        dz = ryp * math.tan(tilt_y) if abs(tilt_y) > 1e-6 else 0.0
        pts.append((cx + rxp, cy + ryp, cz + dz))
    return pts


def ring_yz(cx, cy, cz, ry, rz, n=8, squash_top=1.0, squash_bot=1.0):
    """Generate a ring of n 3D points in the YZ plane (for horizontal arms along X)."""
    pts = []
    for i in range(n):
        ang = (2.0 * math.pi * i) / n
        ly = ry * math.cos(ang)
        lz = rz * math.sin(ang)
        if lz > 0:
            lz *= squash_top
        else:
            lz *= squash_bot
        pts.append((cx, cy + ly, cz + lz))
    return pts


def ring_perp(center, tangent, up_hint=(0.0, 0.0, 1.0), r_up=0.01, r_side=0.01, n=6):
    """Generate a ring of n 3D points strictly perpendicular to `tangent` around `center`."""
    c = Vector(center)
    t = Vector(tangent)
    if t.length < 1e-6:
        t = Vector((1.0, 0.0, 0.0))
    else:
        t.normalize()
    uh = Vector(up_hint)
    u = uh - t * uh.dot(t)
    if u.length < 1e-6:
        fallback = Vector((0.0, 0.0, 1.0)) if abs(t.z) < 0.9 else Vector((0.0, 1.0, 0.0))
        u = fallback - t * fallback.dot(t)
    u.normalize()
    s = t.cross(u).normalized()

    pts = []
    for i in range(n):
        ang = (2.0 * math.pi * i) / n
        pt = c + u * (r_up * math.cos(ang)) + s * (r_side * math.sin(ang))
        pts.append((pt.x, pt.y, pt.z))
    return pts


def loft_rings(bm, rings, close_caps=(True, True), mat_idx=0, cap_mat=None):
    """Bridge a sequence of equal-length point rings into a faceted BMesh shell.
    Returns list of newly created BMVerts.
    """
    if len(rings) < 2:
        raise ValueError("loft_rings requires at least 2 rings")
    n = len(rings[0])
    v_rings = []
    all_verts = []
    for r in rings:
        assert len(r) == n, f"Expected ring of length {n}, got {len(r)}"
        vr = [bm.verts.new(pt) for pt in r]
        v_rings.append(vr)
        all_verts.extend(vr)

    created_faces = []
    for ri in range(len(v_rings) - 1):
        r0 = v_rings[ri]
        r1 = v_rings[ri + 1]
        for i in range(n):
            j = (i + 1) % n
            try:
                f = bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
                f.material_index = mat_idx
                created_faces.append(f)
            except ValueError:
                pass

    cmat = mat_idx if cap_mat is None else cap_mat
    if close_caps[0]:
        try:
            f = bm.faces.new(list(reversed(v_rings[0])))
            f.material_index = cmat
            created_faces.append(f)
        except ValueError:
            pass
    if close_caps[1]:
        try:
            f = bm.faces.new(v_rings[-1])
            f.material_index = cmat
            created_faces.append(f)
        except ValueError:
            pass

    if close_caps[0] and close_caps[1] and created_faces:
        bmesh.ops.recalc_face_normals(bm, faces=created_faces)

    return all_verts


def add_box(bm, center, size, rot=(0.0, 0.0, 0.0), bevel=0.0,
            taper_top=(1.0, 1.0), mat_idx=0):
    """Add an optionally beveled and tapered box to bm. Returns created BMVerts."""
    sx, sy, sz = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5
    coords = [
        (-sx, -sy, -sz),
        ( sx, -sy, -sz),
        ( sx,  sy, -sz),
        (-sx,  sy, -sz),
        (-sx * taper_top[0], -sy * taper_top[1],  sz),
        ( sx * taper_top[0], -sy * taper_top[1],  sz),
        ( sx * taper_top[0],  sy * taper_top[1],  sz),
        (-sx * taper_top[0],  sy * taper_top[1],  sz),
    ]
    verts = [bm.verts.new(c) for c in coords]
    face_idx = [
        (0, 3, 2, 1),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ]
    faces = []
    for fi in face_idx:
        f = bm.faces.new([verts[k] for k in fi])
        f.material_index = mat_idx
        faces.append(f)

    if bevel > 0.0:
        edges = list({e for f in faces for e in f.edges})
        res = bmesh.ops.bevel(
            bm,
            geom=edges,
            offset=bevel,
            segments=1,
            profile=0.5,
            affect="EDGES",
        )
        new_verts = set(res.get("verts", []))
        for v in list(new_verts):
            for f in v.link_faces:
                f.material_index = mat_idx
        # Collect all verts belonging to this part
        part_verts = set()
        for v in new_verts:
            part_verts.add(v)
        for v in verts:
            if v.is_valid:
                part_verts.add(v)
        verts = list(part_verts)

    mat_rot = Euler(rot, "XYZ").to_matrix().to_4x4()
    mat_tr = Matrix.Translation(Vector(center))
    xform = mat_tr @ mat_rot
    for v in verts:
        if v.is_valid:
            v.co = xform @ v.co

    part_faces = list({f for v in verts if v.is_valid for f in v.link_faces})
    if part_faces:
        bmesh.ops.recalc_face_normals(bm, faces=part_faces)
    return [v for v in verts if v.is_valid]


def add_cylinder(bm, p0, p1, r0, r1, segments=8, close_caps=(True, True), mat_idx=0):
    """Add a faceted tapered cylinder between p0 and p1."""
    v0 = Vector(p0)
    v1 = Vector(p1)
    axis = v1 - v0
    length = axis.length
    if length < 1e-6:
        return []
    z_dir = axis.normalized()
    ref = Vector((1, 0, 0)) if abs(z_dir.x) < 0.8 else Vector((0, 1, 0))
    x_dir = z_dir.cross(ref).normalized()
    y_dir = z_dir.cross(x_dir).normalized()

    ring0 = []
    ring1 = []
    for i in range(segments):
        ang = (2.0 * math.pi * i) / segments
        ca, sa = math.cos(ang), math.sin(ang)
        off0 = (x_dir * ca + y_dir * sa) * r0
        off1 = (x_dir * ca + y_dir * sa) * r1
        ring0.append(tuple(v0 + off0))
        ring1.append(tuple(v1 + off1))

    return loft_rings(bm, [ring0, ring1], close_caps=close_caps, mat_idx=mat_idx)


def add_cone(bm, base, tip, r_base, segments=6, mat_idx=0):
    """Add a faceted low-poly cone / spike from base to tip."""
    v0 = Vector(base)
    v1 = Vector(tip)
    axis = v1 - v0
    if axis.length < 1e-6:
        return []
    z_dir = axis.normalized()
    ref = Vector((1, 0, 0)) if abs(z_dir.x) < 0.8 else Vector((0, 1, 0))
    x_dir = z_dir.cross(ref).normalized()
    y_dir = z_dir.cross(x_dir).normalized()

    ring = []
    for i in range(segments):
        ang = (2.0 * math.pi * i) / segments
        off = (x_dir * math.cos(ang) + y_dir * math.sin(ang)) * r_base
        ring.append(bm.verts.new(tuple(v0 + off)))
    v_tip = bm.verts.new(tuple(v1))

    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        f = bm.faces.new((ring[i], ring[j], v_tip))
        f.material_index = mat_idx
        faces.append(f)
    f_cap = bm.faces.new(list(reversed(ring)))
    f_cap.material_index = mat_idx
    faces.append(f_cap)
    bmesh.ops.recalc_face_normals(bm, faces=faces)
    return ring + [v_tip]


def assign_region_verts(bm, vert_list, region_dict, region_name):
    """Record vertex indices (after index_update) for deterministic weight painting."""
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    bucket = region_dict.setdefault(region_name, set())
    for v in vert_list:
        if v.is_valid:
            bucket.add(v.index)


def _diag_score(va, vb):
    """Mirror-invariant orientation score for a quad diagonal."""
    if va.co.z <= vb.co.z:
        lo, hi = va.co, vb.co
    else:
        lo, hi = vb.co, va.co
    # Prefer diagonal slanting outward in |X| as Z increases, then forward/back
    return (abs(hi.x) - abs(lo.x), hi.y - lo.y, abs(hi.x) + abs(lo.x))


def triangulate_symmetric(bm):
    """Convert all faces in bm into pure triangles with mirror-symmetric diagonals across X=0."""
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons, quad_method="SHORT_EDGE", ngon_method="BEAUTY")

    quads = [f for f in bm.faces if len(f.verts) == 4]
    for f in quads:
        v0, v1, v2, v3 = f.verts[0], f.verts[1], f.verts[2], f.verts[3]
        mat_idx = f.material_index
        d02 = (v2.co - v0.co).length_squared
        d13 = (v3.co - v1.co).length_squared

        if abs(d02 - d13) > 1e-6:
            use_02 = d02 < d13
        else:
            use_02 = _diag_score(v0, v2) >= _diag_score(v1, v3)

        bm.faces.remove(f)
        if use_02:
            tris = ((v0, v1, v2), (v0, v2, v3))
        else:
            tris = ((v1, v2, v3), (v1, v3, v0))
        for tri in tris:
            try:
                nf = bm.faces.new(tri)
                nf.material_index = mat_idx
            except ValueError:
                pass

    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))


def add_cloth_creases(bm, verts, strength=0.003, seed=42):
    """Apply subtle, X-symmetric facet creases to interior cloth vertices."""
    for v in verts:
        if not v.is_valid or v.is_boundary:
            continue
        # Deterministic hash invariant under X -> -X mirror
        key = (
            round(abs(v.co.x), 4),
            round(v.co.y, 4),
            round(v.co.z, 4),
            seed,
        )
        h = abs(hash(key)) % 1000
        jitter = ((h / 999.0) * 2.0 - 1.0) * strength
        # Push slightly along radial XY direction
        rx = v.co.x
        ry = v.co.y
        r_len = math.hypot(rx, ry)
        if r_len > 1e-4:
            v.co.x += (rx / r_len) * jitter
            v.co.y += (ry / r_len) * jitter


def count_tris(obj):
    """Count total triangles in a mesh object without modifying it."""
    return sum(max(1, len(p.vertices) - 2) for p in obj.data.polygons)


def finalize_mesh(name, bm, materials, collection=None, triangulate=True):
    """Convert BMesh to a pure-triangle flat-shaded Blender mesh object."""
    if triangulate:
        triangulate_symmetric(bm)
    bm.normal_update()
    mesh = bpy.data.meshes.new(name + "_Mesh")
    bm.to_mesh(mesh)
    bm.free()

    for m in materials:
        mesh.materials.append(m)

    # Crisp faceted low-poly shading
    for poly in mesh.polygons:
        poly.use_smooth = False

    obj = bpy.data.objects.new(name, mesh)
    if collection is None:
        bpy.context.scene.collection.objects.link(obj)
    else:
        collection.objects.link(obj)

    return obj, count_tris(obj)


def bake_mutant_vertex_shading(
    mesh_obj,
    cavity_tint=(0.40, 0.26, 0.34),
    ridge_tint=(1.00, 0.95, 0.86),
    ground_tint=(0.54, 0.48, 0.44),
    countershade=True,
):
    """Bake geometric Countershading (dorsal dark vs ventral light), colored cavity occlusion, and ridge highlights into 'Col'."""
    mesh = mesh_obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.normal_update()

    zs = [v.co.z for v in bm.verts]
    z_min = min(zs) if zs else 0.0
    z_span = max(1e-4, (max(zs) if zs else 1.0) - z_min)

    vert_rgb = []
    for v in bm.verts:
        # Mean neighbor normal curvature: + -> concave cavity, - -> convex ridge
        acc = 0.0
        cnt = 0
        vn = v.normal
        for e in v.link_edges:
            nb = e.other_vert(v)
            dv = nb.co - v.co
            ln = dv.length
            if ln > 1e-6:
                acc += vn.dot(dv / ln)
                cnt += 1
        curv = math.tanh((acc / max(1, cnt)) * 4.2)

        z_norm = max(0.0, min(1.0, (v.co.z - z_min) / z_span))
        base_mul = 0.78 + 0.12 * z_norm
        if countershade:
            # Rule #1 Countershading: dorsal (+Y back / +Z crown) darker; ventral (-Y front chest/belly/throat) +24..30% lighter!
            dorsal_f = max(-1.0, min(1.0, 0.68 * vn.y + 0.42 * max(0.0, vn.z) - 0.15 * abs(vn.x)))
            cs_scale = 0.88 - 0.15 * dorsal_f  # ~0.73 dorsal .. ~1.03 ventral
            base_mul *= cs_scale
            if dorsal_f < -0.12:
                vf = min(1.0, (-dorsal_f - 0.12) * 0.50)
                r = base_mul * (1.0 - vf) + 0.98 * vf
                g = base_mul * (1.0 - vf) + 0.95 * vf
                b = base_mul * (1.0 - vf) + 0.89 * vf
            else:
                r, g, b = base_mul, base_mul, base_mul
        else:
            r, g, b = base_mul, base_mul, base_mul

        if z_norm < 0.24:
            gf = (0.24 - z_norm) / 0.24
            gf = gf * gf * 0.58
            r = r * (1.0 - gf) + ground_tint[0] * gf
            g = g * (1.0 - gf) + ground_tint[1] * gf
            b = b * (1.0 - gf) + ground_tint[2] * gf

        if curv > 0.0:
            # Rule #4: Deep colored cavity occlusion at part seams & muscle folds (never dead pure black!)
            cf = min(1.0, (curv ** 0.85) * 0.86)
            r = r * (1.0 - cf) + cavity_tint[0] * cf
            g = g * (1.0 - cf) + cavity_tint[1] * cf
            b = b * (1.0 - cf) + cavity_tint[2] * cf
        elif curv < 0.0:
            # Strong crisp ridge & part-edge highlight so dark armor, limbs, petals & fingers pop cleanly!
            rf = min(1.0, ((-curv) ** 0.82) * 0.68)
            r = r * (1.0 - rf) + ridge_tint[0] * rf
            g = g * (1.0 - rf) + ridge_tint[1] * rf
            b = b * (1.0 - rf) + ridge_tint[2] * rf

        vert_rgb.append((
            max(0.0, min(1.0, r)),
            max(0.0, min(1.0, g)),
            max(0.0, min(1.0, b)),
            1.0,
        ))
    bm.free()

    col_attr = mesh.color_attributes.get("Col")
    if col_attr is None:
        col_attr = mesh.color_attributes.new(name="Col", type="BYTE_COLOR", domain="CORNER")
    col_data = col_attr.data
    loops = mesh.loops
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            col_data[li].color = vert_rgb[loops[li].vertex_index]


def bake_character_vertex_ao(mesh_obj, style="survivor"):
    """Bake subtle geometric cavity AO, ridge highlights, and boot/hem grounding into vertex color 'Col'."""
    mesh = mesh_obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.normal_update()

    mat_names = [
        (slot.material.name if slot.material else "")
        for slot in mesh_obj.material_slots
    ]
    skin_verts = set()
    if style == "survivor" and mat_names:
        for f in bm.faces:
            mname = mat_names[f.material_index] if f.material_index < len(mat_names) else ""
            if "Skin" in mname or "Lip" in mname or "Eye" in mname:
                for v in f.verts:
                    skin_verts.add(v.index)

    zs = [v.co.z for v in bm.verts]
    z_min = min(zs) if zs else 0.0
    z_span = max(1e-4, (max(zs) if zs else 1.0) - z_min)

    if style == "zombie":
        base_lo, base_span = 0.82, 0.14
        g_thresh, g_tint, g_str = 0.26, (0.48, 0.44, 0.40), 0.55
        c_tint, c_str = (0.44, 0.36, 0.38), 0.68
        r_tint, r_str = (0.98, 0.95, 0.90), 0.36
    elif style == "weapon":
        base_lo, base_span = 0.92, 0.04
        g_thresh, g_tint, g_str = 0.0, (0.92, 0.92, 0.92), 0.0
        c_tint, c_str = (0.46, 0.48, 0.52), 0.62
        r_tint, r_str = (1.00, 1.00, 1.00), 0.38
    else:  # survivor
        base_lo, base_span = 0.88, 0.11
        g_thresh, g_tint, g_str = 0.22, (0.68, 0.64, 0.60), 0.42
        c_tint, c_str = (0.56, 0.52, 0.50), 0.50
        r_tint, r_str = (1.00, 0.99, 0.97), 0.28

    vert_rgb = []
    for v in bm.verts:
        acc = 0.0
        cnt = 0
        vn = v.normal
        for e in v.link_edges:
            nb = e.other_vert(v)
            dv = nb.co - v.co
            ln = dv.length
            if ln > 1e-6:
                acc += vn.dot(dv / ln)
                cnt += 1
        curv = math.tanh((acc / max(1, cnt)) * 3.8)

        z_norm = max(0.0, min(1.0, (v.co.z - z_min) / z_span))
        base_mul = base_lo + base_span * z_norm
        r, g, b = base_mul, base_mul, base_mul

        if g_thresh > 0.0 and z_norm < g_thresh:
            gf = (g_thresh - z_norm) / g_thresh
            gf = gf * gf * g_str
            r = r * (1.0 - gf) + g_tint[0] * gf
            g = g * (1.0 - gf) + g_tint[1] * gf
            b = b * (1.0 - gf) + g_tint[2] * gf

        is_skin = v.index in skin_verts
        if curv > 0.0:
            w_cav = (0.22 if is_skin else c_str)
            cf = min(1.0, (curv ** 0.90) * w_cav)
            r = r * (1.0 - cf) + c_tint[0] * cf
            g = g * (1.0 - cf) + c_tint[1] * cf
            b = b * (1.0 - cf) + c_tint[2] * cf
        elif curv < 0.0:
            w_rdg = (0.14 if is_skin else r_str)
            rf = min(1.0, ((-curv) ** 0.85) * w_rdg)
            r = r * (1.0 - rf) + r_tint[0] * rf
            g = g * (1.0 - rf) + r_tint[1] * rf
            b = b * (1.0 - rf) + r_tint[2] * rf

        vert_rgb.append((
            max(0.0, min(1.0, r)),
            max(0.0, min(1.0, g)),
            max(0.0, min(1.0, b)),
            1.0,
        ))
    bm.free()

    col_attr = mesh.color_attributes.get("Col")
    if col_attr is None:
        col_attr = mesh.color_attributes.new(name="Col", type="BYTE_COLOR", domain="CORNER")
    col_data = col_attr.data
    loops = mesh.loops
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            col_data[li].color = vert_rgb[loops[li].vertex_index]


def apply_box_uvs(mesh_obj, tex_scale=1.7):
    """Apply fast distortion-free triplanar/box UV projection per polygon for PBR textures."""
    mesh = mesh_obj.data
    uv_layer = mesh.uv_layers.get("UVMap") or mesh.uv_layers.new(name="UVMap")
    uv_data = uv_layer.data
    verts = mesh.vertices
    s = float(tex_scale)

    for poly in mesh.polygons:
        nx = abs(poly.normal.x)
        ny = abs(poly.normal.y)
        nz = abs(poly.normal.z)
        if nx >= ny and nx >= nz and nx > 1e-6:
            mode = 0
        elif ny >= nx and ny >= nz and ny > 1e-6:
            mode = 1
        else:
            mode = 2
        for li in poly.loop_indices:
            co = verts[mesh.loops[li].vertex_index].co
            if mode == 0:
                uv_data[li].uv = (co.y * s, co.z * s)
            elif mode == 1:
                uv_data[li].uv = (co.x * s, co.z * s)
            else:
                uv_data[li].uv = (co.x * s, co.y * s)
