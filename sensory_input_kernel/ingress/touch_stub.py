import time
from dataclasses import dataclass

from ..contracts.schemas import SensoryStimulus


@dataclass
class TouchStubIngress:
    intensity: float = 0.2
    signal: str = "touch_idle"

    def read(self) -> SensoryStimulus:
        return SensoryStimulus(
            channel="touch",
            intensity=self.intensity,
            signal=self.signal,
            context={"confidence": 0.85, "source": "touch_stub"},
            timestamp=time.time(),
        )

