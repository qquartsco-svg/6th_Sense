from typing import Dict, Iterable, List

from ..contracts.schemas import SenseChannel, SensoryStimulus, StimulusScore

CHANNEL_BIAS: Dict[SenseChannel, float] = {
    "vision": 1.0,
    "hearing": 0.95,
    "touch": 1.1,
    "smell": 0.7,
    "taste": 0.6,
}


def compute_stimulus_scores(
    stimuli: Iterable[SensoryStimulus], familiarity_fn
) -> List[StimulusScore]:
    out: List[StimulusScore] = []
    for s in stimuli:
        intensity = max(0.0, min(1.0, s.intensity))
        novelty = 1.0 - familiarity_fn(s)
        urgency = min(1.0, 0.6 * intensity + 0.4 * novelty)
        uncertainty = 1.0 - min(1.0, s.context.get("confidence", 0.7))
        valence = -0.6 if any(k in s.signal for k in ("alarm", "impact", "pain", "heat")) else 0.2
        stimulus_score = 0.4 * intensity + 0.3 * novelty + 0.2 * urgency + 0.1 * (1.0 - uncertainty)
        salience = min(1.0, stimulus_score * CHANNEL_BIAS[s.channel])
        out.append(
            StimulusScore(
                channel=s.channel,
                intensity=intensity,
                novelty=novelty,
                urgency=urgency,
                uncertainty=uncertainty,
                valence_tendency=valence,
                stimulus_score=stimulus_score,
                salience_score=salience,
            )
        )
    return out

