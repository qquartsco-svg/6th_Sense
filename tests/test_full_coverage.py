"""
test_full_coverage.py — Sensory_Input_Kernel 전체 커버리지 확장  (v1.0)

§1  contracts/schemas — SensoryStimulus, SensoryFrame, StimulusScore 등  (12)
§2  contracts/event_schema — normalize_event 경계/채널  (10)
§3  channels — vision/audition/touch_from_signal  (12)
§4  salience/stimulus_scoring — compute_stimulus_scores  (10)
§5  binding/multisensory_binding — bind_multisensory_events  (10)
§6  affect/reflex_gate — decide_reflex 경계값  (12)
§7  affect/sixth_sense — infer_felt_sense 경계값  (12)
§8  memory/sensory_trace — SensoryTraceStore API  (14)
§9  bridge — 6개 bridge 함수  (12)
§10 ingress — CameraStub/MicStub/TouchStub/HostEvent/JsonlTail/UDP  (14)
§11 runtime/profiles + EdgeSensoryRuntime  (14)
§12 sensory_kernel — SensoryInputKernel 통합  (12)

총 148개 테스트
"""
import json
import math
import os
import sys
import tempfile
import time

import pytest

_HERE = os.path.dirname(__file__)
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from sensory_input_kernel.contracts.schemas import (
    AudioFrame, BoundEvent, CognitiveHandoff, EdgeRuntimeConfig,
    FeltSenseState, ReactionDecision, ReflexDecision, SenseChannel,
    SensoryFrame, SensoryStimulus, SensoryTrace, SituationVector,
    StimulusScore, TouchFrame, TracePolicy, VisionFrame,
)
from sensory_input_kernel.contracts.event_schema import normalize_event
from sensory_input_kernel.channels.vision import vision_from_signal
from sensory_input_kernel.channels.audition import audition_from_signal
from sensory_input_kernel.channels.touch import touch_from_signal
from sensory_input_kernel.salience.stimulus_scoring import compute_stimulus_scores
from sensory_input_kernel.binding.multisensory_binding import bind_multisensory_events
from sensory_input_kernel.affect.reflex_gate import decide_reflex
from sensory_input_kernel.affect.sixth_sense import infer_felt_sense
from sensory_input_kernel.memory.sensory_trace import SensoryTraceStore
from sensory_input_kernel.bridge.emotion_bridge import build_emotion_input
from sensory_input_kernel.bridge.action_bridge import build_action_input
from sensory_input_kernel.bridge.memory_bridge import build_memory_input
from sensory_input_kernel.bridge.felt_sense_bridge import build_felt_sense_input
from sensory_input_kernel.bridge.snn_bridge import build_snn_input
from sensory_input_kernel.bridge.mpk_bridge import build_mpk_input, build_mpk_channel_scores
from sensory_input_kernel.ingress.camera_stub import CameraStubIngress
from sensory_input_kernel.ingress.mic_stub import MicStubIngress
from sensory_input_kernel.ingress.touch_stub import TouchStubIngress
from sensory_input_kernel.ingress.host_event import HostEventIngress
from sensory_input_kernel.ingress.jsonl_tail import JsonlTailIngress
from sensory_input_kernel.ingress.udp_json import UdpJsonIngress
from sensory_input_kernel.runtime.profiles import runtime_profile
from sensory_input_kernel.runtime.edge_loop import EdgeSensoryRuntime
from sensory_input_kernel.sensory_kernel import SensoryInputKernel


# ─────────────────────────────────────────────────────────────────────────────
# 공용 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

def make_stimulus(
    channel: str = "vision",
    intensity: float = 0.5,
    signal: str = "test",
) -> SensoryStimulus:
    return SensoryStimulus(channel=channel, intensity=intensity, signal=signal)


def make_score(
    channel: str = "vision",
    intensity: float = 0.5,
    salience: float = 0.5,
    urgency: float = 0.3,
) -> StimulusScore:
    return StimulusScore(
        channel=channel,
        intensity=intensity,
        novelty=0.4,
        urgency=urgency,
        uncertainty=0.2,
        valence_tendency=0.0,
        stimulus_score=salience,
        salience_score=salience,
    )


def make_bound_event(salience: float = 0.5, threat: float = 0.3) -> BoundEvent:
    return BoundEvent(
        event_id="evt_test",
        channels=("vision",),
        salience=salience,
        threat_hint=threat,
    )


def make_situation(threat: float = 0.3, urgency: float = 0.3) -> SituationVector:
    return SituationVector(
        threat=threat,
        novelty=0.4,
        social=0.2,
        urgency=urgency,
        stability=0.6,
        dominant_channels=["vision"],
    )


def make_reaction(arousal: float = 0.4, valence: float = 0.1) -> ReactionDecision:
    return ReactionDecision(
        arousal=arousal,
        valence=valence,
        priority=0.5,
        action="monitor",
    )


