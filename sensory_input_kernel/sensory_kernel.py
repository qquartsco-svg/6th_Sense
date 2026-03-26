from __future__ import annotations

from typing import Dict, Iterable, List

from .affect.sixth_sense import infer_felt_sense
from .affect.reflex_gate import decide_reflex
from .binding.multisensory_binding import bind_multisensory_events
from .bridge.action_bridge import build_action_input
from .bridge.emotion_bridge import build_emotion_input
from .bridge.felt_sense_bridge import build_felt_sense_input
from .bridge.memory_bridge import build_memory_input
from .bridge.mpk_bridge import build_mpk_input
from .bridge.snn_bridge import build_snn_input
from .channels.audition import audition_from_signal
from .channels.touch import touch_from_signal
from .channels.vision import vision_from_signal
from .contracts.schemas import (
    AudioFrame,
    CognitiveHandoff,
    ReactionDecision,
    SensoryFrame,
    SensoryStimulus,
    SituationVector,
    TouchFrame,
    VisionFrame,
)
from .memory.sensory_trace import SensoryTraceStore
from .salience.stimulus_scoring import compute_stimulus_scores


class SensoryInputKernel:
    def __init__(self, memory: SensoryTraceStore | None = None) -> None:
        self.memory = memory or SensoryTraceStore()

    def build_frame(self, stimuli: Iterable[SensoryStimulus]) -> SensoryFrame:
        items = list(stimuli)
        v = VisionFrame()
        a = AudioFrame()
        t = TouchFrame()
        smell_proxy = 0.0
        taste_proxy = 0.0
        for s in items:
            if s.channel == "vision":
                v = vision_from_signal(s.intensity, s.signal)
            elif s.channel == "hearing":
                a = audition_from_signal(s.intensity, s.signal)
            elif s.channel == "touch":
                t = touch_from_signal(s.intensity, s.signal)
            elif s.channel == "smell":
                smell_proxy = max(smell_proxy, max(0.0, min(1.0, s.intensity)))
            elif s.channel == "taste":
                taste_proxy = max(taste_proxy, max(0.0, min(1.0, s.intensity)))
        return SensoryFrame(
            vision=v,
            audition=a,
            touch=t,
            smell_proxy=smell_proxy,
            taste_proxy=taste_proxy,
            stimuli=tuple(items),
        )

    def _reaction_from_situation(self, situation: SituationVector) -> ReactionDecision:
        arousal = min(1.0, 0.6 * situation.threat + 0.4 * situation.novelty)
        valence = 0.5 - 0.5 * situation.threat
        priority = min(1.0, 0.5 * situation.urgency + 0.5 * situation.novelty)
        if priority >= 0.75:
            action = "orient_and_record"
        elif priority >= 0.45:
            action = "monitor"
        else:
            action = "ignore_minor"
        return ReactionDecision(arousal=arousal, valence=valence, priority=priority, action=action)

    def _situation_from_scores(self, scores) -> SituationVector:
        if not scores:
            return SituationVector(0.0, 0.0, 0.0, 0.0, 1.0, [])
        threat = max(s.intensity for s in scores)
        novelty = sum(s.novelty for s in scores) / len(scores)
        social = min(1.0, sum(1.0 for s in scores if s.channel in ("vision", "hearing")) / len(scores))
        urgency = min(1.0, sum(s.urgency for s in scores) / len(scores))
        stability = max(0.0, 1.0 - urgency)
        channel_weight: Dict[str, float] = {}
        for s in scores:
            channel_weight[s.channel] = channel_weight.get(s.channel, 0.0) + s.salience_score
        dominant = list(sorted(channel_weight, key=channel_weight.get, reverse=True)[:2])
        return SituationVector(threat, novelty, social, urgency, stability, dominant)

    def process_tick(self, stimuli: Iterable[SensoryStimulus]) -> Dict[str, object]:
        items: List[SensoryStimulus] = list(stimuli)
        frame = self.build_frame(items)
        scores = compute_stimulus_scores(frame.stimuli, familiarity_fn=self.memory.familiarity)
        events = bind_multisensory_events(scores)
        reflex = decide_reflex(events)
        situation = self._situation_from_scores(scores)
        reaction = self._reaction_from_situation(situation)
        felt_sense = infer_felt_sense(situation, reaction, reflex)

        for s in frame.stimuli:
            self.memory.remember_stimulus(s)
        self.memory.write_trace(events, context_tag="tick", valence=reaction.valence)

        handoff = CognitiveHandoff(
            emotion_input=build_emotion_input(reaction),
            memory_input=build_memory_input(situation, trace_count=len(self.memory.traces)),
            action_input=build_action_input(reflex),
            snn_input=build_snn_input(scores),
            mpk_input=build_mpk_input(situation),
            felt_sense_input=build_felt_sense_input(felt_sense),
        )
        return {
            "frame": frame,
            "scores": scores,
            "events": events,
            "reflex": reflex,
            "reaction": reaction,
            "situation": situation,
            "felt_sense": felt_sense,
            "handoff": handoff,
        }
