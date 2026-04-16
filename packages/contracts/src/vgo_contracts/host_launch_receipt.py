from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

HOST_LAUNCH_RECEIPT_FILENAME = "host-launch-receipt.json"


@dataclass(slots=True)
class HostLaunchReceipt:
    host_id: str
    entry_id: str
    launch_mode: str
    launcher_path: str
    requested_stage_stop: str | None
    requested_grade_floor: str | None
    runtime_entrypoint: str
    run_id: str
    created_at: str
    launch_status: str

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def model_validate(cls, payload: dict[str, Any]) -> "HostLaunchReceipt":
        return cls(
            host_id=str(payload["host_id"]),
            entry_id=str(payload["entry_id"]),
            launch_mode=str(payload["launch_mode"]),
            launcher_path=str(payload["launcher_path"]),
            requested_stage_stop=payload.get("requested_stage_stop"),
            requested_grade_floor=payload.get("requested_grade_floor"),
            runtime_entrypoint=str(payload["runtime_entrypoint"]),
            run_id=str(payload["run_id"]),
            created_at=str(payload["created_at"]),
            launch_status=str(payload["launch_status"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


def resolve_host_launch_receipt_path(path: str | Path) -> Path:
    resolved = Path(path).resolve()
    if resolved.name == HOST_LAUNCH_RECEIPT_FILENAME:
        return resolved
    return resolved / HOST_LAUNCH_RECEIPT_FILENAME


def write_host_launch_receipt(path: str | Path, receipt: HostLaunchReceipt) -> Path:
    receipt_path = resolve_host_launch_receipt_path(path)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt_path


def read_host_launch_receipt(path: str | Path) -> HostLaunchReceipt:
    receipt_path = resolve_host_launch_receipt_path(path)
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid host launch receipt payload at: {receipt_path}")
    return HostLaunchReceipt.model_validate(payload)
