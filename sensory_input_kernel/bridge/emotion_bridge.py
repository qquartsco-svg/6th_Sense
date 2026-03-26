from typing import Dict

from ..contracts.schemas import ReactionDecision


def build_emotion_input(reaction: ReactionDecision) -> Dict[str, float]:
    return {
        "arousal": reaction.arousal,
        "valence": reaction.valence,
        "priority": reaction.priority,
    }

