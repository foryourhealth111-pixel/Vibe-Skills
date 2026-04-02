from dataclasses import dataclass, field



def _is_safe_skill_name(value: str) -> bool:
    text = value.strip()
    if not text or text in {'.', '..'}:
        return False
    return '/' not in text and '\\' not in text and ':' not in text


@dataclass(slots=True)
class InstallLedger:
    managed_skill_names: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        bad = [name for name in self.managed_skill_names if not _is_safe_skill_name(str(name))]
        if bad:
            raise ValueError(f'invalid managed skill names: {bad}')
