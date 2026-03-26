from __future__ import annotations

import argparse
import datetime as dt
import json
import signal
import time
from pathlib import Path
from typing import Iterable, List

from .. import CameraStubIngress, MicStubIngress, SensoryInputKernel, TouchStubIngress
from ..ingress.base import SensoryIngress
from .edge_loop import EdgeSensoryRuntime
from .health_server import HealthHttpServer
from .profiles import runtime_profile


def _build_ingress(use_camera: bool, use_mic: bool, use_touch: bool) -> List[SensoryIngress]:
    ingress: List[SensoryIngress] = []
    if use_camera:
        ingress.append(CameraStubIngress())
    if use_mic:
        ingress.append(MicStubIngress())
    if use_touch:
        ingress.append(TouchStubIngress())
    return ingress


def _health_payload(runtime: EdgeSensoryRuntime) -> dict:
    s = runtime.stats
    return {
        "ok": True,
        "ticks": int(s["ticks"]),
        "queue_size": int(s["queued"]),
        "drop_count": int(s["dropped"]),
        "tick_hz": s["tick_hz"],
    }


def _prometheus_metrics(runtime: EdgeSensoryRuntime) -> str:
    s = runtime.stats
    hist = s.get("ingress_latency_histogram", {}) if isinstance(s, dict) else {}
    lines = [
        "# HELP sensory_ticks_total Total sensory ticks",
        "# TYPE sensory_ticks_total counter",
        f"sensory_ticks_total {float(s.get('ticks', 0.0))}",
        "# HELP sensory_queue_size Current queue size",
        "# TYPE sensory_queue_size gauge",
        f"sensory_queue_size {float(s.get('queued', 0.0))}",
        "# HELP sensory_drop_total Dropped stimulus count",
        "# TYPE sensory_drop_total counter",
        f"sensory_drop_total {float(s.get('dropped', 0.0))}",
        "# HELP sensory_ingress_errors_total Ingress read errors",
        "# TYPE sensory_ingress_errors_total counter",
        f"sensory_ingress_errors_total {float(s.get('ingress_errors', 0.0))}",
        "# HELP sensory_ingress_reads_total Ingress read attempts",
        "# TYPE sensory_ingress_reads_total counter",
        f"sensory_ingress_reads_total {float(s.get('ingress_reads', 0.0))}",
        "# HELP sensory_felt_gut_risk Sixth-sense gut risk gauge",
        "# TYPE sensory_felt_gut_risk gauge",
        f"sensory_felt_gut_risk {float(s.get('felt_gut_risk', 0.0))}",
        "# HELP sensory_felt_coherence Sixth-sense coherence gauge",
        "# TYPE sensory_felt_coherence gauge",
        f"sensory_felt_coherence {float(s.get('felt_coherence', 0.0))}",
        "# HELP sensory_felt_confidence Sixth-sense confidence gauge",
        "# TYPE sensory_felt_confidence gauge",
        f"sensory_felt_confidence {float(s.get('felt_confidence', 0.0))}",
    ]
    for k in ("le_1ms", "le_5ms", "le_10ms", "le_50ms", "gt_50ms"):
        v = 0.0
        if isinstance(hist, dict):
            v = float(hist.get(k, 0))
        lines.append(f'sensory_ingress_latency_bucket{{bucket="{k}"}} {v}')
    felt_counts = s.get("felt_tag_counts", {}) if isinstance(s, dict) else {}
    if isinstance(felt_counts, dict):
        for tag in ("premonition_warning", "premonition_clear", "premonition_ambiguous"):
            lines.append(
                f'sensory_felt_tag_total{{tag="{tag}"}} {float(felt_counts.get(tag, 0))}'
            )
    return "\n".join(lines) + "\n"


def _resolve_metrics_path(path: Path, rotate_daily: bool) -> Path:
    if not rotate_daily:
        return path
    stamp = dt.date.today().isoformat()
    if path.suffix:
        return path.with_name(f"{path.stem}-{stamp}{path.suffix}")
    return path.with_name(f"{path.name}-{stamp}")


