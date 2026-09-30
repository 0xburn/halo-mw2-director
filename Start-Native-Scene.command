#!/bin/zsh
set -eu
cd "${0:A:h}"
exec ./scripts/native_scene.sh
