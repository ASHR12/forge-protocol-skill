"""Headless turnaround render for one 3D asset: a strip of N views plus mesh stats, for the orchestrator's
asset gate. Runs in its own background Blender process, never in the live MCP session:

  blender -b --factory-startup --python-exit-code 1 -P scripts/blender_turnaround.py -- \
      --input public/models/rock.glb --output artifacts/turnarounds/rock.png \
      [--views 3 | --angles 0,120,240] [--elevation 15] [--size 768] [--engine eevee|cycles|workbench]
      [--samples 32] [--no-ground] [--keep-frames]

Writes <output> (views side by side) and <output stem>.json (objects, triangles, materials, textures, size).
Imports .glb/.gltf/.fbx/.obj, or opens a .blend. Exit codes: 0 ok, 1 render or import failure, 2 usage error.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

try:
    import bpy
    import numpy as np
    from mathutils import Vector
except ImportError:
    bpy = None


def parse_args(argv: list[str]) -> argparse.Namespace:
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    parser = argparse.ArgumentParser(prog="blender_turnaround.py", description="Headless turnaround strip for one asset.")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--views", type=int, default=3, help="evenly spaced views (default 3)")
    parser.add_argument("--angles", help="explicit comma-separated yaw angles in degrees, e.g. 0,90,180,270")
    parser.add_argument("--elevation", type=float, default=15.0, help="camera elevation in degrees (default 15)")
    parser.add_argument("--size", type=int, default=768, help="square size of each view in px (default 768)")
    parser.add_argument("--engine", choices=["eevee", "cycles", "workbench"], default="eevee")
    parser.add_argument("--samples", type=int, default=32)
    parser.add_argument("--no-ground", action="store_true", help="skip the shadow-catching ground plane")
    parser.add_argument("--keep-frames", action="store_true", help="also keep each view as its own PNG")
    args = parser.parse_args(argv)
    if args.angles:
        try:
            args.angle_list = [float(a) for a in args.angles.split(",") if a.strip()]
        except ValueError:
            parser.error(f"--angles must be numbers, got {args.angles}")
    else:
        if args.views < 1:
            parser.error("--views must be at least 1")
        args.angle_list = [i * 360.0 / args.views for i in range(args.views)]
    if not args.angle_list or args.size < 64 or args.samples < 1:
        parser.error("need at least one angle, --size >= 64 and --samples >= 1")
    return args


def set_engine(scene, name: str) -> str:
    candidates = {"eevee": ["BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"], "cycles": ["CYCLES"], "workbench": ["BLENDER_WORKBENCH"]}[name]
    for candidate in candidates:
        try:
            scene.render.engine = candidate
            return candidate
        except TypeError:
            continue
    raise RuntimeError(f"render engine {name} is not available in this Blender build")


def node_tree(owner):
    if getattr(owner, "node_tree", None) is None and hasattr(owner, "use_nodes"):
        owner.use_nodes = True
    return owner.node_tree


def load_asset(path: Path) -> None:
    suffix = path.suffix.lower()
    if suffix == ".blend":
        bpy.ops.wm.open_mainfile(filepath=str(path))
        return
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if suffix in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif suffix == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path))
    elif suffix == ".obj":
        bpy.ops.wm.obj_import(filepath=str(path))
    else:
        raise RuntimeError(f"unsupported asset type {suffix} (use .glb, .gltf, .fbx, .obj or .blend)")


def mesh_stats(meshes: list) -> dict:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    tris = 0
    materials, images = set(), {}
    for obj in meshes:
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        tris += len(mesh.loop_triangles)
        evaluated.to_mesh_clear()
        for slot in obj.material_slots:
            if slot.material:
                materials.add(slot.material.name)
                if slot.material.node_tree:
                    for node in slot.material.node_tree.nodes:
                        if node.type == "TEX_IMAGE" and node.image:
                            images[node.image.name] = list(node.image.size)
    return {"mesh_objects": len(meshes), "triangles": tris, "materials": sorted(materials),
            "textures": [{"name": k, "size": v} for k, v in sorted(images.items())]}


def bounds(meshes: list) -> tuple[Vector, float, Vector]:
    corners = [obj.matrix_world @ Vector(c) for obj in meshes for c in obj.bound_box]
    lo = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
    hi = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
    center = (lo + hi) / 2
    radius = max((hi - lo).length / 2, 1e-3)
    return center, radius, hi - lo


def add_light(name: str, location: Vector, target: Vector, energy: float, size: float) -> None:
    data = bpy.data.lights.new(name, type="AREA")
    data.energy = energy
    data.size = size
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()


def stage(center: Vector, radius: float, lo_z: float, ground: bool) -> None:
    scene = bpy.context.scene
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    bg = node_tree(world).nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.05, 0.055, 0.065, 1.0)
        bg.inputs[1].default_value = 1.0
    power = 400.0 * radius * radius
    add_light("forge_key", center + Vector((-2.2, -2.6, 2.4)) * radius, center, power, radius * 1.5)
    add_light("forge_fill", center + Vector((2.6, -1.6, 1.0)) * radius, center, power * 0.35, radius * 2.0)
    add_light("forge_rim", center + Vector((0.4, 3.0, 2.2)) * radius, center, power * 0.6, radius * 1.0)
    if ground:
        bpy.ops.mesh.primitive_plane_add(size=radius * 60, location=(center.x, center.y, lo_z))
        plane = bpy.context.active_object
        mat = bpy.data.materials.new("forge_ground")
        bsdf = node_tree(mat).nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = (0.18, 0.18, 0.19, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.85
        plane.data.materials.append(mat)


def camera(center: Vector, radius: float) -> object:
    data = bpy.data.cameras.new("forge_cam")
    data.lens = 50
    data.clip_start = radius * 0.01
    data.clip_end = radius * 100
    cam = bpy.data.objects.new("forge_cam", data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


def place(cam, center: Vector, radius: float, yaw: float, elevation: float) -> None:
    fov = min(cam.data.angle_x, cam.data.angle_y)
    distance = radius / math.sin(fov / 2)
    y, e = math.radians(yaw), math.radians(elevation)
    cam.location = center + Vector((math.sin(y) * math.cos(e), -math.cos(y) * math.cos(e), math.sin(e))) * distance
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()


def compose(frames: list[Path], out: Path, size: int) -> None:
    strips = []
    for frame in frames:
        img = bpy.data.images.load(str(frame))
        px = np.empty(img.size[0] * img.size[1] * 4, dtype=np.float32)
        img.pixels.foreach_get(px)
        strips.append(px.reshape(img.size[1], img.size[0], 4))
        bpy.data.images.remove(img)
    joined = np.concatenate(strips, axis=1)
    h, w = joined.shape[:2]
    result = bpy.data.images.new("forge_turnaround", width=w, height=h, alpha=True)
    result.pixels.foreach_set(joined.ravel())
    result.filepath_raw = str(out)
    result.file_format = "PNG"
    result.save()


def main() -> int:
    args = parse_args(sys.argv)
    if bpy is None:
        print("blender_turnaround.py must run inside Blender: blender -b --python-exit-code 1 -P blender_turnaround.py -- ...",
              file=sys.stderr)
        return 2
    src = Path(args.input).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    if not src.is_file():
        print(f"blender_turnaround.py: input not found: {src}", file=sys.stderr)
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    load_asset(src)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"no mesh objects in {src.name}")
    stats = mesh_stats(meshes)
    center, radius, dims = bounds(meshes)
    lo_z = center.z - dims.z / 2
    stage(center, radius, lo_z, not args.no_ground)
    cam = camera(center, radius)
    scene = bpy.context.scene
    set_engine(scene, args.engine)
    scene.render.resolution_x = scene.render.resolution_y = args.size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = args.samples
        scene.cycles.device = "CPU"
    elif hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = args.samples
    frames = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, yaw in enumerate(args.angle_list, start=1):
            place(cam, center, radius, yaw, args.elevation)
            frame = Path(tmp) / f"view-{i:02d}.png"
            scene.render.filepath = str(frame)
            bpy.ops.render.render(write_still=True)
            if not frame.is_file():
                raise RuntimeError(f"render produced no file for view {i}")
            frames.append(frame)
        compose(frames, out, args.size)
        if args.keep_frames:
            for i, frame in enumerate(frames, start=1):
                frame.replace(out.with_name(f"{out.stem}-view-{i:02d}.png"))
    stats.update({"input": str(src), "output": str(out), "angles": args.angle_list, "elevation": args.elevation,
                  "engine": scene.render.engine, "size_m": [round(d, 4) for d in dims],
                  "blender": bpy.app.version_string})
    out.with_suffix(".json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print("FORGE_TURNAROUND " + json.dumps({"output": str(out), "triangles": stats["triangles"],
                                            "mesh_objects": stats["mesh_objects"]}))
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as exc:  # Blender swallows uncaught errors unless --python-exit-code is set.
        print(f"blender_turnaround.py: {exc}", file=sys.stderr)
        code = 1
    if code:
        sys.exit(code)
