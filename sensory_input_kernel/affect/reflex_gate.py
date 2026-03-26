from typing import Iterable, List

from ..contracts.schemas import BoundEvent, ReflexDecision, SenseChannel


def decide_reflex(events: Iterable[BoundEvent]) -> ReflexDecision:
    items = list(events)
    if not items:
        return ReflexDecision(False, "idle", 0.0, [])

    max_salience = max(e.salience for e in items)
    threat_bias = max(e.threat_hint for e in items)
    focus: List[SenseChannel] = list(items[0].channels)

    if max_salience >= 0.85 or threat_bias >= 0.7:
        return ReflexDecision(True, "startle_or_evade", threat_bias, focus)
    if max_salience >= 0.5:
        return ReflexDecision(True, "orient_attention", threat_bias, focus)
    return ReflexDecision(False, "monitor", threat_bias, focus)

