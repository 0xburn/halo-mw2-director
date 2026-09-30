#!/bin/zsh
set -eu
project_root="${0:A:h:h}"
map_pack="${1:-$project_root/local-assets/halo/native-maps/battle-creek}"
if (( $# )); then shift; fi
map_pack="${map_pack:A}"
if [[ ! -f "$map_pack/map.json" ]]; then
  print -u2 "Map pack not found: $map_pack/map.json"
  exit 1
fi
mkdir -p "$project_root/local-runs/halo-map"
cd "$project_root/local-runs/halo-map"
export IW4L_GAMES="$project_root/local-assets/mw2"
export IW4L_SETTINGS_PATH="$project_root/.tools/iw4l-settings.cfg"
export IW4L_RETAIL_SETTINGS=1 IW4L_CONSOLE_STDIN=1
export IW4L_LOCAL_MAP="$map_pack"
unset IW4L_CINEMA
exec "$project_root/.tools/iw4l-target/play/iw4l" map mp_rust --cmds 'wait world; spawn intervention; force_match_start' "$@"
