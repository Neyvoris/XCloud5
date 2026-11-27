#!/usr/bin/env python3
"""Pin the release SPKI and generate its native C header."""
import argparse
import base64
import binascii
import hashlib
from pathlib import Path

EXPECTED_SHA256 = "2663584d81c0fa6a05bf0cbe878c286902fba284ea5dad5cbc0101b268203595"
X5_EXPECTED_SHA256 = "21ebc0d072e2caead3fcf9faf5795046e185b7b6d1f8a76ec5ef60cf2b6eeff8"
P256_PREFIX = bytes.fromhex("3059301306072a8648ce3d020106082a8648ce3d03010703420004")


def public_der(path):
    with path.open("rb") as pem:
        if pem.readline(64).rstrip(b"\r\n") != b"-----BEGIN PUBLIC KEY-----":
            raise ValueError("Se requiere un PEM con la clave pública SPKI de release")
        lines = pem.read(512).strip().splitlines()
    if len(lines) < 2 or lines[-1] != b"-----END PUBLIC KEY-----":
        raise ValueError("PEM de clave pública incompleto")
    der = base64.b64decode(b"".join(lines[:-1]), validate=True)
    if len(der) != len(P256_PREFIX) + 64 or not der.startswith(P256_PREFIX):
        raise ValueError("Se requiere una clave pública ECDSA P-256")
    digest = hashlib.sha256(der).hexdigest()
    expected = {"release_pubkey.pem": EXPECTED_SHA256, "xcloud5_release_pubkey.pem": X5_EXPECTED_SHA256}.get(path.name)
    if expected and digest != expected:
        raise ValueError("La huella DER no coincide con la clave pública de release")
    return der, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pem", type=Path)
    parser.add_argument("header", type=Path)
    args = parser.parse_args()
    try:
        der, digest = public_der(args.pem)
        rows = ["    " + ", ".join(f"0x{byte:02x}" for byte in der[i:i + 12]) + ","
                for i in range(0, len(der), 12)]
        content = ("/* Generated from the pinned public release key. */\n"
                   "#ifndef X4_UPDATE_RELEASE_PUBKEY_H\n#define X4_UPDATE_RELEASE_PUBKEY_H\n"
                   "static const unsigned char x4_update_release_pubkey_der[] = {\n"
                   + "\n".join(rows) + "\n};\n#endif\n")
        args.header.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.header.with_suffix(".tmp")
        temporary.write_text(content, encoding="ascii", newline="\n")
        temporary.replace(args.header)
    except (OSError, ValueError, binascii.Error) as exc:
        parser.exit(1, f"{exc}\n")
    print(f"XCloud4 update public key SPKI SHA-256 {digest}")


if __name__ == "__main__":
    main()
