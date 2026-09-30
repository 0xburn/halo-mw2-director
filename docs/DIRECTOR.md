# Building scenes faster

The goal is: choose compatible map and character packs, describe a scene, rehearse in the native engine, then record. A browser UI could edit that same scene document; final movement/rendering checks must use the native runtime.

## Implemented foundation

`director/core.py` compiles `director/1` recipes to the native v2 timeline. The included recipe names roles and replaces the hero's input/aim tracks using `sprint`, `quickscope`, `look` and `reveal`. Basic `jump`, `crouch`, `fire`, `reload` and `scope` windows are supported too. The accepted template preserves the rest of the scene. A regression test compares the entire compiled document to that template.

`inspect` summarizes cast, routes, effects and cameras. `catalog` separates installed MW2 files from the rehearsed Rust map. `check` validates timelines and local pack buffers/textures/weights/audio before launching. `build` works offline without retail assets. `preview` passes the chosen scene and map to the native launcher.

Recipe `actors.<role>.actions` replaces that actor's aim/button tracks; its route stays in the template unless explicitly replaced. Time is in seconds. Native coordinates are inches with Z up. This format deliberately rejects arbitrary `character`/`model` fields: the current runtime would ignore them.

## Next layers

1. **Asset packs and map profiles.** Replace slot-based model swaps with explicit character/weapon bindings. Store rig mapping, animation coverage, dimensions, material/audio dependencies and compatibility results. Check each new pack once in a native audition scene. Map profiles store named anchors, traversable routes, cover, jump links and camera positions.
2. **Reusable fights.** Represent an exchange as intent: acquire, sprint to a position, scope to cancel sprint, fire, react to a miss, evade, re-peek and counter. Profiles control reaction time, turn acceleration, aim settling and aggression. Two opponents should respond to one another; random zigzags are not a fight.
3. **Event-driven story beats.** Trigger the next beat when the actor reaches its mark, a round fires, the jumper is airborne or impact occurs. Bound each wait and report a failed rehearsal instead of silently continuing a broken scene. Keep comedic outcomes explicit; do not hide forced results inside the actor behavior.
4. **Native rehearsal checks.** Test ground/capsule clearance, muzzle-to-target visibility, ballistic paths, vehicle sweep/turn radius and camera occlusion. Record evidence when actors get stuck or a requested kill misses. A fixed random seed alone does not make the current real-time simulation deterministic.
5. **Editing and takes.** Chat-authored scenes and/or a visual beat editor compile to one shared representation. Save reusable clips and map anchors. For reliable camera iteration, record actor/event state once and play it back through alternate cameras; timeline seeking needs snapshots, not just changing the clock.

A useful next acceptance test is the same two-actor sniper exchange placed at two clear locations on Rust, then on a second compatible MW2 map, without changing engine code. This separates reusable behavior from map-specific coordinates before building a large editor.

## What “any map and characters” means

The realistic target is any **validated compatible pack**. A new map still needs collision/navigation preparation; a new skeleton needs animation retargeting. Once prepared, that work should be cached and reusable across scenes. The current source does not yet provide universal import or automatic realistic choreography.
