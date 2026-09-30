#!/usr/bin/env python3
"""Local launcher and asset importer. Python 3.9+, standard library only."""
import argparse
import functools
import http.server
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import webbrowser

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
REPO = ROOT / "vendor-src" / "iw4L"
PIN = "1a0daffd182d808ad3fa43adc6da0200fe78610d"
URL = "https://github.com/vladtrc/iw4L.git"
LOCAL_CARGO = ROOT / ".tools" / "cargo"
if (LOCAL_CARGO / "bin" / "cargo").exists():
    os.environ["PATH"] = str(LOCAL_CARGO / "bin") + os.pathsep + os.environ.get("PATH", "")
    os.environ["CARGO_HOME"] = str(LOCAL_CARGO)
    os.environ["RUSTUP_HOME"] = str(ROOT / ".tools" / "rustup")
    os.environ["CARGO_TARGET_DIR"] = str(ROOT / ".tools" / "iw4l-target")
    os.environ["CARGO_PROFILE_PLAY_DEBUG"] = "0"
    os.environ["CARGO_PROFILE_PLAY_INCREMENTAL"] = "false"


def run(argv, cwd=None, env=None, capture=False):
    print("+", " ".join(map(str, argv)), flush=True)
    return subprocess.run(list(map(str, argv)), cwd=cwd, env=env, check=True,
                          text=True, stdout=subprocess.PIPE if capture else None)


def require(name):
    if not shutil.which(name):
        raise ValueError("Missing " + name + ". See prerequisites in README.md.")


def read_config():
    path = WEB / "config.json"
    return json.loads((path if path.exists() else WEB / "config.example.json").read_text())


def write_config(config):
    target = WEB / "config.json"
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n")
    temporary.replace(target)


def setup():
    require("git")
    if not REPO.exists():
        REPO.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "init", REPO])
        run(["git", "remote", "add", "origin", URL], REPO)
    # A network interruption can leave a valid, empty checkout.
    head = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=REPO,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if head.returncode:
        run(["git", "fetch", "--depth", "1", "origin", PIN], REPO)
        run(["git", "checkout", "--detach", "FETCH_HEAD"], REPO)
    actual = run(["git", "rev-parse", "HEAD"], REPO, capture=True).stdout.strip()
    if actual != PIN:
        raise ValueError("IW4L checkout is not at the reviewed commit. Keep your checkout; move it elsewhere, then run setup-iw4l again.")
    patch = ROOT / "patches" / "native-cinema.patch"
    applied = subprocess.run(["git", "apply", "--reverse", "--check", str(patch)], cwd=REPO,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if applied.returncode:
        run(["git", "apply", "--check", patch], REPO)
        run(["git", "apply", patch], REPO)
    print("IW4L is ready at " + str(REPO))


def game_root(raw):
    path = Path(raw).expanduser().resolve()
    if not path.is_dir():
        raise ValueError("Game directory does not exist: " + str(path))
    for name in ("common_mp.ff", "mp_rust.ff"):
        if not any(path.rglob(name)):
            raise ValueError("Missing " + name + " under " + str(path) +
                             ". Point --games at the Windows MW2 (2009) Multiplayer install or its parent.")
    return path


def native(args, export=False):
    require("cargo")
    games = game_root(args.games)
    setup()
    env = os.environ.copy()
    env["IW4L_GAMES"] = str(games)
    command = ["cargo", "run", "--locked", "--profile", "play", "-p", "launcher", "--"]
    if export:
        export_root = REPO / "iw4l-artifacts" / "exports" / "mp_rust"
        before = set(export_root.glob("*/scene.gltf"))
        run(command + ["export-gltf", "mp_rust"], REPO, env)
        outputs = set(export_root.glob("*/scene.gltf")) - before
        if not outputs:
            raise ValueError("Exporter did not produce a new scene.gltf. Read its refusal report above.")
        source = max(outputs, key=lambda p: p.stat().st_mtime)
        import_world(source)
    else:
        run(command + ["map", "mp_rust", "--cmds",
                      "wait world; spawn assault; force_match_start"], REPO, env)


def validate_gltf(document, base):
    unsupported = {"KHR_draco_mesh_compression", "EXT_meshopt_compression", "KHR_texture_basisu"}
    needed = set(document.get("extensionsRequired", []))
    if needed & unsupported:
        raise ValueError("Export an uncompressed GLB/glTF. Unsupported: " + ", ".join(sorted(needed & unsupported)))
    if not str(document.get("asset", {}).get("version", "")).startswith("2."):
        raise ValueError("Expected glTF 2.0")
    dependencies = []
    for resource in document.get("buffers", []) + document.get("images", []):
        uri = resource.get("uri")
        if uri and not uri.startswith("data:"):
            from urllib.parse import unquote, urlsplit
            parsed = urlsplit(uri)
            if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
                raise ValueError("Asset references must be local relative paths: " + uri)
            resource_path = base / unquote(parsed.path)
            try:
                resource_path.resolve().relative_to(base.resolve())
            except ValueError:
                raise ValueError("Asset reference escapes its folder: " + uri)
            if not resource_path.is_file():
                raise ValueError("Missing asset dependency: " + str(resource_path))
            dependencies.append(resource_path)
    return dependencies


def import_world(source):
    source = Path(source).expanduser().resolve()
    if source.is_dir():
        source = source / "scene.gltf"
    if not source.is_file() or source.suffix != ".gltf":
        raise ValueError("Expected the IW4L scene.gltf file, or its containing folder.")
    document = json.loads(source.read_text())
    dependencies = validate_gltf(document, source.parent)
    assets = WEB / "assets"
    assets.mkdir(exist_ok=True)
    # A new folder keeps an already working import intact if copying fails.
    destination = Path(tempfile.mkdtemp(prefix="rust-", dir=assets))
    try:
        shutil.copy2(source, destination / "scene.gltf")
        for dependency in dependencies:
            output = destination / dependency.relative_to(source.parent)
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dependency, output)
        spawn_file = source.with_name("spawns.json")
        if spawn_file.exists():
            json.loads(spawn_file.read_text())
            shutil.copy2(spawn_file, destination / "spawns.json")
        config = read_config()
        config["world"] = str((destination / "scene.gltf").relative_to(WEB))
        config["spawns"] = str((destination / "spawns.json").relative_to(WEB)) if spawn_file.exists() else None
        write_config(config)
    except Exception:
        shutil.rmtree(destination)
        raise
    print("Imported world. Run: python3 manage.py serve")
    if not spawn_file.exists():
        print("No spawns.json supplied. Set spawn/yaw in web/config.json or use F to fly and inspect coordinates.")


