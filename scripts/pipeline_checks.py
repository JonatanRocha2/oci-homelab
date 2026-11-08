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


def _snapshot(state):
    resources = _resources(state)
    if resources is None or type(state.get("serial")) is not int:
        return None
    lineage = state.get("lineage")
    if lineage is None:
        lineage = ""
    if not isinstance(lineage, str):
        return None
    serial = state["serial"]
    if _lineage(lineage):
        return lineage, serial
    if lineage == "" and serial == 0 and resources == []:
        return "", 0
    return None


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
    snapshot = _snapshot(state)
    if snapshot is None:
        return None, "lineage ou serial ausente"
    lineage, serial = snapshot
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
        "state_lineage": lineage,
        "state_serial": serial,
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
    lineage = metadata.get("state_lineage")
    serial = metadata.get("state_serial")
    first = lineage == "" and serial == 0 and metadata.get("empty_state") is True
    if not ((_lineage(lineage) and type(serial) is int) or first):
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
    snapshot = _snapshot(state)
    if snapshot is None:
        return "lineage ou serial ausente"
    if snapshot[0] != metadata.get("state_lineage"):
        return "a lineage do estado mudou depois do plano"
    if snapshot[1] != metadata.get("state_serial"):
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


HOST_CIDR_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)/32$"
)
APPROVED_EGRESS = {("6", 443, 443), ("6", 80, 80), ("6", 53, 53), ("17", 53, 53), ("17", 123, 123)}


def _one_block(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict):
        return value[0]
    return None


def _port_span(options):
    if options in (None, [], {}):
        return None
    block = _one_block(options)
    if block is None:
        return False
    if type(block.get("min")) is int and type(block.get("max")) is int:
        return (block["min"], block["max"])
    span = block.get("destination_port_range")
    nested = span if isinstance(span, dict) else _one_block(span)
    if isinstance(nested, dict) and type(nested.get("min")) is int and type(nested.get("max")) is int:
        return (nested["min"], nested["max"])
    return False


def _exact_number(value, expected):
    if type(value) is int:
        return value == expected
    if isinstance(value, str) and value.isdigit() and str(int(value)) == value:
        return int(value) == expected
    return False


def _flag(value, enabled):
    # assign_public_ip chega como "true" ou "false"; assign_ipv6ip chega como bool.
    if enabled:
        return value is True or value == "true"
    return value is False or value == "false"


def _changes_by_address(changes):
    found = {}
    for change in changes:
        address = change.get("address")
        if address in found or not isinstance(change.get("change"), dict):
            return None
        found[address] = change["change"]
    return found


def _vcn_cidrs(after, unknown):
    blocks = after.get("cidr_blocks")
    single = after.get("cidr_block")
    values = []
    if isinstance(blocks, list) and blocks and all(isinstance(item, str) for item in blocks):
        values.extend(blocks)
    elif blocks not in (None, []):
        return None
    single_unknown = isinstance(unknown, dict) and unknown.get("cidr_block") is True
    if isinstance(single, str):
        values.append(single)
    elif single is None and (single_unknown or values):
        pass
    else:
        return None
    return values or None


def _ssh_rule_ok(rules):
    if not isinstance(rules, list) or len(rules) != 1 or not isinstance(rules[0], dict):
        return False
    rule = rules[0]
    source = rule.get("source")
    if rule.get("protocol") != "6" or rule.get("source_type") != "CIDR_BLOCK" or rule.get("stateless") is not False:
        return False
    if not isinstance(source, str) or not HOST_CIDR_RE.fullmatch(source) or source == "0.0.0.0/32":
        return False
    if rule.get("udp_options") not in (None, [], {}) or rule.get("icmp_options") not in (None, [], {}):
        return False
    return _port_span(rule.get("tcp_options")) == (22, 22)


