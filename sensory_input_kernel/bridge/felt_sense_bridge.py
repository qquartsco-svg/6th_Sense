from typing import Any, Dict

from ..contracts.schemas import FeltSenseState


def build_felt_sense_input(felt: FeltSenseState) -> Dict[str, Any]:
    return {
        "gut_risk": felt.gut_risk,
        "coherence": felt.coherence,
        "confidence": felt.confidence,
        "felt_tag": felt.felt_tag,
        "summary": felt.summary,
    }

