from ..contracts.schemas import VisionFrame


def vision_from_signal(intensity: float, signal: str) -> VisionFrame:
    safe = max(0.0, min(1.0, intensity))
    motion = min(1.0, safe * (1.2 if "approach" in signal or "flash" in signal else 0.8))
    proximity = min(1.0, safe * (1.1 if "close" in signal else 0.7))
    return VisionFrame(brightness=safe, motion=motion, proximity=proximity, object_hint=signal)

