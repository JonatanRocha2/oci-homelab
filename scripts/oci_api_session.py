#!/usr/bin/env python3
"""Prepara a chave de API documentada pelo provider. Nao chama a OCI."""

import os
import pathlib
import re
import stat
import sys

REQUIRED = (
    "OCI_TENANCY_OCID",
    "OCI_USER_OCID",
    "OCI_FINGERPRINT",
    "OCI_PRIVATE_KEY",
    "OCI_REGION",
    "RUNNER_TEMP",
)
TENANCY_RE = re.compile(r"^ocid1\.tenancy\.oc1\.\.[A-Za-z0-9._-]+$")
USER_RE = re.compile(r"^ocid1\.user\.oc1\.\.[A-Za-z0-9._-]+$")
FINGERPRINT_RE = re.compile(r"^(?:[0-9a-f]{2}:){15}[0-9a-f]{2}$")


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def sh(value):
    if not isinstance(value, str) or not value or "\n" in value or "'" in value:
        fail("valor de sessao recusado")
    return "'" + value + "'"


def main():
    if os.environ.get("ACTIONS_STEP_DEBUG") or os.environ.get("ACTIONS_RUNNER_DEBUG"):
        fail("debug do runner recusado")
    missing = [name for name in REQUIRED if not os.environ.get(name, "").strip()]
    if missing:
        fail("faltam variaveis de sessao: " + ",".join(missing))
    tenancy = os.environ["OCI_TENANCY_OCID"].strip()
    user = os.environ["OCI_USER_OCID"].strip()
    fingerprint = os.environ["OCI_FINGERPRINT"].strip().lower()
    region = os.environ["OCI_REGION"].strip()
    private_key = os.environ["OCI_PRIVATE_KEY"]
    if not TENANCY_RE.fullmatch(tenancy) or not USER_RE.fullmatch(user):
        fail("identidade recusada")
    if not FINGERPRINT_RE.fullmatch(fingerprint) or region != "sa-saopaulo-1":
        fail("fingerprint ou regiao recusada")
    if "BEGIN " not in private_key or "PRIVATE KEY" not in private_key:
        fail("chave recusada")
    home = os.environ.get("HOME", "")
    if home and (pathlib.Path(home) / ".oci" / "config").exists():
        fail("ja existe configuracao OCI neste HOME; ela nao sera substituida")

    work = pathlib.Path(os.environ["RUNNER_TEMP"]) / "oci-session"
    work.mkdir(mode=0o700, exist_ok=True)
    work.chmod(0o700)
    key_path = work / "api-key.pem"
    key_path.write_text(private_key if private_key.endswith("\n") else private_key + "\n")
    key_path.chmod(0o600)
    if home:
        config_dir = pathlib.Path(home) / ".oci"
        config_dir.mkdir(mode=0o700, exist_ok=True)
        config_dir.chmod(0o700)
        config = config_dir / "config"
        config.write_text(
            "\n".join(
                [
                    "[DEFAULT]",
                    "user=" + user,
                    "fingerprint=" + fingerprint,
                    "tenancy=" + tenancy,
                    "region=" + region,
                    "key_file=" + str(key_path),
                    "",
                ]
            )
        )
        config.chmod(0o600)
    session = work / "session.env"
    session.write_text(
        "\n".join(
            [
                "export OCI_AUTH=APIKey",
                "export OCI_TENANCY_OCID=" + sh(tenancy),
                "export OCI_USER_OCID=" + sh(user),
                "export OCI_FINGERPRINT=" + sh(fingerprint),
                "export OCI_PRIVATE_KEY_PATH=" + sh(str(key_path)),
                "export OCI_REGION=" + sh(region),
                "unset OCI_PRIVATE_KEY",
                "",
            ]
        )
    )
    session.chmod(stat.S_IRUSR | stat.S_IWUSR)
    if "PRIVATE KEY" in session.read_text():
        fail("sessao vazaria a chave")
    print(session)


if __name__ == "__main__":
    main()
