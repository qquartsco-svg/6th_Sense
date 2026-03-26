import json
import socket
import time


def main() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target = ("127.0.0.1", 8787)
    events = [
        {
            "channel": "touch",
            "signal": "impact",
            "intensity": 0.88,
            "context": {"confidence": 0.9, "source": "imu"},
            "timestamp": time.time(),
        },
        {
            "channel": "vision",
            "signal": "approach_object",
            "intensity": 0.72,
            "context": {"confidence": 0.85, "source": "stereo_cam"},
            "timestamp": time.time(),
        },
    ]
    for event in events:
        sock.sendto(json.dumps(event).encode("utf-8"), target)
    print("sent", len(events), "events")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

