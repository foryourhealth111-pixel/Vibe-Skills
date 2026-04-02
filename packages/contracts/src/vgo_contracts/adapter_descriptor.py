from dataclasses import dataclass


@dataclass(slots=True)
class AdapterDescriptor:
    id: str
    default_target_root: str

    def __post_init__(self) -> None:
        self.id = str(self.id).strip()
        self.default_target_root = str(self.default_target_root).strip()
        if not self.id:
            raise ValueError('adapter id is required')
        if not self.default_target_root:
            raise ValueError('default_target_root is required')
