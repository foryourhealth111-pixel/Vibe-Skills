from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
import warnings


REPO_ROOT = Path(__file__).resolve().parents[4]
RUNTIME_CORE_SRC = REPO_ROOT / "packages" / "runtime-core" / "src"
SCRIPT_PATH = REPO_ROOT / "scripts" / "runtime" / "Invoke-PlanExecute.ps1"

if str(RUNTIME_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(RUNTIME_CORE_SRC))

from vgo_runtime.powershell_bridge import run_powershell_json_command


def _restore_modules(originals: dict[str, types.ModuleType | None]) -> None:
    for name, original in originals.items():
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original


def _load_canonical_entry_module() -> types.ModuleType:
    touched = {
        "vgo_runtime",
        "vgo_contracts",
        "vgo_contracts.canonical_vibe_contract",
        "vgo_contracts.host_launch_receipt",
        "vgo_runtime.router",
        "vgo_runtime.canonical_entry",
    }
    originals = {name: sys.modules.get(name) for name in touched}
    try:
        package = types.ModuleType("vgo_runtime")
        package.__path__ = [str(RUNTIME_CORE_SRC / "vgo_runtime")]
        sys.modules["vgo_runtime"] = package

        contracts_package = types.ModuleType("vgo_contracts")
        contracts_package.__path__ = []
        sys.modules["vgo_contracts"] = contracts_package

        canonical_contract_module = types.ModuleType("vgo_contracts.canonical_vibe_contract")
        canonical_contract_module.resolve_canonical_vibe_contract = lambda repo_root, host_id: {
            "fallback_policy": "blocked",
            "allow_skill_doc_fallback": False,
        }
        sys.modules[canonical_contract_module.__name__] = canonical_contract_module

        host_receipt_module = types.ModuleType("vgo_contracts.host_launch_receipt")

        class HostLaunchReceipt:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

            def model_dump(self):
                return dict(self.__dict__)

        def write_host_launch_receipt(path_or_session_root, receipt):
            base = Path(path_or_session_root)
            if base.suffix:
                path = base
            else:
                path = base / "host-launch-receipt.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(receipt.model_dump()), encoding="utf-8")
            return path

        host_receipt_module.HostLaunchReceipt = HostLaunchReceipt
        host_receipt_module.write_host_launch_receipt = write_host_launch_receipt
        sys.modules[host_receipt_module.__name__] = host_receipt_module

        router_module = types.ModuleType("vgo_runtime.router")
        router_module.load_allowed_vibe_entry_ids = lambda: {"vibe", "vibe-upgrade"}
        sys.modules[router_module.__name__] = router_module

        spec = importlib.util.spec_from_file_location("vgo_runtime.canonical_entry", RUNTIME_CORE_SRC / "vgo_runtime" / "canonical_entry.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        _restore_modules(originals)


def _load_cli_process_module() -> types.ModuleType:
    cli_root = REPO_ROOT / "apps" / "vgo-cli" / "src"
    if str(cli_root) not in sys.path:
        sys.path.insert(0, str(cli_root))

    touched = {
        "vgo_cli",
        "vgo_cli.errors",
        "vgo_cli.process",
    }
    originals = {name: sys.modules.get(name) for name in touched}
    try:
        package = types.ModuleType("vgo_cli")
        package.__path__ = [str(cli_root / "vgo_cli")]
        sys.modules["vgo_cli"] = package

        errors_spec = importlib.util.spec_from_file_location("vgo_cli.errors", cli_root / "vgo_cli" / "errors.py")
        assert errors_spec and errors_spec.loader
        errors_module = importlib.util.module_from_spec(errors_spec)
        sys.modules[errors_spec.name] = errors_module
        errors_spec.loader.exec_module(errors_module)

        spec = importlib.util.spec_from_file_location("vgo_cli.process", cli_root / "vgo_cli" / "process.py")
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        _restore_modules(originals)


class DynamicLoaderIsolationTests(unittest.TestCase):
    def test_canonical_entry_loader_restores_sys_modules(self):
        managed = (
            "vgo_runtime",
            "vgo_contracts",
            "vgo_contracts.canonical_vibe_contract",
            "vgo_contracts.host_launch_receipt",
            "vgo_runtime.router",
            "vgo_runtime.canonical_entry",
        )
        originals = {name: sys.modules.get(name) for name in managed}
        module = _load_canonical_entry_module()
        self.assertEqual("vgo_runtime.canonical_entry", module.__name__)
        for name, original in originals.items():
            self.assertIs(sys.modules.get(name), original)

    def test_cli_process_loader_restores_sys_modules(self):
        managed = ("vgo_cli", "vgo_cli.errors", "vgo_cli.process")
        originals = {name: sys.modules.get(name) for name in managed}
        module = _load_cli_process_module()
        self.assertEqual("vgo_cli.process", module.__name__)
        for name, original in originals.items():
            self.assertIs(sys.modules.get(name), original)


class CliProcessPowerShellPolicyTests(unittest.TestCase):
    def test_choose_powershell_reads_shared_policy_file_override(self):
        module = _load_cli_process_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            policy_path = Path(temp_dir) / "powershell-host-policy.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "preferred_powershell_host": "windows-powershell",
                        "require_pwsh_on_non_windows": True,
                        "allow_windows_powershell_fallback": True,
                        "record_host_resolution_artifacts": True,
                    }
                ),
                encoding="utf-8",
            )
            pwsh_path = Path(temp_dir) / "pwsh.exe"
            powershell_path = Path(temp_dir) / "powershell.exe"
            pwsh_path.write_text("", encoding="utf-8")
            powershell_path.write_text("", encoding="utf-8")

            def fake_which(name: str) -> str | None:
                mapping = {
                    "pwsh": str(pwsh_path),
                    "pwsh.exe": str(pwsh_path),
                    "powershell": str(powershell_path),
                    "powershell.exe": str(powershell_path),
                }
                return mapping.get(name)

            with patch.object(module, "POWERSHELL_HOST_POLICY_PATH", policy_path), patch.object(module, "_is_windows_host", return_value=True), patch.object(module.shutil, "which", side_effect=fake_which):
                resolution = module.choose_powershell(return_diagnostics=True)

        self.assertIsInstance(resolution, dict)
        self.assertEqual(resolution["host_path"], str(powershell_path))
        self.assertEqual(resolution["host_kind"], "windows-powershell")
        self.assertTrue(resolution["policy"]["allow_windows_powershell_fallback"])

    def test_choose_powershell_prefers_pwsh_over_windows_powershell(self):
        module = _load_cli_process_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            pwsh_path = Path(temp_dir) / "pwsh.exe"
            powershell_path = Path(temp_dir) / "powershell.exe"
            pwsh_path.write_text("", encoding="utf-8")
            powershell_path.write_text("", encoding="utf-8")

            def fake_which(name: str) -> str | None:
                mapping = {
                    "pwsh": str(pwsh_path),
                    "pwsh.exe": str(pwsh_path),
                    "powershell": str(powershell_path),
                    "powershell.exe": str(powershell_path),
                }
                return mapping.get(name)

            with patch.object(module, "_is_windows_host", return_value=True), patch.object(module.shutil, "which", side_effect=fake_which):
                resolution = module.choose_powershell(return_diagnostics=True)

        self.assertIsInstance(resolution, dict)
        self.assertEqual(resolution["host_path"], str(pwsh_path))
        self.assertEqual(resolution["host_kind"], "pwsh")
        self.assertFalse(resolution["fallback_used"])

    def test_choose_powershell_uses_windows_fallback_when_pwsh_missing(self):
        module = _load_cli_process_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            powershell_path = Path(temp_dir) / "powershell.exe"
            powershell_path.write_text("", encoding="utf-8")

            def fake_which(name: str) -> str | None:
                mapping = {
                    "pwsh": None,
                    "pwsh.exe": None,
                    "powershell": str(powershell_path),
                    "powershell.exe": str(powershell_path),
                }
                return mapping.get(name)

            def fake_exists(path_self: Path) -> bool:
                return str(path_self) == str(powershell_path)

            def fake_is_file(path_self: Path) -> bool:
                return str(path_self) == str(powershell_path)

            with patch.object(module, "_is_windows_host", return_value=True), patch.object(module.shutil, "which", side_effect=fake_which), patch.object(module.Path, "exists", fake_exists), patch.object(module.Path, "is_file", fake_is_file):
                resolution = module.choose_powershell(return_diagnostics=True)

        self.assertIsInstance(resolution, dict)
        self.assertEqual(resolution["host_path"], str(powershell_path))
        self.assertEqual(resolution["host_kind"], "windows-powershell")
        self.assertTrue(resolution["fallback_used"])

    def test_choose_powershell_reports_pwsh_required_on_non_windows(self):
        module = _load_cli_process_module()
        def fake_which(name: str) -> str | None:
            return None

        def fake_exists(path_self: Path) -> bool:
            return False

        def fake_is_file(path_self: Path) -> bool:
            return False

        with patch.object(module.shutil, "which", side_effect=fake_which), patch.object(module, "_is_windows_host", return_value=False), patch.object(module, "_powershell_host_policy", return_value={
            "preferred_powershell_host": "pwsh",
            "require_pwsh_on_non_windows": True,
            "allow_windows_powershell_fallback": False,
            "record_host_resolution_artifacts": True,
        }), patch.object(module.Path, "exists", fake_exists), patch.object(module.Path, "is_file", fake_is_file):
            resolution = module.choose_powershell(return_diagnostics=True)

        self.assertIsInstance(resolution, dict)
        self.assertIsNone(resolution["host_path"])
        self.assertEqual(resolution.get("error"), "pwsh is required on non-Windows hosts")
        checked_names = [entry["candidate_name"] for entry in resolution["candidates_checked"]]
        self.assertEqual(["path-pwsh", "path-pwsh-exe"], checked_names)

    def test_run_powershell_file_failure_reports_candidates_checked(self):
        module = _load_cli_process_module()
        with self.assertRaises(Exception) as ctx:
            with patch.object(module, "choose_powershell", return_value={
                "host_path": None,
                "host_kind": None,
                "fallback_used": False,
                "candidates_checked": [
                    {"candidate_name": "path-pwsh", "candidate_path": None},
                    {"candidate_name": "path-powershell", "candidate_path": r"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"},
                ],
            }):
                module.run_powershell_file(Path("demo.ps1"), "-Task", "probe")
        message = str(ctx.exception)
        self.assertIn("PowerShell is required to run: demo.ps1", message)
        self.assertIn("candidates checked:", message)
        self.assertIn("path-pwsh", message)
        self.assertIn("powershell.exe", message)

    def test_choose_powershell_invalid_policy_warns_and_uses_defaults(self):
        module = _load_cli_process_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            policy_path = Path(temp_dir) / "powershell-host-policy.json"
            policy_path.write_text("{invalid-json", encoding="utf-8")
            with patch.object(module, "POWERSHELL_HOST_POLICY_PATH", policy_path), warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                policy = module._powershell_host_policy()

        self.assertEqual(policy, module.POWERSHELL_HOST_POLICY_DEFAULTS)
        self.assertEqual(1, len(caught))
        self.assertIn("Invalid JSON in PowerShell host policy", str(caught[0].message))

    def test_choose_powershell_policy_rejects_invalid_field_types(self):
        module = _load_cli_process_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            policy_path = Path(temp_dir) / "powershell-host-policy.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "preferred_powershell_host": "not-a-host",
                        "require_pwsh_on_non_windows": "false",
                        "allow_windows_powershell_fallback": "false",
                        "record_host_resolution_artifacts": 1,
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(module, "POWERSHELL_HOST_POLICY_PATH", policy_path), warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                policy = module._powershell_host_policy()

        self.assertEqual(policy, module.POWERSHELL_HOST_POLICY_DEFAULTS)
        self.assertEqual(4, len(caught))
        messages = [str(item.message) for item in caught]
        self.assertTrue(any("Unsupported preferred_powershell_host" in message for message in messages))
        self.assertTrue(any("require_pwsh_on_non_windows must be boolean" in message for message in messages))
        self.assertTrue(any("allow_windows_powershell_fallback must be boolean" in message for message in messages))
        self.assertTrue(any("record_host_resolution_artifacts must be boolean" in message for message in messages))


