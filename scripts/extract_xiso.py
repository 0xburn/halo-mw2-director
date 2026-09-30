#!/usr/bin/env python3
"""Extract selected map files from a local Xbox XDVDFS image, read-only."""
import argparse
from pathlib import Path, PurePosixPath
import struct


def extract_maps(image, destination, names=("bloodgulch.map",)):
    image, destination = Path(image), Path(destination)
    size = image.stat().st_size
    found = []
    with image.open("rb") as source:
        def read(offset, count):
            if offset < 0 or count < 0 or offset + count > size:
                raise ValueError("XDVDFS entry is outside the image")
            source.seek(offset)
            data = source.read(count)
            if len(data) != count:
                raise ValueError("Truncated image")
            return data

        for partition in (0, 0xFD90000, 0x2080000, 0x18300000):
            if partition + 0x10800 > size:
                continue
            descriptor = read(partition + 0x10000, 2048)
            if descriptor[:20] == descriptor[-20:] == b"MICROSOFT*XBOX*MEDIA":
                sector, length = struct.unpack_from("<II", descriptor, 20)
                break
        else:
            raise ValueError("No Xbox XDVDFS volume found")

        visited_dirs = set()

        def directory(sector, length, path):
            if sector in visited_dirs or len(visited_dirs) >= 4096 or len(path.parts) > 32:
                raise ValueError("Invalid or recursive directory tree")
            visited_dirs.add(sector)
            if not 0 < length <= 4 * 1024 * 1024:
                raise ValueError("Invalid directory size")
            table = read(partition + sector * 2048, length)
            pending, seen = [0], set()
            while pending:
                offset = pending.pop()
                if offset in seen or offset + 14 > length:
                    raise ValueError("Invalid directory entry")
                seen.add(offset)
                left, right, start, count, flags, namelen = struct.unpack_from("<HHIIBB", table, offset)
                if left == 0xFFFF:
                    continue
                if not namelen or offset + 14 + namelen > length:
                    raise ValueError("Invalid filename")
                name = table[offset + 14:offset + 14 + namelen].decode("ascii")
                if name in (".", "..") or any(c in name for c in "/\\\x00"):
                    raise ValueError("Unsafe filename in image")
                item = path / name
                if left:
                    pending.append(left * 4)
                if right:
                    pending.append(right * 4)
                if flags & 0x10:
                    if item.parts[0].lower() == "maps":
                        directory(start, count, item)
                elif len(item.parts) == 2 and item.parts[0].lower() == "maps" and name.lower() in names:
                    destination.mkdir(parents=True, exist_ok=True)
                    output = destination / name.lower()
                    temporary = output.with_suffix(".map.partial")
                    try:
                        with temporary.open("wb") as target:
                            for position in range(0, count, 1024 * 1024):
                                target.write(read(partition + start * 2048 + position, min(1024 * 1024, count - position)))
                        temporary.replace(output)
                    except Exception:
                        temporary.unlink(missing_ok=True)
                        raise
                    found.append(output)
                    print(f"Extracted {item}: {count:,} bytes → {output}")

        directory(sector, length, PurePosixPath())
    missing = set(names) - {p.name for p in found}
    if missing:
        raise ValueError("Map files not found: " + ", ".join(sorted(missing)))
    return found


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    parser.add_argument("destination")
    parser.add_argument("--map", action="append", dest="maps")
    args = parser.parse_args()
    extract_maps(args.image, args.destination, tuple(args.maps or ["bloodgulch.map"]))
