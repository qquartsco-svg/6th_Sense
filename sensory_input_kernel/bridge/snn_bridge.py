from typing import Dict, Iterable

from ..contracts.schemas import StimulusScore


def build_snn_input(scores: Iterable[StimulusScore]) -> Dict[str, object]:
    spikes = []
    for s in scores:
        if s.salience_score >= 0.7:
            spikes.append({"channel": s.channel, "rate_hz": round(20.0 + s.salience_score * 80.0, 2)})
    return {"spike_hints": spikes}

