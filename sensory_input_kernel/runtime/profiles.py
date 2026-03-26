from ..contracts.schemas import EdgeRuntimeConfig


def runtime_profile(name: str) -> EdgeRuntimeConfig:
    key = name.strip().lower()
    if key == "ultra_low":
        return EdgeRuntimeConfig(tick_hz=10.0, max_queue_size=64, drop_policy="drop_oldest")
    if key == "high":
        return EdgeRuntimeConfig(tick_hz=60.0, max_queue_size=512, drop_policy="drop_oldest")
    # default: balanced profile for most edge hosts.
    return EdgeRuntimeConfig(tick_hz=30.0, max_queue_size=256, drop_policy="drop_oldest")

