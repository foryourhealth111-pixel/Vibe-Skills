from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PACK_MANIFEST = REPO_ROOT / "config" / "pack-manifest.json"
TERMINOLOGY_DOC = REPO_ROOT / "docs" / "governance" / "terminology-governance.md"
PUBLIC_DOCS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "README.zh.md",
]

DEPRECATED_ACTIVE_PATTERNS = [
    r"\bprimary route\b",
    r"\bprimary skill\b",
    r"\bsecondary skill\b",
    r"\bdirect owner\b",
    r"\broute owner\b",
    r"\bstage assistant\b",
    r"\bspecialist skills\b",
    r"\bspecialist Skills\b",
    "主路由",
    "主路线",
    "主技能",
    "次技能",
    "阶段助手",
    "辅助专家",
    "咨询专家",
    "专家助手",
]


def load_manifest() -> dict[str, object]:
    return json.loads(PACK_MANIFEST.read_text(encoding="utf-8-sig"))


def test_active_pack_manifest_uses_only_skill_candidates() -> None:
    manifest = load_manifest()
    packs = manifest.get("packs")
    assert isinstance(packs, list)
    assert packs

    for pack in packs:
        assert isinstance(pack, dict)
        pack_id = str(pack.get("id") or "")
        assert pack_id
        assert "route_authority_candidates" not in pack, pack_id
        assert "stage_assistant_candidates" not in pack, pack_id
        skill_candidates = pack.get("skill_candidates")
        assert isinstance(skill_candidates, list), pack_id
        assert skill_candidates, pack_id
        assert all(isinstance(item, str) and item.strip() for item in skill_candidates), pack_id


def test_pack_defaults_point_to_skill_candidates() -> None:
    manifest = load_manifest()
    for pack in manifest["packs"]:
        pack_id = str(pack["id"])
        candidates = set(pack.get("skill_candidates") or [])
        defaults = pack.get("defaults_by_task") or {}
        assert isinstance(defaults, dict), pack_id
        for task_type, skill_id in defaults.items():
            assert skill_id in candidates, f"{pack_id}:{task_type}:{skill_id}"


def test_terminology_governance_doc_exists_and_defines_active_model() -> None:
    text = TERMINOLOGY_DOC.read_text(encoding="utf-8")
    assert "skill_candidates -> skill_routing.selected -> skill_execution_lock -> selected_skill_execution -> skill_usage" in text
    assert "`skill_candidates`" in text
    assert "`skill_routing.selected`" in text
    assert "`skill_execution_lock`" in text
    assert "`selected_skill_execution`" in text
    assert "`skill_usage.used`" in text
    assert "`skill_usage.unused`" in text
    assert "`skill_usage.evidence`" in text
    assert "Retired Context" in text


def test_public_docs_do_not_use_deprecated_routing_terms_as_active_language() -> None:
    failures: list[str] = []
    for path in PUBLIC_DOCS:
        text = path.read_text(encoding="utf-8")
        for pattern in DEPRECATED_ACTIVE_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                failures.append(f"{path.relative_to(REPO_ROOT)} contains {pattern!r}")
    assert failures == []
