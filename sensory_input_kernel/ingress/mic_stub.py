import time
from dataclasses import dataclass

from ..contracts.schemas import SensoryStimulus


@dataclass
class MicStubIngress:
    intensity: float = 0.3
    signal: str = "ambient_audio"

    def read(self) -> SensoryStimulus:
        return SensoryStimulus(
            channel="hearing",
            intensity=self.intensity,
            signal=self.signal,
            context={"confidence": 0.75, "source": "mic_stub"},
            timestamp=time.time(),
        )

