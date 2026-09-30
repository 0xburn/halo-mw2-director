#!/usr/bin/env python3
"""Convert a local Xbox CE multiplayer level into a native IW4L map pack.

Run with the Python environment in requirements-assets.txt. Generated packs
contain game assets and belong under ignored local-assets/, never in git.
"""
import argparse
import json
import math
from pathlib import Path
import struct

import numpy as np
from PIL import Image, ImageFilter
from reclaimer.bitmaps.bitmap_decompilation import extract_bitmaps
from reclaimer.model.model_decompilation import extract_model
from reclaimer.util.compression import decompress_normal32
from export_halo import Converter

UNITS = 120.0  # Halo world unit = ten feet; IW4 uses inches.


def sample(image, uv, wrap=True):
    pixels = np.asarray(image, dtype=np.float32) / 255.0
    h, w = pixels.shape[:2]
    xy = uv * [w, h] - .5
    lo = np.floor(xy).astype(int)
    f = xy - lo
    x0, y0 = lo.T
    if wrap:
        x1, y1 = (x0+1) % w, (y0+1) % h
        x0, y0 = x0 % w, y0 % h
    else:
        x1, y1 = np.clip(x0+1, 0, w-1), np.clip(y0+1, 0, h-1)
        x0, y0 = np.clip(x0, 0, w-1), np.clip(y0, 0, h-1)
    a = pixels[y0, x0]*(1-f[:, :1]) + pixels[y0, x1]*f[:, :1]
    b = pixels[y1, x0]*(1-f[:, :1]) + pixels[y1, x1]*f[:, :1]
    return a*(1-f[:, 1:]) + b*f[:, 1:]


