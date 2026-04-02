from dataclasses import dataclass, field


@dataclass(slots=True)
class VerificationScenario:
    name: str
    checks: list[str] = field(default_factory=list)
