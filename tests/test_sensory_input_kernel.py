import json
import time
import urllib.request
from typing import cast

import pytest

from sensory_input_kernel import (
    CameraStubIngress,
    EdgeRuntimeConfig,
    EdgeSensoryRuntime,
    HostEventIngress,
    JsonlTailIngress,
    SensoryInputKernel,
    SensoryStimulus,
    SensoryTraceStore,
    TouchStubIngress,
    TracePolicy,
    UdpJsonIngress,
    build_mpk_channel_scores,
)
from sensory_input_kernel.runtime.daemon_cli import run_daemon
from sensory_input_kernel.runtime.health_server import HealthHttpServer
from sensory_input_kernel.runtime.profiles import runtime_profile
from sensory_input_kernel.contracts.event_schema import normalize_event


def test_kernel_reacts_and_memorizes() -> None:
    kernel = SensoryInputKernel()
    stimuli = [
        SensoryStimulus(channel="vision", intensity=0.8, signal="flash"),
        SensoryStimulus(channel="hearing", intensity=0.7, signal="alarm"),
    ]
    out = kernel.process_tick(stimuli)

    assert out["reaction"].priority > 0.0
    assert out["situation"].urgency > 0.0
    assert len(kernel.memory.short_term) == 2
    assert out["handoff"].action_input["action"] in {"startle_or_evade", "orient_attention", "monitor"}


def test_familiar_signal_reduces_novelty() -> None:
    kernel = SensoryInputKernel()
    stimulus = SensoryStimulus(channel="touch", intensity=0.6, signal="tap")
    for _ in range(12):
        kernel.memory.remember_stimulus(stimulus)

    out = kernel.process_tick([stimulus])
    assert out["situation"].novelty < 0.2
    assert out["reaction"].action in {"monitor", "ignore_minor"}


def test_multisensory_binding_creates_event() -> None:
    kernel = SensoryInputKernel()
    out = kernel.process_tick(
        [
            SensoryStimulus(channel="vision", intensity=0.95, signal="flash_approach"),
            SensoryStimulus(channel="hearing", intensity=0.9, signal="alarm"),
            SensoryStimulus(channel="touch", intensity=0.8, signal="impact"),
        ]
    )
    assert len(out["events"]) >= 1
    assert out["reflex"].triggered is True


def test_mpk_handoff_has_sensory_5axis() -> None:
    kernel = SensoryInputKernel()
    out = kernel.process_tick([SensoryStimulus(channel="vision", intensity=0.4, signal="scan")])
    mpk = out["handoff"].mpk_input
    assert "mak_sensitivity_tier" in mpk
    assert "sensory_5axis" in mpk


def test_mpk_channel_scores_bridge_has_stable_keys() -> None:
    kernel = SensoryInputKernel()
    out = kernel.process_tick([SensoryStimulus(channel="vision", intensity=0.4, signal="scan")])
    payload = build_mpk_channel_scores(out["situation"])
    assert sorted(payload) == [
        "sensory_novelty",
        "sensory_social",
        "sensory_stability",
        "sensory_threat",
        "sensory_urgency",
    ]


def test_felt_sense_is_emitted_and_handed_off() -> None:
    kernel = SensoryInputKernel()
    out = kernel.process_tick(
        [
            SensoryStimulus(channel="vision", intensity=0.9, signal="flash_approach"),
            SensoryStimulus(channel="touch", intensity=0.85, signal="impact"),
        ]
    )
    felt = out["felt_sense"]
    assert 0.0 <= felt.gut_risk <= 1.0
    assert felt.felt_tag in {"premonition_warning", "premonition_clear", "premonition_ambiguous"}
    assert "felt_sense_input" in out["handoff"].__dict__


def test_edge_runtime_queue_drop_policy() -> None:
    kernel = SensoryInputKernel()
    runtime = EdgeSensoryRuntime(
        kernel,
        EdgeRuntimeConfig(tick_hz=100.0, max_queue_size=2, drop_policy="drop_oldest"),
    )
    runtime.collect_from_ingress([CameraStubIngress(), CameraStubIngress(), CameraStubIngress()])
    assert runtime.stats["queued"] <= 2.0
    assert runtime.stats["dropped"] >= 1.0


def test_edge_runtime_tracks_ingress_errors_and_latency() -> None:
    class BadIngress:
        def read(self):
            raise RuntimeError("boom")

    kernel = SensoryInputKernel()
    runtime = EdgeSensoryRuntime(kernel)
    runtime.collect_from_ingress([BadIngress()])  # type: ignore[list-item]
    stats = runtime.stats
    assert float(stats["ingress_errors"]) >= 1.0
    hist = cast(dict, stats["ingress_latency_histogram"])
    assert sum(hist.values()) >= 1