def _egress_ok(rules):
    if not isinstance(rules, list):
        return False
    found = set()
    for rule in rules:
        if not isinstance(rule, dict) or rule.get("destination") != "0.0.0.0/0":
            return False
        if rule.get("destination_type") != "CIDR_BLOCK" or rule.get("stateless") is not False:
            return False
        tcp = _port_span(rule.get("tcp_options"))
        udp = _port_span(rule.get("udp_options"))
        if tcp is False or udp is False or (tcp is not None and udp is not None):
            return False
        port = tcp if tcp is not None else udp
        if port is None:
            return False
        found.add((rule.get("protocol"), port[0], port[1]))
    return found == APPROVED_EGRESS


def _empty_rules(after, name):
    rules = after.get(name)
    return isinstance(rules, list) and not rules


def summarize(plan):
    changes = plan.get("resource_changes")
    error = check_changes(changes)
    if error:
        return None, error
    indexed = _changes_by_address(changes)
    if indexed is None:
        return None, "mudanca invalida"
    required = (
        "oci_core_instance.homelab",
        "oci_core_vcn.this",
        "oci_core_subnet.public",
        "oci_core_security_list.homelab",
        "oci_core_default_security_list.locked",
    )
    if any(address not in indexed for address in required):
        return None, "plano sem recurso obrigatorio"
    instance = indexed["oci_core_instance.homelab"].get("after")
    if not isinstance(instance, dict) or instance.get("shape") != "VM.Standard.A1.Flex":
        return None, "shape ausente ou inesperada"
    config = _one_block(instance.get("shape_config"))
    source = _one_block(instance.get("source_details"))
    vnic = _one_block(instance.get("create_vnic_details"))
    if config is None or source is None or vnic is None:
        return None, "tamanho da instancia ausente"
    if not _exact_number(config.get("ocpus"), 2) or not _exact_number(config.get("memory_in_gbs"), 12):
        return None, "ocpus ou memoria ausente ou fora do combinado"
    if not _exact_number(source.get("boot_volume_size_in_gbs"), 50) or not _exact_number(source.get("boot_volume_vpus_per_gb"), 10):
        return None, "boot ou vpu ausente ou fora do combinado"
    if not _flag(vnic.get("assign_public_ip"), True) or not _flag(vnic.get("assign_ipv6ip"), False):
        return None, "ipv4 efemero ou ipv6 fora do combinado"
    security = indexed["oci_core_security_list.homelab"].get("after")
    if not isinstance(security, dict) or not _ssh_rule_ok(security.get("ingress_security_rules")):
        return None, "ssh nao e uma unica regra /32 na porta 22"
    if not _egress_ok(security.get("egress_security_rules")):
        return None, "egress fora da lista aprovada"
    locked = indexed["oci_core_default_security_list.locked"].get("after")
    if not isinstance(locked, dict) or not _empty_rules(locked, "ingress_security_rules") or not _empty_rules(locked, "egress_security_rules"):
        return None, "security list padrao nao esta vazia"
    vcn_change = indexed["oci_core_vcn.this"]
    vcn = vcn_change.get("after")
    if not isinstance(vcn, dict) or vcn.get("is_ipv6enabled") is not False:
        return None, "vcn sem ipv6 desligado"
    cidrs = _vcn_cidrs(vcn, vcn_change.get("after_unknown"))
    if cidrs is None or set(cidrs) != {"10.0.0.0/16"}:
        return None, "cidr da vcn ausente ou fora do desenho"
    subnet = indexed["oci_core_subnet.public"].get("after")
    if not isinstance(subnet, dict) or subnet.get("cidr_block") != "10.0.1.0/24":
        return None, "cidr da subnet ausente ou fora do desenho"
    outputs = plan.get("output_changes") if isinstance(plan.get("output_changes"), dict) else {}
    image = outputs.get("image_name") if isinstance(outputs.get("image_name"), dict) else {}
    name = image.get("after")
    if (
        not isinstance(name, str)
        or not name.startswith("Canonical-Ubuntu-24.04-aarch64-")
        or "minimal" in name.lower()
        or "ocid1" in name
    ):
        return None, "imagem ausente ou inesperada"
    lines = ["plano sanitizado"]
    for change in changes:
        actions = ",".join(change["change"]["actions"])
        lines.append(f"recurso {change['address']} acoes {actions}")
    lines.extend([
        "shape VM.Standard.A1.Flex",
        "ocpus 2",
        "memoria_gb 12",
        "boot_gb 50",
        "vpu 10",
        "ipv4_efemero true",
        "ipv6 false",
        "regras_ssh 1",
        "cidr 10.0.0.0/16",
        "cidr 10.0.1.0/24",
        "egress 5",
        "default_security_list vazia",
        "imagem " + name,
    ])
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
    if "id-token" in text or "oci_rpst" in text or "ResourcePrincipal" in text:
        errors.append("homelab.yml ainda pede a troca de token nao exercitada")
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
        if "oci_api_session.py" not in script or "oci_rpst" in script or "ResourcePrincipal" in script:
            errors.append("script remoto nao usa a chave de API documentada")
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


