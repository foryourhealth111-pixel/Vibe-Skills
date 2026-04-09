from dataclasses import asdict, dataclass


@dataclass(slots=True)
class RuntimePacket:
    goal: str
    stage: str
    entry_intent_id: str | None = None
    requested_stage_stop: str | None = None
    requested_grade_floor: str | None = None

    def model_dump(self) -> dict:
        return asdict(self)

    @classmethod
    def model_validate(cls, payload: dict) -> 'RuntimePacket':
        return cls(
            goal=str(payload['goal']),
            stage=str(payload['stage']),
            entry_intent_id=payload.get('entry_intent_id'),
            requested_stage_stop=payload.get('requested_stage_stop'),
            requested_grade_floor=payload.get('requested_grade_floor'),
        )