def run_daemon(
    *,
    steps: int,
    profile: str,
    use_camera: bool,
    use_mic: bool,
    use_touch: bool,
    print_metrics: bool,
    health_host: str = "127.0.0.1",
    health_port: int = 0,
    forever: bool = False,
    metrics_jsonl_path: str = "",
    metrics_flush_every: int = 10,
    metrics_rotate_daily: bool = False,
) -> int:
    kernel = SensoryInputKernel()
    runtime = EdgeSensoryRuntime(kernel, runtime_profile(profile))
    ingress = _build_ingress(use_camera, use_mic, use_touch)
    if not ingress:
        raise ValueError("At least one ingress source must be enabled.")
    server = None
    if health_port >= 0:
        try:
            server = HealthHttpServer(
                health_host,
                health_port,
                health_provider=lambda: {"health": _health_payload(runtime), "metrics": runtime.stats},
                metrics_provider=lambda: _prometheus_metrics(runtime),
            )
            server.start()
        except OSError:
            server = None
    stopping = False

    def _stop_handler(signum, frame) -> None:  # type: ignore[no-untyped-def]
        nonlocal stopping
        stopping = True

    prev_int = signal.getsignal(signal.SIGINT)
    prev_term = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGINT, _stop_handler)
    signal.signal(signal.SIGTERM, _stop_handler)

    outputs = []
    tick_target = max(1, steps)
    tick_count = 0
    flush_every = max(1, metrics_flush_every)
    metrics_path = Path(metrics_jsonl_path) if metrics_jsonl_path else None

    try:
        while (forever and not stopping) or (not forever and tick_count < tick_target):
            started = time.perf_counter()
            runtime.collect_from_ingress(ingress)
            out = runtime.tick()
            outputs.append(out)
            tick_count += 1

            if metrics_path is not None and (tick_count % flush_every == 0):
                resolved_path = _resolve_metrics_path(metrics_path, metrics_rotate_daily)
                resolved_path.parent.mkdir(parents=True, exist_ok=True)
                payload = {
                    "ts": time.time(),
                    "metrics": runtime.stats,
                    "latest_action": out.get("reaction").action if out.get("reaction") else "none",
                    "latest_situation": out.get("situation").__dict__ if out.get("situation") else {},
                    "latest_felt_sense": out.get("felt_sense").__dict__ if out.get("felt_sense") else {},
                }
                with resolved_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(payload, ensure_ascii=True) + "\n")

            tick_dt = 1.0 / max(1e-6, runtime.config.tick_hz)
            elapsed = time.perf_counter() - started
            sleep_for = tick_dt - elapsed
            if sleep_for > 0:
                time.sleep(sleep_for)
    finally:
        signal.signal(signal.SIGINT, prev_int)
        signal.signal(signal.SIGTERM, prev_term)
        if server is not None:
            server.stop()

    payload = {"health": _health_payload(runtime)}
    if server is not None:
        payload["health_endpoint"] = f"http://{health_host}:{server.port}/health"
    print(json.dumps(payload, ensure_ascii=True))
    if print_metrics:
        latest = outputs[-1] if outputs else {}
        payload = {
            "metrics": runtime.stats,
            "latest_situation": latest.get("situation").__dict__ if latest.get("situation") else {},
            "latest_action": latest.get("reaction").action if latest.get("reaction") else "none",
            "latest_felt_sense": latest.get("felt_sense").__dict__ if latest.get("felt_sense") else {},
        }
        print(json.dumps(payload, ensure_ascii=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sensory Input Kernel edge daemon")
    parser.add_argument("--steps", type=int, default=30, help="Number of ticks to execute")
    parser.add_argument(
        "--profile",
        choices=("ultra_low", "balanced", "high"),
        default="balanced",
        help="Runtime profile",
    )
    parser.add_argument("--no-camera", action="store_true", help="Disable camera stub ingress")
    parser.add_argument("--no-mic", action="store_true", help="Disable mic stub ingress")
    parser.add_argument("--no-touch", action="store_true", help="Disable touch stub ingress")
    parser.add_argument("--print-metrics", action="store_true", help="Print metrics payload")
    parser.add_argument("--forever", action="store_true", help="Run until SIGINT/SIGTERM")
    parser.add_argument(
        "--metrics-jsonl-path",
        default="",
        help="Optional JSONL path for periodic metrics flush",
    )
    parser.add_argument(
        "--metrics-flush-every",
        type=int,
        default=10,
        help="Flush metrics every N ticks when metrics-jsonl-path is set",
    )
    parser.add_argument(
        "--metrics-rotate-daily",
        action="store_true",
        help="Rotate metrics JSONL output file by date suffix",
    )
    parser.add_argument("--health-host", default="127.0.0.1", help="Health endpoint host")
    parser.add_argument(
        "--health-port",
        type=int,
        default=0,
        help="Health endpoint port (0=auto, -1=disable)",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return run_daemon(
        steps=max(1, args.steps),
        profile=args.profile,
        use_camera=not args.no_camera,
        use_mic=not args.no_mic,
        use_touch=not args.no_touch,
        print_metrics=args.print_metrics,
        health_host=args.health_host,
        health_port=args.health_port,
        forever=args.forever,
        metrics_jsonl_path=args.metrics_jsonl_path,
        metrics_flush_every=args.metrics_flush_every,
        metrics_rotate_daily=args.metrics_rotate_daily,
    )


if __name__ == "__main__":
    raise SystemExit(main())
