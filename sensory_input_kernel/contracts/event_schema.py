from typing import Any, Dict

from .schemas import SensoryStimulus

ALLOWED_CHANNELS = {"vision", "hearing", "touch", "smell", "taste"}


def normalize_event(event: Dict[str, Any], *, default_channel: str = "vision") -> SensoryStimulus:
    channel = str(event.get("channel", default_channel))
    if channel not in ALLOWED_CHANNELS:
        channel = default_channel if default_channel in ALLOWED_CHANNELS else "vision"
    signal = str(event.get("signal", "event"))
    intensity = max(0.0, min(1.0, float(event.get("intensity", 0.3))))
    context = event.get("context", {})
    if not isinstance(context, dict):
        context = {"raw_context": str(context)}
    timestamp = float(event.get("timestamp", 0.0))
    return SensoryStimulus(  # type: ignore[arg-type]
        channel=channel,
        signal=signal,
        intensity=intensity,
        context=context,
        timestamp=timestamp,
    )

