from dataclasses import dataclass


@dataclass(slots=True)
class AdapterDescriptor:
    id: str
    default_target_root: str
    default_target_root_env: str = ''
    default_target_root_kind: str = ''

    def __post_init__(self) -> None:
        self.id = str(self.id).strip()
        self.default_target_root = str(self.default_target_root).strip()
        self.default_target_root_env = str(self.default_target_root_env).strip()
        self.default_target_root_kind = str(self.default_target_root_kind).strip()
        if not self.id:
            raise ValueError('adapter id is required')
        if not self.default_target_root:
            raise ValueError('default_target_root is required')