def test_edge_runtime_tracks_felt_sense_metrics() -> None:
    kernel = SensoryInputKernel()
    runtime = EdgeSensoryRuntime(kernel)
    runtime.collect_from_ingress([CameraStubIngress(), TouchStubIngress()])
    runtime.tick()
    stats = runtime.stats
    assert float(stats["felt_gut_risk"]) >= 0.0
    assert str(stats["felt_tag"]) in {"premonition_warning", "premonition_clear", "premonition_ambiguous"}
    counts = cast(dict, stats["felt_tag_counts"])
    assert sum(counts.values()) >= 1


def test_trace_policy_prunes_by_cap() -> None:
    store = SensoryTraceStore(trace_policy=TracePolicy(max_traces=2, ttl_seconds=9999.0))
    kernel = SensoryInputKernel(memory=store)
    for _ in range(5):
        kernel.process_tick([SensoryStimulus(channel="vision", intensity=0.9, signal="flash_approach")])
    assert len(kernel.memory.traces) <= 2


def test_runtime_profile_values() -> None:
    assert runtime_profile("ultra_low").tick_hz == 10.0
    assert runtime_profile("balanced").max_queue_size == 256
    assert runtime_profile("high").tick_hz == 60.0


def test_daemon_runner_smoke() -> None:
    code = run_daemon(
        steps=2,
        profile="balanced",
        use_camera=True,
        use_mic=False,
        use_touch=True,
        print_metrics=False,
    )
    assert code == 0


def test_daemon_metrics_jsonl_flush(tmp_path) -> None:
    path = tmp_path / "metrics.jsonl"
    code = run_daemon(
        steps=3,
        profile="balanced",
        use_camera=True,
        use_mic=False,
        use_touch=True,
        print_metrics=False,
        health_port=-1,
        metrics_jsonl_path=str(path),
        metrics_flush_every=1,
    )
    assert code == 0
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 3
    obj = json.loads(lines[0])
    assert "metrics" in obj


def test_host_event_ingress_push_and_read() -> None:
    ingress = HostEventIngress()
    ingress.push_event({"channel": "vision", "signal": "face_detected", "intensity": 0.9})
    s = ingress.read()
    assert s.channel == "vision"
    assert s.signal == "face_detected"
    assert s.intensity > 0.8


def test_jsonl_tail_ingress_reads_line(tmp_path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text('{"channel":"touch","signal":"tap","intensity":0.6}\n', encoding="utf-8")
    ingress = JsonlTailIngress(str(path))
    s = ingress.read()
    assert s.channel == "touch"
    assert s.signal == "tap"
    assert s.intensity == 0.6


def test_udp_ingress_idle_nonblocking() -> None:
    ingress = UdpJsonIngress(port=0, timeout_s=0.0001)
    s = ingress.read()
    assert s.signal in {"udp_idle", "udp_socket_error"}


def test_normalize_event_schema_bounds_and_channel() -> None:
    s = normalize_event({"channel": "invalid", "signal": "x", "intensity": 99}, default_channel="touch")
    assert s.channel == "touch"
    assert s.intensity == 1.0


def test_health_server_serves_json() -> None:
    try:
        server = HealthHttpServer(
            "127.0.0.1",
            0,
            health_provider=lambda: {"ok": True, "v": 1},
            metrics_provider=lambda: "demo_metric 1\n",
        )
    except OSError as exc:
        pytest.skip(f"socket bind unavailable in this environment: {exc}")
    server.start()
    try:
        time.sleep(0.02)
        with urllib.request.urlopen(f"http://127.0.0.1:{server.port}/health", timeout=1.0) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        assert body["ok"] is True
        assert body["v"] == 1
    finally:
        server.stop()


def test_health_server_serves_prometheus_metrics() -> None:
    try:
        server = HealthHttpServer(
            "127.0.0.1",
            0,
            health_provider=lambda: {"ok": True},
            metrics_provider=lambda: "sensory_ticks_total 3\n",
        )
    except OSError as exc:
        pytest.skip(f"socket bind unavailable in this environment: {exc}")
    server.start()
    try:
        time.sleep(0.02)
        with urllib.request.urlopen(f"http://127.0.0.1:{server.port}/metrics", timeout=1.0) as resp:
            text = resp.read().decode("utf-8")
        assert "sensory_ticks_total" in text
    finally:
        server.stop()
