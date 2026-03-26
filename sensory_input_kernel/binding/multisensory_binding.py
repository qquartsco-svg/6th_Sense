from typing import Dict, Iterable, List

from ..contracts.schemas import BoundEvent, StimulusScore


def bind_multisensory_events(scores: Iterable[StimulusScore]) -> List[BoundEvent]:
    by_bucket: Dict[str, List[StimulusScore]] = {"high": [], "mid": [], "low": []}
    for score in scores:
        if score.salience_score >= 0.75:
            by_bucket["high"].append(score)
        elif score.salience_score >= 0.45:
            by_bucket["mid"].append(score)
        else:
            by_bucket["low"].append(score)

    out: List[BoundEvent] = []
    for bucket, items in by_bucket.items():
        if not items:
            continue
        channels = tuple(sorted({item.channel for item in items}))
        salience = sum(i.salience_score for i in items) / len(items)
        threat = sum(max(0.0, -i.valence_tendency) for i in items) / len(items)
        out.append(
            BoundEvent(
                event_id=f"event_{bucket}_{len(out)}",
                channels=channels,
                salience=salience,
                threat_hint=threat,
            )
        )
    return out

