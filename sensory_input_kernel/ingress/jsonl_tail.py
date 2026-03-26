import json
import time
from dataclasses import dataclass

from ..contracts.event_schema import normalize_event
from ..contracts.schemas import SensoryStimulus


@dataclass
class JsonlTailIngress:
    path: str
    fallback_channel: str = "vision"
    _offset: int = 0

    def _read_next_line(self) -> str:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                f.seek(self._offset)
                line = f.readline()
                if line:
                    self._offset = f.tell()
                return line
        except FileNotFoundError:
            return ""

    def read(self) -> SensoryStimulus:
        line = self._read_next_line().strip()
        if not line:
            return SensoryStimulus(
                channel=self.fallback_channel,  # type: ignore[arg-type]
                intensity=0.0,
                signal="jsonl_idle",
                context={"source": "jsonl_tail_idle"},
                timestamp=time.time(),
            )
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return SensoryStimulus(
                channel=self.fallback_channel,  # type: ignore[arg-type]
                intensity=0.1,
                signal="jsonl_parse_error",
                context={"source": "jsonl_tail", "raw": line[:120]},
                timestamp=time.time(),
            )

        obj.setdefault("signal", "jsonl_event")
        obj.setdefault("intensity", 0.3)
        obj.setdefault("timestamp", time.time())
        return normalize_event(obj, default_channel=self.fallback_channel)

