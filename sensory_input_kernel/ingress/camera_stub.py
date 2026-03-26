import time
from dataclasses import dataclass

from ..contracts.schemas import SensoryStimulus


@dataclass
class CameraStubIngress:
    intensity: float = 0.4
    signal: str = "camera_frame"

    def read(self) -> SensoryStimulus:
        return SensoryStimulus(
            channel="vision",
            intensity=self.intensity,
            signal=self.signal,
            context={"confidence": 0.8, "source": "camera_stub"},
            timestamp=time.time(),
        )

