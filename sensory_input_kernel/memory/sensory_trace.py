import time
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple

from ..contracts.schemas import BoundEvent, SenseChannel, SensoryStimulus, SensoryTrace, TracePolicy


@dataclass
class SensoryTraceStore:
    short_term_limit: int = 64
    trace_policy: TracePolicy = field(default_factory=TracePolicy)
    short_term: List[SensoryStimulus] = field(default_factory=list)
    traces: List[SensoryTrace] = field(default_factory=list)
    long_term_signatures: Dict[Tuple[SenseChannel, str], int] = field(default_factory=dict)

    def remember_stimulus(self, stimulus: SensoryStimulus) -> None:
        self.short_term.append(stimulus)
        if len(self.short_term) > self.short_term_limit:
            self.short_term.pop(0)
        key = (stimulus.channel, stimulus.signal)
        self.long_term_signatures[key] = self.long_term_signatures.get(key, 0) + 1

    def familiarity(self, stimulus: SensoryStimulus) -> float:
        hits = self.long_term_signatures.get((stimulus.channel, stimulus.signal), 0)
        return min(1.0, hits / 10.0) if hits > 0 else 0.0

    def _prune(self, now: float) -> None:
        ttl = self.trace_policy.ttl_seconds
        if ttl > 0:
            self.traces = [t for t in self.traces if (now - t.timestamp) <= ttl]
        cap = self.trace_policy.max_traces
        if cap > 0 and len(self.traces) > cap:
            self.traces = self.traces[-cap:]

    def write_trace(self, events: Iterable[BoundEvent], context_tag: str, valence: float) -> None:
        now = time.time()
        for event in events:
            self.traces.append(
                SensoryTrace(
                    event_id=event.event_id,
                    dominant_channels=event.channels,
                    salience=event.salience,
                    valence=valence,
                    context_tag=context_tag,
                    timestamp=now,
                )
            )
        self._prune(now)

