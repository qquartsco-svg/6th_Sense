from typing import Protocol

from ..contracts.schemas import SensoryStimulus


class SensoryIngress(Protocol):
    def read(self) -> SensoryStimulus:
        ...

