from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

from .repo import load_json


RECEIPT_RELPATH = Path(".vibeskills") / "mcp-auto-provision.json"
REQUIRED_SERVERS = ("github", "context7", "serena", "scrapling", "claude-flow")
SCRIPTED_SERVER_COMMANDS = {
    "scrapling": "scrapling",
    "claude-flow": "claude-flow",
}
SCRIPTED_SERVER_INSTALLS = {
    "scrapling": lambda: [sys.executable, "-m", "pip", "install", "scrapling[ai]"],
    "claude-flow": lambda: ["npm", "install", "-g", "claude-flow"],
}


def load_active_servers(target_root: Path) -> dict[str, dict[str, Any]]:
    active_path = target_root / "mcp" / "servers.active.json"
    if not active_path.exists():
        return {}
    try:
        payload = json.loads(active_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    servers = payload.get("servers")
    if not isinstance(servers, dict):
        return {}
    return {
        str(name): dict(config)
        for name, config in servers.items()
        if isinstance(config, dict)
    }


def scripted_server_host_visible(target_root: Path, server_name: str) -> bool:
    return server_name in load_active_servers(target_root)


def upgrade_result_with_active_surface(
    *,
    target_root: Path,
    server_name: str,
    provision_path: str,
    result: ProvisionResult,
) -> ProvisionResult:
    if provision_path != "scripted_cli" or result.status != "local_tool_present":
        return result
    if not scripted_server_host_visible(target_root, server_name):
        return result
    command_name = SCRIPTED_SERVER_COMMANDS.get(server_name)
    if command_name and shutil.which(command_name):
        return ProvisionResult(status="ready", next_step="none")
    return result


@dataclass(frozen=True)
class ProvisionResult:
    status: str
    failure_reason: str | None = None
    next_step: str = "none"


class ProvisionExecutor:
    def attempt(
        self,
        *,
        strategy: str,
        server_name: str,
        contract: dict[str, Any],
        repo_root: Path,
        target_root: Path,
        host_id: str,
        allow_scripted_install: bool,
    ) -> ProvisionResult:
        if strategy == "host_native":
            return ProvisionResult(
                status="host_native_unavailable",
                next_step=f"Complete host-native registration for {server_name} in {host_id}.",
            )
        command_name = SCRIPTED_SERVER_COMMANDS.get(server_name)
        if command_name and shutil.which(command_name):
            return upgrade_result_with_active_surface(
                target_root=target_root,
                server_name=server_name,
                provision_path=strategy,
                result=ProvisionResult(
                status="local_tool_present",
                next_step=f"Register {server_name} in the host active MCP surface for {host_id}.",
                ),
            )
        if not allow_scripted_install:
            return ProvisionResult(
                status="not_attempted_due_to_host_contract",
                next_step=f"Enable scripted install support before attempting {server_name}.",
            )
        install_factory = SCRIPTED_SERVER_INSTALLS.get(server_name)
        if install_factory is None:
            return ProvisionResult(
                status="attempt_failed",
                failure_reason=f"unsupported scripted install contract for {server_name}",
                next_step=f"Install and register {server_name} manually.",
            )
        install_command = install_factory()
        runner = str(install_command[0])
        if runner != sys.executable and shutil.which(runner) is None:
            return ProvisionResult(
                status="attempt_failed",
                failure_reason=f"{runner} is not available",
                next_step=f"Install {runner} first, then retry {server_name} provisioning.",
            )
        completed = subprocess.run(install_command, capture_output=True, text=True)
        if completed.returncode != 0:
            failure_detail = (completed.stderr or completed.stdout or "").strip() or f"{runner} exited {completed.returncode}"
            return ProvisionResult(
                status="attempt_failed",
                failure_reason=failure_detail,
                next_step=f"Review the {runner} install output and install {server_name} manually if needed.",
            )
        if command_name and shutil.which(command_name):
            return upgrade_result_with_active_surface(
                target_root=target_root,
                server_name=server_name,
                provision_path=strategy,
                result=ProvisionResult(
                status="local_tool_present",
                next_step=f"Register {server_name} in the host active MCP surface for {host_id}.",
                ),
            )
        return ProvisionResult(
            status="verification_failed",
            next_step=f"Verify the scripted CLI for {server_name} is available in PATH.",
        )


class FakeExecutor(ProvisionExecutor):
    def __init__(self, *, results: dict[tuple[str, str], ProvisionResult]) -> None:
        self.results = dict(results)

    def attempt(
        self,
        *,
        strategy: str,
        server_name: str,
        contract: dict[str, Any],
        repo_root: Path,
        target_root: Path,
        host_id: str,
        allow_scripted_install: bool,
    ) -> ProvisionResult:
        key = (strategy, server_name)
        if key in self.results:
            return self.results[key]
        return super().attempt(
            strategy=strategy,
            server_name=server_name,
            contract=contract,
            repo_root=repo_root,
            target_root=target_root,
            host_id=host_id,
            allow_scripted_install=allow_scripted_install,
        )


def _warning_entry(
    *,
    server_name: str,
    status: str,
    failure_reason: str | None,
    next_step: str,
    category: str = "unknown",
    provision_path: str = "unknown",
    attempted: bool = True,
) -> dict[str, Any]:
    return {
        "name": server_name,
        "category": category,
        "attempt_required": True,
        "attempted": attempted,
        "provision_path": provision_path,
        "verify_path": "unknown",
        "status": status,
        "failure_reason": failure_reason,
        "next_step": next_step,
        "disclosure_mode": "final_report_only",
    }


def load_registry(repo_root: Path) -> dict[str, Any]:
    return load_json(repo_root / "config" / "mcp-auto-provision.registry.json")


def build_receipt(
    *,
    host_id: str,
    profile: str,
    target_root: Path,
    results: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "install_state": "installed_locally",
        "host_id": host_id,
        "profile": profile,
        "target_root": str(target_root),
        "mcp_auto_provision_attempted": True,
        "mcp_results": results,
    }


def write_receipt(target_root: Path, receipt: dict[str, Any]) -> Path:
    receipt_path = target_root / RECEIPT_RELPATH
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt_path


def attempt_server(
    *,
    repo_root: Path,
    target_root: Path,
    host_id: str,
    server_name: str,
    contract: dict[str, Any],
    allow_scripted_install: bool,
    executor: ProvisionExecutor,
) -> dict[str, Any]:
    strategy = str(contract["strategy"])
    result = executor.attempt(
        strategy=strategy,
        server_name=server_name,
        contract=contract,
        repo_root=repo_root,
        target_root=target_root,
        host_id=host_id,
        allow_scripted_install=allow_scripted_install,
    )
    result = upgrade_result_with_active_surface(
        target_root=target_root,
        server_name=server_name,
        provision_path=strategy,
        result=result,
    )
    return {
        "name": server_name,
        "category": str(contract["category"]),
        "attempt_required": True,
        "attempted": result.status != "not_attempted_due_to_host_contract",
        "provision_path": strategy,
        "verify_path": str(contract["verify_path"]),
        "status": result.status,
        "failure_reason": result.failure_reason,
        "next_step": result.next_step,
        "disclosure_mode": "final_report_only",
    }


def provision_required_mcp(
    *,
    repo_root: Path,
    target_root: Path,
    host_id: str,
    profile: str,
    allow_scripted_install: bool,
    executor: ProvisionExecutor | None = None,
) -> dict[str, Any]:
    try:
        registry = load_registry(repo_root)
    except Exception as exc:
        receipt = build_receipt(
            host_id=host_id,
            profile=profile,
            target_root=target_root,
            results=[
                _warning_entry(
                    server_name=server_name,
                    status="attempt_failed",
                    failure_reason=f"registry load failed: {exc}",
                    next_step="Fix the MCP auto-provision registry or configure MCP servers manually.",
                )
                for server_name in REQUIRED_SERVERS
            ],
        )
        try:
            write_receipt(target_root, receipt)
        except Exception:
            pass
        return receipt

    host_contract = dict(((registry.get("hosts") or {}).get(host_id)) or {})
    active_executor = executor or ProvisionExecutor()
    attempt_order = list(host_contract.get("attempt_order") or registry.get("required_servers") or REQUIRED_SERVERS)
    server_contracts = dict(host_contract.get("servers") or {})
    results: list[dict[str, Any]] = []
    for server_name in attempt_order:
        contract = dict(server_contracts.get(server_name) or {})
        if not contract:
            results.append(
                _warning_entry(
                    server_name=server_name,
                    status="attempt_failed",
                    failure_reason=f"registry contract missing for {server_name}",
                    next_step=f"Fix the MCP registry entry for {server_name} or configure it manually.",
                )
            )
            continue
        try:
            results.append(
                attempt_server(
                    repo_root=repo_root,
                    target_root=target_root,
                    host_id=host_id,
                    server_name=server_name,
                    contract=contract,
                    allow_scripted_install=allow_scripted_install,
                    executor=active_executor,
                )
            )
        except Exception as exc:
            results.append(
                _warning_entry(
                    server_name=server_name,
                    status="attempt_failed",
                    failure_reason=str(exc),
                    next_step=f"Review the failed auto-provision attempt for {server_name} and finish it manually.",
                    category=str(contract.get("category") or "unknown"),
                    provision_path=str(contract.get("strategy") or "unknown"),
                )
            )
    receipt = build_receipt(host_id=host_id, profile=profile, target_root=target_root, results=results)
    try:
        write_receipt(target_root, receipt)
    except Exception:
        pass
    return receipt


def lookup_server(receipt: dict[str, Any], server_name: str) -> dict[str, Any]:
    for entry in receipt.get("mcp_results") or []:
        if str(entry.get("name")) == server_name:
            return dict(entry)
    raise KeyError(server_name)


def manual_follow_up_servers(receipt: dict[str, Any]) -> list[str]:
    follow_up: list[str] = []
    for entry in receipt.get("mcp_results") or []:
        if str(entry.get("status") or "") != "ready":
            follow_up.append(str(entry.get("name") or "unknown"))
    return follow_up
