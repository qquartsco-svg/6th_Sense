from typing import Dict

from ..contracts.schemas import SituationVector


def build_memory_input(situation: SituationVector, trace_count: int) -> Dict[str, float]:
    return {
        "threat": situation.threat,
        "novelty": situation.novelty,
        "urgency": situation.urgency,
        "trace_count": float(trace_count),
    }

