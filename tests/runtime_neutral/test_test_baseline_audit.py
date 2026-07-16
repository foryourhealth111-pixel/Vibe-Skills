from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CORE_SRC = REPO_ROOT / "packages" / "verification-core" / "src"
SCRIPT_ENTRYPOINT = REPO_ROOT / "scripts" / "verify" / "test-baseline-audit.py"
if str(CORE_SRC) not in sys.path:
    sys.path.insert(0, str(CORE_SRC))

from vgo_verify import test_baseline_audit as audit


EXPECTED_LAYER_IDS = [
    "contract_unit",
    "default_install_lifecycle",
    "default_runtime_entry_truth",
    "default_routing_mainline",
    "touched_packaging_release",
    "integration_host_boundary",
]


class TestBaselineAuditPolicyTests(unittest.TestCase):
    def test_policy_file_has_capability_layers_and_network_default(self) -> None:
        policy = audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json")

        self.assertEqual(1, policy["version"])
        self.assertFalse(policy["defaults"]["external_network_allowed"])
        self.assertEqual(EXPECTED_LAYER_IDS, [layer["id"] for layer in policy["layers"]])
        self.assertNotIn("classification", policy)
        self.assertNotIn("risk_keywords", policy)
        self.assertEqual("contract_support", policy["layers"][0]["selection_scope"])

    def test_capability_layers_use_explicit_targets_and_packaging_is_touched_only(self) -> None:
        policy = audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json")
        layers = {layer["id"]: layer for layer in policy["layers"]}

        for layer_id in (
            "default_install_lifecycle",
            "default_runtime_entry_truth",
            "default_routing_mainline",
            "touched_packaging_release",
        ):
            pytest_args = layers[layer_id]["pytest_args"]
            self.assertTrue(pytest_args, layer_id)
            self.assertTrue(all(arg.endswith(".py") for arg in pytest_args), layer_id)

        self.assertEqual("default_regression", layers["default_install_lifecycle"]["selection_scope"])
        self.assertEqual("default_regression", layers["default_runtime_entry_truth"]["selection_scope"])
        self.assertEqual("default_regression", layers["default_routing_mainline"]["selection_scope"])
        self.assertEqual("touched_surface_only", layers["touched_packaging_release"]["selection_scope"])
        self.assertEqual("host_boundary", layers["integration_host_boundary"]["selection_scope"])

    def test_default_capability_layers_keep_file_serial_diagnostics(self) -> None:
        policy = audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json")
        layers = {layer["id"]: layer for layer in policy["layers"]}

        for layer_id in (
            "default_install_lifecycle",
            "default_runtime_entry_truth",
            "default_routing_mainline",
            "touched_packaging_release",
        ):
            self.assertEqual("file_serial", layers[layer_id]["run_strategy"], layer_id)
            self.assertGreaterEqual(layers[layer_id]["per_file_timeout_seconds"], 300, layer_id)

    def test_policy_load_rejects_duplicate_layer_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "policy.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "defaults": {"external_network_allowed": False},
                        "layers": [
                            {"id": "contract_unit", "pytest_args": ["tests/unit"]},
                            {"id": "contract_unit", "pytest_args": ["tests/contract"]},
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(audit.PolicyError, "Duplicate layer id"):
                audit.load_policy(path)

    def test_parse_collect_output_extracts_node_ids(self) -> None:
        output = "\n".join(
            [
                "tests/unit/test_alpha.py::test_one",
                "tests/unit/test_alpha.py::test_param[value]",
                "tests/runtime_neutral/test_beta.py::BetaTests::test_two",
                "packages/runtime-core/src/vgo_runtime/test_lock.py::test_package_node",
                "4 tests collected",
            ]
        )

        self.assertEqual(
            [
                "tests/unit/test_alpha.py::test_one",
                "tests/unit/test_alpha.py::test_param[value]",
                "tests/runtime_neutral/test_beta.py::BetaTests::test_two",
                "packages/runtime-core/src/vgo_runtime/test_lock.py::test_package_node",
            ],
            audit.parse_collect_output(output),
        )

    def test_build_collect_commands_uses_explicit_capability_targets(self) -> None:
        policy = audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json")
        commands = audit.build_collect_commands(policy)

        self.assertEqual(6, len(commands))
        command_map = {
            tuple(item["source_layer_ids"]): item["command"]
            for item in commands
        }
        self.assertEqual(
            [sys.executable, "-m", "pytest", "tests/contract", "tests/unit", "--collect-only", "-q"],
            command_map[("contract_unit",)],
        )
        self.assertIn("tests/runtime_neutral/test_install_profile_differentiation.py", command_map[("default_install_lifecycle",)])
        self.assertIn("tests/runtime_neutral/test_governed_runtime_bridge.py", command_map[("default_runtime_entry_truth",)])
        self.assertIn("tests/runtime_neutral/test_custom_admission_bridge.py", command_map[("default_routing_mainline",)])
        self.assertIn("tests/runtime_neutral/test_release_truth_gate.py", command_map[("touched_packaging_release",)])
        self.assertEqual(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/integration/test_host_global_bootstrap_shell_lifecycle.py",
                "tests/integration/test_install_rerun_matrix.py",
                "tests/integration/test_powershell_wrapper_host_validation_dedupe.py",
                "--collect-only",
                "-q",
            ],
            command_map[("integration_host_boundary",)],
        )

    def test_script_entrypoint_disables_bytecode_before_core_import(self) -> None:
        text = SCRIPT_ENTRYPOINT.read_text(encoding="utf-8")

        disable_index = text.index("sys.dont_write_bytecode = True")
        import_index = text.index("from vgo_verify.test_baseline_audit import")

        self.assertLess(disable_index, import_index)

    def test_scan_file_risks_is_empty_under_explicit_policy(self) -> None:
        policy = audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json")
        with tempfile.TemporaryDirectory() as tempdir:
            path = Path(tempdir) / "tests" / "runtime_neutral" / "test_release.py"
            path.parent.mkdir(parents=True)
            path.write_text("def test_release():\n    assert 'https://example.invalid'\n", encoding="utf-8")

            risks = audit.scan_file_risks(path, policy)

        self.assertEqual([], risks)

    def test_classify_node_uses_explicit_install_layer_membership(self) -> None:
        policy = audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json")

        item = audit.classify_node(
            "tests/runtime_neutral/test_install_profile_differentiation.py::test_profile",
            REPO_ROOT,
            policy,
        )

        self.assertEqual("default_install_lifecycle", item["layer_id"])
        self.assertEqual([], item["risk_tags"])
        self.assertIn("pytest_target:tests/runtime_neutral/test_install_profile_differentiation.py", item["reasons"])

    def test_classify_node_uses_explicit_runtime_truth_layer_membership(self) -> None:
        policy = audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json")

        item = audit.classify_node(
            "tests/runtime_neutral/test_governed_runtime_bridge.py::test_bridge",
            REPO_ROOT,
            policy,
        )

        self.assertEqual("default_runtime_entry_truth", item["layer_id"])
        self.assertEqual("tests/runtime_neutral/test_governed_runtime_bridge.py", item["file"])

    def test_classify_node_uses_explicit_routing_layer_membership(self) -> None:
        policy = audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json")

        item = audit.classify_node(
            "tests/runtime_neutral/test_custom_admission_bridge.py::test_bridge",
            REPO_ROOT,
            policy,
        )

        self.assertEqual("default_routing_mainline", item["layer_id"])
        self.assertIn("pytest_target:tests/runtime_neutral/test_custom_admission_bridge.py", item["reasons"])

    def test_classify_node_rejects_runtime_file_outside_explicit_policy(self) -> None:
        policy = audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json")

        with self.assertRaisesRegex(audit.PolicyError, "No policy layer targets tests/runtime_neutral/test_runtime_contracts.py"):
            audit.classify_node("tests/runtime_neutral/test_runtime_contracts.py::test_contract_shape", REPO_ROOT, policy)

    def test_select_layer_files_returns_only_explicit_capability_targets(self) -> None:
        policy = audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json")
        nodes = [
            "tests/runtime_neutral/test_install_profile_differentiation.py::test_profile",
            "tests/runtime_neutral/test_governed_runtime_bridge.py::test_bridge",
            "tests/runtime_neutral/test_custom_admission_bridge.py::test_bridge",
            "tests/runtime_neutral/test_pack_manifest_role_contract.py::test_manifest",
        ]

        install_files = audit.select_layer_files(nodes, REPO_ROOT, policy, "default_install_lifecycle")
        runtime_files = audit.select_layer_files(nodes, REPO_ROOT, policy, "default_runtime_entry_truth")
        routing_files = audit.select_layer_files(nodes, REPO_ROOT, policy, "default_routing_mainline")
        packaging_files = audit.select_layer_files(nodes, REPO_ROOT, policy, "touched_packaging_release")

        self.assertEqual(["tests/runtime_neutral/test_install_profile_differentiation.py"], install_files)
        self.assertEqual(["tests/runtime_neutral/test_governed_runtime_bridge.py"], runtime_files)
        self.assertEqual(["tests/runtime_neutral/test_custom_admission_bridge.py"], routing_files)
        self.assertEqual(["tests/runtime_neutral/test_pack_manifest_role_contract.py"], packaging_files)

    def test_run_collect_commands_reports_layer_context_on_timeout(self) -> None:
        policy = {
            "defaults": {"pytest_quiet_arg": "-q", "collect_timeout_seconds": 7},
            "layers": [
                {
                    "id": "slow_layer",
                    "pytest_args": ["tests/runtime_neutral/test_governed_runtime_bridge.py"],
                    "timeout_seconds": 7,
                }
            ],
        }

        def timeout_runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            raise subprocess.TimeoutExpired(
                command,
                kwargs["timeout"],
                output="partial stdout",
                stderr="partial stderr",
            )

        with self.assertRaises(RuntimeError) as raised:
            audit.run_collect_commands(REPO_ROOT, policy, runner=timeout_runner)

        message = str(raised.exception)
        self.assertIn("pytest collection timed out", message)
        self.assertIn("tests/runtime_neutral/test_governed_runtime_bridge.py", message)
        self.assertIn("slow_layer", message)
        self.assertIn("7s", message)
        self.assertIn("partial stdout", message)
        self.assertIn("partial stderr", message)

    def test_build_run_layer_command_uses_explicit_files_when_nodes_are_available(self) -> None:
        policy = audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json")
        nodes = [
            "tests/runtime_neutral/test_governed_runtime_bridge.py::test_bridge",
            "tests/runtime_neutral/test_runtime_delivery_acceptance.py::test_delivery",
            "tests/runtime_neutral/test_install_profile_differentiation.py::test_profile",
        ]

        command = audit.build_run_layer_command(
            policy,
            "default_runtime_entry_truth",
            repo_root=REPO_ROOT,
            collected_nodes=nodes,
        )

        self.assertIn("tests/runtime_neutral/test_governed_runtime_bridge.py", command)
        self.assertIn("tests/runtime_neutral/test_runtime_delivery_acceptance.py", command)
        self.assertNotIn("tests/runtime_neutral/test_install_profile_differentiation.py", command)

    def test_build_artifact_summarizes_capability_layers_without_risk_taxonomy(self) -> None:
        policy = audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json")
        nodes = [
            "tests/unit/test_vgo_verify_repo.py::test_repo_root",
            "tests/runtime_neutral/test_install_profile_differentiation.py::test_profile",
            "tests/runtime_neutral/test_governed_runtime_bridge.py::test_bridge",
            "tests/runtime_neutral/test_custom_admission_bridge.py::test_bridge",
            "tests/runtime_neutral/test_pack_manifest_role_contract.py::test_manifest",
            "tests/integration/test_install_rerun_matrix.py::test_build_install_plan_preserves_rerun_semantics",
        ]

        artifact = audit.build_artifact(
            repo_root=REPO_ROOT,
            policy_path=REPO_ROOT / "config" / "test-baseline-policy.json",
            policy=policy,
            collected_nodes=nodes,
            collection_results=[],
            run_result=None,
        )

        self.assertEqual(6, artifact["summary"]["total_nodes"])
        self.assertEqual(0, artifact["summary"]["risk_tag_count"])
        self.assertEqual({}, artifact["risks"])
        self.assertEqual("contract_support", artifact["layers"]["contract_unit"]["selection_scope"])
        self.assertEqual("default_regression", artifact["layers"]["default_install_lifecycle"]["selection_scope"])
        self.assertEqual("touched_surface_only", artifact["layers"]["touched_packaging_release"]["selection_scope"])
        self.assertEqual("host_boundary", artifact["layers"]["integration_host_boundary"]["selection_scope"])
        self.assertEqual(1, artifact["layers"]["contract_unit"]["node_count"])
        self.assertEqual(1, artifact["layers"]["default_install_lifecycle"]["node_count"])
        self.assertEqual(1, artifact["layers"]["default_runtime_entry_truth"]["node_count"])
        self.assertEqual(1, artifact["layers"]["default_routing_mainline"]["node_count"])
        self.assertEqual(1, artifact["layers"]["touched_packaging_release"]["node_count"])
        self.assertEqual(1, artifact["layers"]["integration_host_boundary"]["node_count"])

    def test_write_artifacts_emits_json_and_markdown(self) -> None:
        policy = audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json")
        policy["artifact_names"] = {
            "json": "custom-test-baseline.json",
            "markdown": "custom-test-baseline.md",
        }
        artifact = audit.build_artifact(
            repo_root=REPO_ROOT,
            policy_path=REPO_ROOT / "config" / "test-baseline-policy.json",
            policy=policy,
            collected_nodes=["tests/unit/test_vgo_verify_repo.py::test_repo_root"],
            collection_results=[],
            run_result=None,
        )

        with tempfile.TemporaryDirectory() as tempdir:
            written = audit.write_artifacts(REPO_ROOT, artifact, tempdir, policy=policy)
            json_path = Path(written["json"])
            md_path = Path(written["markdown"])

            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            self.assertEqual("custom-test-baseline.json", json_path.name)
            self.assertEqual("custom-test-baseline.md", md_path.name)
            self.assertEqual(1, json.loads(json_path.read_text(encoding="utf-8"))["summary"]["total_nodes"])
            self.assertIn("Test Baseline Audit", md_path.read_text(encoding="utf-8"))

    def test_resolve_repo_root_uses_vco_marker_not_generic_ancestor_config(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            outer = Path(tempdir) / "outer"
            inner = Path(tempdir) / "outer" / "tools" / "Vibe-Skills"
            script_path = inner / "packages" / "verification-core" / "src" / "vgo_verify" / "test_baseline_audit.py"
            (outer / ".git").mkdir(parents=True)
            (outer / "config").mkdir()
            (inner / "config").mkdir(parents=True)
            (inner / "config" / "version-governance.json").write_text("{}\n", encoding="utf-8")
            script_path.parent.mkdir(parents=True)
            script_path.write_text("# fixture\n", encoding="utf-8")

            resolved = audit.resolve_repo_root(script_path)

        self.assertEqual(inner.resolve(), resolved)


class FakeCompletedProcess:
    def __init__(self, args: list[str], returncode: int = 0, stdout: str = "", stderr: str = "") -> None:
        self.args = args
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class FakeRunner:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, command: list[str], **kwargs: object) -> FakeCompletedProcess:
        self.calls.append({"command": command, "kwargs": kwargs})
        stdout = "\n".join(
            [
                "tests/unit/test_vgo_verify_repo.py::test_repo_root",
                "tests/runtime_neutral/test_install_profile_differentiation.py::test_profile",
                "tests/runtime_neutral/test_governed_runtime_bridge.py::test_bridge",
                "tests/runtime_neutral/test_custom_admission_bridge.py::test_bridge",
                "tests/runtime_neutral/test_pack_manifest_role_contract.py::test_manifest",
                "tests/integration/test_install_rerun_matrix.py::test_build_install_plan_preserves_rerun_semantics",
                "6 tests collected",
            ]
        )
        if "--collect-only" not in command:
            stdout = "1 passed"
        return FakeCompletedProcess(command, stdout=stdout)


