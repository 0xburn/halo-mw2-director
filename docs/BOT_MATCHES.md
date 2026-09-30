# Autonomous native bot matches

After [native setup](NATIVE_SETUP.md) and preparing [Battle Creek](HALO_MAPS.md):

```sh
./scripts/native_bot_match.sh
```

This starts native team deathmatch: four MW2 quickscopers (allies) against four
Spartans (axis). They use observations, navigation, ordinary user commands,
weapon collision/damage and respawning. There is no cinematic timeline or
scripted kill. Both classes spawn with 30 HP and instant respawns: zero respawn/wave timers,
killcams disabled, and the fixed death-watch wait removed from the locally loaded
script with `IW4L_INSTANT_RESPAWN=1`. Normal scoring, corpses and spawn selection
remain active. A changed script without the expected death block fails loading
explicitly rather than silently retaining the delay.
Time and score limits are disabled.
Reserve ammunition is
replenished; magazines still empty and require normal reloads.

Left-click (or F6) cycles **soldiers 1–4 → Spartans 1–4 → overview**. **V** (or F7) toggles first person / an eased shoulder camera for
the selected bot; F5 returns directly to overview. The shoulder camera follows
turns smoothly, aims near the character’s torso, sits up to 273 units behind
the player, and checks walls before pulling back. Its field of view stays wide
when the bot scopes in, and it clears first-person camera animation on entry.
A textured model bust,
player name and class sit beside the score HUD. **X** toggles auto-director: it
ranks unobstructed head/torso sightlines and favors the opponent nearest the
player’s crosshair, with smaller bonuses for aiming down sights and firing.
It can switch to the better attacker during a fight. Cuts require a meaningful
advantage and a brief stable candidate, with a shorter hold when leaving an idle
or dead player. With no visible fights, it favors players approaching opponents.
Clicking/F5/F6 returns to manual selection.

Your first/third-person choice persists through deaths. First-person holds the
last view until respawn; it does not enter MW2's automatic third-person death cam.
Switching players resets recoil/landing history; small grounded steps are eased
without smoothing away jump arcs. In overview, use WASD to move,
Q/E down/up, arrow keys to turn, and Shift to move faster. The observed bot
keeps its AI controller; clicks never take control of its movement or weapon.

Bots favor outdoor spawn points and reachable central patrol positions near
the main floor (preferring the banks over low creek-bed patrol points), and
pursue the most recently spotted enemy for up to four seconds after losing sight.
Firing still requires a fresh positive line-of-sight check.

Both profiles use the Intervention, its first-person model and animations,
and Sleight of Hand Pro/Lightweight/Ninja-style perks. Spartans use the local
CE body model, 270 in/s forward movement, reduced gravity, a 252 in/s jump
impulse, and stronger air control. They jump evasively when enemies are visible
and there is headroom. Spartan shots use the weapon's aimed spread even in
midair; soldiers keep the native movement/jump accuracy penalties. COD bots
release movement while raising the scope and wait until grounded with negligible
horizontal speed before firing, then resume moving between shots.

The class is a CE-style movement adaptation to IW4 collision and animation,
not a complete Halo physics implementation. It does not add Halo shields.

Reusable native console commands (`watch 1`–`4` selects soldiers; `watch 5`–`8` selects Spartans):

```text
bot quickscope 4
bot spartan 4
bot hold on
bot hold off
watch next
watch 5
watch third
watch first
watch overview
watch auto
watch manual
watch status
```

Spartans require the prepared local Chief pack (`IW4L_CHIEF_PACK`). Use a team
mode (`IW4L_GAMETYPE=war`) for opposing class teams. The launcher sets both.
Pass another prepared map directory as the launcher's first argument. Navigation
supports walking and drops; imported scenery collision and complicated ledges
remain limitations of the map/AI prototype.

The replicated movement profile changes the native network protocol to 82;
all peers must use this build. Older native demo files may be incompatible.
