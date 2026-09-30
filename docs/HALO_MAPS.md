# Local Halo map import

The experimental map bridge converts a locally installed Xbox Halo CE multiplayer map into geometry, textures, collision, and spawn records for native IW4L. It uses MW2 movement and weapons. The Halo executable/engine is not embedded.

From the project root, after [native setup](NATIVE_SETUP.md):

```sh
# Extract Battle Creek from a local Xbox CE XISO; its internal name is beavercreek.
python3 scripts/extract_xiso.py /path/to/Halo.xiso.iso local-assets/halo/maps --map beavercreek.map

# Use the asset Python environment containing requirements-assets.txt dependencies.
.tools/halo39/bin/python scripts/prepare_native_halo_map.py \
  local-assets/halo/maps/beavercreek.map local-assets/halo/native-maps/battle-creek

./scripts/build_native.sh
./scripts/native_halo_map.sh
```

The launcher defaults to `local-assets/halo/native-maps/battle-creek`. Pass another pack directory as its first argument. It sets `IW4L_LOCAL_MAP`, loads the existing MW2 asset bootstrap, replaces its visible level and collision, and starts an ordinary controllable session. Cinematic playback is disabled for this launcher.

The conversion includes Halo BSP geometry, diffuse/detail textures baked with the original lightmaps, placed scenery, sky geometry, collision polygons, and multiplayer starts. Imported maps are stored as `map.json` plus RGBA textures. All generated packs contain game assets and must remain local.

The native window uses the MW2 `mp_rust` bootstrap name/loading screen; its level geometry and collision are replaced by the Halo pack. Use WASD/mouse, Shift to sprint, Space to jump, left click to fire, and right click to aim.

Current import limits: single-BSP Xbox CE levels only; Battle Creek is the first target. Textures and Halo lightmaps are baked into diffuse atlases; the default import uses up to 4096-pixel atlases with compressed highlights and native mipmaps. Detail sharpness remains limited by atlas resolution. Water uses animated layers from the original flow/ripple bitmaps, but remains opaque; layered transparent shaders are approximated; sky layers are static. Scenery is visual only, with level collision coming from the BSP. Halo teleporters, pickups, vehicle physics, and Halo game rules are not implemented. MW2 killstreak systems have not been adapted to Halo map entities. Dynamic weapon/player lighting uses a uniform ambient sample. Other maps need native verification before being called supported.

The existing Rust scene's routes and camera coordinates are specific to Rust. A new imported map needs its own scene choreography.

See [native graphics](NATIVE_GRAPHICS.md) for filtering, edge smoothing, contact shading, and rebuilding older packs.
