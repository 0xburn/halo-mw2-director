#!/usr/bin/env python3
"""Convert local Halo CE map models to embedded glTF 2.0 GLBs.

Requires Python 3.9, reclaimer 2.11.2, Pillow and NumPy. Reclaimer parses
the retail data; this bridge writes glTF meshes, skins, textures and clips.
"""
import argparse
import contextlib
from io import BytesIO
import json
from pathlib import Path
import struct

import numpy as np
from PIL import Image
from reclaimer.meta.wrappers.halo1_map import Halo1Map
from reclaimer.model.model_decompilation import extract_model
from reclaimer.animation.animation_decompilation import extract_animation
from reclaimer.bitmaps.bitmap_decompilation import extract_bitmaps
from reclaimer.util import int_to_fourcc

SCALE = .03048  # 100 JMS units = one Halo world unit = ten feet.
MODELS = {
    "chief": r"characters\cyborg\cyborg",
    "pistol": r"weapons\pistol\pistol",
    "sniper": r"weapons\sniper rifle\sniper rifle",
    "rocket": r"weapons\rocket launcher\rocket launcher",
}
CLIPS = {"idle": "stand pistol idle", "walk": "stand pistol move-front",
         "rifle_idle": "stand rifle idle", "rifle_walk": "stand rifle move-front",
         "rocket_idle": "stand missile idle", "rocket_walk": "stand missile move-front"}


def transform(node):
    # Normalize the local rotation before building the bind transform.
    q = np.array([-node.rot_i, -node.rot_j, -node.rot_k, node.rot_w], dtype=float)
    q /= np.linalg.norm(q)
    x, y, z, w = q
    matrix = np.eye(4)
    matrix[:3, :3] = [
        [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
        [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
        [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)],
    ]
    position = [node.pos_x*SCALE, node.pos_y*SCALE, node.pos_z*SCALE]
    matrix[:3, 3] = position
    return position, q.tolist(), matrix


class Glb:
    def __init__(self):
        self.data = bytearray()
        self.doc = {"asset": {"version": "2.0", "generator": "Chief on Rust / local CE bridge"},
                    "buffers": [], "bufferViews": [], "accessors": [], "meshes": [],
                    "nodes": [], "materials": [], "textures": [], "images": [],
                    "samplers": [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}]}

    def blob(self, data):
        while len(self.data) % 4:
            self.data.append(0)
        view = len(self.doc["bufferViews"])
        self.doc["bufferViews"].append({"buffer": 0, "byteOffset": len(self.data), "byteLength": len(data)})
        self.data.extend(data)
        return view

    def accessor(self, values, typ, component=5126, bounds=False):
        array = np.asarray(values, dtype={5126: "<f4", 5125: "<u4", 5123: "<u2"}[component])
        count = len(array)
        if not count or not np.isfinite(array).all():
            raise ValueError("Invalid or empty mesh/animation buffer")
        result = {"bufferView": self.blob(array.tobytes()), "componentType": component, "count": count, "type": typ}
        if bounds:
            result["min"] = np.atleast_1d(array.min(axis=0)).tolist()
            result["max"] = np.atleast_1d(array.max(axis=0)).tolist()
        index = len(self.doc["accessors"])
        self.doc["accessors"].append(result)
        return index

    def image(self, data):
        index = len(self.doc["images"])
        self.doc["images"].append({"bufferView": self.blob(data), "mimeType": "image/png"})
        self.doc["textures"].append({"source": index, "sampler": 0})
        return index

    def save(self, path):
        while len(self.data) % 4:
            self.data.append(0)
        self.doc["buffers"] = [{"byteLength": len(self.data)}]
        # Empty optional glTF arrays are invalid according to the schema.
        self.doc = {k: v for k, v in self.doc.items() if v != []}
        header = json.dumps(self.doc, separators=(",", ":"), allow_nan=False).encode()
        header += b" " * (-len(header) % 4)
        payload = struct.pack("<II", len(header), 0x4e4f534a) + header + struct.pack("<II", len(self.data), 0x004e4942) + self.data
        temporary = path.with_suffix(".glb.tmp")
        temporary.write_bytes(struct.pack("<4sII", b"glTF", 2, 12 + len(payload)) + payload)
        temporary.replace(path)


