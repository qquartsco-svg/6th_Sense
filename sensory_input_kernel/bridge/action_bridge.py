from typing import Dict

from ..contracts.schemas import ReflexDecision


def build_action_input(reflex: ReflexDecision) -> Dict[str, object]:
    return {
        "triggered": reflex.triggered,
        "action": reflex.action,
        "attention_focus": list(reflex.attention_focus),
    }

