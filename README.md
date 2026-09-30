# Halo / MW2 Director

A native Mac cinematic prototype that stages Halo CE characters and weapons inside the original Modern Warfare 2 Rust map, built on [IW4L](https://github.com/vladtrc/iw4L).

The included 24-second take chains two Intervention quickscopes, a blue Chief reveal, a Warthog splatter with an MW2 promotion, and a battlefield overview with plasma volleys, an airborne rocket triple kill, and a staged sniper duel.

**Source and scene instructions only. Game assets, extracted models/audio, recordings, and game binaries are not included.** Bring your own local MW2 (2009) and Halo CE data. This is a cinematic prototype, not a released cross-platform multiplayer game.

## What works

- Native IW4L/Metal playback, checked on an Apple M1 Pro.
- [Native graphics improvements](docs/NATIVE_GRAPHICS.md): texture filtering, edge anti-aliasing, contact shading and animated Halo water.
- [Autonomous 4v4 bot matches](docs/BOT_MATCHES.md): MW2 quickscopers versus jumping Spartans, with cycling first-person spectator views.
- Experimental [Battle Creek import](docs/HALO_MAPS.md): Halo CE geometry, textures, collision and spawn points with native MW2 movement and weapons.
- A 16-slot authored cast with MW2 soldiers and imported blue CE Chief meshes using MW2 rigs.
- Native controller-driven sprinting, jumping, aiming, shots and deaths; cinematic damage protections keep the intended cast alive until their beats.
- Warthog/driver presentation, CE sounds, plasma effects and native RPG damage.
- Scene-file reload and F9 replay; camera cuts and a native-window MP4 recorder with game audio on macOS.
- A small director tool for readable actions, scene inspection and asset preflight.

## Scene instructions

The engine consumes a detailed JSON timeline. The new authoring layer lets repeated actions be written more clearly. For example, the first shot in [the readable recipe](director/examples/rust-crossover.scene.json):

```json
{
  "do": "quickscope",
  "target": "runner",
  "acquire": 0.84,
  "ads": 1.11,
  "at": 1.30,
  "release": 1.37,
  "height": 40,
  "turn_speed": 540,
  "response": 26
}
```

This expands into eased targeting, scope input and a fire window. The recipe references the accepted Rust template, which supplies the rest of the cast, map-specific routes, effects and cameras. It currently replaces the hero's opening actions; the rest of the choreography is still a detailed timeline. Actions are timed input macros, not yet reactive combat AI.

```sh
# No game assets needed to inspect or compile a recipe:
python3 scripts/director.py inspect director/examples/rust-crossover.scene.json
python3 scripts/director.py build director/examples/rust-crossover.scene.json

# After setting up local game assets:
python3 scripts/director.py catalog
python3 scripts/director.py check director/examples/rust-crossover.scene.json
python3 scripts/director.py preview director/examples/rust-crossover.scene.json
```

Preflight checks actor references, supported slots, finite positions, timeline ranges, mesh buffers, texture sizes, skin weights and PCM audio. It does not prove that a route clears a wall or that a shot will hit. Those require a native rehearsal.

See [native setup](docs/NATIVE_SETUP.md) and [the director design and next steps](docs/DIRECTOR.md).

## Run and record

After native setup:

```sh
python3 scripts/build_battlefield_take.py
./scripts/native_scene.sh
# In another terminal, with the game still running:
python3 scripts/export_native_scene.py
```

The recorder writes H.264/AAC MP4 plus raw capture/timing metadata into ignored `exports/`. It requires macOS 15+, Swift, FFmpeg and Screen & System Audio Recording permission. It records application audio, with the microphone disabled. Window borders may need cropping; `--raw` and `--crop width:height:x:y` re-export an existing take. For a nondefault scene, pass `--scene path/to/compiled.native.json`.

An older browser storyboard is also included: `python3 manage.py serve`. With no imported assets it uses procedural placeholders. It is a separate renderer, not the native footage renderer.

## Current limits

- Native scene v2 supports 16 cast slots, not 32. Slots 0–7 use MW2 soldiers and 8–15 use the imported Chief. Arbitrary per-actor models are not implemented.
- Rust is the rehearsed cinematic map. Battle Creek has a separate native playtest launcher; Halo map shaders and gameplay features remain incomplete. Other installed maps require native verification.
- The Warthog follows an authored route with a baked driver pose, not general vehicle physics.
- Camera cuts currently activate after the local player's death. Fight choreography, stunt protection and some punchline effects remain specific to the take.
- The video is captured in real time. Cold-load/frame-timing variance can affect shots; the scene verifier reports actual outcomes.
- No claim of every device/controller working. This project's native cinematic was tested on Apple silicon/macOS.

## Development

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
node --test tests/scene.test.js tests/weapon.test.js
python3 scripts/verify_battlefield_take.py  # after a complete native take
```

IW4L is fetched at `1a0daffd182d808ad3fa43adc6da0200fe78610d` and changed by `patches/native-cinema.patch`; its full checkout is not vendored. Existing browser tests cover the earlier scene sampler/weapon logic, not native rendering. The director regression checks that the readable recipe preserves the accepted native timeline.

Credits and third-party notices: [NOTICE](NOTICE), [asset credits](docs/LOCAL_ASSET_CREDITS.md), [IW4L Apache-2.0 license](IW4L-LICENSE.txt), [Three.js MIT license](web/vendor/THREE-LICENSE.txt).
