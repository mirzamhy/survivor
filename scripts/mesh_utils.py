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
