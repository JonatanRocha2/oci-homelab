#!/usr/bin/env python3
"""Guardas do plano e do apply. Nao chama a OCI e nao imprime segredo."""

import hashlib
import json
import pathlib
import re
import sys

REPO = "JonatanRocha2/oci-homelab"
REF = "refs/heads/main"
WORKFLOW = ".github/workflows/homelab.yml"
APPLY_ENVIRONMENT = "homelab-apply"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
ALLOWED_CIDRS = {"10.0.0.0/16", "10.0.1.0/24"}
ALLOWED_ADDRESSES = {
    "data.oci_identity_availability_domains.available",
    "data.oci_core_images.ubuntu_arm",
    "terraform_data.guards",
    "oci_core_instance.homelab",
    "oci_core_vcn.this",
    "oci_core_internet_gateway.this",
    "oci_core_route_table.public",
    "oci_core_security_list.homelab",
    "oci_core_default_security_list.locked",
    "oci_core_subnet.public",
}
SAFE_ACTIONS = {"create", "update", "no-op", "read"}
FORBIDDEN_OUTPUT = (
    "ocid1",
    "BEGIN ",
    "PRIVATE",
    "ssh-ed25519",
    "ssh-rsa",
    "AAAAC3",
)


def _die(message):
    print(message, file=sys.stderr)
    return 1


def require_approval(payload, actor):
    if not isinstance(actor, str) or not actor.strip():
        return "quem disparou o workflow nao esta identificado"
    if not isinstance(payload, list) or not payload:
        return "nao ha registro de aprovacao; o ambiente nao segurou o job"
    approved = False
    for item in payload:
        if not isinstance(item, dict):
            return "registro de aprovacao invalido"
        names = []
        for env in item.get("environments") or []:
            if isinstance(env, dict) and isinstance(env.get("name"), str):
                names.append(env["name"])
        if APPLY_ENVIRONMENT not in names:
            continue
        if item.get("state") != "approved":
            return "a aprovacao de homelab-apply nao esta approved"
        user = item.get("user") if isinstance(item.get("user"), dict) else {}
        login = user.get("login")
        if not isinstance(login, str) or not login.strip():
            return "a aprovacao nao identifica o revisor"
        if login.casefold().endswith("[bot]"):
            return "aprovacao feita por aplicacao nao serve"
        approved = True
    if not approved:
        return "nenhuma aprovacao approved de homelab-apply"
    return None


def _resources(state):
    if not isinstance(state, dict):
        return None
    resources = state.get("resources")
    if not isinstance(resources, list):
        return None
    if any(not isinstance(item, dict) for item in resources):
        return None
    return resources


def guard_state(state, allow_empty):
    resources = _resources(state)
    if resources is None:
        return "estado remoto ausente ou invalido"
    empty = len(resources) == 0
    if empty and not allow_empty:
        return "estado remoto sem recursos; o primeiro uso exige acknowledge_empty_state"
    if (not empty) and allow_empty:
        return "acknowledge_empty_state so vale quando o estado nao tem recursos"
    return None


def _lineage(value):
    if not isinstance(value, str) or not value or len(value) > 128:
        return False
    if any(char.isspace() for char in value) or "/" in value or "ocid1" in value:
        return False
    return True


def check_changes(changes):
    if not isinstance(changes, list):
        return "plano sem resource_changes"
    for change in changes:
        if not isinstance(change, dict):
            return "mudanca invalida"
        address = change.get("address")
        if address not in ALLOWED_ADDRESSES:
            return "o plano tem recurso fora da lista fechada"
        body = change.get("change") if isinstance(change.get("change"), dict) else {}
        actions = body.get("actions")
        if not isinstance(actions, list) or not actions:
            return "acao de plano ausente"
        if any(action not in SAFE_ACTIONS for action in actions):
            return "o plano tem acao que este fluxo nao aplica"
        if "delete" in actions:
            return "o plano tem delete"
    return None