class MapConverter(Converter):
    def __init__(self, source, output):
        super().__init__(source, output)
        self.shader_cache = {}
        self.doc = dict(version=1, name=Path(source).stem, units='inches',
                        surfaces=[], materials=[], spawns=[], collision={})
        self.positions, self.normals, self.uvs = [], [], []
        self.indices = []
        self.material_cache = {}

    def texture(self, index):
        try:
            return super().texture(index)
        except NotImplementedError:
            index &= 65535
            file = next((self.output/'textures').glob(f'bitmap-{index}*.dds'))
            raw = file.read_bytes()
            flags = struct.unpack_from('<I', raw, 80)[0]
            height, width = struct.unpack_from('<II', raw, 12)
            bits = struct.unpack_from('<I', raw, 88)[0]
            if flags != 2 or bits != 8:
                raise
            alpha = Image.frombytes('L', (width, height), raw[128:128+width*height])
            image = Image.new('RGBA', (width, height), (255,255,255,255))
            image.putalpha(alpha)
            self.texture_cache[index] = image
            return image.copy()

    def shader(self, index):
        index &= 65535
        if index in self.shader_cache:
            return self.shader_cache[index]
        sh = self.meta(index)
        result = dict(name=self.tags[index].path, base=None, details=[], alpha=False)
        if hasattr(sh, 'senv_attrs'):
            env = sh.senv_attrs
            d = env.diffuse
            result['base'] = self.texture(d.base_map.id)
            result['alpha'] = bool(env.environment_shader.flags.alpha_tested)
            result['blend'] = env.environment_shader.type.enum_name.startswith('blended')
            for prefix in ('primary', 'secondary'):
                img = self.texture(getattr(d, prefix+'_detail_map').id)
                if img is not None:
                    result['details'].append((img, getattr(d, prefix+'_detail_map_scale')))
        elif hasattr(sh, 'swat_attrs'):
            water = sh.swat_attrs.water_shader
            flow = self.texture(water.base_map.id)
            if flow is None:
                raise ValueError('Water shader is missing its flow bitmap')
            waves = self.texture(water.ripple_maps.id)
            yy, xx = np.mgrid[0:1024, 0:1024]
            coords = np.column_stack(((xx.ravel()+.5)/1024, (yy.ravel()+.5)/1024))
            color = sample(flow, coords)
            color[:, :3] = np.array([.08, .17, .19]) + color[:, :3]*.24
            if waves is not None:
                normal = sample(waves, coords*12)[:, :3]*2-1
                light = np.array([.18, .28, .94])
                light /= np.linalg.norm(light)
                shine = np.maximum(normal @ light, 0)**36
                color[:, :3] += shine[:, None]*np.array([.28, .32, .33])
            color[:, 3] = 1
            result['base'] = Image.fromarray(np.clip(color.reshape(1024,1024,4)*255, 0, 255).astype('uint8'))
            result['water'] = True
        elif hasattr(sh, 'soso_attrs'):
            result['base'] = self.texture(sh.soso_attrs.maps.diffuse_map.id)
            result['alpha'] = bool(sh.soso_attrs.flags.alpha_tested) if hasattr(sh.soso_attrs, 'flags') else True
        else:
            for field in ('sotr_attrs', 'schi_attrs', 'scex_attrs'):
                attrs = getattr(sh, field, None)
                if attrs is None:
                    continue
                maps = getattr(attrs, 'maps', None)
                if maps is not None and maps.STEPTREE:
                    # Chicago layers run from overlays to the base image. The
                    # first sky layer is a star/noise mask, not the blue sky.
                    layer = maps.STEPTREE[-1] if field == 'schi_attrs' else maps.STEPTREE[0]
                    result['base'] = self.texture(layer.bitmap.id)
                    result['alpha'] = True
                    if field == 'schi_attrs' and result['base'] is not None:
                        yy, xx = np.mgrid[0:1024, 0:1024]
                        coords = np.column_stack(((xx.ravel()+.5)/1024, (yy.ravel()+.5)/1024))
                        color = sample(result['base'], coords * [layer.map_u_scale or 1, layer.map_v_scale or 1])
                        if 'cloud' in result['name']:
                            mask = self.texture(maps.STEPTREE[0].bitmap.id)
                            if mask is not None:
                                color[:, 3] *= sample(mask, coords)[:, 3]
                        if 'sky clear blue' in result['name']:
                            color[:, 3] = 1
                            result['alpha'] = False
                        result['base'] = Image.fromarray(np.clip(color.reshape(1024,1024,4)*255,0,255).astype('uint8'))
                    break
        if result['base'] is None:
            color = [110, 140, 155, 255] if hasattr(sh, 'swat_attrs') else [180, 180, 180, 255]
            result['base'] = Image.new('RGBA', (4, 4), tuple(color))
        self.shader_cache[index] = result
        return result

    def diffuse(self, shader, uv):
        col = sample(shader['base'], uv)
        details = shader['details']
        if details:
            a = sample(details[0][0], uv*details[0][1])
            if len(details) > 1:
                b = sample(details[1][0], uv*details[1][1])
                mask = col[:, 3:] if shader.get('blend') else b[:, 3:]
                a = a*(1-mask) + b*mask
            col[:, :3] *= a[:, :3]*2
        if not shader['alpha']:
            col[:, 3] = 1
        return col

    def material(self, name, image, alpha=False, water=False):
        key = (name, alpha, water)
        if key in self.material_cache:
            return self.material_cache[key]
        i = len(self.doc['materials'])
        file = f'texture-{i}.rgba'
        (self.output/file).write_bytes(image.convert('RGBA').tobytes())
        self.doc['materials'].append(dict(name=name, file=file, width=image.width,
                                          height=image.height, alpha=alpha, water=water))
        self.material_cache[key] = i
        return i

    def surface(self, pos, normal, uv, triangles, material, sky=False):
        pos = np.asarray(pos, dtype=float)
        normal = np.asarray(normal, dtype=float)
        uv = np.asarray(uv, dtype=float)
        tri = np.asarray(triangles, dtype=int)
        if not len(tri):
            return
        if min(tri.flat) < 0 or max(tri.flat) >= len(pos):
            raise ValueError('Invalid render triangle index')
        start, base = len(self.positions), len(self.indices)
        self.positions.extend(pos.tolist())
        self.normals.extend(normal.tolist())
        self.uvs.extend(uv.tolist())
        self.indices.extend((tri+start).reshape(-1).tolist())
        self.doc['surfaces'].append(dict(first_vertex=start, vertex_count=len(pos),
                                         first_index=base, index_count=tri.size,
                                         material=material, sky=sky))

    def bsp(self, bsp, atlas_scale):
        triangles = np.frombuffer(bsp.surface.STEPTREE, '<u2').reshape(-1, 3)
        lmmeta = self.meta(bsp.lightmap_bitmaps.id & 65535, True)
        directory = self.output/'textures'
        directory.mkdir(exist_ok=True)
        error = extract_bitmaps(lmmeta, 'lightmap', out_dir=directory,
                                bitmap_ext='dds', halo_map=self.map)
        if error:
            raise ValueError(error)
        for lm in bsp.lightmaps.STEPTREE:
            page = None
            if lm.bitmap_index >= 0:
                page = Image.open(directory/f'lightmap__{lm.bitmap_index}_tex0.dds').convert('RGBA')
                size = (min(4096, page.width*atlas_scale), min(4096, page.height*atlas_scale))
                atlas = np.zeros((size[1], size[0], 4), dtype=np.uint8)
                coverage = np.zeros(size[::-1], dtype=bool)
                material = len(self.doc['materials'])
            for part in lm.materials.STEPTREE:
                n = part.vertices_count
                raw = bytes(part.compressed_vertices.STEPTREE)
                rows = list(struct.iter_unpack('<3f3I2f', raw[:32*n]))
                pos = np.array([v[:3] for v in rows])*UNITS
                normals = np.array([decompress_normal32(v[3]) for v in rows])
                uv = np.array([v[6:8] for v in rows])
                tri = triangles[part.surfaces:part.surfaces+part.surface_count].astype(int)
                shader = self.shader(part.shader.id)
                if page is not None and part.lightmap_vertices_count == n:
                    luv = np.array([[u/32767, v/32767] for _, u, v in
                                    struct.iter_unpack('<I2h', raw[32*n:32*n+8*n])])
                    for t in tri:
                        p = luv[t]*size - .5
                        lo = np.maximum(np.floor(p.min(axis=0)).astype(int)-1, 0)
                        hi = np.minimum(np.ceil(p.max(axis=0)).astype(int)+1, np.array(size)-1)
                        if np.any(hi < lo):
                            continue
                        yy, xx = np.mgrid[lo[1]:hi[1]+1, lo[0]:hi[0]+1]
                        xy = np.column_stack((xx.ravel(), yy.ravel()))
                        mat = np.column_stack((p[1]-p[0], p[2]-p[0]))
                        if abs(np.linalg.det(mat)) < 1e-8:
                            continue
                        b = (xy-p[0]) @ np.linalg.inv(mat).T
                        weights = np.column_stack((1-b.sum(axis=1), b))
                        inside = (weights >= -.0001).all(axis=1)
                        xy, weights = xy[inside], weights[inside]
                        if not len(xy):
                            continue
                        col = self.diffuse(shader, weights @ uv[t])
                        lighting = sample(page, weights @ luv[t], wrap=False)
                        # Preserve baked shadow contrast and compress highlights before
                        # quantization, instead of hard-clipping bright grass/rock.
                        lit = col[:, :3] * lighting[:, :3] * 1.5
                        col[:, :3] = np.where(lit <= .65, lit,
                            .65 + .35 * (1 - np.exp(-(lit-.65)/.35)))
                        col[:, 3] = 1
                        atlas[xy[:, 1], xy[:, 0]] = np.clip(col*255, 0, 255).astype('uint8')
                        coverage[xy[:, 1], xy[:, 0]] = True
                    self.surface(pos, normals, luv, tri, material)
                else:
                    img = shader['base'].copy()
                    if not shader['alpha']:
                        img.putalpha(255)
                    mid = self.material(shader['name'], img, shader['alpha'], shader.get('water', False))
                    self.surface(pos, normals, uv, tri, mid)
            if page is not None:
                # Extrude the atlas islands into their guard pixels for filtering.
                img = Image.fromarray(atlas)
                for _ in range(4):
                    grown = np.asarray(img.filter(ImageFilter.MaxFilter(3)))
                    atlas[~coverage] = grown[~coverage]
                    coverage |= grown[:, :, 3] > 0
                    img = Image.fromarray(atlas)
                img.putalpha(255)
                actual = self.material(f'lightmap-{lm.bitmap_index}', img)
                if actual != material:
                    raise ValueError('Unexpected unlightmapped material inside lightmap group')
                print(f'Baked lightmap {lm.bitmap_index}: {size[0]}x{size[1]}', flush=True)

    def collision(self, bsp):
        coll = bsp.collision_bsp.STEPTREE[0]
        verts = np.array([v[:3] for v in struct.iter_unpack('<3fi', coll.vertices.STEPTREE)])*UNITS
        edges = list(struct.iter_unpack('<6i', coll.edges.STEPTREE))
        planes = list(struct.iter_unpack('<4f', coll.planes.STEPTREE))
        triangles = []
        for si, (plane, edge, flags, broken, material) in enumerate(struct.iter_unpack('<IIBBh', coll.surfaces.STEPTREE)):
            ring, visited = [], set()
            while edge not in visited:
                visited.add(edge)
                a, b, forward, reverse, left, right = edges[edge]
                if left == si:
                    ring.append(a); edge = forward
                elif right == si:
                    ring.append(b); edge = reverse
                else:
                    raise ValueError('Broken collision polygon edge')
                if len(visited) > len(edges):
                    raise ValueError('Unclosed collision polygon')
            normal = np.array(planes[plane & 0x7fffffff][:3])
            if plane & 0x80000000:
                normal = -normal
            for k in range(1, len(ring)-1):
                t = [ring[0], ring[k], ring[k+1]]
                a, b, c = verts[t]
                # IW4 collision triangles use clockwise winding when viewed from the free side.
                if np.dot(np.cross(b-a, c-a), normal) > 0:
                    t[1], t[2] = t[2], t[1]
                triangles.append(t)
        self.doc['collision'] = dict(positions=verts.tolist(), indices=np.array(triangles).reshape(-1).tolist())

    def model(self, model_id, origin, rotation, sky=False):
        meta = self.meta(model_id & 65535, True)
        for geometry in meta.geometries.STEPTREE:
            for part in geometry.parts.STEPTREE:
                raw = bytearray(part.compressed_vertices.STEPTREE.data)
                for offset in range(0, len(raw), 32):
                    raw[offset+28], raw[offset+29] = raw[offset+29], raw[offset+28]
                part.compressed_vertices.STEPTREE.data = raw
        model = next(m for m in extract_model(meta, write_jms=False) if m.lod_level == 'superhigh')
        yaw, pitch, roll = rotation
        cy, sy, cp, sp, cr, sr = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch), math.cos(roll), math.sin(roll)
        rot = np.array([[cy,-sy,0],[sy,cy,0],[0,0,1]]) @ np.array([[cp,0,sp],[0,1,0],[-sp,0,cp]]) @ np.array([[1,0,0],[0,cr,-sr],[0,sr,cr]])
        pos = np.array([[v.pos_x, v.pos_y, v.pos_z] for v in model.verts])*1.2
        pos = pos @ rot.T + np.array(origin)*UNITS
        if sky:
            pos *= .016
            pos[:, 2] -= 1024
        normals = np.array([[v.norm_i, v.norm_j, v.norm_k] for v in model.verts]) @ rot.T
        uv = np.array([[v.tex_u, 1-v.tex_v] for v in model.verts])
        for i, ref in enumerate(meta.shaders.STEPTREE):
            tris = [[t.v0,t.v1,t.v2] for t in model.tris if t.shader == i]
            if not tris:
                continue
            shader = self.shader(ref.shader.id)
            img = shader['base'].copy()
            if not shader['alpha']:
                img.putalpha(255)
            mid = self.material(shader['name'], img, shader['alpha'], shader.get('water', False))
            self.surface(pos, normals, uv, tris, mid, sky)

    def run(self, atlas_scale):
        si = next(i for i,t in enumerate(self.tags) if t.class_1.enum_name == 'scenario')
        sc = self.meta(si)
        if len(sc.structure_bsps.STEPTREE) != 1:
            raise ValueError('First importer supports single-BSP multiplayer maps')
        bi = next(i for i,t in enumerate(self.tags) if t.class_1.enum_name == 'scenario_structure_bsp')
        bsp = self.meta(bi)
        self.bsp(bsp, atlas_scale)
        self.collision(bsp)
        for p in sc.player_starting_locations.STEPTREE:
            if p.bsp_index == 0:
                self.doc['spawns'].append(dict(origin=[v*UNITS for v in p.position],
                    angles=[0, math.degrees(p.facing), 0], team=p.team_index))
        for p in sc.sceneries.STEPTREE:
            if p.type < 0:
                continue
            scenery = self.meta(sc.sceneries_palette.STEPTREE[p.type].name.id & 65535)
            self.model(scenery.obje_attrs.model.id, p.position, p.rotation)
        for skyref in sc.skies.STEPTREE:
            sky = self.meta(skyref.sky.id & 65535)
            self.model(sky.model.id, [0,0,0], [0,0,0], sky=True)
        self.doc.update(positions=self.positions, normals=self.normals, uvs=self.uvs, indices=self.indices)
        self.doc['bounds'] = [[getattr(bsp, 'world_bounds_'+axis)[i]*UNITS for axis in 'xyz'] for i in (0,1)]
        out = self.output/'map.json'
        out.write_text(json.dumps(self.doc, separators=(',', ':'), allow_nan=False)+'\n')
        print(f'{out}: {len(self.positions)} vertices, {len(self.indices)//3} triangles, {len(self.doc["spawns"])} spawns', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('map', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--atlas-scale', type=int, default=32)
    args = parser.parse_args()
    if not 1 <= args.atlas_scale <= 32:
        parser.error('--atlas-scale must be between 1 and 32')
    MapConverter(args.map, args.output).run(args.atlas_scale)


if __name__ == '__main__':
    main()
