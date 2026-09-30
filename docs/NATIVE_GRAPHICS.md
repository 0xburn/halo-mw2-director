# Native graphics

The native Metal renderer now applies edge anti-aliasing before the HUD. Imported Halo maps also receive restrained screen-space contact shading. These are ordinary raster rendering effects and do not require NVIDIA hardware.

The Halo map converter defaults to scale 32 / up to 4096-pixel baked atlases, preserves bright texture detail with a highlight shoulder, and imports animated flow/ripple water. The native loader builds alpha-aware mip chains, preserves foliage cutout coverage, and selects trilinear 4× anisotropic filtering. Atlas samplers clamp; repeating material textures wrap.

Rebuild an older local pack to get the new lighting bake and water:

```sh
.tools/halo39/bin/python scripts/prepare_native_halo_map.py \
  local-assets/halo/maps/beavercreek.map local-assets/halo/native-maps/battle-creek
./scripts/build_native.sh
./scripts/native_bot_match.sh
```

The first load warms native shaders. `IW4L_CLARITY=0 ./scripts/native_bot_match.sh` disables the added screen-space pass for comparison; imported texture/mipmap changes remain.

Limits: original CE geometry, baked world lighting, uniform character ambient lighting. Contact shading is screen-space ambient occlusion, not new sun shadows or ray tracing. Water is an animated opaque approximation, without refraction or live reflections. This is not DLSS or MetalFX. The extra map texture memory is about 261 MB before mipmaps (about 348 MB with the full chains), versus 76 MB in the previous pack.

Validated on Apple M1 Pro / Metal at 1280×720: native build, overview and first-person rendering, eight bot combat, and no refused draw calls in the inspected run. Sustained GPU performance has not been benchmarked.
