# MATE ROV 2026 — Vertical Profiling Float ("Argus-P")
# Builds the full float, studio lighting, camera, and renders a preview.
# Target: Blender 5.1+ (also runs on 4.x). Z-up, real-world meters.
# Verified envelope: 0.860 m tall x Ø 0.176 m (rules: < 1.0 m, < 0.18 m).

import bpy
import math
from mathutils import Vector

# ----------------------------------------------------------------------------
# 0. Clean scene
# ----------------------------------------------------------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# ----------------------------------------------------------------------------
# 1. Materials
# ----------------------------------------------------------------------------
def make_mat(name, color, metallic=0.0, roughness=0.4, alpha=None, emission=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    if alpha is not None:
        bsdf.inputs['Alpha'].default_value = alpha
        m.surface_render_method = 'DITHERED'
    if emission is not None:
        ec = bsdf.inputs.get('Emission Color') or bsdf.inputs.get('Emission')
        es = bsdf.inputs.get('Emission Strength')
        if ec: ec.default_value = emission[0]
        if es: es.default_value = emission[1]
    return m

MAT_YELLOW  = make_mat('BP_SafetyYellow', (0.85, 0.50, 0.01, 1), roughness=0.35)
MAT_WHITE   = make_mat('BP_HullWhite',    (0.68, 0.71, 0.75, 1), roughness=0.45)
MAT_BLACK   = make_mat('BP_Black',        (0.015, 0.015, 0.02, 1), roughness=0.45)
MAT_STEEL   = make_mat('BP_Steel',        (0.55, 0.57, 0.60, 1), metallic=0.9, roughness=0.25)
MAT_BLADDER = make_mat('BP_BladderAmber', (0.95, 0.45, 0.05, 1), roughness=0.15, alpha=0.55)
MAT_LED     = make_mat('BP_LEDGreen',     (0.1, 0.9, 0.2, 1), roughness=0.2,
                       emission=((0.1, 0.9, 0.2, 1), 4.0))
MAT_RED     = make_mat('BP_StrobeRed',    (0.9, 0.05, 0.05, 1), roughness=0.25,
                       emission=((0.9, 0.05, 0.05, 1), 3.0))
MAT_POD     = make_mat('BP_SensorBlack',  (0.03, 0.035, 0.04, 1), roughness=0.5)

# ----------------------------------------------------------------------------
# 2. Helpers
# ----------------------------------------------------------------------------
def assign(obj, mat):
    if obj.data and hasattr(obj.data, 'materials'):
        obj.data.materials.append(mat)

def cyl(name, radius, depth, z, mat, vertices=64):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=vertices, location=(0, 0, z))
    o = bpy.context.active_object; o.name = name; assign(o, mat)
    return o

def sphere(name, r, z, mat, scale_z=1.0):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=64, ring_count=32, location=(0, 0, z))
    o = bpy.context.active_object; o.name = name
    o.scale.z = scale_z
    bpy.ops.object.transform_apply(scale=True)
    assign(o, mat)
    return o

