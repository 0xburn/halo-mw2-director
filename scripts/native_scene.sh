#!/bin/zsh
set -eu
project_root="${0:A:h:h}"
scene_file="$project_root/local-assets/scenes/worlds-collide-native.json"
map_name=""
while (( $# )); do
  case "$1" in
    --scene) scene_file="$2"; shift 2 ;;
    --map) map_name="$2"; shift 2 ;;
    *) break ;;
  esac
done
scene_file="${scene_file:A}"
if [[ -z "$map_name" ]]; then
  map_name=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("map", "mp_rust"))' "$scene_file")
fi
mkdir -p "$project_root/local-runs/cinema"
cd "$project_root/local-runs/cinema"
export IW4L_GAMES="$project_root/local-assets/mw2"
export IW4L_SETTINGS_PATH="$project_root/.tools/iw4l-settings.cfg"
export IW4L_RETAIL_SETTINGS=1 IW4L_CONSOLE_STDIN=1
export IW4L_CHIEF_PACK="$project_root/local-assets/halo/native"
export IW4L_CINEMA="$scene_file"
exec "$project_root/.tools/iw4l-target/play/iw4l" map "$map_name" --cmds 'wait world; spawn intervention; force_match_start' "$@"
