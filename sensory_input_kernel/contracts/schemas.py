from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Tuple

SenseChannel = Literal["vision", "hearing", "touch", "smell", "taste"]


@dataclass(frozen=True)
class SensoryStimulus:
    channel: SenseChannel
    intensity: float
    signal: str
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass(frozen=True)
class VisionFrame:
    brightness: float = 0.0
    motion: float = 0.0
    proximity: float = 0.0
    object_hint: str = "unknown"


@dataclass(frozen=True)
class AudioFrame:
    loudness: float = 0.0
    pitch_shift: float = 0.0
    rhythm_change: float = 0.0
    voice_hint: str = "ambient"


@dataclass(frozen=True)
class TouchFrame:
    pressure: float = 0.0
    vibration: float = 0.0
    temperature: float = 0.0
    pain_like: float = 0.0


@dataclass(frozen=True)
class SensoryFrame:
    vision: VisionFrame = VisionFrame()
    audition: AudioFrame = AudioFrame()
    touch: TouchFrame = TouchFrame()
    smell_proxy: float = 0.0
    taste_proxy: float = 0.0
    stimuli: Tuple[SensoryStimulus, ...] = ()


@dataclass(frozen=True)
class StimulusScore:
    channel: SenseChannel
    intensity: float
    novelty: float
    urgency: float
    uncertainty: float
    valence_tendency: float
    stimulus_score: float
    salience_score: float


@dataclass(frozen=True)
class BoundEvent:
    event_id: str
    channels: Tuple[SenseChannel, ...]
    salience: float
    threat_hint: float


@dataclass(frozen=True)
class ReflexDecision:
    triggered: bool
    action: str
    threat_bias: float
    attention_focus: List[SenseChannel]


@dataclass(frozen=True)
class SensoryTrace:
    event_id: str
    dominant_channels: Tuple[SenseChannel, ...]
    salience: float
    valence: float
    context_tag: str
    timestamp: float = 0.0


@dataclass(frozen=True)
class ReactionDecision:
    arousal: float
    valence: float
    priority: float
    action: str


@dataclass(frozen=True)
class SituationVector:
    threat: float
    novelty: float
    social: float
    urgency: float
    stability: float
    dominant_channels: List[SenseChannel]


@dataclass(frozen=True)
class FeltSenseState:
    gut_risk: float
    coherence: float
    confidence: float
    felt_tag: str
    summary: str


@dataclass(frozen=True)
class CognitiveHandoff:
    emotion_input: Dict[str, Any]
    memory_input: Dict[str, Any]
    action_input: Dict[str, Any]
    snn_input: Dict[str, Any]
    mpk_input: Dict[str, Any]
    felt_sense_input: Dict[str, Any]


@dataclass(frozen=True)
class TracePolicy:
    max_traces: int = 4096
    ttl_seconds: float = 3600.0


@dataclass(frozen=True)
class EdgeRuntimeConfig:
    tick_hz: float = 30.0
    max_queue_size: int = 256
    drop_policy: Literal["drop_oldest", "drop_newest"] = "drop_oldest"

