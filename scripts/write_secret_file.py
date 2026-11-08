#!/usr/bin/env python3
"""Grava uma variavel de ambiente num arquivo 0600. O valor nao vai para o argv."""

import os
import pathlib
import sys


def main():
    if len(sys.argv) != 4:
        print("uso incorreto", file=sys.stderr)
        return 1
    kind, name, target = sys.argv[1:]
    value = os.environ.get(name, "")
    if not value.strip():
        print("variavel vazia", file=sys.stderr)
        return 1
    if "BEGIN " in value and "PRIVATE KEY" in value:
        print("material de chave recusado", file=sys.stderr)
        return 1
    if kind == "backend":
        lowered = value.lower()
        if any(token in lowered for token in ("access_key", "secret_key", "password", "private_key")):
            print("backend nao pode carregar segredo de acesso", file=sys.stderr)
            return 1
        if "bucket" not in lowered or "endpoints" not in lowered:
            print("backend incompleto", file=sys.stderr)
            return 1
    elif kind != "tfvars":
        print("tipo recusado", file=sys.stderr)
        return 1
    path = pathlib.Path(target)
    path.write_text(value if value.endswith("\n") else value + "\n")
    os.chmod(path, 0o600)
    return 0


if __name__ == "__main__":
    sys.exit(main())
