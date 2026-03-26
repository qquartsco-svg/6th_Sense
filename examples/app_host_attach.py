import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sensory_input_kernel import EdgeSensoryRuntime, HostEventIngress, SensoryInputKernel


def main() -> int:
    ingress = HostEventIngress()
    kernel = SensoryInputKernel()
    runtime = EdgeSensoryRuntime(kernel)

    ingress.push_event(
        {
            "channel": "vision",
            "signal": "operator_face_detected",
            "intensity": 0.82,
            "context": {"confidence": 0.93, "source": "camera_app"},
        }
    )
    ingress.push_event(
        {
            "channel": "hearing",
            "signal": "alarm_beep",
            "intensity": 0.77,
            "context": {"confidence": 0.87, "source": "audio_app"},
        }
    )

    runtime.collect_from_ingress([ingress])
    out = runtime.tick()
    print(out["situation"])
    print(out["reaction"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

