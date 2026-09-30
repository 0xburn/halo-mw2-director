#!/bin/zsh
set -eu
project_root="${0:A:h:h}"
cd "$project_root/vendor-src/iw4L"
# Keep path spelling consistent: changing Cargo's home spelling invalidates
# dependency fingerprints even when it resolves to the same directory.
export CARGO_HOME="$PWD/../../.tools/cargo"
export RUSTUP_HOME="$PWD/../../.tools/rustup"
export CARGO_TARGET_DIR="$PWD/../../.tools/iw4l-target"
export CARGO_PROFILE_PLAY_DEBUG=0 CARGO_PROFILE_PLAY_INCREMENTAL=false
if [[ -x ../../.tools/cargo/bin/cargo ]]; then
  exec ../../.tools/cargo/bin/cargo build --locked --profile play -p launcher
fi
# Fresh checkouts can use an existing system Rust installation.
unset CARGO_HOME RUSTUP_HOME
exec cargo build --locked --profile play -p launcher
