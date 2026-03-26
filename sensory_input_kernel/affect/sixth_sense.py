from ..contracts.schemas import FeltSenseState, ReactionDecision, ReflexDecision, SituationVector


def infer_felt_sense(
    situation: SituationVector, reaction: ReactionDecision, reflex: ReflexDecision
) -> FeltSenseState:
    # Sixth-sense heuristic: combines threat, urgency, novelty and reflex bias.
    gut_risk = min(1.0, 0.45 * situation.threat + 0.35 * situation.urgency + 0.2 * reflex.threat_bias)
    coherence = max(0.0, 0.5 * situation.stability + 0.5 * (1.0 - situation.novelty))
    confidence = min(1.0, 0.6 * coherence + 0.4 * reaction.priority)

    if gut_risk >= 0.75:
        tag = "premonition_warning"
    elif confidence >= 0.7:
        tag = "premonition_clear"
    else:
        tag = "premonition_ambiguous"

    summary = (
        f"gut_risk={gut_risk:.2f}, coherence={coherence:.2f}, "
        f"confidence={confidence:.2f}, tag={tag}"
    )
    return FeltSenseState(
        gut_risk=gut_risk,
        coherence=coherence,
        confidence=confidence,
        felt_tag=tag,
        summary=summary,
    )