def torus(name, major, minor, z, mat, rot=None, loc=(0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                     major_segments=64, minor_segments=16,
                                     location=(loc[0], loc[1], z))
    o = bpy.context.active_object; o.name = name
    if rot: o.rotation_euler = rot
    assign(o, mat)
    return o

# ----------------------------------------------------------------------------
# 3. The float — bottom (z=0) to top (z=0.86), envelope Ø 0.176 m
# ----------------------------------------------------------------------------
# 3.1 Ballast keel (bottom-heavy trim for stable vertical attitude)
cyl('BP_Keel_Weight', 0.050, 0.06, 0.03, MAT_BLACK)

# 3.2 Sensor pod — pressure sensor at the very bottom face (judge-friendly)
cyl('BP_Sensor_Pod', 0.025, 0.05, 0.055, MAT_POD)
cyl('BP_Sensor_Face', 0.020, 0.004, 0.032, MAT_STEEL)  # sensor diaphragm face

# 3.3 Lower dome (yellow) — overlaps tube interior
sphere('BP_Dome_Bottom', 0.078, 0.10, MAT_YELLOW, scale_z=0.6)

# 3.4 Main pressure hull tube (white), z 0.10 -> 0.56, Ø 0.156
cyl('BP_Hull_Cylinder', 0.078, 0.46, 0.33, MAT_WHITE)

# 3.5 Buoyancy engine: low-profile external bladder at the waist (Ø 0.176)
torus('BP_Bladder', 0.076, 0.012, 0.33, MAT_BLADDER)

# 3.6 Clamp / fairing rings
torus('BP_Clamp_Low',  0.079, 0.006, 0.16, MAT_STEEL)
torus('BP_Clamp_Mid',  0.079, 0.006, 0.33, MAT_STEEL)
torus('BP_Clamp_High', 0.079, 0.006, 0.50, MAT_STEEL)

# 3.7 Fuse + switch pod on upper hull (single-fuse rule, inspector-visible)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.068, 0, 0.44))
fuse = bpy.context.active_object; fuse.name = 'BP_Fuse_Pod'
fuse.scale = (0.018, 0.030, 0.045); bpy.ops.object.transform_apply(scale=True)
assign(fuse, MAT_YELLOW)

# 3.8 Upper dome (yellow)
sphere('BP_Dome_Top', 0.078, 0.56, MAT_YELLOW, scale_z=0.6)

# 3.9 U-bolt recovery handle (2026 requirement) — loop against dome flank
torus('BP_Ubolt_Handle', 0.028, 0.006, 0.585, MAT_STEEL,
      rot=(math.radians(90), 0, 0), loc=(0.052, 0))

# 3.10 Antenna mast (yellow) + LoRa whip (black); total height 0.86 m
cyl('BP_Mast', 0.010, 0.15, 0.705, MAT_YELLOW)
cyl('BP_Antenna', 0.003, 0.08, 0.82, MAT_BLACK)

# 3.11 Strobe + status LED at mast base
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.010, segments=32, ring_count=16, location=(0.012, 0, 0.645))
strobe = bpy.context.active_object; strobe.name = 'BP_Strobe'; assign(strobe, MAT_RED)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.006, segments=32, ring_count=16, location=(-0.012, 0, 0.645))
led = bpy.context.active_object; led.name = 'BP_StatusLED'; assign(led, MAT_LED)

# 3.12 Small label plates on hull
for i, z in enumerate((0.24, 0.42)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0, -0.0770, z))
    p = bpy.context.active_object; p.name = f'BP_LabelPlate_{i+1}'
    p.scale = (0.05, 0.0015, 0.035); bpy.ops.object.transform_apply(scale=True)
    assign(p, MAT_YELLOW)

# ----------------------------------------------------------------------------
# 4. Ground + lighting + camera (studio)
# ----------------------------------------------------------------------------
bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
ground = bpy.context.active_object; ground.name = 'BP_Ground'
assign(ground, make_mat('BP_Floor', (0.045, 0.05, 0.06, 1), roughness=0.95))

def area_light(name, energy, loc, size):
    data = bpy.data.lights.new(name, 'AREA'); data.energy = energy; data.shape = 'DISK'; data.size = size
    o = bpy.data.objects.new(name, data); bpy.context.scene.collection.objects.link(o); o.location = loc
    return o

def track(obj, target):
    c = obj.constraints.new('TRACK_TO'); c.target = target
    c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'

key  = area_light('BP_Key',  110, ( 1.4, -1.2, 1.6), 1.2)
fill = area_light('BP_Fill',  45, (-1.2, -0.6, 1.0), 1.0)
rim  = area_light('BP_Rim',  180, ( 0.4,  1.4, 1.8), 0.8)

bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0.43))
focus = bpy.context.active_object; focus.name = 'BP_Focus'

for l in (key, fill, rim): track(l, focus)

cam_data = bpy.data.cameras.new('BP_Camera'); cam_data.lens = 60
cam = bpy.data.objects.new('BP_Camera', cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location = (1.05, -1.35, 0.72)
track(cam, focus)
bpy.context.scene.camera = cam

world = bpy.data.worlds.new('BP_World') if not bpy.data.worlds else bpy.data.worlds[0]
bpy.context.scene.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
bg.inputs['Color'].default_value = (0.05, 0.06, 0.08, 1)
bg.inputs['Strength'].default_value = 0.05

# ----------------------------------------------------------------------------
# 5. Render settings + preview render
# ----------------------------------------------------------------------------
scene = bpy.context.scene
scene.view_settings.exposure = -0.6
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 640
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = '//mate_float_preview.png'

bpy.ops.render.render(write_still=True)
print('MATE float build complete ->', scene.render.filepath)
