from __future__ import annotations

import time
from collections import deque
from typing import Deque, Dict, Iterable, List

from ..contracts.schemas import EdgeRuntimeConfig, SensoryStimulus
from ..ingress.base import SensoryIngress
from ..sensory_kernel import SensoryInputKernel


class EdgeSensoryRuntime:
    def __init__(self, kernel: SensoryInputKernel, config: EdgeRuntimeConfig | None = None) -> None:
        self.kernel = kernel
        self.config = config or EdgeRuntimeConfig()
        self._queue: Deque[SensoryStimulus] = deque()
        self._ticks = 0
        self._dropped = 0
        self._ingress_errors = 0
        self._ingress_reads = 0
        self._ingress_latency_hist: Dict[str, int] = {
            "le_1ms": 0,
            "le_5ms": 0,
            "le_10ms": 0,
            "le_50ms": 0,
            "gt_50ms": 0,
        }
        self._felt_gut_risk = 0.0
        self._felt_coherence = 0.0
        self._felt_confidence = 0.0
        self._felt_tag = "premonition_ambiguous"
        self._felt_tag_counts: Dict[str, int] = {
            "premonition_warning": 0,
            "premonition_clear": 0,
            "premonition_ambiguous": 0,
        }

    def _observe_ingress_latency(self, elapsed_ms: float) -> None:
        if elapsed_ms <= 1.0:
            self._ingress_latency_hist["le_1ms"] += 1
        elif elapsed_ms <= 5.0:
            self._ingress_latency_hist["le_5ms"] += 1
        elif elapsed_ms <= 10.0:
            self._ingress_latency_hist["le_10ms"] += 1
        elif elapsed_ms <= 50.0:
            self._ingress_latency_hist["le_50ms"] += 1
        else:
            self._ingress_latency_hist["gt_50ms"] += 1

    @property
    def stats(self) -> Dict[str, object]:
        return {
            "ticks": float(self._ticks),
            "queued": float(len(self._queue)),
            "dropped": float(self._dropped),
            "tick_hz": self.config.tick_hz,
            "ingress_reads": float(self._ingress_reads),
            "ingress_errors": float(self._ingress_errors),
            "ingress_latency_histogram": dict(self._ingress_latency_hist),
            "felt_gut_risk": float(self._felt_gut_risk),
            "felt_coherence": float(self._felt_coherence),
            "felt_confidence": float(self._felt_confidence),
            "felt_tag": self._felt_tag,
            "felt_tag_counts": dict(self._felt_tag_counts),
        }

    def enqueue(self, stimuli: Iterable[SensoryStimulus]) -> None:
        for s in stimuli:
            if len(self._queue) >= self.config.max_queue_size:
                if self.config.drop_policy == "drop_oldest":
                    self._queue.popleft()
                    self._dropped += 1
                else:
                    self._dropped += 1
                    continue
            self._queue.append(s)

    def collect_from_ingress(self, ingress: Iterable[SensoryIngress]) -> None:
        collected: List[SensoryStimulus] = []
        for source in ingress:
            started = time.perf_counter()
            try:
                collected.append(source.read())
            except Exception:
                self._ingress_errors += 1
            finally:
                elapsed_ms = (time.perf_counter() - started) * 1000.0
                self._observe_ingress_latency(elapsed_ms)
                self._ingress_reads += 1
        self.enqueue(collected)

    def tick(self, max_items_per_tick: int = 16) -> Dict[str, object]:
        batch: List[SensoryStimulus] = []
        for _ in range(min(max_items_per_tick, len(self._queue))):
            batch.append(self._queue.popleft())
        self._ticks += 1
        out = self.kernel.process_tick(batch)
        felt = out.get("felt_sense")
        if felt is not None:
            self._felt_gut_risk = float(getattr(felt, "gut_risk", 0.0))
            self._felt_coherence = float(getattr(felt, "coherence", 0.0))
            self._felt_confidence = float(getattr(felt, "confidence", 0.0))
            tag = str(getattr(felt, "felt_tag", "premonition_ambiguous"))
            self._felt_tag = tag
            self._felt_tag_counts[tag] = self._felt_tag_counts.get(tag, 0) + 1
        return out

    def run_steps(self, steps: int, ingress: Iterable[SensoryIngress]) -> List[Dict[str, object]]:
        outputs: List[Dict[str, object]] = []
        tick_dt = 1.0 / max(1e-6, self.config.tick_hz)
        for _ in range(steps):
            started = time.perf_counter()
            self.collect_from_ingress(ingress)
            outputs.append(self.tick())
            elapsed = time.perf_counter() - started
            sleep_for = tick_dt - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)
        return outputs
