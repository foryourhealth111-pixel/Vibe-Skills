from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if os.name == "nt":
    import msvcrt
else:
    import fcntl


CONTRACTS_SRC = Path(__file__).resolve().parents[2] / "packages" / "contracts" / "src"
if CONTRACTS_SRC.is_dir() and str(CONTRACTS_SRC) not in sys.path:
    sys.path.insert(0, str(CONTRACTS_SRC))

from vgo_contracts.workspace_memory_identity import workspace_memory_id  # noqa: E402
from vgo_contracts.live_governance_contract import (  # noqa: E402
    LiveGovernanceContract,
    load_live_governance_contract_file,
)


LANE_KIND = {
    "serena": ("project_decision_gate", "architecture_decision"),
    "ruflo": ("handoff_card", "short_term_semantic_context"),
    "cognee": ("entity_relation_ingest", "long_term_graph_context"),
}

LANE_OWNER = {
    "serena": "Serena",
    "ruflo": "ruflo",
    "cognee": "Cognee",
}

WORKSPACE_MEMORY_IDENTITY_SCOPE = "workspace"
WORKSPACE_MEMORY_DRIVER_CONTRACT = "workspace_shared_memory_v1"
WORKSPACE_MEMORY_LOGICAL_OWNERS = ["state_store", "serena", "ruflo", "cognee"]

NOISE_TOKENS = {
    "tmp",
    "temp",
    "telemetry",
    "heartbeat",
    "trace",
    "debug",
    "metric",
    "metrics",
    "log",
    "logs",
    "cache",
    "latency",
}

SIGNAL_TOKENS = {
    "approved",
    "decision",
    "handoff",
    "relation",
    "specified_by",
    "planned_in",
    "executed_as",
    "compatibility",
    "continuity",
}

STOP_TOKENS = {
    "approved",
    "about",
    "after",
    "along",
    "and",
    "around",
    "asks",
    "because",
    "before",
    "between",
    "codex",
    "context",
    "continuity",
    "debug",
    "decision",
    "dependencies",
    "dependency",
    "evidence",
    "execution",
    "follow-up",
    "from",
    "graph",
    "implementation",
    "into",
    "keep",
    "next",
    "onto",
    "over",
    "plan",
    "planner",
    "planning",
    "preserving",
    "prior",
    "prepare",
    "recall",
    "relationship",
    "retain",
    "review",
    "runtime",
    "step",
    "than",
    "that",
    "their",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "under",
    "until",
    "user",
    "vibe",
    "vibeskills",
    "what",
    "when",
    "where",
    "while",
    "them",
    "then",
    "which",
    "with",
    "within",
    "without",
    "would",
    "were",
    "whose",
    "your",
    "for",
    "the",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_parent(path)
    content = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")


def write_jsonl_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    ensure_parent(path)
    content = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    if content:
        content += "\n"

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(path.parent), delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


class PlaneLock:
    def __init__(self, plane_path: Path) -> None:
        self._lock_path = Path(f"{plane_path}.lock")
        self._handle = None

    def __enter__(self) -> "PlaneLock":
        ensure_parent(self._lock_path)
        self._handle = self._lock_path.open("a+", encoding="utf-8")
        if os.name == "nt":
            self._handle.seek(0)
            msvcrt.locking(self._handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._handle is None:
            return
        try:
            if os.name == "nt":
                self._handle.seek(0)
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None


def tokenize(text: str, *, filter_stop_tokens: bool = True) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9_/-]{3,}", text.lower())
        if token and (not filter_stop_tokens or token not in STOP_TOKENS)
    }


def score_record(query: str, record: dict[str, Any]) -> int:
    query_tokens = tokenize(query)
    haystack = " ".join(
        [
            str(record.get("summary") or ""),
            " ".join(str(v) for v in record.get("keywords") or []),
            " ".join(str(v) for v in record.get("items") or []),
            " ".join(str(v) for v in record.get("evidence_paths") or []),
            str(record.get("relation") or ""),
            str(record.get("source") or ""),
            str(record.get("target") or ""),
        ]
    )
    return len(query_tokens & tokenize(haystack))


def dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_id = str(row.get("record_id") or "")
        if not row_id:
            row_id = hashlib.sha256(json.dumps(row, sort_keys=True).encode("utf-8")).hexdigest()[:16]
            row["record_id"] = row_id
        by_id[row_id] = row
    return list(by_id.values())


