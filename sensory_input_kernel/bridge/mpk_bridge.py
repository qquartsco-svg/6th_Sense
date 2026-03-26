from typing import Dict

from ..contracts.schemas import SituationVector


def build_mpk_input(situation: SituationVector) -> Dict[str, object]:
    if situation.threat >= 0.8:
        tier = "executive"
    elif situation.urgency >= 0.55:
        tier = "operational"
    else:
        tier = "public"
    return {
        "mak_sensitivity_tier": tier,
        "sensory_5axis": {
            "threat": situation.threat,
            "novelty": situation.novelty,
            "social": situation.social,
            "urgency": situation.urgency,
            "stability": situation.stability,
        },
    }


def build_mpk_channel_scores(situation: SituationVector) -> Dict[str, float]:
    """
    Lightweight bridge for MemoryPhase_Kernel.

    This does not import MPK directly. It only exposes a stable
    channel_id -> score map that MPK can turn into ChannelReading tuples.
    """
    return {
        "sensory_threat": float(situation.threat),
        "sensory_novelty": float(situation.novelty),
        "sensory_social": float(situation.social),
        "sensory_urgency": float(situation.urgency),
        "sensory_stability": float(situation.stability),
    }
