> **Korean (canonical):** [README.md](README.md)

# Sensory Input Kernel (SIK)

SIK is a lightweight kernel that accepts five-sense stimuli
(vision/hearing/touch/smell/taste), then:
1) computes immediate reactions,
2) stores short-term and long-term memory traces,
3) emits a 5-axis situation judgement vector.

One-line definition:
**world -> sensory input -> stimulus interpretation -> reaction -> memory trace**.

Extended flow:
**five-sense intake -> sixth-sense emergence (felt judgement state) -> cognitive/action handoff**

## Core Goal

- Standardize a **sense-first reaction loop** before knowledge-heavy reasoning
- Keep stimulus-reaction-memory logic as an independent reusable module
- Provide a common input layer for MemoryPhase_Kernel, FirstOrder, and edge hosts

## Model

- Input channels: `vision`, `hearing`, `touch`, `smell`, `taste`
- Reaction output: `ReactionDecision(arousal, valence, priority, action)`
- Situation output: `SituationVector(threat, novelty, social, urgency, stability, dominant_channels)`
- Memory:
  - Short-term memory: recent stimulus buffer
  - Long-term memory: familiarity from `(channel, signal)` signature frequency

## Layered MVP (v0.2.0)

- Layer 0 `Raw Channels`: vision/audition/touch first, with smell/taste proxies
- Layer 1 `Sensory Frame`: per-tick merged frame (`SensoryFrame`)
- Layer 2 `Salience`: intensity/novelty/urgency/uncertainty/valence scoring
- Layer 3 `Binding`: multisensory event binding (`BoundEvent`)
- Layer 4 `Affective/Reflex Gate`: reflex gating (`startle_or_evade`, `orient_attention`)
- Layer 5 `Sensory Trace`: memory trace persistence (`SensoryTraceStore`)
- Layer 6 `Cognitive Handoff`: bridge outputs for emotion/memory/action/snn/mpk
- Layer 6.5 `Felt Sense`: `FeltSenseState` (gut_risk/coherence/confidence/felt_tag)

## Edge-Ready Independent Module (v0.9.1)

- `ingress/`: sensor adapter interface (`CameraStubIngress`, `MicStubIngress`, `TouchStubIngress`)
- production-style ingress options:
  - `HostEventIngress`: direct host/app injection via `push_event()`
  - `JsonlTailIngress`: local JSONL tail ingestion
  - `UdpJsonIngress`: UDP JSON packet ingestion (`channel/signal/intensity/context/timestamp`)
- `runtime/`: edge loop (`EdgeSensoryRuntime`) with queue/drop policy/tick processing
- `contracts/event_schema.py`: normalized input-event schema (`normalize_event`)
- `TracePolicy`: long-running memory bounds (`max_traces`, `ttl_seconds`)
- stdlib-only and no external engine import, so hosts can attach it directly (apps/robots/edge devices)
- CLI daemon entrypoint: `sensory-edge-daemon` (health/metrics JSON output)
- optional HTTP status endpoints: `/health` (JSON), `/metrics` (Prometheus text)
- long-running mode: `--forever` with graceful SIGINT/SIGTERM shutdown
- periodic metrics sink: `--metrics-jsonl-path` + `--metrics-flush-every`
- daily rotation for metrics sink: `--metrics-rotate-daily`
- ingress observability fields: `ingress_errors`, `ingress_latency_histogram`
- felt-sense observability fields: `felt_gut_risk`, `felt_coherence`, `felt_confidence`, `felt_tag_counts`

In practice:

- implemented channels: camera/mic/touch/app-event/jsonl/udp
- proxy channels: smell/taste
- role: standardize sensory intake into salience / reflex / trace / handoff before heavier cognition

## MPK handoff

SIK fits naturally in front of `MemoryPhase_Kernel`.

- `SIK`
  - converts sensory input into a `SituationVector` and `handoff.mpk_input`
- `MPK`
  - decides `liquid / semi_frozen / frozen` phase and allowed interpretability tiers

The preferred integration is a **thin bridge payload**, not a hard package dependency.

- `build_mpk_input()`
- `build_mpk_channel_scores()`

Example:

```bash
python3 examples/run_sik_mpk_session.py
```

## Core Equations

Per-channel salience:

`S_i(t) = b_i * [0.4*I_i + 0.3*N_i + 0.2*U_i + 0.1*(1-Q_i)]`

- `I_i`: intensity
- `N_i`: novelty (`1 - familiarity`)
- `U_i`: urgency
- `Q_i`: uncertainty
- `b_i`: channel bias (vision/hearing/touch/smell/taste)

Situation axes (example):

- `threat = max(I_i)`
- `novelty = mean(N_i)`
- `urgency = mean(U_i)`
- `stability = 1 - urgency`

Trace retention:

`M_trace <- prune_by_ttl_and_cap(M_trace, ttl_seconds, max_traces)`

## Quick Start

```python
from sensory_input_kernel import SensoryInputKernel, SensoryStimulus

kernel = SensoryInputKernel()
stimuli = [
    SensoryStimulus(channel="vision", intensity=0.9, signal="bright_flash"),
    SensoryStimulus(channel="hearing", intensity=0.7, signal="sharp_alarm"),
]
out = kernel.process_tick(stimuli)
print(out["reaction"])
print(out["situation"])
print(out["felt_sense"])
print(out["handoff"].mpk_input)
```

