from ..contracts.schemas import TouchFrame


def touch_from_signal(intensity: float, signal: str) -> TouchFrame:
    safe = max(0.0, min(1.0, intensity))
    is_impact = "impact" in signal or "heat" in signal or "pain" in signal
    return TouchFrame(
        pressure=safe,
        vibration=min(1.0, safe * (1.2 if "vibration" in signal else 0.7)),
        temperature=min(1.0, safe * (1.2 if "heat" in signal else 0.4)),
        pain_like=min(1.0, safe * (1.4 if is_impact else 0.2)),
    )

