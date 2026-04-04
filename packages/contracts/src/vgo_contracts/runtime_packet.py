from dataclasses import asdict, dataclass


@dataclass(slots=True)
class RuntimePacket:
    goal: str
    stage: str

    def model_dump(self) -> dict:
        return asdict(self)

    @classmethod
    def model_validate(cls, payload: dict) -> 'RuntimePacket':
        return cls(goal=str(payload['goal']), stage=str(payload['stage']))
