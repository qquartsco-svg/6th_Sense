"""
Bridge demo: Sensory Input Kernel -> Memory Phase Kernel.

Run from 00_BRAIN root or from this package root:
    python3 examples/run_sik_mpk_session.py
"""

from pathlib import Path
import sys


HERE = Path(__file__).resolve()
ROOT = HERE.parents[3]
SIK_ROOT = HERE.parents[1]
MPK_ROOT = ROOT / "_staging" / "MemoryPhase_Kernel"

for candidate in (SIK_ROOT, MPK_ROOT):
    path = str(candidate)
    if path not in sys.path:
        sys.path.insert(0, path)

from sensory_input_kernel import (  # noqa: E402
    SensoryInputKernel,
    SensoryStimulus,
    build_mpk_channel_scores,
)
from memory_phase_kernel import (  # noqa: E402
    IdentityProfile,
    LiveSignalFrame,
    MemoryPhaseKernel,
    readings_from_simple_map,
)


def main() -> int:
    sik = SensoryInputKernel()
    mpk = MemoryPhaseKernel()

    profile = IdentityProfile(
        subject_id="demo-user",
        channel_weights={
            "sensory_threat": 0.35,
            "sensory_novelty": 0.20,
            "sensory_social": 0.10,
            "sensory_urgency": 0.20,
            "sensory_stability": 0.15,
        },
    )

    stimuli = [
        SensoryStimulus(channel="vision", intensity=0.82, signal="person_detected"),
        SensoryStimulus(channel="hearing", intensity=0.35, signal="familiar_voice"),
        SensoryStimulus(channel="touch", intensity=0.10, signal="idle_contact"),
    ]
    sensory_out = sik.process_tick(stimuli)
    mpk_scores = build_mpk_channel_scores(sensory_out["situation"])
    frame = LiveSignalFrame(readings=readings_from_simple_map(mpk_scores))
    decision = mpk.evaluate(profile, frame)

    print("SIK situation:", sensory_out["situation"])
    print("MPK scores:", mpk_scores)
    print("MPK phase:", decision.phase.value)
    print("MPK tiers:", ", ".join(decision.allowed_tiers))
    print("MPK resonance:", f"{decision.score_bundle.resonance_index:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