def import_model(kind, raw):
    source = Path(raw).expanduser().resolve()
    data = source.read_bytes()
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError("Expected a binary .glb file exported as glTF 2.0.")
    version, length, json_size, chunk_type = struct.unpack_from("<IIII", data, 4)
    if version != 2 or length != len(data) or chunk_type != 0x4E4F534A or 20 + json_size > len(data):
        raise ValueError("Invalid GLB header or JSON chunk.")
    document = json.loads(data[20:20+json_size].rstrip(b" \x00"))
    dependencies = validate_gltf(document, source.parent)
    if dependencies:
        raise ValueError("Use a self-contained .glb with embedded textures and buffers.")
    destination = WEB / "assets" / (kind + ".glb")
    destination.parent.mkdir(exist_ok=True)
    temporary = destination.with_suffix(".glb.tmp")
    temporary.write_bytes(data)
    temporary.replace(destination)
    config = read_config()
    if kind in ("chief", "rifle"):
        config[kind]["url"] = str(destination.relative_to(WEB))
    else:
        spec = config.setdefault("models", {}).setdefault(kind, {"length": {"pistol": .4, "sniper": 1.6, "rocket": 1.2}[kind], "rotation": [0, 0, 0]})
        spec["url"] = str(destination.relative_to(WEB))
    write_config(config)
    print("Imported " + kind + ". Adjust model rotation/size/animation names in web/config.json if needed.")


class LocalHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, format, *args):
        if args and str(args[1]) not in ("200", "304"):
            super().log_message(format, *args)


def serve(args):
    if not (WEB / "config.json").exists():
        write_config(read_config())
    handler = functools.partial(LocalHandler, directory=str(WEB))
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        url = "http://127.0.0.1:" + str(server.server_port)
        print("Prototype: " + url + "\nCtrl+C to stop.", flush=True)
        if not args.no_open:
            threading.Timer(.3, lambda: webbrowser.open(url)).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def doctor():
    print("Python:", sys.version.split()[0])
    for tool in ("git", "cargo"):
        print(tool + ":", shutil.which(tool) or "not installed (needed only for IW4L)")
    config = read_config()
    paths = [("world", config["world"]), ("chief", config["chief"]["url"])]
    paths += [(name, spec.get("url")) for name, spec in config.get("models", {"rifle": config["rifle"]}).items()]
    for label, path in paths:
        print(label + ":", "procedural placeholder" if path is None else ("OK: " if (WEB / path).is_file() else "MISSING: ") + path)
    print("IW4L commit:", PIN)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    commands.add_parser("setup-iw4l")
    web = commands.add_parser("serve")
    web.add_argument("--port", type=int, default=8765)
    web.add_argument("--no-open", action="store_true")
    for verb in ("native", "export-rust"):
        item = commands.add_parser(verb)
        item.add_argument("--games", required=True)
    item = commands.add_parser("import-world")
    item.add_argument("path")
    item = commands.add_parser("import-model")
    item.add_argument("kind", choices=["chief", "rifle", "pistol", "sniper", "rocket"])
    item.add_argument("path")
    args = parser.parse_args()
    try:
        if args.command == "serve": serve(args)
        elif args.command == "doctor": doctor()
        elif args.command == "setup-iw4l": setup()
        elif args.command == "native": native(args)
        elif args.command == "export-rust": native(args, export=True)
        elif args.command == "import-world": import_world(args.path)
        elif args.command == "import-model": import_model(args.kind, args.path)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print("Error:", error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