def write_metadata(plan, state, sha):
    if not SHA_RE.fullmatch(sha or ""):
        return None, "sha invalido"
    error = check_changes(plan.get("resource_changes"))
    if error:
        return None, error
    resources = _resources(state)
    if resources is None:
        return None, "estado remoto ausente ou invalido"
    if not _lineage(state.get("lineage")) or type(state.get("serial")) is not int:
        return None, "lineage ou serial ausente"
    addresses = []
    for change in plan.get("resource_changes") or []:
        addresses.append(change["address"])
    metadata = {
        "repository": REPO,
        "ref": REF,
        "git_sha": sha,
        "workflow": WORKFLOW,
        "has_delete": False,
        "empty_state": len(resources) == 0,
        "state_lineage": state["lineage"],
        "state_serial": state["serial"],
        "resource_addresses": addresses,
    }
    return metadata, None


def verify_binding(metadata, plan_bytes, sha):
    if not isinstance(metadata, dict):
        return "metadata invalida"
    digest = hashlib.sha256(plan_bytes).hexdigest()
    expected = {
        "repository": REPO,
        "ref": REF,
        "git_sha": sha,
        "workflow": WORKFLOW,
        "has_delete": False,
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            return "o plano nao esta amarrado a este commit"
    if metadata.get("plan_sha256") != digest or not HEX64_RE.fullmatch(digest):
        return "o arquivo do plano nao confere com o hash aprovado"
    if not _lineage(metadata.get("state_lineage")) or type(metadata.get("state_serial")) is not int:
        return "metadata sem lineage"
    if type(metadata.get("empty_state")) is not bool:
        return "metadata sem empty_state"
    return None


def guard_apply_state(state, metadata, allow_empty):
    error = guard_state(state, allow_empty)
    if error:
        return error
    if metadata.get("empty_state") is not allow_empty:
        return "acknowledge_empty_state nao confere com o plano salvo"
    if state.get("lineage") != metadata.get("state_lineage"):
        return "a lineage do estado mudou depois do plano"
    if state.get("serial") != metadata.get("state_serial"):
        return "o serial do estado mudou depois do plano"
    return None


def verify_run(run, sha):
    if not isinstance(run, dict):
        return "execucao do plano invalida"
    if run.get("conclusion") != "success" or run.get("status") != "completed":
        return "a execucao do plano nao terminou com success"
    if run.get("event") != "workflow_dispatch":
        return "o plano nao veio de workflow_dispatch"
    if run.get("path") != WORKFLOW or run.get("head_branch") != "main":
        return "o plano nao veio do workflow de main"
    if run.get("head_sha") != sha or not SHA_RE.fullmatch(sha or ""):
        return "o sha informado nao e o da execucao do plano"
    repository = run.get("repository")
    if repository is not None:
        name = repository.get("full_name") if isinstance(repository, dict) else None
        if name != REPO:
            return "execucao de outro repositorio"
    html_url = run.get("html_url")
    if isinstance(html_url, str) and html_url and REPO not in html_url:
        return "execucao fora deste repositorio"
    return None


def _walk_strings(value, found):
    if isinstance(value, str):
        found.append(value)
    elif isinstance(value, dict):
        for item in value.values():
            _walk_strings(item, found)
    elif isinstance(value, list):
        for item in value:
            _walk_strings(item, found)


def _safe_number(value):
    if type(value) in (int, float) and not isinstance(value, bool):
        return str(value)
    return "ausente"


def summarize(plan):
    error = check_changes(plan.get("resource_changes"))
    if error:
        return None, error
    lines = ["plano sanitizado"]
    for change in plan.get("resource_changes") or []:
        actions = ",".join(change["change"]["actions"])
        lines.append(f"recurso {change['address']} acoes {actions}")
        after = change["change"].get("after")
        if change["address"] == "oci_core_instance.homelab" and isinstance(after, dict):
            shape = after.get("shape")
            lines.append("shape " + (shape if shape == "VM.Standard.A1.Flex" else "inesperada"))
            config = after.get("shape_config") if isinstance(after.get("shape_config"), dict) else {}
            lines.append("ocpus " + _safe_number(config.get("ocpus")))
            lines.append("memoria_gb " + _safe_number(config.get("memory_in_gbs")))
            source = after.get("source_details") if isinstance(after.get("source_details"), dict) else {}
            lines.append("boot_gb " + _safe_number(source.get("boot_volume_size_in_gbs")))
            lines.append("vpu " + _safe_number(source.get("boot_volume_vpus_per_gb")))
            vnic = after.get("create_vnic_details") if isinstance(after.get("create_vnic_details"), dict) else {}
            public = vnic.get("assign_public_ip")
            ipv6 = vnic.get("assign_ipv6ip")
            lines.append("ipv4_efemero " + ("true" if public is True else "false" if public is False else "ausente"))
            lines.append("ipv6 " + ("true" if ipv6 is True else "false" if ipv6 is False else "ausente"))
        if change["address"] == "oci_core_security_list.homelab" and isinstance(after, dict):
            rules = after.get("ingress_security_rules")
            count = len(rules) if isinstance(rules, list) else -1
            lines.append(f"regras_ssh {count}")
        if change["address"] in {"oci_core_vcn.this", "oci_core_subnet.public"} and isinstance(after, dict):
            cidr = after.get("cidr_block")
            lines.append("cidr " + (cidr if cidr in ALLOWED_CIDRS else "diferente_do_desenho"))
    outputs = plan.get("output_changes") if isinstance(plan.get("output_changes"), dict) else {}
    image = outputs.get("image_name")
    if isinstance(image, dict) and isinstance(image.get("after"), str):
        name = image["after"]
        if name.startswith("Canonical-Ubuntu-24.04-aarch64-") and "ocid1" not in name:
            lines.append("imagem " + name)
        else:
            lines.append("imagem inesperada")
    text = "\n".join(lines) + "\n"
    if any(token in text for token in FORBIDDEN_OUTPUT):
        return None, "resumo vazaria dado proibido"
    for match in IPV4_RE.findall(text):
        if not any(match in cidr for cidr in ALLOWED_CIDRS):
            return None, "resumo vazaria endereco"
    return text, None


def redact(text):
    text = re.sub(r"ocid1\.[A-Za-z0-9._-]+", "[ocid]", text)
    text = re.sub(r"ssh-(?:ed25519|rsa) [A-Za-z0-9+/=]+", "[chave]", text)
    text = re.sub(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----", "[chave]", text)
    text = IPV4_RE.sub("[ip]", text)
    text = re.sub(r"(?i)(passphrase|secret|token|password|authorization)(=|:)\s*\S+", r"\1=[oculto]", text)
    return text


def _needle(*parts):
    return " ".join(parts)


def command_violations(text, filename):
    apply_line = re.compile(r"\b(?:tofu|terraform)\b.*\bapply\b")
    destroy_line = re.compile(r"\b(?:tofu|terraform)\b.*\bdestroy\b")
    saved_apply = "tofu -chdir=infra " + "apply -auto-approve -input=false -no-color -lock-timeout=5m"
    errors = []
    for line in text.splitlines():
        if destroy_line.search(line):
            errors.append(filename + " destroi")
        elif apply_line.search(line) and not (filename == "ci-apply.sh" and saved_apply in line):
            errors.append(filename + " aplica fora do plano salvo")
    return errors


def workflow_errors(root):
    root = pathlib.Path(root)
    errors = []
    apply_cmd = _needle("tofu", "apply")
    terraform_apply = _needle("terraform", "apply")
    tofu_destroy = _needle("tofu", "destroy")
    terraform_destroy = _needle("terraform", "destroy")
    workflows = list((root / ".github" / "workflows").glob("*.yml"))
    names = {path.name for path in workflows}
    if "homelab.yml" not in names or "validate.yml" not in names:
        errors.append("faltam workflows esperados")
        return errors
    for path in workflows:
        text = path.read_text()
        errors.extend(command_violations(text, path.name))
        if "pull_request_target" in text:
            errors.append(path.name + " tem pull_request_target")
        if tofu_destroy in text or terraform_destroy in text:
            errors.append(path.name + " tem destroy")
        if "set -x" in text or "TF_VAR_public_ipv4_pricing_acknowledged" in text:
            errors.append(path.name + " enfraquece o log ou o gate de preco")
        if path.name != "homelab.yml" and (apply_cmd in text or terraform_apply in text):
            errors.append(path.name + " aplica")
        if "pull_request" in text and ("secrets." in text or "id-token" in text or "environment:" in text):
            errors.append(path.name + " de pull request pede segredo ou ambiente")
        for token in (".pem", "tfstate", "id_ed25519", "BEGIN "):
            if token in text:
                errors.append(path.name + " cita material que nao pode ir para artifact")
    homelab = root / ".github" / "workflows" / "homelab.yml"
    text = homelab.read_text()
    if "pull_request" in text or re.search(r"(?m)^on:\n(?:.*\n)*?  push:", text):
        errors.append("homelab.yml nao pode rodar em pull request ou push")
    required = [
        "workflow_dispatch",
        "homelab-plan",
        "homelab-apply",
        "oci-homelab-state",
        "cancel-in-progress: false",
        REPO,
        "acknowledge_empty_state",
        "default: false",
        "id-token: write",
        "homelab-plan.enc",
        "require-approval",
        "scripts/ci-plan.sh",
        "scripts/ci-apply.sh",
    ]
    for item in required:
        if item not in text:
            errors.append("homelab.yml sem " + item)
    if apply_cmd in text or terraform_apply in text:
        errors.append("homelab.yml aplica direto")
    if text.count("actions: write") != 1:
        errors.append("gravar artifact so pode existir no job de plano")
    if text.find("require-approval") > text.find("scripts/ci-apply.sh"):
        errors.append("a aprovacao precisa aparecer antes do script de apply")
    validate = (root / ".github" / "workflows" / "validate.yml").read_text()
    if "environment:" in validate or "id-token" in validate or "secrets." in validate:
        errors.append("validate.yml pede ambiente, token ou segredo")
    for path in (root / "scripts").glob("*.sh"):
        errors.extend(command_violations(path.read_text(), path.name))
    plan = (root / "scripts" / "ci-plan.sh").read_text()
    apply = (root / "scripts" / "ci-apply.sh").read_text()
    saved_apply = "tofu -chdir=infra " + "apply -auto-approve -input=false -no-color -lock-timeout=5m"
    if apply_cmd in plan or terraform_apply in plan or tofu_destroy in plan or tofu_destroy in apply or terraform_destroy in apply:
        errors.append("script de plano aplica ou algum script destroi")
    if apply.count(saved_apply) != 1:
        errors.append("o script de apply nao tem exatamente um apply do plano salvo")
    if (
        apply.find("verify-binding") > apply.find(saved_apply)
        or apply.find("guard-apply-state") > apply.find(saved_apply)
        or apply.find("verify-run") > apply.find(saved_apply)
    ):
        errors.append("o apply roda antes da conferencia do plano")
    if apply.find("require-approval") > apply.find(saved_apply):
        errors.append("o script de apply nao confere a aprovacao")
    for script in (plan, apply):
        if "ci-guard.sh" not in script or "env:HOMELAB_PLAN_PASSPHRASE" not in script:
            errors.append("script remoto sem guarda ou sem cifra pela variavel")
        if "echo \"$HOMELAB" in script or "echo \"$OCI_" in script or "echo \"$AWS_" in script:
            errors.append("script imprime segredo")
    return errors


def _sample_plan(actions):
    return {
        "resource_changes": [
            {
                "address": "oci_core_instance.homelab",
                "change": {
                    "actions": actions,
                    "after": {
                        "shape": "VM.Standard.A1.Flex",
                        "id": "ocid1.instance.oc1.sa-saopaulo-1.example",
                        "shape_config": {"ocpus": 2, "memory_in_gbs": 12},
                        "source_details": {"boot_volume_size_in_gbs": 50, "boot_volume_vpus_per_gb": 10},
                        "create_vnic_details": {"assign_public_ip": True, "assign_ipv6ip": False},
                    },
                },
            },
            {
                "address": "oci_core_security_list.homelab",
                "change": {
                    "actions": ["create"],
                    "after": {"ingress_security_rules": [{"source": "203.0.113.10/32", "tcp_options": {"destination_port_range": {"min": 22}}}]},
                },
            },
            {
                "address": "oci_core_vcn.this",
                "change": {"actions": ["create"], "after": {"cidr_block": "10.0.0.0/16"}},
            },
        ],
        "output_changes": {"image_name": {"after": "Canonical-Ubuntu-24.04-aarch64-2026.10.27-0"}},
    }


def _approval(state, environment, login):
    return [{"state": state, "environments": [{"name": environment}], "user": {"login": login}, "comment": ""}]


def selftest():
    failures = []

    def check(label, error):
        if error:
            failures.append(label + ": " + error)

    def check_fail(label, error):
        if not error:
            failures.append(label + ": deveria falhar")

    check_fail("vazio", require_approval([], "joana"))
    check_fail("pendente", require_approval(_approval("pending", APPLY_ENVIRONMENT, "joana"), "paulo"))
    check_fail("rejeitado", require_approval(_approval("rejected", APPLY_ENVIRONMENT, "joana"), "paulo"))
    check_fail("ambiente errado", require_approval(_approval("approved", "homelab-plan", "joana"), "paulo"))
    check("mesmo dono", require_approval(_approval("approved", APPLY_ENVIRONMENT, "paulo"), "paulo"))
    check_fail("bot", require_approval(_approval("approved", APPLY_ENVIRONMENT, "runner[bot]"), "paulo"))
    check_fail("ator vazio", require_approval(_approval("approved", APPLY_ENVIRONMENT, "joana"), ""))
    check_fail("sem login", require_approval([{"state": "approved", "environments": [{"name": APPLY_ENVIRONMENT}], "user": {}}], "paulo"))
    check("aprovado", require_approval(_approval("approved", APPLY_ENVIRONMENT, "joana"), "paulo"))

    empty = {"lineage": "abc", "serial": 0, "resources": []}
    filled = {"lineage": "abc", "serial": 4, "resources": [{"type": "oci_core_vcn"}]}
    check_fail("estado vazio", guard_state(empty, False))
    check("estado vazio explicito", guard_state(empty, True))
    check("estado cheio", guard_state(filled, False))
    check_fail("flag com estado cheio", guard_state(filled, True))
    check_fail("estado invalido", guard_state({}, False))

    plan = _sample_plan(["create"])
    metadata, error = write_metadata(plan, empty, "a" * 40)
    check("metadata", error)
    blob = b"plano-binario"
    metadata["plan_sha256"] = hashlib.sha256(blob).hexdigest()
    check("binding", verify_binding(metadata, blob, "a" * 40))
    check_fail("binding sha", verify_binding(metadata, blob, "b" * 40))
    check_fail("binding bytes", verify_binding(metadata, b"outro", "a" * 40))
    _, error = write_metadata(_sample_plan(["delete"]), empty, "a" * 40)
    check_fail("delete", error)
    extra = _sample_plan(["create"])
    extra["resource_changes"].append({"address": "oci_core_nat_gateway.this", "change": {"actions": ["create"], "after": {}}})
    _, error = write_metadata(extra, empty, "a" * 40)
    if error is None:
        failures.append("nat: deveria falhar")
    summary, error = summarize(plan)
    check("resumo", error)
    if summary is None or "ocid1" in summary or "203.0.113" in summary or "VM.Standard.A1.Flex" not in summary:
        failures.append("resumo vazou ou perdeu o shape")
    redacted = redact("ocid1.tenancy.oc1..example 203.0.113.10 token=abc")
    if "ocid1" in redacted or "203.0.113" in redacted or "abc" in redacted:
        failures.append("redacao falhou")

    run = {
        "conclusion": "success",
        "status": "completed",
        "event": "workflow_dispatch",
        "path": WORKFLOW,
        "head_branch": "main",
        "head_sha": "c" * 40,
        "html_url": "https://github.com/" + REPO + "/actions/runs/1",
    }
    if not command_violations("tofu -chdir=infra apply -auto-approve agora\n", "outro.sh"):
        failures.append("apply solto deveria falhar")
    if not command_violations("terraform destroy\n", "ci-apply.sh"):
        failures.append("destroy deveria falhar")
    if command_violations(
        "tofu -chdir=infra " + "apply -auto-approve -input=false -no-color -lock-timeout=5m plano\n",
        "ci-apply.sh",
    ):
        failures.append("apply do plano salvo foi recusado")
    check("run", verify_run(run, "c" * 40))
    pushed = dict(run, event="push")
    check_fail("run push", verify_run(pushed, "c" * 40))
    check("apply state", guard_apply_state(empty, metadata, True))
    check_fail("serial", guard_apply_state(dict(empty, serial=1), metadata, True))

    root = pathlib.Path(__file__).resolve().parents[1]
    for error in workflow_errors(root):
        failures.append(error)
    import os
    import subprocess

    session_env = os.environ.copy()
    session_env.pop("ACTIONS_STEP_DEBUG", None)
    session_env.pop("ACTIONS_RUNNER_DEBUG", None)
    session_env.update(
        {
            "OCI_RPST_SELFTEST": "1",
            "ACTIONS_ID_TOKEN_REQUEST_TOKEN": "dummy",
            "ACTIONS_ID_TOKEN_REQUEST_URL": "https://example.invalid/token",
            "OCI_GITHUB_OIDC_AUDIENCE": "oci-homelab",
            "OCI_IDENTITY_DOMAIN_URL": "https://example.identity.oraclecloud.com",
            "OCI_OAUTH_CLIENT_ID": "dummy",
            "OCI_OAUTH_CLIENT_SECRET": "dummy",
            "OCI_REGION": "sa-saopaulo-1",
            "OCI_RPST_RESOURCE_TYPE": "githubactions",
            "RUNNER_TEMP": "/tmp",
        }
    )
    session_script = str(root / "scripts" / "oci_rpst_session.py")
    precheck = subprocess.run([sys.executable, session_script], env=session_env, capture_output=True, text=True)
    if precheck.returncode != 0 or "session precheck ok" not in precheck.stdout:
        failures.append("sessao precheck falhou")
    incomplete = dict(session_env)
    incomplete["OCI_OAUTH_CLIENT_SECRET"] = ""
    refused = subprocess.run([sys.executable, session_script], env=incomplete, capture_output=True, text=True)
    if refused.returncode == 0 or "dummy" in refused.stderr:
        failures.append("sessao incompleta deveria falhar sem valor")
    debugged = dict(session_env)
    debugged["ACTIONS_STEP_DEBUG"] = "true"
    traced = subprocess.run([sys.executable, session_script], env=debugged, capture_output=True, text=True)
    if traced.returncode == 0:
        failures.append("sessao com debug deveria falhar")

    cipher = "-aes-256-cbc -pbkdf2 -iter 600000 -salt -pass env:HOMELAB_PLAN_PASSPHRASE"
    plan_script = (root / "scripts" / "ci-plan.sh").read_text()
    apply_script = (root / "scripts" / "ci-apply.sh").read_text()
    if cipher not in plan_script or cipher not in apply_script:
        failures.append("cifra dos scripts divergiu")
    else:
        import os
        import subprocess
        import tempfile

        env = os.environ.copy()
        env["HOMELAB_PLAN_PASSPHRASE"] = "teste-local"
        with tempfile.TemporaryDirectory() as tmp:
            plan_path = pathlib.Path(tmp, "homelab.tfplan")
            plan_path.write_bytes(b"plano-cifrado")
            metadata = {
                "repository": REPO,
                "ref": REF,
                "git_sha": "d" * 40,
                "workflow": WORKFLOW,
                "has_delete": False,
                "plan_sha256": hashlib.sha256(b"plano-cifrado").hexdigest(),
                "state_lineage": "lineage",
                "state_serial": 0,
                "empty_state": True,
            }
            pathlib.Path(tmp, "metadata.json").write_text(json.dumps(metadata))
            packed = subprocess.run(
                ["tar", "-C", tmp, "-cf", "-", "homelab.tfplan", "metadata.json"],
                check=True,
                capture_output=True,
            )
            enc = pathlib.Path(tmp, "homelab-plan.enc")
            subprocess.run(
                ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "600000", "-salt", "-pass", "env:HOMELAB_PLAN_PASSPHRASE", "-out", str(enc)],
                input=packed.stdout,
                check=True,
                env=env,
                capture_output=True,
            )
            opened = subprocess.run(
                ["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "600000", "-salt", "-pass", "env:HOMELAB_PLAN_PASSPHRASE", "-in", str(enc)],
                check=True,
                env=env,
                capture_output=True,
            )
            subprocess.run(["tar", "-C", tmp, "-xf", "-"], input=opened.stdout, check=True)
            error = verify_binding(metadata, plan_path.read_bytes(), "d" * 40)
            if error:
                failures.append("cifra: " + error)

    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"pipeline selftest ok")
    return 0


def _load(path):
    return json.loads(pathlib.Path(path).read_text())


def main(argv):
    if len(argv) < 2:
        return _die("comando ausente")
    command = argv[1]
    args = argv[2:]

    def flag(name):
        if name not in args:
            raise SystemExit(_die("falta " + name))
        return args[args.index(name) + 1]

    if command == "selftest":
        return selftest()
    if command == "workflows":
        errors = workflow_errors(flag("--root"))
        if errors:
            return _die("\n".join(errors))
        print("workflows ok")
        return 0
    if command == "require-approval":
        error = require_approval(_load(flag("--file")), flag("--actor"))
        if error:
            return _die(error)
        print("approval ok")
        return 0
    if command == "guard-state":
        allow = os_environ_flag("ALLOW_EMPTY_STATE")
        error = guard_state(_load(flag("--state")), allow)
        if error:
            return _die(error)
        print("state ok")
        return 0
    if command == "write-metadata":
        plan = _load(flag("--plan-json"))
        state = _load(flag("--state"))
        blob = pathlib.Path(flag("--plan-bin")).read_bytes()
        metadata, error = write_metadata(plan, state, flag("--sha"))
        if error:
            return _die(error)
        metadata["plan_sha256"] = hashlib.sha256(blob).hexdigest()
        target = pathlib.Path(flag("--out"))
        target.write_text(json.dumps(metadata, sort_keys=True) + "\n")
        print("metadata ok")
        return 0
    if command == "verify-binding":
        metadata = _load(flag("--metadata"))
        blob = pathlib.Path(flag("--plan-bin")).read_bytes()
        error = verify_binding(metadata, blob, flag("--sha"))
        if error:
            return _die(error)
        print("binding ok")
        return 0
    if command == "guard-apply-state":
        error = guard_apply_state(_load(flag("--state")), _load(flag("--metadata")), os_environ_flag("ALLOW_EMPTY_STATE"))
        if error:
            return _die(error)
        print("apply state ok")
        return 0
    if command == "verify-run":
        error = verify_run(_load(flag("--run")), flag("--sha"))
        if error:
            return _die(error)
        print("run ok")
        return 0
    if command == "summarize":
        text, error = summarize(_load(flag("--plan-json")))
        if error:
            return _die(error)
        sys.stdout.write(text)
        return 0
    if command == "redact":
        source = pathlib.Path(flag("--file")).read_text(errors="replace")
        tail = "\n".join(source.splitlines()[-40:])
        sys.stderr.write(redact(tail) + "\n")
        return 0
    return _die("comando desconhecido")


def os_environ_flag(name):
    import os

    return os.environ.get(name) == "true"


if __name__ == "__main__":
    sys.exit(main(sys.argv))
