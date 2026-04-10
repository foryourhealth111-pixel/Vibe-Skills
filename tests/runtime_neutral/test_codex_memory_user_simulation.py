from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
INSTALL_SCRIPT = REPO_ROOT / "install.sh"
RELEVANT_TOPIC = "quartz-scheduler"
RELEVANT_DEPENDENCY = "planner"
IRRELEVANT_TOPIC = "billing-export"
IRRELEVANT_DEPENDENCY = "audit-ledger"


def resolve_powershell() -> str | None:
    candidates = [
        shutil.which("pwsh"),
        shutil.which("pwsh.exe"),
        r"C:\Program Files\PowerShell\7\pwsh.exe",
        r"C:\Program Files\PowerShell\7-preview\pwsh.exe",
        shutil.which("powershell"),
        shutil.which("powershell.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(Path(candidate))
    return None


def load_json(path: str | Path) -> dict[str, object]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def create_fake_codex_command(directory: Path) -> Path:
    suffix = ".cmd" if os.name == "nt" else ""
    command_path = directory / f"codex{suffix}"
    if os.name == "nt":
        command_path.write_text(
            "@echo off\r\n"
            "setlocal EnableDelayedExpansion\r\n"
            "set OUT=\r\n"
            ":loop\r\n"
            "if \"%~1\"==\"\" goto done\r\n"
            "if /I \"%~1\"==\"-o\" (\r\n"
            "  set OUT=%~2\r\n"
            "  shift\r\n"
            "  shift\r\n"
            "  goto loop\r\n"
            ")\r\n"
            "shift\r\n"
            "goto loop\r\n"
            ":done\r\n"
            "if \"%OUT%\"==\"\" exit /b 2\r\n"
            "> \"%OUT%\" echo {\"status\":\"completed\",\"summary\":\"fake codex specialist executed\",\"verification_notes\":[\"fake native specialist executed\"],\"changed_files\":[],\"bounded_output_notes\":[\"fake codex adapter\"]}\r\n"
            "echo fake codex ok\r\n"
            "exit /b 0\r\n",
            encoding="utf-8",
        )
    else:
        command_path.write_text(
            "#!/usr/bin/env sh\n"
            "OUT=''\n"
            "while [ \"$#\" -gt 0 ]; do\n"
            "  case \"$1\" in\n"
            "    -o)\n"
            "      OUT=\"$2\"\n"
            "      shift 2\n"
            "      ;;\n"
            "    *)\n"
            "      shift\n"
            "      ;;\n"
            "  esac\n"
            "done\n"
            "if [ -z \"$OUT\" ]; then\n"
            "  exit 2\n"
            "fi\n"
            "printf '%s' '{\"status\":\"completed\",\"summary\":\"fake codex specialist executed\",\"verification_notes\":[\"fake native specialist executed\"],\"changed_files\":[],\"bounded_output_notes\":[\"fake codex adapter\"]}' > \"$OUT\"\n"
            "printf 'fake codex ok\\n'\n",
            encoding="utf-8",
        )
        command_path.chmod(command_path.stat().st_mode | stat.S_IXUSR)
    return command_path


def install_codex(target_root: Path, *, env: dict[str, str]) -> None:
    command = [
        "bash",
        str(INSTALL_SCRIPT),
        "--host",
        "codex",
        "--profile",
        "full",
        "--target-root",
        str(target_root),
    ]
    subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )


def run_installed_runtime(
    installed_root: Path,
    *,
    task: str,
    artifact_root: Path,
    env: dict[str, str],
    host_id: str = "codex",
) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    run_id = f"pytest-codex-memory-sim-{host_id}-{uuid.uuid4().hex[:8]}"
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-Command",
        (
            "& { "
            f"$result = & '{installed_root / 'scripts' / 'runtime' / 'invoke-vibe-runtime.ps1'}' "
            f"-Task '{task}' "
            "-Mode interactive_governed "
            f"-RunId '{run_id}' "
            f"-ArtifactRoot '{artifact_root}'; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    completed = subprocess.run(
        command,
        cwd=installed_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=True,
    )
    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        raise AssertionError(
            "installed invoke-vibe-runtime returned null payload. "
            f"stderr={completed.stderr.strip()}"
        )
    return json.loads(stdout)


def run_repo_governed_runtime(task: str, artifact_root: Path, env: dict[str, str] | None = None) -> dict[str, object]:
    shell = resolve_powershell()
    if shell is None:
        raise unittest.SkipTest("PowerShell executable not available in PATH")

    script_path = REPO_ROOT / "scripts" / "runtime" / "invoke-vibe-runtime.ps1"
    run_id = "pytest-codex-shared-memory-" + uuid.uuid4().hex[:10]
    command = [
        shell,
        "-NoLogo",
        "-NoProfile",
        "-Command",
        (
            "& { "
            f"$result = & '{script_path}' "
            f"-Task '{task}' "
            "-Mode interactive_governed "
            f"-RunId '{run_id}' "
            f"-ArtifactRoot '{artifact_root}'; "
            "$result | ConvertTo-Json -Depth 20 }"
        ),
    ]
    effective_env = os.environ.copy()
    if env:
        effective_env.update(env)
    effective_env["VGO_DISABLE_NATIVE_SPECIALIST_EXECUTION"] = "1"

    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=effective_env,
        check=True,
    )
    stdout = completed.stdout.strip()
    if stdout in ("", "null"):
        raise AssertionError(
            "invoke-vibe-runtime returned null payload. "
            f"stderr={completed.stderr.strip()}"
        )
    return json.loads(stdout)