Edge attachment example:

```python
from sensory_input_kernel import (
    CameraStubIngress, MicStubIngress, TouchStubIngress,
    EdgeRuntimeConfig, EdgeSensoryRuntime, SensoryInputKernel
)

kernel = SensoryInputKernel()
rt = EdgeSensoryRuntime(kernel, EdgeRuntimeConfig(tick_hz=20.0, max_queue_size=128))
ingress = [CameraStubIngress(), MicStubIngress(), TouchStubIngress()]

outs = rt.run_steps(steps=5, ingress=ingress)
print(rt.stats)
print(outs[-1]["situation"])
```

CLI daemon run:

```bash
cd _staging/Sensory_Input_Kernel
python3 -m sensory_input_kernel.runtime.daemon_cli --steps 10 --profile balanced --print-metrics --health-port 8088
# or after install: sensory-edge-daemon --steps 10 --profile high --print-metrics
```

Long-running + JSONL metrics flush:

```bash
sensory-edge-daemon \
  --forever \
  --profile balanced \
  --health-port 8088 \
  --metrics-jsonl-path ./runtime_metrics.jsonl \
  --metrics-flush-every 20 \
  --metrics-rotate-daily
```

Direct host attachment example:

```python
from sensory_input_kernel import HostEventIngress, SensoryInputKernel, EdgeSensoryRuntime

ing = HostEventIngress()
kernel = SensoryInputKernel()
rt = EdgeSensoryRuntime(kernel)

ing.push_event({"channel": "vision", "signal": "person_detected", "intensity": 0.85})
rt.collect_from_ingress([ing])
out = rt.tick()
print(out["situation"])
```

Example scripts:

- app attachment: `examples/app_host_attach.py`
- robot UDP sender: `examples/robot_udp_sender.py`
- Prometheus config: `examples/monitoring/prometheus.yml`
- Prometheus alert rules: `examples/monitoring/alert_rules.yml`
- Grafana queries: `examples/monitoring/GRAFANA_QUERIES.md`
- Grafana dashboard template: `examples/monitoring/grafana_dashboard.json`
- local monitoring runbook: `examples/monitoring/RUN_PROMETHEUS.md`

## Test

```bash
cd _staging/Sensory_Input_Kernel
python3 -m pytest tests/ -q --tb=no
```

Current local verification baseline:

- `19 passed`

## Changelog / Integrity

- change summary: `CHANGELOG.md`
- integrity note: `BLOCKCHAIN_INFO.md`
- continuity log: `PHAM_BLOCKCHAIN_LOG.md`
- SHA-256 manifest: `SIGNATURE.sha256`

Important:

- the word "blockchain" here does not mean a distributed consensus network
- in this repository it refers to a **continuity and integrity documentation pattern**
- actual verification is done through the SHA-256 manifest and verification script

Verification:

```bash
python3 scripts/verify_signature.py
```

Regenerate signature manifest:

```bash
python3 scripts/generate_signature.py
python3 scripts/verify_signature.py
```

## Sensory-Channel-First Release (6th_Sense)

For a channel-first public release, use this sequence:

1. Run tests: `python3 -m pytest tests/ -q --tb=no`
2. Sync version markers: `VERSION` / `pyproject.toml` / `sensory_input_kernel.__version__`
3. Regenerate signature: `python3 scripts/generate_signature.py`
4. Verify signature: `python3 scripts/verify_signature.py`
5. Keep README(KR/EN) and CHANGELOG in sync

## GitHub Publish Guide (qquartsco-svg/6th_Sense)

Initial upload from this folder:

```bash
cd _staging/Sensory_Input_Kernel
git init
git add .
git commit -m "Release Sensory Input Kernel v0.9.2"
git branch -M main
git remote add origin https://github.com/qquartsco-svg/6th_Sense.git
git push -u origin main
```

If remote is already connected:

```bash
git add .
git commit -m "Update sensory channels and signature flow"
git push
```

## Version

- `0.9.2`: added signature manifest generator script and release/publish runbook for sensory-channel-first deployment
- `0.9.1`: version/doc consistency sync (`VERSION`/`pyproject`/`__version__`, README verification baseline)
- `0.9.0`: five-sense to sixth-sense extension (`FeltSenseState`, `felt_sense_input`) integrated into handoff
- `0.8.0`: daily metrics rotation, Prometheus `/metrics`, ingress error/latency histogram stats
- `0.7.0`: `--forever` mode, graceful signal shutdown, periodic JSONL metrics flush
- `0.6.0`: fixed input schema (`normalize_event`), health HTTP endpoint support, 2 example scripts
- `0.5.0`: practical host/robot ingress adapters (`HostEventIngress`, `JsonlTailIngress`, `UdpJsonIngress`)
- `0.4.0`: executable edge service entrypoint with runtime profiles and health/metrics JSON
- `0.3.0`: edge runtime and ingress adapters with queue/drop/memory retention controls
- `0.2.0`: layered pipeline MVP with frame/salience/binding/reflex/trace/handoff
- `0.1.0`: initial release (5-sense channels, reaction loop, memory, 5-axis judgement)