def _provider_plan():
    egress = []
    for protocol, minimum, maximum in sorted(APPROVED_EGRESS):
        options = [{"min": minimum, "max": maximum, "source_port_range": []}]
        rule = {
            "protocol": protocol,
            "destination": "0.0.0.0/0",
            "destination_type": "CIDR_BLOCK",
            "stateless": False,
            "tcp_options": options if protocol == "6" else [],
            "udp_options": options if protocol == "17" else [],
        }
        egress.append(rule)
    return {
        "resource_changes": [
            {"address": "terraform_data.guards", "change": {"actions": ["create"], "after": {"input": "known"}}},
            {
                "address": "oci_core_vcn.this",
                "change": {
                    "actions": ["create"],
                    "after": {"cidr_block": None, "cidr_blocks": ["10.0.0.0/16"], "is_ipv6enabled": False},
                    "after_unknown": {"cidr_block": True},
                },
            },
            {"address": "oci_core_internet_gateway.this", "change": {"actions": ["create"], "after": {"enabled": True}}},
            {
                "address": "oci_core_route_table.public",
                "change": {"actions": ["create"], "after": {"route_rules": [{"destination": "0.0.0.0/0", "destination_type": "CIDR_BLOCK"}]}},
            },
            {
                "address": "oci_core_security_list.homelab",
                "change": {
                    "actions": ["create"],
                    "after": {
                        "ingress_security_rules": [{
                            "protocol": "6",
                            "source": "203.0.113.10/32",
                            "source_type": "CIDR_BLOCK",
                            "stateless": False,
                            "tcp_options": [{"min": 22, "max": 22}],
                            "udp_options": [],
                            "icmp_options": [],
                        }],
                        "egress_security_rules": egress,
                    },
                },
            },
            {
                "address": "oci_core_default_security_list.locked",
                "change": {"actions": ["create"], "after": {"ingress_security_rules": [], "egress_security_rules": []}},
            },
            {"address": "oci_core_subnet.public", "change": {"actions": ["create"], "after": {"cidr_block": "10.0.1.0/24"}}},
            {
                "address": "oci_core_instance.homelab",
                "change": {
                    "actions": ["create"],
                    "after": {
                        "shape": "VM.Standard.A1.Flex",
                        "id": "ocid1.instance.oc1.sa-saopaulo-1.example",
                        "shape_config": [{"ocpus": 2, "memory_in_gbs": 12}],
                        "source_details": [{"boot_volume_size_in_gbs": 50, "boot_volume_vpus_per_gb": 10, "source_id": "ocid1.image.oc1.sa-saopaulo-1.example"}],
                        "create_vnic_details": [{"assign_public_ip": True, "assign_ipv6ip": False}],
                    },
                },
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
    _, error = summarize(plan)
    check_fail("resumo incompleto", error)
    summary, error = summarize(_provider_plan())
    check("resumo", error)
    if (
        summary is None
        or "ocid1" in summary
        or "203.0.113" in summary
        or "ausente" in summary
        or "diferente_do_desenho" in summary
        or "ocpus 2" not in summary
        or "memoria_gb 12" not in summary
        or "cidr 10.0.0.0/16" not in summary
        or "cidr 10.0.1.0/24" not in summary
    ):
        failures.append("resumo vazou ou perdeu o tamanho")
    listed = _provider_plan()
    for change in listed["resource_changes"]:
        if change["address"] == "oci_core_instance.homelab":
            change["change"]["after"]["shape_config"] = {"ocpus": 2, "memory_in_gbs": 12}
            change["change"]["after"]["source_details"] = {"boot_volume_size_in_gbs": 50, "boot_volume_vpus_per_gb": 10}
            change["change"]["after"]["create_vnic_details"] = {"assign_public_ip": True, "assign_ipv6ip": False}
    check("resumo em objeto", summarize(listed)[1])
    wrong_size = _provider_plan()
    for change in wrong_size["resource_changes"]:
        if change["address"] == "oci_core_instance.homelab":
            change["change"]["after"]["shape_config"] = [{"ocpus": 4, "memory_in_gbs": 24}]
    _, error = summarize(wrong_size)
    check_fail("ocpus errado", error)
    missing_size = _provider_plan()
    for change in missing_size["resource_changes"]:
        if change["address"] == "oci_core_instance.homelab":
            change["change"]["after"]["shape_config"] = []
    _, error = summarize(missing_size)
    check_fail("tamanho ausente", error)
    wrong_cidr = _provider_plan()
    for change in wrong_cidr["resource_changes"]:
        if change["address"] == "oci_core_vcn.this":
            change["change"]["after"]["cidr_blocks"] = ["10.9.0.0/16"]
            change["change"]["after_unknown"] = {}
    _, error = summarize(wrong_cidr)
    check_fail("cidr errado", error)
    known_legacy = _provider_plan()
    for change in known_legacy["resource_changes"]:
        if change["address"] == "oci_core_vcn.this":
            change["change"]["after"]["cidr_block"] = "10.8.0.0/16"
            change["change"]["after_unknown"] = {"cidr_block": False}
    _, error = summarize(known_legacy)
    check_fail("cidr legado errado", error)
    open_ssh = _provider_plan()
    for change in open_ssh["resource_changes"]:
        if change["address"] == "oci_core_security_list.homelab":
            change["change"]["after"]["ingress_security_rules"][0]["source"] = "0.0.0.0/0"
    _, error = summarize(open_ssh)
    check_fail("ssh aberto", error)
    string_sizes = _provider_plan()
    for change in string_sizes["resource_changes"]:
        if change["address"] == "oci_core_instance.homelab":
            change["change"]["after"]["source_details"][0]["boot_volume_size_in_gbs"] = "50"
            change["change"]["after"]["source_details"][0]["boot_volume_vpus_per_gb"] = "10"
    check("boot em texto", summarize(string_sizes)[1])
    wrong_boot = _provider_plan()
    for change in wrong_boot["resource_changes"]:
        if change["address"] == "oci_core_instance.homelab":
            change["change"]["after"]["source_details"][0]["boot_volume_size_in_gbs"] = "60"
    _, error = summarize(wrong_boot)
    check_fail("boot errado", error)
    string_flag = _provider_plan()
    for change in string_flag["resource_changes"]:
        if change["address"] == "oci_core_instance.homelab":
            change["change"]["after"]["create_vnic_details"][0]["assign_public_ip"] = "true"
    check("ipv4 em texto", summarize(string_flag)[1])
    ipv6_on = _provider_plan()
    for change in ipv6_on["resource_changes"]:
        if change["address"] == "oci_core_instance.homelab":
            change["change"]["after"]["create_vnic_details"][0]["assign_ipv6ip"] = True
    _, error = summarize(ipv6_on)
    check_fail("ipv6 ligado", error)
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
    first = {"lineage": "", "serial": 0, "resources": []}
    first_meta, error = write_metadata(plan, first, "a" * 40)
    check("primeiro estado", error)
    if first_meta is None or first_meta.get("state_lineage") != "" or first_meta.get("state_serial") != 0 or first_meta.get("empty_state") is not True:
        failures.append("primeiro estado nao ficou vazio")
    else:
        first_meta["plan_sha256"] = hashlib.sha256(blob).hexdigest()
        check("binding primeiro", verify_binding(first_meta, blob, "a" * 40))
        check("apply primeiro", guard_apply_state(first, first_meta, True))
        check("apply primeiro sem chave", guard_apply_state({"serial": 0, "resources": []}, first_meta, True))
    _, error = write_metadata(plan, {"lineage": "", "serial": 0, "resources": [{"type": "oci_core_vcn"}]}, "a" * 40)
    check_fail("lineage vazia com recurso", error)
    _, error = write_metadata(plan, {"lineage": "", "serial": 1, "resources": []}, "a" * 40)
    check_fail("lineage vazia com serial", error)

    root = pathlib.Path(__file__).resolve().parents[1]
    for error in workflow_errors(root):
        failures.append(error)
    versions = (root / "infra" / "versions.tf").read_text()
    readme = (root / "README.md").read_text()
    if "use_lockfile                = true" not in versions:
        failures.append("use_lockfile saiu do backend")
    if "respondeu 412" not in readme or "use_lockfile" not in readme:
        failures.append("o texto nao registra o teste concorrente da trava S3")
    if 'backend "oci"' in versions:
        failures.append("backend OCI nativo nao existe nesta configuracao")
    import os
    import subprocess
    import tempfile

    session_script = str(root / "scripts" / "oci_api_session.py")
    marker = "TESTKEY-LOCAL-ONLY"
    with tempfile.TemporaryDirectory() as tmp:
        session_env = os.environ.copy()
        session_env.pop("ACTIONS_STEP_DEBUG", None)
        session_env.pop("ACTIONS_RUNNER_DEBUG", None)
        session_env.update(
            {
                "HOME": tmp,
                "RUNNER_TEMP": tmp,
                "OCI_TENANCY_OCID": "ocid1.tenancy.oc1.." + ("a" * 32),
                "OCI_USER_OCID": "ocid1.user.oc1.." + ("b" * 32),
                "OCI_FINGERPRINT": "aa:" * 15 + "bb",
                "OCI_PRIVATE_KEY": "-----BEGIN " + "PRIVATE KEY-----\n" + marker + "\n-----END " + "PRIVATE KEY-----\n",
                "OCI_REGION": "sa-saopaulo-1",
            }
        )
        precheck = subprocess.run([sys.executable, session_script], env=session_env, capture_output=True, text=True)
        if precheck.returncode != 0 or marker in precheck.stdout or "PRIVATE KEY" in precheck.stdout:
            failures.append("sessao de chave vazou ou falhou")
        else:
            session_file = pathlib.Path(precheck.stdout.strip())
            body = session_file.read_text()
            if "OCI_AUTH=APIKey" not in body or marker in body or "PRIVATE KEY" in body:
                failures.append("arquivo de sessao invalido")
            key_file = pathlib.Path(tmp) / "oci-session" / "api-key.pem"
            if marker not in key_file.read_text() or (key_file.stat().st_mode & 0o777) != 0o600:
                failures.append("chave temporaria sem modo 0600")
        incomplete = dict(session_env)
        incomplete["OCI_PRIVATE_KEY"] = ""
        refused = subprocess.run([sys.executable, session_script], env=incomplete, capture_output=True, text=True)
        if refused.returncode == 0 or marker in refused.stderr:
            failures.append("sessao incompleta deveria falhar sem valor")
        blocked = pathlib.Path(tmp) / ".oci"
        blocked.mkdir(exist_ok=True)
        (blocked / "config").write_text("existing\n")
        kept = subprocess.run([sys.executable, session_script], env=session_env, capture_output=True, text=True)
        if kept.returncode == 0 or (blocked / "config").read_text() != "existing\n":
            failures.append("sessao substituiu configuracao existente")
        debugged = dict(session_env)
        debugged["HOME"] = str(pathlib.Path(tmp) / "empty-home")
        pathlib.Path(debugged["HOME"]).mkdir()
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
    print("pipeline selftest ok (fixtures locais, sem OCI)")
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