def selected_capsule_text(context_pack: dict[str, object] | None) -> str:
    if not context_pack:
        return ""

    parts: list[str] = []
    for capsule in context_pack.get("selected_capsules") or []:
        parts.append(str(capsule.get("title") or ""))
        parts.extend(str(line) for line in capsule.get("summary_lines") or [])
    return "\n".join(part for part in parts if part).lower()


def extract_memory_metrics(payload: dict[str, object]) -> dict[str, object]:
    report = load_json(payload["summary"]["artifacts"]["memory_activation_report"])
    stage_by_name = {stage["stage"]: stage for stage in report["stages"]}
    requirement_context = stage_by_name["requirement_doc"]["context_injection"]
    plan_context = stage_by_name["xl_plan"]["context_injection"]
    execute_context = stage_by_name["plan_execute"]["context_injection"]
    backend_hits = [
        {
            "stage": stage["stage"],
            "owner": action["owner"],
            "status": action["status"],
            "item_count": int(action.get("item_count") or 0),
        }
        for stage in report["stages"]
        for action in stage.get("read_actions", [])
        if str(action.get("owner")) in {"Serena", "Cognee", "ruflo"}
        and str(action.get("status")) == "backend_read"
        and int(action.get("item_count") or 0) > 0
    ]

    return {
        "report": report,
        "stage_by_name": stage_by_name,
        "requirement_context": requirement_context,
        "plan_context": plan_context,
        "execute_context": execute_context,
        "selected_text": "\n".join(
            [
                selected_capsule_text(requirement_context),
                selected_capsule_text(plan_context),
                selected_capsule_text(execute_context),
            ]
        ).lower(),
        "backend_hit_count": len(backend_hits),
        "backend_hits": backend_hits,
        "requirement_text": Path(payload["summary"]["artifacts"]["requirement_doc"]).read_text(encoding="utf-8").lower(),
        "plan_text": Path(payload["summary"]["artifacts"]["execution_plan"]).read_text(encoding="utf-8").lower(),
    }


