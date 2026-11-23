#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Verify shipped PS4 glyph atlases really contain Russian Cyrillic."""
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1] / "assets/fonts"
REQUIRED = set(range(0x0410, 0x0450)) | {0x0401, 0x0451, 0x2116}
ATLAS_MAX = 4 * 1024 * 1024

def verify(path):
    data = path.read_bytes()
    if len(data) < 32:
        raise AssertionError(f"{path}: truncated")
    magic, version, faces, glyph_count, alpha_count, face_bytes, glyph_bytes = \
        struct.unpack_from("<8s6I", data)
    assert magic == b"X4FNT01\0" and version == 1
    assert face_bytes == 32 and glyph_bytes == 24
    assert faces >= 14 and glyph_count > 0
    assert len(data) == 32 + faces * face_bytes + glyph_count * glyph_bytes + alpha_count
    glyph_base = 32 + faces * face_bytes
    for face in range(faces):
        size, weight, first, count, *_ = struct.unpack_from("<8I", data, 32 + face * face_bytes)
        assert first + count <= glyph_count
        codepoints = set()
        for i in range(first, first + count):
            cp = struct.unpack_from("<I", data, glyph_base + i * glyph_bytes)[0]
            codepoints.add(cp)
        missing = REQUIRED - codepoints
        if missing:
            raise AssertionError(f"{path.name}: {len(missing)} missing Cyrillic codepoints at size {size}, weight {weight}")
    print(f"PASS {path.name}: {faces} faces, all Russian letters, {len(data)} bytes")
    return len(data)

def main():
    noto = verify(ROOT / "noto_sans.x4font")
    inter = verify(ROOT / "inter.x4font")
    manifest = json.loads((ROOT / "ATLAS.json").read_text(encoding="utf-8"))
    fallback = manifest["fallback_bytes"]
    assert noto < ATLAS_MAX and inter + fallback <= ATLAS_MAX
    assert manifest["atlas_bytes"] == noto and manifest["inter"]["atlas_bytes"] == inter
    print(f"PASS Cyrillic asset budget: Inter + fallback = {inter + fallback}/{ATLAS_MAX} bytes")

if __name__ == "__main__":
    main()
