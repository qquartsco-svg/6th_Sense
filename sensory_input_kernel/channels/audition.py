from ..contracts.schemas import AudioFrame


def audition_from_signal(intensity: float, signal: str) -> AudioFrame:
    safe = max(0.0, min(1.0, intensity))
    alert = "alarm" in signal or "siren" in signal
    return AudioFrame(
        loudness=safe,
        pitch_shift=min(1.0, safe * (1.3 if alert else 0.6)),
        rhythm_change=min(1.0, safe * (1.1 if alert else 0.5)),
        voice_hint=signal,
    )

