from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "config" / "governed-evolution-artifact-policy.json"


def test_governed_evolution_policy_uses_step_artifact_field_structure() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    assert policy["version"] >= 1
    assert policy["policy_id"] == "governed-evolution-artifact-policy-v4"
    assert set(policy["steps"].keys()) == {"observation", "proposal", "readiness"}

    for step_name, step in policy["steps"].items():
        assert isinstance(step, dict)
        assert step, f"{step_name} must declare artifact files"
        for file_name, artifact in step.items():
            assert file_name.endswith((".json", ".md")), file_name
            assert "desc" in artifact, file_name
            assert "important_field" in artifact, file_name
            assert "units" in artifact, file_name
            assert isinstance(artifact["units"], dict), file_name
            assert "artifact_dependent_fields" in artifact, file_name


def test_governed_evolution_policy_explicitly_declares_stage_profiles() -> None:
    policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    profiles = policy["stop_stage_profiles"]
    assert set(profiles.keys()) == {"requirement_doc", "xl_plan", "phase_cleanup"}

    for profile_name, profile in profiles.items():
        steps = profile["steps"]
        assert set(steps.keys()) == {"observation", "proposal", "readiness"}, profile_name
        for step_name, step in steps.items():
            assert "enabled_artifacts" in step, f"{profile_name}.{step_name}"
            assert isinstance(step["enabled_artifacts"], list), f"{profile_name}.{step_name}"
            for file_name in step["enabled_artifacts"]:
                assert file_name.endswith((".json", ".md")), f"{profile_name}.{step_name}:{file_name}"