def load_workspace_memory_policy_bundle(repo_root: Path) -> dict[str, Any]:
    config_root = repo_root / "config"
    bundle: dict[str, Any] = {}
    for name in (
        "memory-ingest-policy",
        "memory-disclosure-policy",
        "workspace-memory-plane",
    ):
        path = config_root / f"{name}.json"
        bundle[name.replace("-", "_")] = load_json(path) if path.exists() else {}
    return bundle


def _relative_runtime_contract(
    repo_root: Path,
    policy_bundle: dict[str, Any] | None,
) -> dict[str, Any]:
    contract_path = repo_root / "config" / "live-document-contract.json"
    policy_bundle = policy_bundle or {}
    if "live_document_contract" in policy_bundle:
        raw_contract = policy_bundle["live_document_contract"]
        if not isinstance(raw_contract, dict):
            raise ValueError(
                f"live governance artifact contract is required: {contract_path}: "
                "contract payload must be an object"
            )
        try:
            contract = LiveGovernanceContract.model_validate(raw_contract)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"live governance artifact contract is required: {contract_path}: {exc}"
            ) from exc
    elif contract_path.is_file():
        try:
            contract = load_live_governance_contract_file(contract_path)
        except (OSError, TypeError, ValueError) as exc:
            raise ValueError(
                f"live governance artifact contract is required: {contract_path}: {exc}"
            ) from exc
    else:
        raise ValueError(
            f"live governance artifact contract is required: {contract_path}"
        )
    sink = contract.artifact_sink
    legacy_roots = sink.legacy_documentation_root_map
    session_receipts = sink.session_receipts.model_dump()
    return {
        "artifact_sink_root": sink.root,
        "legacy_requirement_root": legacy_roots["requirement"],
        "legacy_execution_plan_root": legacy_roots["plan"],
        "legacy_projection_root": sink.legacy_projection_root,
        "artifact_paths": sink.artifact_path_map,
        "primary_document_paths": sink.primary_document_path_map,
        "manifest_path": sink.manifest_path,
        "legacy_compatibility_path": sink.legacy_compatibility_path,
        "session_root": session_receipts["root"],
        "session_receipts": session_receipts,
        "legacy_documentation_roots": list(sink.legacy_documentation_roots),
        "legacy_removal_release": sink.legacy_removal_release,
        "legacy_write_mode": sink.legacy_write_mode,
    }


