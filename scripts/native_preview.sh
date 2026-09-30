#!/bin/zsh
# Use the compiled native IW4L renderer and local retail data.
set -eu
project_root="${0:A:h:h}"
cd "$project_root/vendor-src/iw4L"
export IW4L_GAMES="$project_root/local-assets/mw2"
export IW4L_SETTINGS_PATH="$project_root/.tools/iw4l-settings.cfg"
export IW4L_RETAIL_SETTINGS=1
exec "$project_root/.tools/iw4l-target/play/iw4l" map mp_rust "$@"
