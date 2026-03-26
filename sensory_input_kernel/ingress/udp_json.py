import json
import socket
import time
from dataclasses import dataclass, field
from typing import Optional

from ..contracts.event_schema import normalize_event
from ..contracts.schemas import SensoryStimulus


@dataclass
class UdpJsonIngress:
    host: str = "127.0.0.1"
    port: int = 8787
    timeout_s: float = 0.001
    fallback_channel: str = "hearing"
    _sock: Optional[socket.socket] = field(default=None, init=False)

    def _ensure_socket(self) -> socket.socket:
        if self._sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((self.host, self.port))
            sock.settimeout(self.timeout_s)
            self._sock = sock
        return self._sock

    def read(self) -> SensoryStimulus:
        try:
            sock = self._ensure_socket()
        except OSError:
            return SensoryStimulus(
                channel=self.fallback_channel,  # type: ignore[arg-type]
                intensity=0.0,
                signal="udp_socket_error",
                context={"source": "udp_json_bind_error"},
                timestamp=time.time(),
            )
        try:
            data, _ = sock.recvfrom(4096)
        except (socket.timeout, BlockingIOError):
            return SensoryStimulus(
                channel=self.fallback_channel,  # type: ignore[arg-type]
                intensity=0.0,
                signal="udp_idle",
                context={"source": "udp_json_idle"},
                timestamp=time.time(),
            )
        except OSError:
            return SensoryStimulus(
                channel=self.fallback_channel,  # type: ignore[arg-type]
                intensity=0.0,
                signal="udp_socket_error",
                context={"source": "udp_json_error"},
                timestamp=time.time(),
            )

        try:
            obj = json.loads(data.decode("utf-8"))
            obj.setdefault("signal", "udp_event")
            obj.setdefault("intensity", 0.3)
            obj.setdefault("timestamp", time.time())
            return normalize_event(obj, default_channel=self.fallback_channel)
        except Exception:
            return SensoryStimulus(
                channel=self.fallback_channel,  # type: ignore[arg-type]
                intensity=0.1,
                signal="udp_parse_error",
                context={"source": "udp_json_parse"},
                timestamp=time.time(),
            )