class TestBaselineAuditCliTests(unittest.TestCase):
    def test_collect_only_uses_subprocess_without_running_tests(self) -> None:
        runner = FakeRunner()
        exit_code = audit.main(["--collect-only"], runner=runner)

        self.assertEqual(0, exit_code)
        self.assertEqual(6, len(runner.calls))
        self.assertTrue(all("--collect-only" in call["command"] for call in runner.calls))
        for call in runner.calls:
            env = call["kwargs"]["env"]
            self.assertEqual("1", env["VIBESKILLS_TEST_DISABLE_NETWORK"])
            self.assertEqual("1", env["PYTHONDONTWRITEBYTECODE"])
            self.assertEqual(str(REPO_ROOT / ".tmp" / "pycache"), env["PYTHONPYCACHEPREFIX"])

    def test_collect_only_overrides_run_layer(self) -> None:
        runner = FakeRunner()
        exit_code = audit.main(["--collect-only", "--run-layer", "contract_unit"], runner=runner)

        self.assertEqual(0, exit_code)
        self.assertEqual(6, len(runner.calls))
        self.assertTrue(all("--collect-only" in call["command"] for call in runner.calls))

    def test_run_layer_sets_disable_network_env(self) -> None:
        runner = FakeRunner()
        exit_code = audit.main(["--run-layer", "contract_unit"], runner=runner)

        self.assertEqual(0, exit_code)
        run_calls = [call for call in runner.calls if "--collect-only" not in call["command"]]
        self.assertEqual(1, len(run_calls))
        env = run_calls[0]["kwargs"]["env"]
        self.assertEqual("1", env["VIBESKILLS_TEST_DISABLE_NETWORK"])
        self.assertEqual("1", env["PYTHONDONTWRITEBYTECODE"])
        self.assertEqual(str(REPO_ROOT / ".tmp" / "pycache"), env["PYTHONPYCACHEPREFIX"])
        self.assertEqual(
            [sys.executable, "-m", "pytest", "tests/unit/test_vgo_verify_repo.py", "-q"],
            run_calls[0]["command"],
        )

    def test_run_layer_uses_capability_files_for_requested_layer(self) -> None:
        runner = FakeRunner()
        exit_code = audit.main(["--run-layer", "default_runtime_entry_truth"], runner=runner)

        self.assertEqual(0, exit_code)
        run_calls = [call for call in runner.calls if "--collect-only" not in call["command"]]
        self.assertEqual(1, len(run_calls))
        command = run_calls[0]["command"]
        self.assertIn("tests/runtime_neutral/test_governed_runtime_bridge.py", command)
        self.assertNotIn("tests/runtime_neutral/test_install_profile_differentiation.py", command)
        self.assertNotIn("tests/runtime_neutral", command)

    def test_build_run_layer_command_preserves_pytest_options_when_narrowing_to_files(self) -> None:
        policy = copy.deepcopy(audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json"))
        layers = {layer["id"]: layer for layer in policy["layers"]}
        layers["default_runtime_entry_truth"]["pytest_args"] = [
            "tests/runtime_neutral/test_governed_runtime_bridge.py",
            "tests/runtime_neutral/test_runtime_delivery_acceptance.py",
            "-k",
            "runtime",
            "--maxfail=1",
        ]
        nodes = [
            "tests/runtime_neutral/test_governed_runtime_bridge.py::test_bridge",
            "tests/runtime_neutral/test_runtime_delivery_acceptance.py::test_delivery",
            "tests/runtime_neutral/test_install_profile_differentiation.py::test_profile",
        ]

        command = audit.build_run_layer_command(
            policy,
            "default_runtime_entry_truth",
            repo_root=REPO_ROOT,
            collected_nodes=nodes,
        )

        self.assertIn("-k", command)
        self.assertEqual("runtime", command[command.index("-k") + 1])
        self.assertIn("--maxfail=1", command)
        self.assertIn("tests/runtime_neutral/test_governed_runtime_bridge.py", command)
        self.assertIn("tests/runtime_neutral/test_runtime_delivery_acceptance.py", command)
        self.assertNotIn("tests/runtime_neutral/test_install_profile_differentiation.py", command)

    def test_run_layer_accepts_capability_layer(self) -> None:
        runner = FakeRunner()
        exit_code = audit.main(["--run-layer", "default_routing_mainline"], runner=runner)

        self.assertEqual(0, exit_code)
        run_calls = [call for call in runner.calls if "--collect-only" not in call["command"]]
        self.assertEqual(1, len(run_calls))
        self.assertEqual(
            [sys.executable, "-m", "pytest", "tests/runtime_neutral/test_custom_admission_bridge.py", "-q"],
            run_calls[0]["command"],
        )

    def test_run_layer_raises_policy_error_for_unknown_layer_without_collected_nodes(self) -> None:
        policy = copy.deepcopy(audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json"))

        with self.assertRaisesRegex(audit.PolicyError, "Unknown layer id: missing_layer"):
            audit.run_layer(
                REPO_ROOT,
                policy,
                "missing_layer",
                collected_nodes=None,
                runner=FakeRunner(),
            )

    def test_run_layer_file_serial_strategy_records_per_file_results(self) -> None:
        policy = copy.deepcopy(audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json"))
        layers = {layer["id"]: layer for layer in policy["layers"]}
        layers["default_runtime_entry_truth"]["per_file_timeout_seconds"] = 123
        runner = FakeRunner()

        result = audit.run_layer(
            REPO_ROOT,
            policy,
            "default_runtime_entry_truth",
            collected_nodes=[
                "tests/runtime_neutral/test_governed_runtime_bridge.py::test_bridge",
                "tests/runtime_neutral/test_runtime_delivery_acceptance.py::test_delivery",
            ],
            runner=runner,
        )

        self.assertEqual(0, result["exit_code"])
        self.assertEqual("file_serial", result["run_strategy"])
        self.assertEqual(2, len(result["file_results"]))
        run_calls = [call for call in runner.calls if "--collect-only" not in call["command"]]
        self.assertEqual(2, len(run_calls))
        self.assertEqual(
            [sys.executable, "-m", "pytest", "tests/runtime_neutral/test_governed_runtime_bridge.py", "-q"],
            run_calls[0]["command"],
        )
        self.assertEqual(123, run_calls[0]["kwargs"]["timeout"])
        self.assertIn("tests/runtime_neutral/test_runtime_delivery_acceptance.py", result["stdout"])

    def test_run_layer_file_serial_strategy_caps_file_timeout_by_layer_budget(self) -> None:
        policy = copy.deepcopy(audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json"))
        layers = {layer["id"]: layer for layer in policy["layers"]}
        layers["default_runtime_entry_truth"]["timeout_seconds"] = 5
        layers["default_runtime_entry_truth"]["per_file_timeout_seconds"] = 123
        runner = FakeRunner()

        audit.run_layer(
            REPO_ROOT,
            policy,
            "default_runtime_entry_truth",
            collected_nodes=["tests/runtime_neutral/test_governed_runtime_bridge.py::test_bridge"],
            runner=runner,
        )

        run_calls = [call for call in runner.calls if "--collect-only" not in call["command"]]
        self.assertEqual(5, run_calls[0]["kwargs"]["timeout"])

    def test_run_layer_default_strategy_reports_timeout(self) -> None:
        policy = copy.deepcopy(audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json"))
        layers = {layer["id"]: layer for layer in policy["layers"]}
        layers["contract_unit"]["timeout_seconds"] = 7

        def timeout_runner(command: list[str], **kwargs: object) -> FakeCompletedProcess:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"], output="partial stdout", stderr="partial stderr")

        result = audit.run_layer(
            REPO_ROOT,
            policy,
            "contract_unit",
            runner=timeout_runner,
        )

        self.assertEqual(124, result["exit_code"])
        self.assertEqual(7, result["timeout_seconds"])
        self.assertIn("partial stdout", result["stdout"])
        self.assertIn("partial stderr", result["stderr"])
        self.assertEqual([], result["selected_files"])
        self.assertEqual(0, result["selected_file_count"])

    def test_run_layer_file_serial_strategy_emits_progress_events(self) -> None:
        runner = FakeRunner()
        events: list[str] = []

        audit.run_layer(
            REPO_ROOT,
            audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json"),
            "default_runtime_entry_truth",
            collected_nodes=["tests/runtime_neutral/test_governed_runtime_bridge.py::test_bridge"],
            runner=runner,
            progress=events.append,
        )

        self.assertEqual(
            ["[INFO] start_file tests/runtime_neutral/test_governed_runtime_bridge.py"],
            events[:1],
        )
        self.assertIn(
            "[FILE] tests/runtime_neutral/test_governed_runtime_bridge.py exit_code=0",
            events[-1],
        )

    def test_run_layer_file_serial_strategy_reports_timeout_file(self) -> None:
        policy = copy.deepcopy(audit.load_policy(REPO_ROOT / "config" / "test-baseline-policy.json"))
        layers = {layer["id"]: layer for layer in policy["layers"]}
        layers["default_runtime_entry_truth"]["per_file_timeout_seconds"] = 7

        def timeout_runner(command: list[str], **kwargs: object) -> FakeCompletedProcess:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"], output="partial stdout", stderr="partial stderr")

        result = audit.run_layer(
            REPO_ROOT,
            policy,
            "default_runtime_entry_truth",
            collected_nodes=["tests/runtime_neutral/test_governed_runtime_bridge.py::test_bridge"],
            runner=timeout_runner,
        )

        self.assertEqual(124, result["exit_code"])
        self.assertEqual("timeout", result["file_results"][0]["status"])
        self.assertEqual("tests/runtime_neutral/test_governed_runtime_bridge.py", result["file_results"][0]["file"])
        self.assertIn("partial stdout", result["stdout"])
        self.assertIn("partial stderr", result["stderr"])

    def test_main_reports_missing_policy_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            missing_policy = Path(tempdir) / "missing-policy.json"
            stderr = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
            try:
                original_stderr = sys.stderr
                sys.stderr = stderr
                exit_code = audit.main(["--policy", str(missing_policy), "--collect-only"], runner=FakeRunner())
            finally:
                sys.stderr = original_stderr
            stderr.seek(0)
            message = stderr.read()
            stderr.close()

        self.assertEqual(2, exit_code)
        self.assertIn("[ERROR]", message)
        self.assertIn("missing-policy.json", message)
        self.assertNotIn("Traceback", message)

    def test_main_reports_collection_failure_without_traceback(self) -> None:
        class FailingCollectRunner(FakeRunner):
            def __call__(self, command: list[str], **kwargs: object) -> FakeCompletedProcess:
                self.calls.append({"command": command, "kwargs": kwargs})
                return FakeCompletedProcess(command, returncode=2, stdout="", stderr="collection failed")

        stderr = tempfile.TemporaryFile(mode="w+", encoding="utf-8")
        try:
            original_stderr = sys.stderr
            sys.stderr = stderr
            exit_code = audit.main(["--collect-only"], runner=FailingCollectRunner())
        finally:
            sys.stderr = original_stderr
        stderr.seek(0)
        message = stderr.read()
        stderr.close()

        self.assertEqual(1, exit_code)
        self.assertIn("[ERROR]", message)
        self.assertIn("pytest collection failed", message)
        self.assertNotIn("Traceback", message)

    def test_script_entrypoint_runs_collect_only(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "packages" / "verification-core" / "src" / "vgo_verify" / "test_baseline_audit.py"),
                "--collect-only",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )

        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("[INFO] total_nodes=", completed.stdout)


if __name__ == "__main__":
    unittest.main()