class Converter:
    def __init__(self, map_path, output, armor_color="green"):
        self.armor_color = armor_color
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.texture_cache = {}
        # This old parser logs descriptor-cache warnings on startup. Keep its
        # full diagnostic output without overwhelming the asset report.
        with (self.output / "parser.log").open("w") as log, contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
            self.map = Halo1Map()
            self.map.load_map(str(Path(map_path).resolve()))
        if self.map.engine != "halo1xbox":
            raise ValueError("This converter is verified for Xbox CE maps; PC resource-map loading is not implemented")
        self.tags = self.map.tag_index.tag_index

    def find(self, path, classes):
        return next((i for i, ref in enumerate(self.tags) if ref.path.lower() == path.lower() and ref.class_1.enum_name in classes), None)

    def meta(self, index, convert=False):
        ref = self.tags[index]
        result = self.map.get_meta(index, reextract=True)
        if result is None:
            raise ValueError("Cannot read tag: " + ref.path)
        if convert:
            self.map.meta_to_tag_data(result, int_to_fourcc(ref.class_1.data), ref)
        return result

    def texture(self, index):
        index &= 65535
        if index == 65535:
            return None
        if index not in self.texture_cache:
            meta = self.meta(index, True)
            directory = self.output / "textures"
            directory.mkdir(exist_ok=True)
            name = f"bitmap-{index}"
            error = extract_bitmaps(meta, name, out_dir=directory, bitmap_ext="dds", halo_map=self.map)
            if error:
                raise ValueError(str(error))
            candidates = sorted(directory.glob(name + "*.dds"))
            if not candidates:
                raise ValueError("No texture extracted for " + self.tags[index].path)
            self.texture_cache[index] = Image.open(candidates[0]).convert("RGBA")
        return self.texture_cache[index].copy()

    def material(self, glb, shader_ref, kind):
        index = shader_ref.shader.id & 65535
        ref = self.tags[index]
        shader = self.meta(index)
        material = {"name": ref.path.split("\\")[-1], "doubleSided": True,
                    "pbrMetallicRoughness": {"metallicFactor": .2, "roughnessFactor": .65}}
        if hasattr(shader, "soso_attrs"):
            attrs = shader.soso_attrs
            diffuse = self.texture(attrs.maps.diffuse_map.id)
            if diffuse is not None:
                # CE's model alpha generally carries specular data, not opacity.
                diffuse.putalpha(255)
                if kind == "chief" and "armor" in ref.path:
                    mask = self.texture(attrs.maps.multipurpose_map.id)
                    if mask is not None:
                        pixels = np.asarray(diffuse).astype(float)
                        weight = np.asarray(mask.resize(diffuse.size))[:, :, 3:4].astype(float) / 255
                        palette = {"green": [.38, .49, .20], "blue": [.12, .40, 1.0], "red": [1.0, .14, .10]}
                        pixels[:, :, :3] *= 1-weight + weight*np.array(palette[self.armor_color])
                        diffuse = Image.fromarray(pixels.astype("uint8"))
                buf = BytesIO(); diffuse.save(buf, format="PNG")
                material["pbrMetallicRoughness"]["baseColorTexture"] = {"index": glb.image(buf.getvalue())}
            if "visor" in ref.path:
                # CE gets the gold from a reflection shader. A black diffuse
                # sample alone loses the visor completely in a PBR viewer.
                material["pbrMetallicRoughness"].pop("baseColorTexture", None)
                material["pbrMetallicRoughness"].update(baseColorFactor=[.85,.49,.08,1], metallicFactor=.7, roughnessFactor=.19)
                material["emissiveFactor"] = [.12,.065,.006]
        else:
            material["pbrMetallicRoughness"]["baseColorFactor"] = [.2, .3, .25, 1]
        glb.doc["materials"].append(material)

    def convert(self, kind):
        index = self.find(MODELS[kind], {"model", "gbxmodel"})
        if index is None:
            raise ValueError(f"Missing {kind} in this map")
        meta = self.meta(index, True)
        # Reclaimer 2.11.2 swaps offsets 28–29 as a u16, although the
        # compressed Xbox vertex stores two separate signed bone bytes.
        # Undo that swap before JMS extraction discards the rigid bone.
        for geometry in meta.geometries.STEPTREE:
            for part in geometry.parts.STEPTREE:
                raw = bytearray(part.compressed_vertices.STEPTREE.data)
                for offset in range(0, len(raw), 32):
                    raw[offset+28], raw[offset+29] = raw[offset+29], raw[offset+28]
                part.compressed_vertices.STEPTREE.data = raw
        models = extract_model(meta, write_jms=False)
        model = next((x for x in models if x.lod_level == "superhigh"), None)
        if model is None or not model.verts or not model.tris:
            raise ValueError(f"No high-detail geometry for {kind}")
        glb = Glb()
        for shader in meta.shaders.STEPTREE:
            self.material(glb, shader, kind)
        positions = [[v.pos_x*SCALE, v.pos_y*SCALE, v.pos_z*SCALE] for v in model.verts]
        normals = [[v.norm_i, v.norm_j, v.norm_k] for v in model.verts]
        uv = [[v.tex_u, 1-v.tex_v] for v in model.verts]
        joints, weights = [], []
        for v in model.verts:
            if v.node_0 < 0:
                raise ValueError("Vertex lost its primary bone assignment")
            a = v.node_0
            b = v.node_1 if v.node_1 >= 0 else a
            if a >= len(model.nodes) or b >= len(model.nodes):
                raise ValueError("Vertex references an invalid skeleton node")
            weight = max(0, min(1, v.node_1_weight))
            joints.append([a, b, 0, 0]); weights.append([1-weight, weight, 0, 0])
        attributes = {"POSITION": glb.accessor(positions, "VEC3", bounds=True),
                      "NORMAL": glb.accessor(normals, "VEC3"), "TEXCOORD_0": glb.accessor(uv, "VEC2"),
                      "JOINTS_0": glb.accessor(joints, "VEC4", 5123), "WEIGHTS_0": glb.accessor(weights, "VEC4")}
        primitives = []
        for shader in range(len(meta.shaders.STEPTREE)):
            indices = [v for tri in model.tris if tri.shader == shader for v in (tri.v0, tri.v1, tri.v2)]
            if not indices:
                continue
            if min(indices) < 0 or max(indices) >= len(positions):
                raise ValueError("Triangle references an invalid vertex")
            # The light-shield layers on Chief are effects, not opaque armor.
            if kind == "chief" and "shield" in meta.shaders.STEPTREE[shader].shader.filepath:
                continue
            primitives.append({"attributes": attributes, "indices": glb.accessor(indices, "SCALAR", 5125), "material": shader})
        glb.doc["meshes"].append({"name": kind, "primitives": primitives})
        world = {}
        def node_world(i):
            if i not in world:
                local = transform(model.nodes[i])[2]
                parent = model.nodes[i].parent_index
                world[i] = node_world(parent) @ local if parent >= 0 else local
            return world[i]
        for i, node in enumerate(model.nodes):
            position, rotation, _ = transform(node)
            item = {"name": node.name.replace(" ", "_"), "translation": position, "rotation": rotation}
            children = [j for j, n in enumerate(model.nodes) if n.parent_index == i]
            if children: item["children"] = children
            glb.doc["nodes"].append(item)
        inverses = [np.linalg.inv(node_world(i)).T.reshape(16).tolist() for i in range(len(model.nodes))]
        glb.doc["skins"] = [{"joints": list(range(len(model.nodes))), "inverseBindMatrices": glb.accessor(inverses, "MAT4")}]
        mesh_node = len(glb.doc["nodes"])
        glb.doc["nodes"].append({"name": kind, "mesh": 0, "skin": 0})
        root = len(glb.doc["nodes"])
        # Halo: +X forward, +Z up. glTF: -Z forward, +Y up.
        glb.doc["nodes"].append({"name": "Halo_basis", "matrix": [0,0,-1,0, -1,0,0,0, 0,1,0,0, 0,0,0,1],
                                 "children": [mesh_node] + [i for i, n in enumerate(model.nodes) if n.parent_index < 0]})
        glb.doc["scenes"] = [{"nodes": [root]}]; glb.doc["scene"] = 0
        for marker in model.markers:
            position, rotation, _ = transform(marker)
            marker_index = len(glb.doc["nodes"])
            glb.doc["nodes"].append({"name": "marker_" + marker.name.replace(" ", "_"), "translation": position, "rotation": rotation})
            parent = marker.parent if marker.parent >= 0 else root
            glb.doc["nodes"][parent].setdefault("children", []).append(marker_index)
        if kind == "chief":
            self.animations(glb, model)
        path = self.output / (kind + ".glb")
        glb.save(path)
        print(f"{kind}: {len(model.verts):,} vertices, {len(model.tris):,} triangles, {len(model.nodes)} bones, {len(glb.doc.get('animations', []))} clips → {path}", flush=True)
        return path

    def animations(self, glb, model):
        index = self.find(MODELS["chief"], {"model_animations"})
        meta = self.meta(index, True)
        glb.doc["animations"] = []
        model_nodes = {n.name: i for i, n in enumerate(model.nodes)}
        for label, name in CLIPS.items():
            index = next(i for i, a in enumerate(meta.animations.STEPTREE) if a.name == name)
            animation = extract_animation(index, meta, write_jma=False)
            if animation is None: raise ValueError("Cannot extract animation " + name)
            animation.apply_root_node_info_to_states(undo=True)
            times = [f / 30 for f in range(len(animation.frames))]
            time_accessor = glb.accessor(times, "SCALAR", bounds=True)
            clip = {"name": label, "channels": [], "samplers": []}
            for j, node in enumerate(animation.nodes):
                if node.name not in model_nodes:
                    raise ValueError("Animation node missing from model: " + node.name)
                translations, rotations = [], []
                for frame in animation.frames:
                    t, q, _ = transform(frame[j]); translations.append(t); rotations.append(q)
                for path, values, typ in [("translation", translations, "VEC3"), ("rotation", rotations, "VEC4")]:
                    sampler = len(clip["samplers"])
                    clip["samplers"].append({"input": time_accessor, "output": glb.accessor(values, typ), "interpolation": "LINEAR"})
                    clip["channels"].append({"sampler": sampler, "target": {"node": model_nodes[node.name], "path": path}})
            glb.doc["animations"].append(clip)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map")
    parser.add_argument("output")
    parser.add_argument("--armor-color", choices=["green", "blue", "red"], default="green")
    parser.add_argument("--only", choices=list(MODELS))
    args = parser.parse_args()
    converter = Converter(args.map, args.output, args.armor_color)
    for kind in ([args.only] if args.only else MODELS):
        converter.convert(kind)
