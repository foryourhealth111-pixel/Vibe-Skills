from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

from ._io import write_json_atomic


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class RunState:
    run_id: str
    task_id: str
    state: str
    continuation_mode: str
    accepted_revision_count: int
    active_work_unit: str | None
    completed_work_units: tuple[str, ...]
    failed_work_units: tuple[str, ...]
    reused_work_units: tuple[str, ...]
    superseded_work_units: tuple[str, ...]
    last_transition: str

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


def write_run_state(
    path: Path,
    *,
    run_id: str,
    task_id: str,
    state: str,
    continuation_mode: str = "fresh",
    accepted_revision_count: int = 0,
    active_work_unit: str | None = None,
    completed_work_units: tuple[str, ...] = (),
    failed_work_units: tuple[str, ...] = (),
    reused_work_units: tuple[str, ...] = (),
    superseded_work_units: tuple[str, ...] = (),
) -> RunState:
    run_state = RunState(
        run_id=run_id,
        task_id=task_id,
        state=state,
        continuation_mode=continuation_mode,
        accepted_revision_count=accepted_revision_count,
        active_work_unit=active_work_unit,
        completed_work_units=completed_work_units,
        failed_work_units=failed_work_units,
        reused_work_units=reused_work_units,
        superseded_work_units=superseded_work_units,
        last_transition=_utc_now(),
    )
    write_json_atomic(path, run_state.model_dump())
    return run_state


def load_run_state(path: Path) -> RunState:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return RunState(
        run_id=str(payload["run_id"]),
        task_id=str(payload["task_id"]),
        state=str(payload["state"]),
        continuation_mode=str(payload.get("continuation_mode") or "fresh"),
        accepted_revision_count=int(payload.get("accepted_revision_count", 0)),
        active_work_unit=(str(payload["active_work_unit"]) if payload.get("active_work_unit") is not None else None),
        completed_work_units=tuple(str(value) for value in payload.get("completed_work_units", [])),
        failed_work_units=tuple(str(value) for value in payload.get("failed_work_units", [])),
        reused_work_units=tuple(str(value) for value in payload.get("reused_work_units", [])),
        superseded_work_units=tuple(str(value) for value in payload.get("superseded_work_units", [])),
        last_transition=str(payload["last_transition"]),
    )
