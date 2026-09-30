# Local cinematic assets

MW2 Rust, soldier meshes, animations and audio come from the user's local MW2 data. Chief and the CE weapons come from the user's local Halo CE map. Retail files and converted packs stay in ignored local directories.

The Halo 3 General insignia is Beorn's reconstruction of Bungie's rank artwork, supplied in the author's [Halo 3 insignia post](https://forums.bungie.org/halo/archive29.pl?read=854391) and [General PNG](https://files.bungie.org/beorn_ranks/General.png). The local native HUD uses `local-assets/halo/native/halo3-general.png` and a raw RGBA copy of that 400×600 image. It is not included in the engine patch.

Blue armor is produced by the original CE armor color mask, preserving the base texture detail, undersuit and separate gold visor:

```sh
.tools/halo39/bin/python scripts/export_halo.py local-assets/halo/maps/bloodgulch.map web/assets --only chief --armor-color blue
.tools/halo39/bin/python scripts/prepare_native_chief.py
```

`--armor-color` also accepts `green` and `red`. The native pack is read at map load. Restart the native preview after regenerating it.

The native battlefield additionally uses CE Warthog geometry, a baked seated Chief driver, plasma grenade and rocket projectile meshes, and local CE sound permutations. `prepare_native_battlefield.py` writes standards-compliant PCM WAV headers without changing the extracted samples. `mix_native_impact.py` mixes the CE blood splat, vehicle crash and suspension samples with a short generated bass impact; Chief's death voice plays separately. Warthog engine, plasma, rocket and triple-kill announcer samples come from the same local CE map. The promotion menu and `mp_level_up` sound come from local MW2 data. Converted assets and recordings remain local and are not included in the engine patch.