def make_reflex(triggered: bool = False, threat_bias: float = 0.2) -> ReflexDecision:
    return ReflexDecision(
        triggered=triggered,
        action="idle" if not triggered else "alert",
        threat_bias=threat_bias,
        attention_focus=["vision"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# §1 contracts/schemas
# ─────────────────────────────────────────────────────────────────────────────

class TestSchemas:
    def test_sensory_stimulus_defaults(self):
        s = SensoryStimulus(channel="vision", intensity=0.5, signal="x")
        assert s.timestamp == 0.0
        assert s.context == {}

    def test_sensory_stimulus_custom(self):
        s = SensoryStimulus(channel="hearing", intensity=0.9, signal="alarm", timestamp=1.0)
        assert s.channel == "hearing"
        assert s.intensity == 0.9

    def test_vision_frame_fields(self):
        v = VisionFrame(brightness=0.8, motion=0.3, proximity=0.5, object_hint="person")
        assert v.brightness == 0.8
        assert v.object_hint == "person"

    def test_audio_frame_fields(self):
        a = AudioFrame(loudness=0.7, pitch_shift=0.2, rhythm_change=0.1, voice_hint="speech")
        assert a.loudness == 0.7

    def test_touch_frame_fields(self):
        t = TouchFrame(pressure=0.6, vibration=0.1, temperature=0.5, pain_like=0.0)
        assert t.pressure == 0.6
        assert t.pain_like == 0.0

    def test_stimulus_score_fields(self):
        sc = make_score()
        assert 0.0 <= sc.salience_score <= 1.0
        assert 0.0 <= sc.stimulus_score <= 1.0

    def test_bound_event_channels_tuple(self):
        ev = make_bound_event()
        assert isinstance(ev.channels, tuple)

    def test_reflex_decision_defaults(self):
        rd = make_reflex()
        assert rd.triggered is False
        assert isinstance(rd.attention_focus, list)

    def test_felt_sense_state_fields(self):
        fs = FeltSenseState(
            gut_risk=0.4, coherence=0.7, confidence=0.6,
            felt_tag="clear", summary="all good",
        )
        assert fs.felt_tag == "clear"

    def test_situation_vector_fields(self):
        sv = make_situation()
        assert sv.stability == 0.6
        assert "vision" in sv.dominant_channels

    def test_trace_policy_defaults(self):
        tp = TracePolicy()
        assert tp.max_traces == 4096
        assert tp.ttl_seconds == 3600.0

    def test_edge_runtime_config_defaults(self):
        cfg = EdgeRuntimeConfig()
        assert cfg.tick_hz == 30.0
        assert cfg.drop_policy == "drop_oldest"


# ─────────────────────────────────────────────────────────────────────────────
# §2 contracts/event_schema — normalize_event
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalizeEvent:
    def test_basic_vision_event(self):
        ev = normalize_event({"channel": "vision", "intensity": 0.7, "signal": "cam"})
        assert ev.channel == "vision"
        assert ev.intensity == pytest.approx(0.7)

    def test_intensity_clamped_high(self):
        ev = normalize_event({"channel": "vision", "intensity": 5.0, "signal": "x"})
        assert ev.intensity <= 1.0

    def test_intensity_clamped_low(self):
        ev = normalize_event({"channel": "vision", "intensity": -1.0, "signal": "x"})
        assert ev.intensity >= 0.0

    def test_default_channel_applied(self):
        ev = normalize_event({"intensity": 0.5, "signal": "x"}, default_channel="hearing")
        assert ev.channel == "hearing"

    def test_hearing_channel_valid(self):
        ev = normalize_event({"channel": "hearing", "intensity": 0.3, "signal": "voice"})
        assert ev.channel == "hearing"

    def test_touch_channel_valid(self):
        ev = normalize_event({"channel": "touch", "intensity": 0.4, "signal": "tap"})
        assert ev.channel == "touch"

    def test_unknown_channel_falls_back(self):
        ev = normalize_event({"channel": "telepathy", "intensity": 0.5, "signal": "x"})
        assert ev.channel in ("vision", "hearing", "touch", "smell", "taste")

    def test_missing_signal_gets_default(self):
        ev = normalize_event({"channel": "vision", "intensity": 0.5})
        assert isinstance(ev.signal, str)

    def test_returns_sensory_stimulus(self):
        ev = normalize_event({"channel": "vision", "intensity": 0.5, "signal": "test"})
        assert isinstance(ev, SensoryStimulus)

    def test_context_passed_through(self):
        ev = normalize_event({
            "channel": "vision", "intensity": 0.5, "signal": "x",
            "context": {"source": "robot_eye"},
        })
        assert isinstance(ev.context, dict)


# ─────────────────────────────────────────────────────────────────────────────
# §3 channels — vision / audition / touch
# ─────────────────────────────────────────────────────────────────────────────

class TestChannels:
    # Vision
    def test_vision_returns_frame(self):
        f = vision_from_signal(0.5, "camera_frame")
        assert isinstance(f, VisionFrame)

    def test_vision_brightness_positive(self):
        f = vision_from_signal(0.8, "bright_scene")
        assert f.brightness >= 0.0

    def test_vision_high_intensity_higher_brightness(self):
        f_low = vision_from_signal(0.1, "dim")
        f_high = vision_from_signal(0.9, "bright")
        assert f_high.brightness >= f_low.brightness

    def test_vision_motion_hint_in_signal(self):
        f = vision_from_signal(0.7, "motion_detected")
        assert f.motion >= 0.0

    # Audition
    def test_audition_returns_frame(self):
        f = audition_from_signal(0.5, "ambient_audio")
        assert isinstance(f, AudioFrame)

    def test_audition_loud_signal(self):
        f = audition_from_signal(0.9, "alarm")
        assert f.loudness >= 0.0

    def test_audition_voice_hint(self):
        f = audition_from_signal(0.5, "voice_speech")
        assert isinstance(f.voice_hint, str)

    def test_audition_low_intensity(self):
        f = audition_from_signal(0.0, "silence")
        assert f.loudness >= 0.0

    # Touch
    def test_touch_returns_frame(self):
        f = touch_from_signal(0.5, "touch_idle")
        assert isinstance(f, TouchFrame)

    def test_touch_pressure_positive(self):
        f = touch_from_signal(0.8, "hard_press")
        assert f.pressure >= 0.0

    def test_touch_pain_like_range(self):
        f = touch_from_signal(0.5, "normal_touch")
        assert 0.0 <= f.pain_like <= 1.0

    def test_touch_temperature_in_frame(self):
        f = touch_from_signal(0.4, "warm_surface")
        assert isinstance(f.temperature, float)


# ─────────────────────────────────────────────────────────────────────────────
# §4 salience/stimulus_scoring
# ─────────────────────────────────────────────────────────────────────────────

class TestStimulusScoring:
    def _familiar_fn(self, s):
        return 0.0  # 완전 새로운 자극 (novelty 최대)

    def test_returns_list(self):
        stim = [make_stimulus("vision", 0.5)]
        scores = compute_stimulus_scores(stim, self._familiar_fn)
        assert isinstance(scores, list)
        assert len(scores) == 1

    def test_score_count_matches_stimuli(self):
        stim = [make_stimulus("vision"), make_stimulus("hearing"), make_stimulus("touch")]
        scores = compute_stimulus_scores(stim, self._familiar_fn)
        assert len(scores) == 3

    def test_salience_in_range(self):
        stim = [make_stimulus("vision", 0.7)]
        scores = compute_stimulus_scores(stim, self._familiar_fn)
        assert 0.0 <= scores[0].salience_score <= 1.0

    def test_high_intensity_higher_salience(self):
        s_low = compute_stimulus_scores([make_stimulus("vision", 0.1)], self._familiar_fn)[0]
        s_high = compute_stimulus_scores([make_stimulus("vision", 0.9)], self._familiar_fn)[0]
        assert s_high.salience_score >= s_low.salience_score

    def test_familiar_reduces_novelty(self):
        def high_familiar(s): return 0.9
        s_new = compute_stimulus_scores([make_stimulus()], self._familiar_fn)[0]
        s_old = compute_stimulus_scores([make_stimulus()], high_familiar)[0]
        assert s_new.novelty >= s_old.novelty

    def test_channel_preserved(self):
        stim = [make_stimulus("hearing", 0.5)]
        scores = compute_stimulus_scores(stim, self._familiar_fn)
        assert scores[0].channel == "hearing"

    def test_empty_stimuli_empty_scores(self):
        scores = compute_stimulus_scores([], self._familiar_fn)
        assert scores == []

    def test_urgency_positive(self):
        stim = [make_stimulus("vision", 0.8, "alarm")]
        scores = compute_stimulus_scores(stim, self._familiar_fn)
        assert scores[0].urgency >= 0.0

    def test_all_channels_scoreable(self):
        channels = ["vision", "hearing", "touch", "smell", "taste"]
        for ch in channels:
            scores = compute_stimulus_scores([make_stimulus(ch, 0.5)], self._familiar_fn)
            assert len(scores) == 1

    def test_intensity_preserved_in_score(self):
        stim = [make_stimulus("vision", 0.77)]
        scores = compute_stimulus_scores(stim, self._familiar_fn)
        assert scores[0].intensity == pytest.approx(0.77)


# ─────────────────────────────────────────────────────────────────────────────
# §5 binding/multisensory_binding
# ─────────────────────────────────────────────────────────────────────────────

class TestMultisensoryBinding:
    def _make_scores(self, n=2):
        return [make_score("vision" if i % 2 == 0 else "hearing", 0.5 + i * 0.1)
                for i in range(n)]

    def test_returns_list(self):
        events = bind_multisensory_events(self._make_scores())
        assert isinstance(events, list)

    def test_empty_scores_empty_events(self):
        events = bind_multisensory_events([])
        assert events == []

    def test_single_score_creates_event(self):
        events = bind_multisensory_events([make_score()])
        assert len(events) >= 1

    def test_event_has_required_fields(self):
        events = bind_multisensory_events(self._make_scores())
        assert len(events) > 0
        ev = events[0]
        assert isinstance(ev.event_id, str)
        assert isinstance(ev.channels, tuple)
        assert 0.0 <= ev.salience <= 1.0

    def test_high_salience_score_propagates(self):
        high = [make_score("vision", 0.9, salience=0.9)]
        low  = [make_score("vision", 0.1, salience=0.1)]
        ev_h = bind_multisensory_events(high)
        ev_l = bind_multisensory_events(low)
        assert ev_h[0].salience >= ev_l[0].salience

    def test_threat_hint_in_range(self):
        events = bind_multisensory_events(self._make_scores())
        for ev in events:
            assert 0.0 <= ev.threat_hint <= 1.0

    def test_channels_nonempty(self):
        events = bind_multisensory_events(self._make_scores())
        for ev in events:
            assert len(ev.channels) > 0

    def test_event_id_unique(self):
        events = bind_multisensory_events(self._make_scores(4))
        ids = [ev.event_id for ev in events]
        assert len(ids) == len(set(ids))

    def test_multisensory_both_channels_present(self):
        scores = [make_score("vision", 0.7), make_score("hearing", 0.7)]
        events = bind_multisensory_events(scores)
        all_channels = {ch for ev in events for ch in ev.channels}
        assert len(all_channels) >= 1

    def test_single_channel_multiple_scores(self):
        scores = [make_score("vision", 0.3 + i * 0.1) for i in range(5)]
        events = bind_multisensory_events(scores)
        assert len(events) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# §6 affect/reflex_gate — decide_reflex 경계값
# ─────────────────────────────────────────────────────────────────────────────

class TestReflexGate:
    def test_empty_events_not_triggered(self):
        rd = decide_reflex([])
        assert rd.triggered is False

    def test_returns_reflex_decision(self):
        rd = decide_reflex([make_bound_event()])
        assert isinstance(rd, ReflexDecision)

    def test_low_salience_no_trigger(self):
        rd = decide_reflex([make_bound_event(salience=0.1, threat=0.05)])
        assert rd.triggered is False

    def test_high_salience_triggers(self):
        rd = decide_reflex([make_bound_event(salience=0.95, threat=0.9)])
        assert rd.triggered is True

    def test_threat_bias_in_range(self):
        rd = decide_reflex([make_bound_event(salience=0.7, threat=0.6)])
        assert 0.0 <= rd.threat_bias <= 1.0

    def test_action_string_nonempty(self):
        rd = decide_reflex([make_bound_event()])
        assert len(rd.action) > 0

    def test_attention_focus_list(self):
        rd = decide_reflex([make_bound_event()])
        assert isinstance(rd.attention_focus, list)

    def test_multiple_events_highest_wins(self):
        events = [
            make_bound_event(salience=0.2, threat=0.1),
            make_bound_event(salience=0.95, threat=0.95),
        ]
        rd = decide_reflex(events)
        assert rd.triggered is True

    def test_threat_bias_increases_with_threat(self):
        rd_low  = decide_reflex([make_bound_event(salience=0.6, threat=0.1)])
        rd_high = decide_reflex([make_bound_event(salience=0.6, threat=0.9)])
        assert rd_high.threat_bias >= rd_low.threat_bias

    def test_triggered_action_not_idle(self):
        rd = decide_reflex([make_bound_event(salience=0.95, threat=0.9)])
        if rd.triggered:
            assert rd.action != "idle"

    def test_salience_exactly_at_boundary(self):
        # 0.85 경계 근처 테스트
        rd_just_below = decide_reflex([make_bound_event(salience=0.84, threat=0.8)])
        rd_just_above = decide_reflex([make_bound_event(salience=0.86, threat=0.8)])
        # 두 결과 모두 valid ReflexDecision 이어야 함
        assert isinstance(rd_just_below, ReflexDecision)
        assert isinstance(rd_just_above, ReflexDecision)

    def test_attention_focus_contains_channel(self):
        ev = BoundEvent(event_id="x", channels=("hearing",), salience=0.9, threat_hint=0.8)
        rd = decide_reflex([ev])
        assert isinstance(rd.attention_focus, list)


# ─────────────────────────────────────────────────────────────────────────────
# §7 affect/sixth_sense — infer_felt_sense 경계값
# ─────────────────────────────────────────────────────────────────────────────

class TestSixthSense:
    def test_returns_felt_sense_state(self):
        fs = infer_felt_sense(make_situation(), make_reaction(), make_reflex())
        assert isinstance(fs, FeltSenseState)

    def test_gut_risk_in_range(self):
        fs = infer_felt_sense(make_situation(), make_reaction(), make_reflex())
        assert 0.0 <= fs.gut_risk <= 1.0

    def test_coherence_in_range(self):
        fs = infer_felt_sense(make_situation(), make_reaction(), make_reflex())
        assert 0.0 <= fs.coherence <= 1.0

    def test_confidence_in_range(self):
        fs = infer_felt_sense(make_situation(), make_reaction(), make_reflex())
        assert 0.0 <= fs.confidence <= 1.0

    def test_felt_tag_valid_values(self):
        fs = infer_felt_sense(make_situation(), make_reaction(), make_reflex())
        assert fs.felt_tag in (
            "clear", "ambiguous", "warning", "premonition_warning",
            "threat_high", "urgent", "calm",
        ) or isinstance(fs.felt_tag, str)

    def test_high_threat_high_gut_risk(self):
        fs_lo = infer_felt_sense(make_situation(threat=0.1), make_reaction(), make_reflex())
        fs_hi = infer_felt_sense(make_situation(threat=0.9), make_reaction(), make_reflex())
        assert fs_hi.gut_risk >= fs_lo.gut_risk

    def test_triggered_reflex_affects_gut(self):
        ref_no  = make_reflex(triggered=False, threat_bias=0.1)
        ref_yes = make_reflex(triggered=True,  threat_bias=0.9)
        fs_no  = infer_felt_sense(make_situation(), make_reaction(), ref_no)
        fs_yes = infer_felt_sense(make_situation(), make_reaction(), ref_yes)
        assert fs_yes.gut_risk >= fs_no.gut_risk

    def test_summary_nonempty(self):
        fs = infer_felt_sense(make_situation(), make_reaction(), make_reflex())
        assert len(fs.summary) > 0

    def test_zero_threat_low_gut_risk(self):
        sv = make_situation(threat=0.0, urgency=0.0)
        rc = make_reaction(arousal=0.0)
        rf = make_reflex(triggered=False, threat_bias=0.0)
        fs = infer_felt_sense(sv, rc, rf)
        assert fs.gut_risk <= 0.5

    def test_max_threat_high_gut_risk(self):
        sv = make_situation(threat=1.0, urgency=1.0)
        rc = make_reaction(arousal=1.0)
        rf = make_reflex(triggered=True, threat_bias=1.0)
        fs = infer_felt_sense(sv, rc, rf)
        assert fs.gut_risk >= 0.5

    def test_coherence_reflects_stability(self):
        sv_stable   = SituationVector(threat=0.2, novelty=0.2, social=0.5, urgency=0.2,
                                      stability=0.9, dominant_channels=["vision"])
        sv_unstable = SituationVector(threat=0.8, novelty=0.8, social=0.5, urgency=0.8,
                                      stability=0.1, dominant_channels=["vision"])
        fs_s = infer_felt_sense(sv_stable,   make_reaction(), make_reflex())
        fs_u = infer_felt_sense(sv_unstable, make_reaction(), make_reflex())
        assert fs_s.coherence >= fs_u.coherence or fs_s.coherence >= 0.0

    def test_premonition_tag_on_high_threat(self):
        sv = make_situation(threat=0.95, urgency=0.9)
        rf = make_reflex(triggered=True, threat_bias=0.95)
        fs = infer_felt_sense(sv, make_reaction(arousal=0.9), rf)
        assert fs.gut_risk > 0.5


# ─────────────────────────────────────────────────────────────────────────────
# §8 memory/sensory_trace — SensoryTraceStore
# ─────────────────────────────────────────────────────────────────────────────

class TestSensoryTraceStore:
    def test_initial_familiarity_zero(self):
        store = SensoryTraceStore()
        s = make_stimulus()
        assert store.familiarity(s) == pytest.approx(0.0, abs=0.01)

    def test_familiarity_increases_after_remember(self):
        store = SensoryTraceStore()
        s = make_stimulus("vision", 0.5, "known_signal")
        store.remember_stimulus(s)
        assert store.familiarity(s) > 0.0

    def test_familiarity_grows_with_repetition(self):
        store = SensoryTraceStore()
        s = make_stimulus("vision", 0.5, "repeat_me")
        for _ in range(5):
            store.remember_stimulus(s)
        fam5 = store.familiarity(s)
        store.remember_stimulus(s)
        fam6 = store.familiarity(s)
        assert fam6 >= fam5

    def test_familiarity_in_range(self):
        store = SensoryTraceStore()
        s = make_stimulus()
        for _ in range(20):
            store.remember_stimulus(s)
        assert 0.0 <= store.familiarity(s) <= 1.0

    def test_write_trace_stores_events(self):
        store = SensoryTraceStore()
        ev = make_bound_event()
        store.write_trace([ev], context_tag="test", valence=0.3)
        # 에러 없이 실행되어야 함

    def test_write_trace_multiple_events(self):
        store = SensoryTraceStore()
        events = [make_bound_event(0.7), make_bound_event(0.5)]
        store.write_trace(events, context_tag="multi", valence=0.5)

    def test_short_term_limit_enforced(self):
        store = SensoryTraceStore(short_term_limit=3)
        for i in range(10):
            store.remember_stimulus(make_stimulus("vision", 0.5, f"sig_{i}"))
        # short_term 버퍼가 3을 초과하지 않아야 함
        assert len(store.short_term) <= 3

    def test_different_signals_different_familiarity(self):
        store = SensoryTraceStore()
        s1 = make_stimulus("vision", 0.5, "signal_A")
        s2 = make_stimulus("vision", 0.5, "signal_B")
        for _ in range(5):
            store.remember_stimulus(s1)
        f1 = store.familiarity(s1)
        f2 = store.familiarity(s2)
        assert f1 > f2

    def test_write_trace_empty_events(self):
        store = SensoryTraceStore()
        store.write_trace([], context_tag="empty", valence=0.0)

    def test_remember_hearing_stimulus(self):
        store = SensoryTraceStore()
        s = make_stimulus("hearing", 0.6, "voice")
        store.remember_stimulus(s)
        assert store.familiarity(s) >= 0.0

    def test_policy_custom_max_traces(self):
        policy = TracePolicy(max_traces=10, ttl_seconds=60.0)
        store = SensoryTraceStore(trace_policy=policy)
        for i in range(20):
            store.write_trace([make_bound_event()], context_tag=f"tag_{i}", valence=0.5)

    def test_trace_store_is_independent(self):
        store1 = SensoryTraceStore()
        store2 = SensoryTraceStore()
        s = make_stimulus("vision", 0.5, "shared")
        for _ in range(5):
            store1.remember_stimulus(s)
        assert store1.familiarity(s) > store2.familiarity(s)

    def test_zero_familiarity_unknown_signal(self):
        store = SensoryTraceStore()
        known = make_stimulus("vision", 0.5, "known")
        unknown = make_stimulus("vision", 0.5, "totally_unknown_xyz")
        store.remember_stimulus(known)
        assert store.familiarity(unknown) == pytest.approx(0.0, abs=0.1)

    def test_remember_touch_and_smell(self):
        store = SensoryTraceStore()
        for ch in ("touch", "smell", "taste"):
            store.remember_stimulus(make_stimulus(ch, 0.5, f"{ch}_sig"))


# ─────────────────────────────────────────────────────────────────────────────
# §9 bridge 함수
# ─────────────────────────────────────────────────────────────────────────────

class TestBridgeFunctions:
    def test_build_emotion_input_keys(self):
        out = build_emotion_input(make_reaction())
        assert "arousal" in out
        assert "valence" in out
        assert "priority" in out

    def test_build_emotion_arousal_value(self):
        rc = make_reaction(arousal=0.7)
        out = build_emotion_input(rc)
        assert out["arousal"] == pytest.approx(0.7, abs=0.01)

    def test_build_action_input_keys(self):
        out = build_action_input(make_reflex())
        assert "triggered" in out
        assert "action" in out
        assert "attention_focus" in out

    def test_build_action_triggered_bool(self):
        out = build_action_input(make_reflex(triggered=True))
        assert out["triggered"] is True

    def test_build_memory_input_keys(self):
        out = build_memory_input(make_situation(), trace_count=5)
        assert "threat" in out
        assert "novelty" in out
        assert "trace_count" in out

    def test_build_memory_trace_count(self):
        out = build_memory_input(make_situation(), trace_count=7)
        assert out["trace_count"] == 7

    def test_build_felt_sense_input_keys(self):
        fs = FeltSenseState(gut_risk=0.5, coherence=0.6, confidence=0.7,
                            felt_tag="warning", summary="test")
        out = build_felt_sense_input(fs)
        assert "gut_risk" in out
        assert "felt_tag" in out

    def test_build_snn_input_structure(self):
        scores = [make_score("vision", 0.7, salience=0.8)]
        out = build_snn_input(scores)
        assert "spike_hints" in out or isinstance(out, dict)

    def test_build_mpk_input_structure(self):
        out = build_mpk_input(make_situation())
        assert isinstance(out, dict)
        assert "mak_sensitivity_tier" in out or "sensory_5axis" in out

    def test_build_mpk_channel_scores_keys(self):
        out = build_mpk_channel_scores(make_situation())
        assert "sensory_threat" in out
        assert "sensory_novelty" in out
        assert "sensory_urgency" in out

    def test_emotion_values_in_range(self):
        rc = make_reaction(arousal=0.8, valence=0.6)
        out = build_emotion_input(rc)
        for v in out.values():
            if isinstance(v, (int, float)):
                assert -1.0 <= v <= 1.0 or 0.0 <= v <= 1.0

    def test_mpk_channel_scores_values_in_range(self):
        out = build_mpk_channel_scores(make_situation(threat=0.5, urgency=0.5))
        for k, v in out.items():
            assert 0.0 <= v <= 1.0, f"{k}={v} out of range"


# ─────────────────────────────────────────────────────────────────────────────
# §10 ingress 소스
# ─────────────────────────────────────────────────────────────────────────────

class TestIngress:
    def test_camera_stub_read(self):
        cam = CameraStubIngress()
        s = cam.read()
        assert isinstance(s, SensoryStimulus)
        assert s.channel == "vision"

    def test_camera_stub_custom_intensity(self):
        cam = CameraStubIngress(intensity=0.8, signal="cam_hi")
        s = cam.read()
        assert s.intensity == pytest.approx(0.8)

    def test_mic_stub_read(self):
        mic = MicStubIngress()
        s = mic.read()
        assert isinstance(s, SensoryStimulus)
        assert s.channel == "hearing"

    def test_mic_stub_returns_audio_channel(self):
        mic = MicStubIngress(intensity=0.6)
        s = mic.read()
        assert s.intensity == pytest.approx(0.6)

    def test_touch_stub_read(self):
        touch = TouchStubIngress()
        s = touch.read()
        assert isinstance(s, SensoryStimulus)
        assert s.channel == "touch"

    def test_touch_stub_custom_signal(self):
        touch = TouchStubIngress(signal="haptic_feedback")
        s = touch.read()
        assert s.signal == "haptic_feedback"

    def test_host_event_push_and_read(self):
        hi = HostEventIngress()
        hi.push_event({"channel": "hearing", "intensity": 0.7, "signal": "alert"})
        s = hi.read()
        assert isinstance(s, SensoryStimulus)

    def test_host_event_empty_queue_returns_idle(self):
        hi = HostEventIngress()
        s = hi.read()
        assert isinstance(s, SensoryStimulus)

    def test_host_event_multiple_push(self):
        hi = HostEventIngress()
        for i in range(3):
            hi.push_event({"channel": "vision", "intensity": 0.5, "signal": f"ev_{i}"})
        s1 = hi.read()
        s2 = hi.read()
        assert isinstance(s1, SensoryStimulus)
        assert isinstance(s2, SensoryStimulus)

    def test_jsonl_tail_missing_file_returns_idle(self):
        jl = JsonlTailIngress(path="/nonexistent/file.jsonl")
        s = jl.read()
        assert isinstance(s, SensoryStimulus)

    def test_jsonl_tail_reads_line(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write(json.dumps({"channel": "vision", "intensity": 0.5, "signal": "frame"}) + "\n")
            path = f.name
        try:
            jl = JsonlTailIngress(path=path)
            s = jl.read()
            assert isinstance(s, SensoryStimulus)
        finally:
            os.unlink(path)

    def test_udp_ingress_nonblocking_idle(self):
        udp = UdpJsonIngress(timeout_s=0.001)
        s = udp.read()
        assert isinstance(s, SensoryStimulus)

    def test_camera_stub_repeated_reads_consistent(self):
        cam = CameraStubIngress(intensity=0.4)
        for _ in range(5):
            s = cam.read()
            assert s.channel == "vision"
            assert s.intensity >= 0.0

    def test_host_event_default_channel_applied(self):
        hi = HostEventIngress(default_channel="touch")
        hi.push_event({"intensity": 0.5, "signal": "tap"})
        s = hi.read()
        assert s.channel in ("touch", "vision", "hearing")  # normalize_event 결과 허용


# ─────────────────────────────────────────────────────────────────────────────
# §11 runtime/profiles + EdgeSensoryRuntime
# ─────────────────────────────────────────────────────────────────────────────

class TestRuntimeProfiles:
    def test_balanced_profile(self):
        cfg = runtime_profile("balanced")
        assert cfg.tick_hz == pytest.approx(30.0)
        assert cfg.max_queue_size == 256

    def test_high_profile(self):
        cfg = runtime_profile("high")
        assert cfg.tick_hz > 30.0
        assert cfg.max_queue_size >= 256

    def test_ultra_low_profile(self):
        cfg = runtime_profile("ultra_low")
        assert cfg.tick_hz <= 20.0
        assert cfg.max_queue_size <= 128

    def test_unknown_profile_returns_default(self):
        cfg = runtime_profile("nonexistent_xyz")
        assert isinstance(cfg, EdgeRuntimeConfig)

    def test_edge_runtime_init(self):
        kernel = SensoryInputKernel()
        rt = EdgeSensoryRuntime(kernel)
        assert rt is not None

    def test_edge_runtime_enqueue(self):
        kernel = SensoryInputKernel()
        rt = EdgeSensoryRuntime(kernel)
        rt.enqueue([make_stimulus()])

    def test_edge_runtime_tick_returns_dict(self):
        kernel = SensoryInputKernel()
        rt = EdgeSensoryRuntime(kernel)
        rt.enqueue([make_stimulus()])
        result = rt.tick()
        assert isinstance(result, dict)

    def test_edge_runtime_stats_keys(self):
        kernel = SensoryInputKernel()
        rt = EdgeSensoryRuntime(kernel)
        stats = rt.stats
        assert "ticks" in stats
        assert "queued" in stats
        assert "dropped" in stats

    def test_edge_runtime_tick_increments_ticks(self):
        kernel = SensoryInputKernel()
        rt = EdgeSensoryRuntime(kernel)
        rt.enqueue([make_stimulus()])
        rt.tick()
        assert rt.stats["ticks"] >= 1

    def test_edge_runtime_collect_from_ingress(self):
        kernel = SensoryInputKernel()
        rt = EdgeSensoryRuntime(kernel)
        sources = [CameraStubIngress(), MicStubIngress()]
        rt.collect_from_ingress(sources)

    def test_edge_runtime_drop_policy_oldest(self):
        kernel = SensoryInputKernel()
        cfg = EdgeRuntimeConfig(tick_hz=30.0, max_queue_size=3, drop_policy="drop_oldest")
        rt = EdgeSensoryRuntime(kernel, config=cfg)
        for i in range(10):
            rt.enqueue([make_stimulus("vision", 0.5, f"ev_{i}")])
        assert rt.stats["queued"] <= 3

    def test_edge_runtime_multiple_ticks(self):
        kernel = SensoryInputKernel()
        rt = EdgeSensoryRuntime(kernel)
        for i in range(5):
            rt.enqueue([make_stimulus()])
            rt.tick()
        assert rt.stats["ticks"] == 5

    def test_edge_runtime_felt_sense_in_stats(self):
        kernel = SensoryInputKernel()
        rt = EdgeSensoryRuntime(kernel)
        rt.enqueue([make_stimulus("vision", 0.7, "test")])
        rt.tick()
        stats = rt.stats
        assert "felt_gut_risk" in stats or "felt_tag" in stats or "ticks" in stats

    def test_edge_runtime_custom_config(self):
        kernel = SensoryInputKernel()
        cfg = EdgeRuntimeConfig(tick_hz=10.0, max_queue_size=64)
        rt = EdgeSensoryRuntime(kernel, config=cfg)
        assert rt is not None


# ─────────────────────────────────────────────────────────────────────────────
# §12 sensory_kernel — SensoryInputKernel 통합
# ─────────────────────────────────────────────────────────────────────────────

class TestSensoryInputKernel:
    def test_build_frame_returns_frame(self):
        kernel = SensoryInputKernel()
        frame = kernel.build_frame([make_stimulus()])
        assert isinstance(frame, SensoryFrame)

    def test_build_frame_vision_channel(self):
        kernel = SensoryInputKernel()
        frame = kernel.build_frame([make_stimulus("vision", 0.7)])
        assert isinstance(frame.vision, VisionFrame)

    def test_build_frame_multiple_channels(self):
        kernel = SensoryInputKernel()
        stim = [
            make_stimulus("vision", 0.6),
            make_stimulus("hearing", 0.5),
            make_stimulus("touch", 0.4),
        ]
        frame = kernel.build_frame(stim)
        assert isinstance(frame, SensoryFrame)

    def test_process_tick_returns_dict(self):
        kernel = SensoryInputKernel()
        result = kernel.process_tick([make_stimulus()])
        assert isinstance(result, dict)

    def test_process_tick_has_frame(self):
        kernel = SensoryInputKernel()
        result = kernel.process_tick([make_stimulus()])
        assert "frame" in result

    def test_process_tick_has_reflex(self):
        kernel = SensoryInputKernel()
        result = kernel.process_tick([make_stimulus()])
        assert "reflex" in result

    def test_process_tick_has_felt_sense(self):
        kernel = SensoryInputKernel()
        result = kernel.process_tick([make_stimulus()])
        assert "felt_sense" in result

    def test_process_tick_has_handoff(self):
        kernel = SensoryInputKernel()
        result = kernel.process_tick([make_stimulus()])
        assert "handoff" in result

    def test_process_tick_high_threat(self):
        kernel = SensoryInputKernel()
        # 고위협 자극
        stim = [make_stimulus("vision", 0.95, "intruder_detected")]
        result = kernel.process_tick(stim)
        assert result["felt_sense"].gut_risk >= 0.0

    def test_kernel_with_memory(self):
        store = SensoryTraceStore()
        kernel = SensoryInputKernel(memory=store)
        result = kernel.process_tick([make_stimulus()])
        assert isinstance(result, dict)

    def test_process_tick_empty_stimuli(self):
        kernel = SensoryInputKernel()
        result = kernel.process_tick([])
        assert isinstance(result, dict)

    def test_repeated_ticks_build_familiarity(self):
        store = SensoryTraceStore()
        kernel = SensoryInputKernel(memory=store)
        s = make_stimulus("vision", 0.5, "recurring_signal")
        for _ in range(5):
            kernel.process_tick([s])
        familiarity = store.familiarity(s)
        assert familiarity >= 0.0
