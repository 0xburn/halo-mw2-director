#!/bin/zsh
set -eu
project_root="${0:A:h:h}"
map_pack="${1:-$project_root/local-assets/halo/native-maps/battle-creek}"
if (( $# )); then shift; fi
map_pack="${map_pack:A}"
[[ -f "$map_pack/map.json" ]] || { print -u2 "Missing map pack: $map_pack/map.json"; exit 1; }
[[ -f "$project_root/local-assets/halo/native/chief.json" ]] || { print -u2 "Prepare the native Halo character pack first."; exit 1; }
mkdir -p "$project_root/local-runs/bot-match"
cd "$project_root/local-runs/bot-match"
export IW4L_GAMES="$project_root/local-assets/mw2"
export IW4L_SETTINGS_PATH="$project_root/.tools/iw4l-settings.cfg"
export IW4L_RETAIL_SETTINGS=1 IW4L_CONSOLE_STDIN=1
export IW4L_LOCAL_MAP="$map_pack"
export IW4L_CHIEF_PACK="$project_root/local-assets/halo/native"
export IW4L_BOT_MATCH=1 IW4L_GAMETYPE=war IW4L_INSTANT_RESPAWN=1
export IW4L_SCRIPT_DVARS='set scr_war_timelimit 0; set scr_war_scorelimit 0; set scr_war_playerrespawndelay 0; set scr_war_waverespawndelay 0; set scr_teambalance 0; set scr_team_fftype 0; set scr_game_allowkillcam 0; set scr_player_forcerespawn 1'
unset IW4L_CINEMA
exec "$project_root/.tools/iw4l-target/play/iw4l" map mp_rust --cmds 'wait world; spawn intervention; force_match_start' "$@"
