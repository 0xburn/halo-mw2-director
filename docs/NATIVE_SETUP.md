# Native Mac setup

The accepted take ran on Apple M1 Pro/macOS with Metal. These steps expose the existing local pipeline; a complete empty-machine installation has not been rehearsed. Native source builds and patch applicability have been checked. Expect the first engine compile and asset conversion to take time.

## Prerequisites

- Xcode command-line tools and Rust via rustup, following the pinned engine's build documentation.
- Python 3 for authoring. Asset conversion was tested in Python 3.9 with `requirements-assets.txt`.
- Your local Windows MW2 (2009) Multiplayer data, including `main` and `zone/english`.
- Your local Halo CE `bloodgulch.map`. The tested source is the Xbox cache format (version 5); the sound tag indices in the converter currently depend on this source.
- For MP4 recording: macOS 15+, Swift and FFmpeg, plus macOS recording permission.

Keep local data under:

```text
local-assets/mw2/Call of Duty Modern Warfare 2/main/
local-assets/mw2/Call of Duty Modern Warfare 2/zone/english/
local-assets/halo/maps/bloodgulch.map
```

These folders are ignored. The repository does not download retail game data. `scripts/extract_xiso.py` can extract the map from your local Xbox XDVDFS image.

## Build the engine

```sh
python3 manage.py setup-iw4l
./scripts/build_native.sh
```

Setup fetches the pinned IW4L revision and applies the full native patch. It refuses an incompatible checkout rather than replacing it. If upgrading a checkout that has only the older spawn-export patch, preserve it elsewhere and use a fresh checkout. Builds reuse the existing local Rust installation when present, or a system `cargo` for fresh clones.

## Prepare the native asset packs

Create a Python 3.9 virtual environment at `.tools/halo39` and install the pinned conversion dependencies:

```sh
python3.9 -m venv .tools/halo39
.tools/halo39/bin/python -m pip install -r requirements-assets.txt
mkdir -p local-assets/halo/native web/assets
```

Export the local MW2 skeleton/material catalog before running the retargeting scripts. From the repository root:

```sh
project_root="$PWD"
cd vendor-src/iw4L
IW4L_GAMES="$project_root/local-assets/mw2" IW4L_CINEMA_EXPORT=1 \
  ../../.tools/iw4l-target/play/iw4l export-gltf mp_rust
cd "$project_root"

.tools/halo39/bin/python scripts/export_halo.py \
  local-assets/halo/maps/bloodgulch.map web/assets --armor-color blue
.tools/halo39/bin/python scripts/prepare_native_chief.py
.tools/halo39/bin/python scripts/prepare_native_sniper.py
.tools/halo39/bin/python scripts/prepare_native_battlefield.py
```

The engine export generates `vendor-src/iw4L/iw4l-artifacts/cinema-sources/catalog.json`, consumed by the Chief retargeter. Converted packs remain local. Changing meshes/materials requires restarting the native game; changing scene JSON replays the take.

The optional Halo 3 General badge is separately credited in `LOCAL_ASSET_CREDITS.md`; its PNG and 400×600 raw RGBA copy are not distributed. The game can run without that cosmetic override.

```sh
python3 scripts/director.py check director/examples/rust-crossover.scene.json
python3 scripts/build_battlefield_take.py
./scripts/native_scene.sh
```

Press F9 to replay. `python3 scripts/verify_battlefield_take.py` checks actual outcomes from the latest completed native take. Other maps and model templates require a native compatibility rehearsal; a successful file check alone is insufficient.
