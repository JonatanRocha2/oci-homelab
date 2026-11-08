#!/usr/bin/env python3
"""Troca o JWT efemero do GitHub por um RPST. Nao usa a chave de API."""

import base64
import json
import os
import pathlib
import stat
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

REQUIRED = (
    "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
    "ACTIONS_ID_TOKEN_REQUEST_URL",
    "OCI_GITHUB_OIDC_AUDIENCE",
    "OCI_IDENTITY_DOMAIN_URL",
    "OCI_OAUTH_CLIENT_ID",
    "OCI_OAUTH_CLIENT_SECRET",
    "OCI_REGION",
    "OCI_RPST_RESOURCE_TYPE",
    "RUNNER_TEMP",
)


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def main():
    if os.environ.get("ACTIONS_STEP_DEBUG") or os.environ.get("ACTIONS_RUNNER_DEBUG"):
        fail("debug do runner recusado")
    missing = [name for name in REQUIRED if not os.environ.get(name, "").strip()]
    if missing:
        fail("faltam variaveis de sessao: " + ",".join(missing))
    domain = os.environ["OCI_IDENTITY_DOMAIN_URL"].strip().rstrip("/")
    parsed = urllib.parse.urlparse(domain)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        fail("url do dominio recusada")
    region = os.environ["OCI_REGION"].strip()
    if region != "sa-saopaulo-1":
        fail("regiao recusada")
    if os.environ.get("OCI_RPST_SELFTEST") == "1":
        print("session precheck ok")
        return

    work = pathlib.Path(os.environ["RUNNER_TEMP"]) / "oci-session"
    work.mkdir(mode=0o700, exist_ok=True)
    work.chmod(0o700)
    private = work / "private.pem"
    public = work / "public.pem"
    subprocess.run(
        ["openssl", "genrsa", "-out", str(private), "2048"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    private.chmod(0o600)
    subprocess.run(
        ["openssl", "rsa", "-in", str(private), "-pubout", "-out", str(public)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    public.chmod(0o644)

    audience = urllib.parse.quote(os.environ["OCI_GITHUB_OIDC_AUDIENCE"].strip())
    separator = "&" if "?" in os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"] else "?"
    request = urllib.request.Request(
        os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"] + separator + "audience=" + audience,
        headers={"Authorization": "bearer " + os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            jwt = json.loads(response.read().decode()).get("value")
    except (urllib.error.URLError, json.JSONDecodeError, KeyError):
        fail("oidc do GitHub falhou")
    if not isinstance(jwt, str) or jwt.count(".") != 2:
        fail("oidc do GitHub falhou")

    form = urllib.parse.urlencode(
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "requested_token_type": "urn:oci:token-type:oci-rpst",
            "public_key": public.read_text(),
            "subject_token": jwt,
            "subject_token_type": "jwt",
            "res_type": os.environ["OCI_RPST_RESOURCE_TYPE"].strip(),
            "rpst_exp": "60",
        }
    ).encode()
    basic = base64.b64encode(
        (os.environ["OCI_OAUTH_CLIENT_ID"] + ":" + os.environ["OCI_OAUTH_CLIENT_SECRET"]).encode()
    ).decode()
    exchange = urllib.request.Request(
        domain + "/oauth2/v1/token",
        data=form,
        headers={"Authorization": "Basic " + basic, "Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(exchange, timeout=30) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        fail(f"troca do token HTTP {error.code}")
    except (urllib.error.URLError, json.JSONDecodeError):
        fail("troca do token falhou")
    token = payload.get("token") if isinstance(payload, dict) else None
    if not isinstance(token, str) or not token.strip():
        fail("troca do token falhou")

    rpst = work / "rpst"
    rpst.write_text(token)
    rpst.chmod(0o600)
    session = work / "session.env"
    session.write_text(
        "\n".join(
            [
                "export OCI_AUTH=ResourcePrincipal",
                "export OCI_RESOURCE_PRINCIPAL_VERSION=2.2",
                "export OCI_RESOURCE_PRINCIPAL_RPST=" + sh(rpst),
                "export OCI_RESOURCE_PRINCIPAL_PRIVATE_PEM=" + sh(private),
                "export OCI_RESOURCE_PRINCIPAL_REGION=" + sh(region),
                "",
            ]
        )
    )
    session.chmod(stat.S_IRUSR | stat.S_IWUSR)
    print(session)


def sh(path):
    text = str(path)
    if not text.startswith("/") or "\n" in text or "'" in text:
        fail("caminho de sessao recusado")
    return "'" + text + "'"


if __name__ == "__main__":
    main()
