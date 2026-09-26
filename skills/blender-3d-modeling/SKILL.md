---
name: blender-3d-modeling
description: Build original 3D models, props, and product designs in Blender through the Kimi Work Blender plugin — parametric build scripts, real-world dimension verification, studio lighting, and preview rendering. Use when the user asks to create/design/model a new 3D object in Blender (e.g. "build me a ... in Blender", "design a ... float/drone/housing"), especially when the native mcp__plugin-blender_blender__* tools are absent from the tool surface and the stdio MCP channel must be used instead.
---

# Blender 3D Modeling

Build new 3D models in Blender 5.1+ via the official MCP bridge. For operating on an existing
scene (import takeovers, precise transforms, delivery exports), defer to the managed `blender`
plugin skills. This skill owns **creating new models** and the **stdio transport fallback**.

## Workflow

1. **Preflight** — run the layer checks and resolve any red layer before writing a single line of
   bpy. Most "MCP won't connect" cases are environment problems, not code problems:
   [references/setup-troubleshooting.md](references/setup-troubleshooting.md)
2. **Derive hard constraints first** — collect the real-world size/mass/rule limits the model must
   satisfy (competition specs, print bed, part clearances). These become numeric assertions for
   step 5. Never trust the design doc alone; verify against the built mesh.
3. **Write one idempotent build script** — a single Python file that clears `BP_*` objects,
   rebuilds everything, sets lighting/camera, and renders. Structure it in sections:
   materials → helpers (`cyl`/`sphere`/`torus` assign-material wrappers) → parts bottom-to-top
   (Z-up, meters, real dimensions) → studio (floor, 3 area lights + world, Track-To camera) →
   render settings + `bpy.ops.render.render(write_still=True)`. Use the `BP_` name prefix for
   every created object so selection, deletion, and verification are trivial.
4. **Execute** via `scripts/mcp_run.py` (see below). One call runs the whole build; judge success
   by the `stdout` field ("build complete -> ..."), not the empty `result`.
5. **Verify numerically, then visually** — run a bbox-envelope check over all `BP_*` parts
   (exclude floor/lights/camera/focus empty) and assert against the step-2 constraints. Fix
   violations by editing the build script and re-running it whole — do not stack per-part patch
   scripts. Then view the render and iterate lighting/exposure (below).
6. **Iterate in whole-rebuild cycles** — each cycle is: edit build script → run → verify → view
   render. Two or three cycles are normal; stop when the envelope passes and the render reads well.

## Transport: stdio MCP client

When native `mcp__plugin-blender_blender__*` tools are not in the tool surface, execute code
through the plugin's official server launcher with the bundled client:

```bash
python3 scripts/mcp_run.py @/path/to/build_script.py          # execute_blender_code
python3 scripts/mcp_run.py '{"name":"get_objects_summary","arguments":{}}'   # any read-only tool
```

The client speaks newline-delimited JSON-RPC to `blender_mcp_launcher.py` (path resolved from the
managed Blender plugin). The first positional arg starting with `@` is read as a file and sent as
`execute_blender_code`; otherwise the arg is a raw tool-call JSON. Timeouts: handshake 60 s, tool
call 600 s. On `"Cannot connect to Blender at localhost:9876"` the GUI Blender has exited —
restart it (see the troubleshooting reference) before retrying; do not hammer the port.

## Blender 5.x facts used by the build pattern

- Render engine enum is `'BLENDER_EEVEE'`. For tabletop-size models: key/fill/rim area lights at
  ~110/45/180 W, disk size 0.8–1.2 m, placed 1.2–1.8 m from origin; world Background strength
  0.05; `scene.view_settings.exposure = -0.6`. A first render that looks "blown out white" is the
  default — these numbers are the corrected baseline, not a starting point to halve gradually.
- White hull material that keeps its shading: Base Color ~(0.68, 0.71, 0.75), roughness ~0.45 —
  (0.88+) white reads as overexposed under any key light.
- Locate Principled BSDF by `n.type == 'BSDF_PRINCIPLED'`; set sockets by name
  (`'Base Color'`, `'Metallic'`, `'Roughness'`). Translucency: `mat.surface_render_method =
  'DITHERED'` (Blender 4.2+); emission sockets `'Emission Color'`/`'Emission Strength'`.
- Useful primitives: `primitive_cylinder_add(radius=, depth=, vertices=64)`;
  `primitive_uv_sphere_add(radius=, segments=64, ring_count=32)`; `primitive_torus_add(
  major_radius=, minor_radius=, major_segments=64, minor_segments=16)`. For domed end caps use a
  UV sphere with `scale.z` applied (~0.6) overlapping the tube interior — no boolean needed.
- Camera aims via `TRACK_TO` constraint (`track_axis='TRACK_NEGATIVE_Z'`, `up_axis='UP_Y'`) on a
  focus empty at the model's mid-height.

## Verification snippet (adapt and send as the `code` payload)

```python
import bpy
from mathutils import Vector
skip = {'BP_Ground', 'BP_Camera', 'BP_Key', 'BP_Fill', 'BP_Rim', 'BP_Focus'}
parts = [o for o in bpy.data.objects if o.name.startswith('BP_') and o.name not in skip]
lo = Vector((1e9,)*3); hi = Vector((-1e9,)*3)
for o in parts:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c)
        lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
size = hi - lo
print('PARTS:', len(parts), '| HEIGHT %.3f | DIAMETER %.3f' % (size.z, max(size.x, size.y)))
```

Watch for silent envelope violations: tori (bladder/handle/rings) and offset pods often extend
past the "main body" diameter and fail the real constraint even when the design looks compact.
