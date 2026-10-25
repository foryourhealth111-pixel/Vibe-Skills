from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from vgo_contracts.workspace_memory_identity import workspace_memory_id

from .workspace_memory_schema import (
    WORKSPACE_MEMORY_DRIVER_CONTRACT,
    WORKSPACE_MEMORY_IDENTITY_ROOT,
    WORKSPACE_MEMORY_IDENTITY_SCOPE,
)


@dataclass(frozen=True, slots=True)
class WorkspaceMemoryIdentity:
    workspace_id: str
    workspace_root: str
    identity_root: str
    identity_scope: str
    driver_contract: str

    def model_dump(self) -> dict[str, object]:
        return asdict(self)


def build_workspace_memory_identity(
    workspace_root: str | Path,
    *,
    host_id: str | None = None,
) -> WorkspaceMemoryIdentity:
    del host_id
    workspace_root_path = Path(workspace_root).resolve()
    identity_root_path = (workspace_root_path / WORKSPACE_MEMORY_IDENTITY_ROOT).resolve()
    workspace_id = workspace_memory_id(identity_root_path)

    return WorkspaceMemoryIdentity(
        workspace_id=workspace_id,
        workspace_root=str(workspace_root_path),
        identity_root=str(identity_root_path),
        identity_scope=WORKSPACE_MEMORY_IDENTITY_SCOPE,
        driver_contract=WORKSPACE_MEMORY_DRIVER_CONTRACT,
    )