def ensure_workspace_descriptor(repo_root: Path, policy_bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    workspace_root = repo_root.resolve()
    sidecar_root = workspace_root / ".vibeskills"
    descriptor_path = sidecar_root / "project.json"
    if descriptor_path.exists():
        descriptor = load_json(descriptor_path)
    else:
        descriptor = {
            "schema_version": 1,
            "brand": "vibeskills",
            "generated_at": utc_now(),
            "workspace_root": str(workspace_root),
            "workspace_sidecar_root": str(sidecar_root),
            "project_descriptor_path": str(descriptor_path),
            "default_artifact_root": str(sidecar_root),
            "relative_runtime_contract": _relative_runtime_contract(
                workspace_root,
                policy_bundle,
            ),
            "host_sidecar_root": None,
        }
    descriptor["workspace_root"] = str(workspace_root)
    descriptor["workspace_sidecar_root"] = str(sidecar_root)
    descriptor["project_descriptor_path"] = str(descriptor_path)
    descriptor["default_artifact_root"] = str(sidecar_root)
    descriptor["relative_runtime_contract"] = _relative_runtime_contract(
        workspace_root,
        policy_bundle,
    )
    descriptor["memory_plane"] = {
        "identity_root": descriptor["project_descriptor_path"],
        "identity_scope": WORKSPACE_MEMORY_IDENTITY_SCOPE,
        "driver_contract": WORKSPACE_MEMORY_DRIVER_CONTRACT,
        "logical_owners": list(WORKSPACE_MEMORY_LOGICAL_OWNERS),
    }
    descriptor.setdefault("host_sidecar_root", None)
    write_json(descriptor_path, descriptor)
    return descriptor


def resolve_plane_path(descriptor: dict[str, Any]) -> Path:
    return Path(str(descriptor["workspace_sidecar_root"])) / "memory" / "workspace-memory-plane.jsonl"


def workspace_memory_projection(descriptor: dict[str, Any], plane_path: Path) -> dict[str, Any]:
    workspace_root = str(descriptor["workspace_root"])
    identity_root = str(descriptor["project_descriptor_path"])
    return {
        "schema_version": 1,
        "workspace_root": workspace_root,
        "workspace_sidecar_root": str(descriptor["workspace_sidecar_root"]),
        "descriptor_path": str(descriptor["project_descriptor_path"]),
        "workspace_id": workspace_memory_id(identity_root),
        "plane_path": str(plane_path),
    }


def is_temp_like_path(value: str) -> bool:
    normalized = value.replace("\\", "/").lower()
    return (
        normalized.startswith("/tmp/")
        or normalized.startswith("/var/tmp/")
        or "/.tmp/" in normalized
        or "/tmp/" in normalized
        or "/temp/" in normalized
        or "/cache/" in normalized
        or "/logs/" in normalized
        or normalized.endswith(".log")
    )


def classify_noise(record: dict[str, Any]) -> str | None:
    lane = str(record.get("lane") or "")
    if lane == "serena" and not str(record.get("summary") or "").strip():
        return "empty_summary"
    if lane == "ruflo" and not str(record.get("summary") or "").strip() and not record.get("items"):
        return "empty_handoff"
    if lane == "cognee":
        fields = [str(record.get("source") or "").strip(), str(record.get("relation") or "").strip(), str(record.get("target") or "").strip()]
        if any(not value for value in fields):
            return "empty_relation"

    text_parts = [
        str(record.get("summary") or ""),
        str(record.get("source") or ""),
        str(record.get("relation") or ""),
        str(record.get("target") or ""),
        " ".join(str(v) for v in record.get("items") or []),
        " ".join(str(v) for v in record.get("keywords") or []),
        " ".join(str(v) for v in record.get("evidence_paths") or []),
    ]
    raw_tokens = tokenize(" ".join(text_parts), filter_stop_tokens=False)
    if not raw_tokens:
        return "empty_payload"
    if raw_tokens & SIGNAL_TOKENS:
        return None
    tokens = {token for token in raw_tokens if token not in STOP_TOKENS}
    if not tokens:
        return "noise_only_tokens"
    noise_token_count = len(tokens & NOISE_TOKENS)
    signal_token_count = len(tokens - NOISE_TOKENS)
    noise_ratio = float(noise_token_count) / float(len(tokens)) if tokens else 0.0
    evidence_paths = [str(v) for v in record.get("evidence_paths") or [] if str(v).strip()]
    all_temp_like = bool(evidence_paths) and all(is_temp_like_path(path) for path in evidence_paths)
    if signal_token_count == 0:
        return "noise_only_tokens"
    if all_temp_like and signal_token_count <= 2 and noise_token_count >= 2:
        return "temp_path_noise"
    if all_temp_like and noise_ratio >= 0.5 and signal_token_count <= 4:
        return "temp_path_telemetry_noise"
    return None


def _serena_records(payload: dict[str, Any], project_key: str | None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for decision in payload.get("decisions") or []:
        if not isinstance(decision, dict):
            continue
        record_basis = json.dumps(
            {
                "lane": "serena",
                "project_key": project_key,
                "summary": decision.get("summary"),
                "evidence_paths": decision.get("evidence_paths"),
            },
            sort_keys=True,
        )
        records.append(
            {
                "record_id": hashlib.sha256(record_basis.encode("utf-8")).hexdigest()[:16],
                "lane": "serena",
                "kind": "architecture_decision",
                "signal_type": "architecture_decision",
                "project_key": project_key,
                "summary": str(decision.get("summary") or "").strip(),
                "evidence_paths": [str(v) for v in decision.get("evidence_paths") or [] if str(v).strip()],
                "keywords": [str(v) for v in decision.get("keywords") or [] if str(v).strip()],
                "updated_at": utc_now(),
            }
        )
    return records


def _ruflo_records(payload: dict[str, Any], project_key: str | None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for card in payload.get("cards") or []:
        if not isinstance(card, dict):
            continue
        record_basis = json.dumps(
            {
                "lane": "ruflo",
                "project_key": project_key,
                "run_id": payload.get("run_id"),
                "summary": card.get("summary"),
                "scope": card.get("scope"),
            },
            sort_keys=True,
        )
        records.append(
            {
                "record_id": hashlib.sha256(record_basis.encode("utf-8")).hexdigest()[:16],
                "lane": "ruflo",
                "kind": "handoff_card",
                "signal_type": "handoff_card",
                "project_key": project_key,
                "scope": str(card.get("scope") or "xl"),
                "summary": str(card.get("summary") or "").strip(),
                "items": [str(v) for v in card.get("items") or [] if str(v).strip()],
                "evidence_paths": [str(v) for v in card.get("evidence_paths") or [] if str(v).strip()],
                "keywords": [str(v) for v in card.get("keywords") or [] if str(v).strip()],
                "run_id": str(payload.get("run_id") or ""),
                "updated_at": utc_now(),
            }
        )
    return records


def _cognee_records(payload: dict[str, Any], project_key: str | None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for relation in payload.get("relations") or []:
        if not isinstance(relation, dict):
            continue
        record_basis = json.dumps(
            {
                "lane": "cognee",
                "project_key": project_key,
                "source": relation.get("source"),
                "relation": relation.get("relation"),
                "target": relation.get("target"),
            },
            sort_keys=True,
        )
        records.append(
            {
                "record_id": hashlib.sha256(record_basis.encode("utf-8")).hexdigest()[:16],
                "lane": "cognee",
                "kind": "entity_relation_ingest",
                "signal_type": "entity_relation_ingest",
                "project_key": project_key,
                "source": str(relation.get("source") or "").strip(),
                "relation": str(relation.get("relation") or "").strip(),
                "target": str(relation.get("target") or "").strip(),
                "evidence_paths": [str(v) for v in relation.get("evidence_paths") or [] if str(v).strip()],
                "keywords": [str(v) for v in relation.get("keywords") or [] if str(v).strip()],
                "updated_at": utc_now(),
            }
        )
    return records


def build_lane_records(lane: str, payload: dict[str, Any], project_key: str | None) -> list[dict[str, Any]]:
    if lane == "serena":
        return _serena_records(payload, project_key)
    if lane == "ruflo":
        return _ruflo_records(payload, project_key)
    return _cognee_records(payload, project_key)


def format_read_items(lane: str, ranked: list[dict[str, Any]], top_k: int) -> list[str]:
    if lane == "serena":
        return [
            f"Serena decision: {row.get('summary')} (evidence: {', '.join(row.get('evidence_paths') or [])})"
            for row in ranked
            if row.get("_score", 0) > 0
        ]
    if lane == "ruflo":
        return [
            f"ruflo handoff: {row.get('summary')} (scope: {row.get('scope')})"
            for row in ranked
            if row.get("_score", 0) > 0
        ]
    return [
        f"Cognee relation: {row.get('source')} {row.get('relation')} {row.get('target')}"
        for row in ranked
        if row.get("_score", 0) > 0
    ]


def read_ranked_rows(
    plane_path: Path,
    *,
    lane: str,
    project_key: str | None,
    query: str,
    top_k: int,
) -> list[dict[str, Any]]:
    rows = load_jsonl(plane_path)
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("lane") or "") != lane:
            continue
        if str(row.get("kind") or "") not in LANE_KIND[lane]:
            continue
        if project_key and str(row.get("project_key") or "") != project_key:
            continue
        row = dict(row)
        row["_score"] = score_record(query, row)
        filtered.append(row)
    filtered.sort(key=lambda item: (item["_score"], str(item.get("updated_at") or "")), reverse=True)
    return filtered[:top_k]


def build_capsules(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    capsules: list[dict[str, Any]] = []
    for row in rows:
        capsules.append(
            {
                "capsule_id": str(row.get("record_id") or ""),
                "owner": LANE_OWNER.get(str(row.get("lane") or ""), "state_store"),
                "lane": str(row.get("lane") or ""),
                "kind": str(row.get("kind") or ""),
                "disclosure_level": "bounded",
                "summary": str(row.get("summary") or row.get("relation") or ""),
                "updated_at": str(row.get("updated_at") or ""),
            }
        )
    return capsules


def write_response(
    response_path: Path,
    *,
    ok: bool,
    status: str,
    lane: str,
    store_path: Path,
    project_key: str | None,
    project_key_source: str | None,
    items: list[str],
    capsules: list[dict[str, Any]],
    suppressed_count: int,
    workspace_plane: dict[str, Any],
    driver_mode: str,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "ok": ok,
        "status": status,
        "lane": lane,
        "store_path": str(store_path),
        "project_key": project_key,
        "project_key_source": project_key_source,
        "item_count": len(items),
        "items": items,
        "capsule_count": len(capsules),
        "capsules": capsules,
        "suppressed_count": suppressed_count,
        "workspace_memory_plane": workspace_plane,
        "driver_mode": driver_mode,
        "generated_at": utc_now(),
    }
    if extra:
        payload.update(extra)
    write_json(response_path, payload)


def execute(
    *,
    lane: str,
    action: str,
    repo_root: Path,
    payload_path: Path,
    response_path: Path,
    project_key: str | None,
    driver_mode: str,
) -> int:
    payload = load_json(payload_path)
    policy_bundle = load_workspace_memory_policy_bundle(repo_root)
    descriptor = ensure_workspace_descriptor(repo_root, policy_bundle=policy_bundle)
    plane_path = resolve_plane_path(descriptor)
    ensure_parent(plane_path)
    workspace_plane = workspace_memory_projection(descriptor, plane_path)
    project_key_source = str(payload.get("project_key_source") or ("workspace_plane" if project_key else "")) or None

    status = "guarded_no_write"
    items: list[str] = []
    capsules: list[dict[str, Any]] = []
    suppressed_count = 0

    if action == "read":
        if lane == "serena" and not project_key:
            status = "deferred_no_project_key"
        else:
            top_k = int(payload.get("top_k") or 2)
            ranked = read_ranked_rows(
                plane_path,
                lane=lane,
                project_key=project_key,
                query=str(payload.get("task") or ""),
                top_k=top_k,
            )
            items = format_read_items(lane, ranked, top_k)
            status = "backend_read" if items else "backend_read_empty"
            capsules = build_capsules(ranked[: len(items) if items else 0])
    else:
        candidate_records = build_lane_records(lane, payload, project_key)
        if not candidate_records or (lane == "serena" and not project_key):
            status = "guarded_no_write"
        else:
            admitted: list[dict[str, Any]] = []
            for record in candidate_records:
                reason = classify_noise(record)
                if reason:
                    suppressed_count += 1
                    continue
                admitted.append(record)

            if not admitted:
                status = "guarded_noise_suppressed" if suppressed_count > 0 else "guarded_no_write"
            else:
                with PlaneLock(plane_path):
                    rows = load_jsonl(plane_path)
                    rows.extend(admitted)
                    write_jsonl_atomic(plane_path, dedupe_rows(rows))
                capsules = build_capsules(admitted)
                if lane == "serena":
                    items = [f"Persisted Serena decision: {row.get('summary')}" for row in admitted]
                elif lane == "ruflo":
                    items = [f"Persisted ruflo handoff card: {row.get('summary')}" for row in admitted]
                else:
                    items = [
                        f"Persisted Cognee relation: {row.get('source')} {row.get('relation')} {row.get('target')}"
                        for row in admitted
                    ]
                status = "backend_write_with_noise_suppressed" if suppressed_count > 0 else "backend_write"

    write_response(
        response_path,
        ok=status.startswith("backend_"),
        status=status,
        lane=lane,
        store_path=plane_path,
        project_key=project_key,
        project_key_source=project_key_source,
        items=items,
        capsules=capsules,
        suppressed_count=suppressed_count,
        workspace_plane=workspace_plane,
        driver_mode=driver_mode,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", required=True, choices=["serena", "ruflo", "cognee"])
    parser.add_argument("--action", required=True, choices=["read", "write"])
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--session-root", required=True)
    parser.add_argument("--store-path", required=True)
    parser.add_argument("--payload-path", required=True)
    parser.add_argument("--response-path", required=True)
    parser.add_argument("--project-key")
    parser.add_argument("--driver-mode", default="workspace_broker")
    args = parser.parse_args()

    return execute(
        lane=args.lane,
        action=args.action,
        repo_root=Path(args.repo_root),
        payload_path=Path(args.payload_path),
        response_path=Path(args.response_path),
        project_key=args.project_key,
        driver_mode=str(args.driver_mode),
    )


if __name__ == "__main__":
    raise SystemExit(main())