class CodexMemoryUserSimulationTests(unittest.TestCase):
    def _install_codex_context(self, root: Path, name: str) -> tuple[Path, Path, dict[str, str]]:
        target_root = root / name
        bridge_root = root / f"{name}-bridges"
        target_root.mkdir(parents=True, exist_ok=True)
        bridge_root.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["CODEX_HOME"] = str(target_root)
        env["VGO_CODEX_EXECUTABLE"] = str(create_fake_codex_command(bridge_root))
        install_codex(target_root, env=env)

        installed_root = target_root / "skills" / "vibe"
        self.assertTrue(installed_root.exists())
        return target_root, installed_root, env

    def _runtime_env(
        self,
        *,
        base_env: dict[str, str],
        target_root: Path,
        project_key: str,
        backend_root: Path | None = None,
    ) -> dict[str, str]:
        return {
            **base_env,
            "VCO_HOST_ID": "codex",
            "SERENA_PROJECT_KEY": project_key,
            "VIBE_MEMORY_BACKEND_ROOT": str(backend_root or (target_root / ".vibeskills" / "memory-backend")),
        }

    def _evaluate_installed_case(
        self,
        *,
        installed_root: Path,
        target_root: Path,
        base_env: dict[str, str],
        project_key: str,
        artifact_prefix: str,
        seed_tasks: list[str],
        follow_up_task: str,
        filler_tasks: list[str] | None = None,
        backend_root: Path | None = None,
    ) -> dict[str, object]:
        runtime_env = self._runtime_env(
            base_env=base_env,
            target_root=target_root,
            project_key=project_key,
            backend_root=backend_root,
        )

        for index, task in enumerate(seed_tasks):
            run_installed_runtime(
                installed_root,
                task=task,
                artifact_root=target_root / ".vibeskills" / f"{artifact_prefix}-seed-{index}",
                env=runtime_env,
            )
        for index, task in enumerate(filler_tasks or []):
            run_installed_runtime(
                installed_root,
                task=task,
                artifact_root=target_root / ".vibeskills" / f"{artifact_prefix}-filler-{index}",
                env=runtime_env,
            )

        payload = run_installed_runtime(
            installed_root,
            task=follow_up_task,
            artifact_root=target_root / ".vibeskills" / f"{artifact_prefix}-follow-up",
            env=runtime_env,
        )
        metrics = extract_memory_metrics(payload)
        metrics["payload"] = payload
        return metrics

    def test_codex_user_simulation_prefers_relevant_memory_and_keeps_injection_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            target_root, installed_root, base_env = self._install_codex_context(temp_root, "codex-user-sim")
            runtime_env = {
                **base_env,
                "VCO_HOST_ID": "codex",
                "SERENA_PROJECT_KEY": "pytest-codex-user-sim",
                "VIBE_MEMORY_BACKEND_ROOT": str(target_root / ".vibeskills" / "memory-backend"),
            }

            run_installed_runtime(
                installed_root,
                task="XL approved decision: keep quartz-scheduler runtime continuity and graph relationship between quartz-scheduler and planner. $vibe",
                artifact_root=target_root / ".vibeskills" / "memory-sim-relevant-seed",
                env=runtime_env,
            )
            run_installed_runtime(
                installed_root,
                task="XL approved decision: retain billing-export continuity and graph relationship between billing-export and audit-ledger. $vibe",
                artifact_root=target_root / ".vibeskills" / "memory-sim-irrelevant-seed",
                env=runtime_env,
            )
            follow_up = run_installed_runtime(
                installed_root,
                task="XL follow-up quartz-scheduler continuity review with planner dependency recall before the next implementation step. $vibe",
                artifact_root=target_root / ".vibeskills" / "memory-sim-follow-up",
                env=runtime_env,
            )

            report = load_json(follow_up["summary"]["artifacts"]["memory_activation_report"])
            stage_by_name = {stage["stage"]: stage for stage in report["stages"]}
            requirement_stage = stage_by_name["requirement_doc"]
            requirement_context = requirement_stage["context_injection"]
            execute_context = stage_by_name["plan_execute"]["context_injection"]

            selected_text = "\n".join(
                "\n".join(
                    [
                        str(capsule.get("title") or ""),
                        *[str(line) for line in capsule.get("summary_lines") or []],
                    ]
                )
                for capsule in requirement_context["selected_capsules"]
            ).lower()
            referenced_payloads: set[str] = set()
            for capsule in requirement_context["selected_capsules"]:
                expansion_ref = str(capsule.get("expansion_ref") or "")
                if "#" in expansion_ref:
                    referenced_payloads.add(expansion_ref.split("#", 1)[0])
            total_candidates = sum(
                int(load_json(path).get("capsule_count") or 0)
                for path in referenced_payloads
            )

            self.assertIn("quartz-scheduler", selected_text)
            self.assertNotIn("billing-export", selected_text)
            self.assertEqual("L2_capsule_summary", requirement_context["disclosure_level"])
            self.assertEqual("L3_evidence_pack", execute_context["disclosure_level"])
            self.assertLessEqual(
                len(requirement_context["selected_capsules"]),
                int(requirement_context["budget"]["top_k"]),
            )
            self.assertGreater(total_candidates, len(requirement_context["selected_capsules"]))

            requirement_text = Path(follow_up["summary"]["artifacts"]["requirement_doc"]).read_text(encoding="utf-8").lower()
            plan_text = Path(follow_up["summary"]["artifacts"]["execution_plan"]).read_text(encoding="utf-8").lower()
            self.assertIn("## memory context", requirement_text)
            self.assertIn("## memory context", plan_text)
            self.assertIn("quartz-scheduler", plan_text)

    def test_workspace_memory_is_shared_between_codex_and_claude_code_in_same_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            shared_env = {
                "VIBE_MEMORY_BACKEND_ROOT": str(temp_root / "backends"),
                "SERENA_PROJECT_KEY": "pytest-shared-workspace-hosts",
            }

            run_repo_governed_runtime(
                "XL approved decision: keep atlas-cache runtime continuity and graph relationship between atlas-cache and planner. $vibe",
                artifact_root=temp_root / "codex-seed",
                env={**shared_env, "VCO_HOST_ID": "codex"},
            )
            follow_up = run_repo_governed_runtime(
                "XL follow-up atlas-cache continuity review with planner dependency recall before the next step. $vibe",
                artifact_root=temp_root / "claude-follow-up",
                env={**shared_env, "VCO_HOST_ID": "claude-code"},
            )

            report = load_json(follow_up["summary"]["artifacts"]["memory_activation_report"])
            read_actions = [
                action
                for stage in report["stages"]
                for action in stage.get("read_actions", [])
            ]

            self.assertTrue(
                any(
                    str(action.get("status")) == "backend_read" and int(action.get("item_count") or 0) > 0
                    for action in read_actions
                )
            )

            requirement_text = Path(follow_up["summary"]["artifacts"]["requirement_doc"]).read_text(encoding="utf-8").lower()
            plan_text = Path(follow_up["summary"]["artifacts"]["execution_plan"]).read_text(encoding="utf-8").lower()
            self.assertIn("atlas-cache", requirement_text)
            self.assertIn("atlas-cache", plan_text)

    def test_workspace_memory_does_not_bleed_between_distinct_codex_workspaces(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            shared_backend_root = temp_root / "shared-backend-root"

            target_a, installed_a, env_a = self._install_codex_context(temp_root, "codex-workspace-a")
            target_b, installed_b, env_b = self._install_codex_context(temp_root, "codex-workspace-b")

            runtime_env_a = {
                **env_a,
                "VCO_HOST_ID": "codex",
                "SERENA_PROJECT_KEY": "pytest-workspace-isolation",
                "VIBE_MEMORY_BACKEND_ROOT": str(shared_backend_root),
            }
            runtime_env_b = {
                **env_b,
                "VCO_HOST_ID": "codex",
                "SERENA_PROJECT_KEY": "pytest-workspace-isolation",
                "VIBE_MEMORY_BACKEND_ROOT": str(shared_backend_root),
            }

            run_installed_runtime(
                installed_a,
                task="XL approved decision: keep orion-rewrite runtime continuity and graph relationship between orion-rewrite and reviewer. $vibe",
                artifact_root=target_a / ".vibeskills" / "workspace-a-seed",
                env=runtime_env_a,
            )
            follow_up = run_installed_runtime(
                installed_b,
                task="XL follow-up orion-rewrite continuity review with reviewer dependency recall before the next implementation step. $vibe",
                artifact_root=target_b / ".vibeskills" / "workspace-b-follow-up",
                env=runtime_env_b,
            )

            report = load_json(follow_up["summary"]["artifacts"]["memory_activation_report"])
            read_actions = [
                action
                for stage in report["stages"]
                for action in stage.get("read_actions", [])
            ]

            self.assertFalse(
                any(
                    str(action.get("status")) == "backend_read" and int(action.get("item_count") or 0) > 0
                    for action in read_actions
                )
            )
            self.assertTrue(any(str(action.get("status")) == "backend_read_empty" for action in read_actions))

    def test_quantitative_related_followup_hit_rate_meets_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            target_root, installed_root, base_env = self._install_codex_context(temp_root, "codex-hit-rate")
            seed_tasks = [
                f"XL approved decision: keep {RELEVANT_TOPIC} runtime continuity and graph relationship between {RELEVANT_TOPIC} and {RELEVANT_DEPENDENCY}. $vibe",
                f"XL approved decision: retain {IRRELEVANT_TOPIC} continuity and graph relationship between {IRRELEVANT_TOPIC} and {IRRELEVANT_DEPENDENCY}. $vibe",
            ]
            follow_up_tasks = [
                f"XL follow-up {RELEVANT_TOPIC} continuity review with {RELEVANT_DEPENDENCY} dependency recall before the next implementation step. $vibe",
                f"XL prepare {RELEVANT_TOPIC} execution plan using {RELEVANT_DEPENDENCY} continuity evidence before coding. $vibe",
                f"XL assess {RELEVANT_TOPIC} rollout risk with {RELEVANT_DEPENDENCY} linkage and prior continuity evidence before execution. $vibe",
                f"XL debug {RELEVANT_TOPIC} next step while preserving {RELEVANT_DEPENDENCY} continuity and prior relationship context. $vibe",
            ]

            hits = 0
            irrelevant_bleeds = 0
            for index, task in enumerate(follow_up_tasks):
                metrics = self._evaluate_installed_case(
                    installed_root=installed_root,
                    target_root=target_root,
                    base_env=base_env,
                    project_key=f"pytest-codex-hit-rate-{index}",
                    artifact_prefix=f"codex-hit-rate-{index}",
                    seed_tasks=seed_tasks,
                    follow_up_task=task,
                )
                if RELEVANT_TOPIC in str(metrics["selected_text"]) and int(metrics["backend_hit_count"]) >= 2:
                    hits += 1
                if IRRELEVANT_TOPIC in str(metrics["selected_text"]):
                    irrelevant_bleeds += 1

            hit_rate = hits / len(follow_up_tasks)
            bleed_rate = irrelevant_bleeds / len(follow_up_tasks)
            self.assertGreaterEqual(hit_rate, 1.0, {"hit_rate": hit_rate, "hits": hits})
            self.assertEqual(0.0, bleed_rate, {"bleed_rate": bleed_rate, "irrelevant_bleeds": irrelevant_bleeds})

    def test_quantitative_irrelevant_followup_false_recall_rate_stays_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            target_root, installed_root, base_env = self._install_codex_context(temp_root, "codex-false-recall")
            seed_tasks = [
                f"XL approved decision: keep {RELEVANT_TOPIC} runtime continuity and graph relationship between {RELEVANT_TOPIC} and {RELEVANT_DEPENDENCY}. $vibe",
            ]
            unrelated_follow_ups = [
                "Prepare nebularender release notes and quartzcatalog acceptance criteria without touching other domains. $vibe",
                "Draft harborinvoice rollout notes and lanternledger acceptance criteria without recalling prior runtime continuity. $vibe",
                "Write willowqueue documentation and emberbatch success checks with no dependency recall. $vibe",
                "Plan skylinemeter cleanup guidance and riveraudit checklists without revisiting old execution history. $vibe",
            ]

            false_recalls = 0
            for index, task in enumerate(unrelated_follow_ups):
                metrics = self._evaluate_installed_case(
                    installed_root=installed_root,
                    target_root=target_root,
                    base_env=base_env,
                    project_key=f"pytest-codex-false-recall-{index}",
                    artifact_prefix=f"codex-false-recall-{index}",
                    seed_tasks=seed_tasks,
                    follow_up_task=task,
                )
                if int(metrics["backend_hit_count"]) > 0 or int(metrics["plan_context"]["capsule_count"]) > 0:
                    false_recalls += 1

            false_recall_rate = false_recalls / len(unrelated_follow_ups)
            self.assertEqual(
                0.0,
                false_recall_rate,
                {"false_recall_rate": false_recall_rate, "false_recalls": false_recalls},
            )

    def test_quantitative_recall_survives_intervening_turn_noise(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            target_root, installed_root, base_env = self._install_codex_context(temp_root, "codex-decay")
            seed_tasks = [
                f"XL approved decision: keep {RELEVANT_TOPIC} runtime continuity and graph relationship between {RELEVANT_TOPIC} and {RELEVANT_DEPENDENCY}. $vibe",
            ]
            filler_template = (
                "XL approved decision: retain {topic} continuity and graph relationship between {topic} and {dependency}. $vibe"
            )
            filler_pairs = [
                ("nebula-cache", "audit-anchor"),
                ("signal-router", "release-anchor"),
                ("harbor-metrics", "batch-window"),
            ]

            retained_hits = 0
            depths = [0, 1, 3]
            for depth in depths:
                filler_tasks = [
                    filler_template.format(topic=topic, dependency=dependency)
                    for topic, dependency in filler_pairs[:depth]
                ]
                metrics = self._evaluate_installed_case(
                    installed_root=installed_root,
                    target_root=target_root,
                    base_env=base_env,
                    project_key=f"pytest-codex-decay-{depth}",
                    artifact_prefix=f"codex-decay-{depth}",
                    seed_tasks=seed_tasks,
                    follow_up_task=(
                        f"XL follow-up {RELEVANT_TOPIC} continuity review with {RELEVANT_DEPENDENCY} dependency recall "
                        "before the next implementation step. $vibe"
                    ),
                    filler_tasks=filler_tasks,
                )
                if RELEVANT_TOPIC in str(metrics["selected_text"]) and int(metrics["backend_hit_count"]) >= 2:
                    retained_hits += 1

            retention_rate = retained_hits / len(depths)
            self.assertEqual(1.0, retention_rate, {"retention_rate": retention_rate, "retained_hits": retained_hits})

    def test_quantitative_cross_workspace_leak_rate_stays_zero(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            shared_backend_root = temp_root / "shared-backend-root"

            target_a, installed_a, env_a = self._install_codex_context(temp_root, "codex-bench-workspace-a")
            target_b, installed_b, env_b = self._install_codex_context(temp_root, "codex-bench-workspace-b")

            topic_pairs = [
                ("orion-rewrite", "reviewer"),
                ("helix-cache", "planner"),
                ("signal-router", "release-anchor"),
            ]

            leaks = 0
            for index, (topic, dependency) in enumerate(topic_pairs):
                metrics_a = self._runtime_env(
                    base_env=env_a,
                    target_root=target_a,
                    project_key=f"pytest-codex-leak-{index}",
                    backend_root=shared_backend_root,
                )
                metrics_b = self._runtime_env(
                    base_env=env_b,
                    target_root=target_b,
                    project_key=f"pytest-codex-leak-{index}",
                    backend_root=shared_backend_root,
                )
                run_installed_runtime(
                    installed_a,
                    task=f"XL approved decision: keep {topic} runtime continuity and graph relationship between {topic} and {dependency}. $vibe",
                    artifact_root=target_a / ".vibeskills" / f"workspace-a-bench-seed-{index}",
                    env=metrics_a,
                )
                payload = run_installed_runtime(
                    installed_b,
                    task=f"XL follow-up {topic} continuity review with {dependency} dependency recall before the next implementation step. $vibe",
                    artifact_root=target_b / ".vibeskills" / f"workspace-b-bench-follow-up-{index}",
                    env=metrics_b,
                )
                metrics = extract_memory_metrics(payload)
                if int(metrics["backend_hit_count"]) > 0 or int(metrics["plan_context"]["capsule_count"]) > 0:
                    leaks += 1

            leak_rate = leaks / len(topic_pairs)
            self.assertEqual(0.0, leak_rate, {"leak_rate": leak_rate, "leaks": leaks})


if __name__ == "__main__":
    unittest.main()