class DelegatedLaneContractTests(unittest.TestCase):
    def test_plan_execute_uses_repo_root_first_working_directory_logic(self):
        script_text = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("Resolve-VibeDelegatedLaneWorkingDirectory", script_text)
        self.assertIn("requested_lane_root = $requestedLaneRoot", script_text)
        self.assertIn("lane_root_invalid", script_text)
        self.assertIn("requested_working_directory = if", script_text)
        self.assertIn("effective_working_directory = [string]$workingDirectoryInfo.effective_working_directory", script_text)
        self.assertIn("repo_root_invalid", script_text)
        self.assertIn("repo_root_missing", script_text)

    def test_plan_execute_recovers_payload_from_artifact_when_stdout_missing(self):
        script_text = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("Resolve-VibeDelegatedLanePayload", script_text)
        self.assertIn("source = 'lane_payload_artifact'", script_text)
        self.assertIn("lane_payload_artifact:read_failed", script_text)
        self.assertIn("empty_lane_receipt_path", script_text)
        self.assertIn("payload_source = [string]$payloadRecovery.source", script_text)

    def test_plan_execute_failure_message_is_actionable(self):
        script_text = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("Delegated lane payload handoff failed for lane_id=", script_text)
        self.assertIn("effective_working_directory=", script_text)
        self.assertIn("stdout_path=", script_text)
        self.assertIn("stderr_path=", script_text)
        self.assertIn("payload_path=", script_text)

    def test_delegated_lane_launch_metadata_records_host_resolution(self):
        script_text = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("host_kind = if ($invocation.PSObject.Properties.Name -contains 'host_kind')", script_text)
        self.assertIn("fallback_used = [bool]$(if ($invocation.PSObject.Properties.Name -contains 'fallback_used')", script_text)
        self.assertIn("lane_root_fallback_reason = if ($null -eq $workingDirectoryInfo.lane_root_fallback_reason)", script_text)
        self.assertIn("resolved_command = [string]($invocation.host_path)", script_text)
        self.assertIn("resolved_arguments = @($invocation.arguments)", script_text)
        self.assertIn("arguments_render_mode = 'RenderedString'", script_text)
        self.assertIn("preflight = [pscustomobject]@{", script_text)

    def test_runtime_execution_records_preflight_and_render_mode(self):
        script_text = (REPO_ROOT / "scripts" / "runtime" / "VibeExecution.Common.ps1").read_text(encoding="utf-8")
        self.assertIn("function New-VibeProcessPreflightResult", script_text)
        self.assertIn("command = [string]$Command", script_text)
        self.assertIn("Preflight.resolved_command", script_text)
        self.assertIn("Failed to persist launch metadata to", script_text)
        self.assertIn("Process preflight failed:", script_text)
        self.assertIn("arguments_render_mode = if ($usedArgumentList) { 'ArgumentList' } else { 'RenderedString' }", script_text)
        self.assertIn("launch_metadata_path", script_text)
        self.assertIn("script_used_as_executable", script_text)

    def test_parallel_lane_failure_cleans_up_remaining_handles(self):
        script_text = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("function Stop-VibeDelegatedLaneHandle", script_text)
        self.assertIn("$completedLaneIds = New-Object 'System.Collections.Generic.HashSet[string]'", script_text)
        self.assertIn("Stop-VibeDelegatedLaneHandle -Handle $remainingHandle", script_text)

    def test_runtime_execution_mentions_unicode_path_preflight_surfaces(self):
        script_text = (REPO_ROOT / "scripts" / "runtime" / "VibeExecution.Common.ps1").read_text(encoding="utf-8")
        self.assertIn("resolved executable does not exist:", script_text)
        self.assertIn("working directory does not exist:", script_text)
        self.assertIn("powershell script path is being used as the executable instead of the host:", script_text)
        self.assertIn("python command spec did not resolve to a host executable:", script_text)

    def test_execution_runtime_policy_uses_existing_coherence_gate_path(self):
        policy_text = (REPO_ROOT / "config" / "execution-runtime-policy.json").read_text(encoding="utf-8")
        self.assertIn("scripts/verify/vibe-release-install-runtime-coherence-gate.ps1", policy_text)
        self.assertNotIn("scripts/verify/vibe-version-consistency-gate.ps1", policy_text)

    def test_runtime_summary_artifacts_allow_early_bounded_stop_nulls(self):
        script_text = (REPO_ROOT / "scripts" / "runtime" / "VibeRuntime.Common.ps1").read_text(encoding="utf-8")
        self.assertIn("[AllowEmptyString()] [string]$IntentContractPath = ''", script_text)
        self.assertIn("[AllowEmptyString()] [string]$RequirementDocPath = ''", script_text)
        self.assertIn("[AllowEmptyString()] [string]$RequirementReceiptPath = ''", script_text)
        self.assertIn("intent_contract = if ([string]::IsNullOrWhiteSpace($IntentContractPath)) { $null } else { $IntentContractPath }", script_text)



