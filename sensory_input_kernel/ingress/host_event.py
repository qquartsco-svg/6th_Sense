import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict

from ..contracts.event_schema import normalize_event
from ..contracts.schemas import SensoryStimulus


@dataclass
class HostEventIngress:
    default_channel: str = "vision"
    default_signal: str = "host_event"
    default_intensity: float = 0.3
    _queue: Deque[SensoryStimulus] = field(default_factory=deque)

    def push_event(self, event: Dict[str, object]) -> None:
        payload = dict(event)
        payload.setdefault("signal", self.default_signal)
        payload.setdefault("intensity", self.default_intensity)
        payload.setdefault("timestamp", time.time())
        self._queue.append(
            normalize_event(payload, default_channel=self.default_channel)
        )

    def read(self) -> SensoryStimulus:
        if self._queue:
            return self._queue.popleft()
        return SensoryStimulus(
            channel=self.default_channel,  # type: ignore[arg-type]
            intensity=0.0,
            signal="idle",
            context={"source": "host_event_ingress_idle"},
            timestamp=time.time(),
        )