class PowerShellBridgeDiagnosticTests(unittest.TestCase):
    def test_delegated_lane_empty_stdout_is_classified(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "empty.ps1"
            script_path.write_text("", encoding="utf-8")
            command = [
                sys.executable,
                "-c",
                "import sys; sys.exit(0)",
            ]
            with self.assertRaises(RuntimeError) as ctx:
                run_powershell_json_command(command, cwd=Path(temp_dir), bridge_label="delegated lane bridge")
        message = str(ctx.exception)
        self.assertIn("delegated lane payload handoff", message)
        self.assertIn("returned empty stdout", message)
        self.assertIn("cwd=", message)
        self.assertIn(f"command={Path(sys.executable).name}", message)

    def test_non_zero_exit_mentions_canonical_bridge_startup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            command = [
                sys.executable,
                "-c",
                "import sys; sys.stderr.write('boom\\n'); sys.exit(7)",
            ]
            with self.assertRaises(RuntimeError) as ctx:
                run_powershell_json_command(command, cwd=Path(temp_dir), bridge_label="canonical entry bridge")
        message = str(ctx.exception)
        self.assertIn("canonical bridge startup", message)
        self.assertIn("exit=7", message)
        self.assertIn("stderr=boom", message)


class BridgeFailureLayeringTests(unittest.TestCase):
    def test_canonical_entry_reads_shared_policy_file_override(self):
        module = _load_canonical_entry_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            policy_path = Path(temp_dir) / "powershell-host-policy.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "preferred_powershell_host": "windows-powershell",
                        "require_pwsh_on_non_windows": True,
                        "allow_windows_powershell_fallback": True,
                        "record_host_resolution_artifacts": True,
                    }
                ),
                encoding="utf-8",
            )
            pwsh_path = Path(temp_dir) / "pwsh.exe"
            powershell_path = Path(temp_dir) / "powershell.exe"
            pwsh_path.write_text("", encoding="utf-8")
            powershell_path.write_text("", encoding="utf-8")

            def fake_which(name: str) -> str | None:
                mapping = {
                    "pwsh": str(pwsh_path),
                    "pwsh.exe": str(pwsh_path),
                    "powershell": str(powershell_path),
                    "powershell.exe": str(powershell_path),
                }
                return mapping.get(name)

            with patch.object(module, "POWERSHELL_HOST_POLICY_PATH", policy_path), patch.object(module, "_is_windows_host", return_value=True), patch.object(module.shutil, "which", side_effect=fake_which):
                resolution = module._resolve_powershell_host(return_diagnostics=True)

        self.assertIsInstance(resolution, dict)
        self.assertEqual(resolution["host_path"], str(powershell_path))
        self.assertEqual(resolution["host_kind"], "windows-powershell")
        self.assertTrue(resolution["policy"]["allow_windows_powershell_fallback"])

    def test_canonical_entry_non_windows_skips_windows_install_path_candidates(self):
        module = _load_canonical_entry_module()

        def fake_which(name: str) -> str | None:
            return None

        def fake_exists(path_self: Path) -> bool:
            return False

        def fake_is_file(path_self: Path) -> bool:
            return False

        with patch.object(module, "_is_windows_host", return_value=False), patch.object(module.shutil, "which", side_effect=fake_which), patch.object(module.Path, "exists", fake_exists), patch.object(module.Path, "is_file", fake_is_file):
            resolution = module._resolve_powershell_host(return_diagnostics=True)

        self.assertIsInstance(resolution, dict)
        self.assertEqual(resolution.get("error"), "pwsh is required on non-Windows hosts")
        checked_names = [entry["candidate_name"] for entry in resolution["candidates_checked"]]
        self.assertEqual(["path-pwsh", "path-pwsh-exe"], checked_names)

    def test_canonical_entry_policy_rejects_invalid_field_types(self):
        module = _load_canonical_entry_module()
        with tempfile.TemporaryDirectory() as temp_dir:
            policy_path = Path(temp_dir) / "powershell-host-policy.json"
            policy_path.write_text(
                json.dumps(
                    {
                        "preferred_powershell_host": "bad-host",
                        "require_pwsh_on_non_windows": "false",
                        "allow_windows_powershell_fallback": "false",
                        "record_host_resolution_artifacts": 1,
                    }
                ),
                encoding="utf-8",
            )
            with patch.object(module, "POWERSHELL_HOST_POLICY_PATH", policy_path), warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                policy = module._powershell_host_policy()

        self.assertEqual(policy, module.POWERSHELL_HOST_POLICY_DEFAULTS)
        self.assertEqual(4, len(caught))
        messages = [str(item.message) for item in caught]
        self.assertTrue(any("Unsupported preferred_powershell_host" in message for message in messages))
        self.assertTrue(any("require_pwsh_on_non_windows must be boolean" in message for message in messages))
        self.assertTrue(any("allow_windows_powershell_fallback must be boolean" in message for message in messages))
        self.assertTrue(any("record_host_resolution_artifacts must be boolean" in message for message in messages))

    def test_canonical_entry_startup_failure_is_distinct_from_payload_handoff_failure(self):
        module = _load_canonical_entry_module()
        with tempfile.TemporaryDirectory() as repo_dir:
            repo_root = Path(repo_dir)
            bridge_path = repo_root / "scripts" / "runtime"
            bridge_path.mkdir(parents=True, exist_ok=True)
            (bridge_path / "Invoke-VibeCanonicalEntry.ps1").write_text("# stub", encoding="utf-8")

            def fake_startup_bridge(command, *, cwd, bridge_label, env=None, timeout=None):
                raise RuntimeError(
                    "canonical entry bridge failed during canonical bridge startup: subprocess exited non-zero before JSON payload was returned (exit=11; cwd=%s; command=python; stderr=startup boom)" % cwd
                )

            def fake_payload_bridge(command, *, cwd, bridge_label, env=None, timeout=None):
                raise RuntimeError(
                    "canonical entry bridge failed during delegated lane payload handoff: canonical entry bridge returned invalid JSON stdout (cwd=%s; command=python; stdout=not-json)" % cwd
                )

            with patch.object(module, "_resolve_powershell_host", return_value={"host_path": sys.executable, "host_kind": "pwsh", "fallback_used": False, "candidates_checked": []}):
                with patch.object(module, "run_powershell_json_command", side_effect=fake_startup_bridge):
                    with self.assertRaises(RuntimeError) as startup_ctx:
                        module.invoke_vibe_runtime_entrypoint(
                            repo_root=repo_root,
                            host_id="codex",
                            entry_id="vibe",
                            prompt="test",
                            requested_stage_stop=None,
                            requested_grade_floor=None,
                            run_id="run-startup",
                            artifact_root=None,
                            force_runtime_neutral=False,
                        )
                with patch.object(module, "run_powershell_json_command", side_effect=fake_payload_bridge):
                    with self.assertRaises(RuntimeError) as payload_ctx:
                        module.invoke_vibe_runtime_entrypoint(
                            repo_root=repo_root,
                            host_id="codex",
                            entry_id="vibe",
                            prompt="test",
                            requested_stage_stop=None,
                            requested_grade_floor=None,
                            run_id="run-payload",
                            artifact_root=None,
                            force_runtime_neutral=False,
                        )

        startup_message = str(startup_ctx.exception)
        payload_message = str(payload_ctx.exception)
        self.assertIn("canonical bridge startup", startup_message)
        self.assertNotIn("delegated lane payload handoff", startup_message)
        self.assertIn("delegated lane payload handoff", payload_message)
        self.assertNotIn("canonical bridge startup", payload_message)

    def test_bridge_succeeds_from_unicode_working_directory(self):
        with tempfile.TemporaryDirectory(prefix="vibe-桥接-羽裳-") as temp_dir:
            cwd = Path(temp_dir)
            payload = {"status": "ok", "cwd": str(cwd)}
            command = [
                sys.executable,
                "-c",
                "import json, os; print(json.dumps({'status':'ok','cwd':os.getcwd()}, ensure_ascii=False))",
            ]
            result = run_powershell_json_command(command, cwd=cwd, bridge_label="canonical entry bridge")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["cwd"], str(cwd))
        self.assertIn("桥接", result["cwd"])

    def test_bridge_failure_from_unicode_working_directory_preserves_context(self):
        with tempfile.TemporaryDirectory(prefix="vibe-桥接-羽裳-") as temp_dir:
            cwd = Path(temp_dir)
            command = [
                sys.executable,
                "-c",
                "import sys; sys.stderr.write('unicode boom\\n'); sys.exit(9)",
            ]
            with self.assertRaises(RuntimeError) as ctx:
                run_powershell_json_command(command, cwd=cwd, bridge_label="canonical entry bridge")
        message = str(ctx.exception)
        self.assertIn("canonical bridge startup", message)
        self.assertIn("exit=9", message)
        self.assertIn("unicode boom", message)
        self.assertIn(str(cwd), message)
        self.assertIn("桥接", message)


    def test_real_bridge_smoke_surfaces_preflight_script_missing_instead_of_invalid_python_host(self):
        helper_text = (REPO_ROOT / "scripts" / "common" / "vibe-governance-helpers.ps1").read_text(encoding="utf-8")
        runtime_text = (REPO_ROOT / "scripts" / "runtime" / "VibeExecution.Common.ps1").read_text(encoding="utf-8")
        self.assertIn("Test-VgoWindowsRunnableCommandPath", helper_text)
        self.assertIn("powershell script path does not exist:", runtime_text)
        self.assertIn("Process startup failed for {0}:", runtime_text)

    def test_canonical_entry_builds_command_for_unicode_repo_root(self):
        module = _load_canonical_entry_module()
        with tempfile.TemporaryDirectory(prefix="vibe-规范入口-羽裳-") as repo_dir:
            repo_root = Path(repo_dir)
            bridge_dir = repo_root / "scripts" / "runtime"
            bridge_dir.mkdir(parents=True, exist_ok=True)
            (bridge_dir / "Invoke-VibeCanonicalEntry.ps1").write_text("# stub", encoding="utf-8")

            observed: dict[str, object] = {}

            def fake_bridge(command, *, cwd, bridge_label, env=None, timeout=None):
                observed["command"] = list(command)
                observed["cwd"] = cwd
                observed["bridge_label"] = bridge_label
                return {
                    "run_id": "run-1",
                    "session_root": str(repo_root / ".vibeskills" / "outputs" / "runtime" / "vibe-sessions" / "run-1"),
                    "summary_path": str(repo_root / ".vibeskills" / "outputs" / "runtime" / "vibe-sessions" / "run-1" / "runtime-summary.json"),
                    "summary": {},
                }

            with patch.object(module, "_resolve_powershell_host", return_value={
                "host_path": sys.executable,
                "host_kind": "pwsh",
                "fallback_used": False,
                "candidates_checked": [],
            }), patch.object(module, "run_powershell_json_command", side_effect=fake_bridge):
                module.invoke_vibe_runtime_entrypoint(
                    repo_root=repo_root,
                    host_id="claude-code",
                    entry_id="vibe",
                    prompt="unicode probe",
                    requested_stage_stop=None,
                    requested_grade_floor=None,
                    run_id="run-1",
                    artifact_root=None,
                    force_runtime_neutral=False,
                )

        self.assertEqual(observed["cwd"], repo_root)
        self.assertEqual(observed["bridge_label"], "canonical entry bridge")
        self.assertEqual(observed["command"][0], sys.executable)
        self.assertIn(str((repo_root / "scripts" / "runtime" / "Invoke-VibeCanonicalEntry.ps1")), observed["command"])
        self.assertIn("规范入口", str(repo_root))

    def test_canonical_entry_preserves_bridge_context_when_not_launched_from_repo_cwd(self):
        module = _load_canonical_entry_module()
        with tempfile.TemporaryDirectory() as repo_dir, tempfile.TemporaryDirectory() as other_dir:
            repo_root = Path(repo_dir)
            bridge_path = repo_root / "scripts" / "runtime"
            bridge_path.mkdir(parents=True, exist_ok=True)
            (bridge_path / "Invoke-VibeCanonicalEntry.ps1").write_text("# stub", encoding="utf-8")

            observed: dict[str, object] = {}

            def fake_bridge(command, *, cwd, bridge_label, env=None, timeout=None):
                observed["cwd"] = cwd
                raise RuntimeError("canonical entry bridge failed during delegated lane payload handoff")

            old_cwd = Path.cwd()
            os.chdir(other_dir)
            try:
                with patch.object(module, "_resolve_powershell_host", return_value={"host_path": sys.executable, "host_kind": "pwsh", "fallback_used": False, "candidates_checked": []}), patch.object(module, "run_powershell_json_command", side_effect=fake_bridge):
                    with self.assertRaises(RuntimeError) as ctx:
                        module.invoke_vibe_runtime_entrypoint(
                            repo_root=repo_root,
                            host_id="codex",
                            entry_id="vibe",
                            prompt="test",
                            requested_stage_stop=None,
                            requested_grade_floor=None,
                            run_id="run-1",
                            artifact_root=None,
                            force_runtime_neutral=False,
                        )
            finally:
                os.chdir(old_cwd)

        self.assertEqual(observed["cwd"], repo_root)
        self.assertIn("delegated lane payload handoff", str(ctx.exception))

    def test_canonical_entry_reports_candidates_when_powershell_missing(self):
        module = _load_canonical_entry_module()
        with tempfile.TemporaryDirectory() as repo_dir:
            repo_root = Path(repo_dir)
            bridge_path = repo_root / "scripts" / "runtime"
            bridge_path.mkdir(parents=True, exist_ok=True)
            (bridge_path / "Invoke-VibeCanonicalEntry.ps1").write_text("# stub", encoding="utf-8")
            with self.assertRaises(RuntimeError) as ctx:
                with patch.object(
                    module,
                    "_resolve_powershell_host",
                    return_value={
                        "host_path": None,
                        "host_kind": None,
                        "fallback_used": False,
                        "candidates_checked": [
                            {"candidate_name": "path-pwsh", "candidate_path": None},
                            {"candidate_name": "path-powershell", "candidate_path": r"C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"},
                        ],
                    },
                ):
                    module.invoke_vibe_runtime_entrypoint(
                        repo_root=repo_root,
                        host_id="codex",
                        entry_id="vibe",
                        prompt="test",
                        requested_stage_stop=None,
                        requested_grade_floor=None,
                        run_id="run-1",
                        artifact_root=None,
                        force_runtime_neutral=False,
                    )
        message = str(ctx.exception)
        self.assertIn("PowerShell executable not found; locations searched (PATH and well-known install paths):", message)
        self.assertIn("path-pwsh", message)
        self.assertIn("powershell.exe", message)

    def test_canonical_entry_surfaces_pwsh_policy_reason_when_missing_on_non_windows(self):
        module = _load_canonical_entry_module()
        with tempfile.TemporaryDirectory() as repo_dir:
            repo_root = Path(repo_dir)
            bridge_path = repo_root / "scripts" / "runtime"
            bridge_path.mkdir(parents=True, exist_ok=True)
            (bridge_path / "Invoke-VibeCanonicalEntry.ps1").write_text("# stub", encoding="utf-8")
            with self.assertRaises(RuntimeError) as ctx:
                with patch.object(
                    module,
                    "_resolve_powershell_host",
                    return_value={
                        "host_path": None,
                        "host_kind": None,
                        "fallback_used": False,
                        "candidates_checked": [
                            {"candidate_name": "path-pwsh", "candidate_path": None},
                            {"candidate_name": "path-pwsh-exe", "candidate_path": None},
                        ],
                        "error": "pwsh is required on non-Windows hosts",
                    },
                ):
                    module.invoke_vibe_runtime_entrypoint(
                        repo_root=repo_root,
                        host_id="codex",
                        entry_id="vibe",
                        prompt="test",
                        requested_stage_stop=None,
                        requested_grade_floor=None,
                        run_id="run-1",
                        artifact_root=None,
                        force_runtime_neutral=False,
                    )
        message = str(ctx.exception)
        self.assertIn("pwsh is required on non-Windows hosts", message)
        self.assertIn("locations searched (PATH and well-known install paths): path-pwsh, path-pwsh-exe", message)


if __name__ == "__main__":
    unittest.main()
