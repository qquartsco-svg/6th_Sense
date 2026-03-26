> **English:** [README_EN.md](README_EN.md)

# Sensory Input Kernel (SIK)

오감(시각/청각/촉각/후각/미각) 자극을 입력받아,
1) 즉시 반응을 계산하고,
2) 단기/장기 기억으로 축적하며,
3) 5축 상황벡터로 판단하는 경량 커널입니다.

한 줄 정의:
**세계 -> 감각 입력 -> 자극 해석 -> 반응 -> 기억 누적**의 앞문 커널.

흐름 확장:
**오감 수용 -> 육감 발현(느낌/판단 상태) -> 상위 인지/행동 엔진 핸드오프**

## 핵심 목적

- 지식 기반 추론 이전에, **감각 기반 반응 루프**를 표준화
- 자극-반응-기억 연결을 분리 가능한 독립 모듈로 제공
- MemoryPhase_Kernel, FirstOrder, 엣지 호스트가 공통 입력 계층으로 재사용 가능

## 모델

- 입력 채널: `vision`, `hearing`, `touch`, `smell`, `taste`
- 반응 출력: `ReactionDecision(arousal, valence, priority, action)`
- 상황 판단(5축): `SituationVector(threat, novelty, social, urgency, stability)`
- 보조 메타: `dominant_channels` (축이 아닌 채널 우세도 요약)
- 기억:
  - 단기기억: 최근 자극 버퍼
  - 장기기억: `(channel, signal)` 시그니처 빈도 기반 친숙도

중요:

- 현재 구현의 **실채널**은 `vision`, `hearing`, `touch` 중심이다.
- `smell`, `taste`는 현재 `proxy` 입력으로만 다뤄진다.
- 즉 지금 버전은 “오감 완성 엔진”보다 **3실채널 + 2프록시 구조의 sensory front kernel**로 보는 것이 정확하다.
- proxy 예시:
  - `smell`: gas sensor flag, chemical event tag
  - `taste`: ingest event, chemical input tag

## 레이어 구조

핵심 파이프라인 MVP 도입 버전은 `v0.2.0`, 현재 패키지 버전은 `v0.9.2`이다.

- Layer 0 `Raw Channels`: vision/audition/touch 중심 + smell/taste proxy
- Layer 1 `Sensory Frame`: `SensoryFrame`으로 한 틱 감각 상태 결합
- Layer 2 `Salience`: intensity/novelty/urgency/uncertainty/valence 기반 점수화
- Layer 3 `Binding`: 다감각 이벤트 결합 (`BoundEvent`)
- Layer 4 `Affective/Reflex Gate`: 반사 반응 게이트 (`startle_or_evade`, `orient_attention`)
- Layer 5 `Sensory Trace`: 감각 흔적 저장 (`SensoryTraceStore`)
- Layer 6 `Cognitive Handoff`: emotion/memory/action/snn/mpk 브리지 출력
- Layer 6.5 `Felt Sense`: `FeltSenseState` (gut_risk/coherence/confidence/felt_tag)
  - 의미: salience/reflex 후단에서 생성되는 저지연 직관 요약 신호이며, 상위 인지와 MPK 입력에 함께 사용된다.

## 엣지 독립 모듈 (현재 v0.9.2)

- `ingress/`: 센서 입력 어댑터 인터페이스 (`CameraStubIngress`, `MicStubIngress`, `TouchStubIngress`)
- 실연동 ingress:
  - `HostEventIngress`: 앱/로봇 코드에서 `push_event()`로 직접 주입
  - `JsonlTailIngress`: 로컬 JSONL 이벤트 파일 tail 방식 수신
  - `UdpJsonIngress`: UDP JSON 패킷 수신 (`channel/signal/intensity/context/timestamp`)
- `runtime/`: 엣지 루프 (`EdgeSensoryRuntime`) — 큐/드롭 정책/틱 기반 처리
- `contracts/event_schema.py`: 입력 이벤트 스키마 정규화 (`normalize_event`)
- `TracePolicy`: `max_traces`, `ttl_seconds`로 장기 실행 메모리 상한 관리
- 외부 엔진 import 없음(stdlib only) -> 앱/로봇/임베디드 호스트에 부착형으로 사용 가능
- CLI 데몬 엔트리: `sensory-edge-daemon` (health/metrics JSON 출력)
- 선택형 HTTP 상태 엔드포인트: `/health`(JSON), `/metrics`(Prometheus text)
- 장기 실행 모드: `--forever` + SIGINT/SIGTERM graceful shutdown
- 주기적 메트릭 저장: `--metrics-jsonl-path` + `--metrics-flush-every`
- 일자별 메트릭 로테이션: `--metrics-rotate-daily`
- ingress 관측치: `ingress_errors`, `ingress_latency_histogram`
- 육감 관측치: `felt_gut_risk`, `felt_coherence`, `felt_confidence`, `felt_tag_counts`

정리하면:

- 실구현: camera/mic/touch/app-event/jsonl/udp
- 프록시 채널: smell/taste
- 역할: 감각 입력을 바로 지식 추론으로 보내지 않고, 먼저 salience / reflex / trace / handoff 형태로 표준화하는 앞문 커널

## MPK 연결

이 커널은 `MemoryPhase_Kernel` 앞단에 놓이기 좋다.

- `SIK`
  - 감각 입력을 받아 `SituationVector`와 `handoff.mpk_input`으로 정리
- `MPK`
  - 그 입력을 바탕으로 `liquid / semi_frozen / frozen` 위상과 열람 티어를 결정

실전 연결에서는 강결합 import보다 **얇은 bridge payload**가 더 안전하다.

- [mpk_bridge.py](sensory_input_kernel/bridge/mpk_bridge.py)
  - `build_mpk_input()`
  - `build_mpk_channel_scores()`

예제:

```bash
python3 examples/run_sik_mpk_session.py
```

## 핵심 수식

채널별 salience:

`S_i(t) = b_i * [0.4*I_i + 0.3*N_i + 0.2*U_i + 0.1*(1-Q_i)]`

- `I_i`: intensity
- `N_i`: novelty (`1 - familiarity`)
- `U_i`: urgency
- `Q_i`: uncertainty
- `b_i`: 채널 바이어스(vision/hearing/touch/smell/taste)

전체 상황축(예시):

- `threat = max(I_i)`
- `novelty = mean(N_i)`
- `social = clamp01(mean(context_social_cues))`  # 대화/근접/집단 신호의 정규화 요약
- `urgency = mean(U_i)`
- `stability = 1 - urgency`

기억 흔적 보존:

`M_trace <- prune_by_ttl_and_cap(M_trace, ttl_seconds, max_traces)`

## 빠른 시작

```python
from sensory_input_kernel import SensoryInputKernel, SensoryStimulus

kernel = SensoryInputKernel()

stimuli = [
    SensoryStimulus(channel="vision", intensity=0.9, signal="bright_flash"),
    SensoryStimulus(channel="hearing", intensity=0.7, signal="sharp_alarm"),
    SensoryStimulus(channel="touch", intensity=0.5, signal="vibration"),
]

out = kernel.process_tick(stimuli)
print(out["reaction"])
print(out["situation"])
print(out["felt_sense"])
print(out["handoff"].mpk_input)
```

엣지 런타임 부착 예시:

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

CLI 데몬 실행:

```bash
cd _staging/Sensory_Input_Kernel
python3 -m sensory_input_kernel.runtime.daemon_cli --steps 10 --profile balanced --print-metrics --health-port 8088
# 또는 설치 후: sensory-edge-daemon --steps 10 --profile high --print-metrics
```

장기 실행 + JSONL 메트릭 flush:

```bash
sensory-edge-daemon \
  --forever \
  --profile balanced \
  --health-port 8088 \
  --metrics-jsonl-path ./runtime_metrics.jsonl \
  --metrics-flush-every 20 \
  --metrics-rotate-daily
```

앱 코드 직접 부착 예시:

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

실행 샘플 파일:

- 앱 부착 예시: `examples/app_host_attach.py`
- 로봇 UDP 송신 예시: `examples/robot_udp_sender.py`
- Prometheus 설정: `examples/monitoring/prometheus.yml`
- Prometheus 알람 룰: `examples/monitoring/alert_rules.yml`
- Grafana 쿼리 모음: `examples/monitoring/GRAFANA_QUERIES.md`
- Grafana 대시보드 템플릿: `examples/monitoring/grafana_dashboard.json`
- 로컬 실행 가이드: `examples/monitoring/RUN_PROMETHEUS.md`

## 테스트

```bash
cd _staging/Sensory_Input_Kernel
python3 -m pytest tests/ -q --tb=no
```

현재 로컬 점검 기준:

- `19 passed`
- 범주: core pipeline, ingress normalization, runtime queue/drop, MPK bridge, metrics/health

## 버전

- `0.9.1`: 버전/문서 정합 정리 (`VERSION`/`pyproject`/`__version__`, README 검증 수치 동기화)
- `0.9.0`: 오감 -> 육감 확장 추가 (`FeltSenseState`, `felt_sense_input`) 및 핸드오프 연계
- `0.8.0`: metrics 일자 로테이션, `/metrics` Prometheus 출력, ingress 에러/지연 히스토그램 통계 추가
- `0.7.0`: `--forever` 장기 실행, SIGINT/SIGTERM graceful shutdown, metrics JSONL 주기 flush
- `0.6.0`: 이벤트 스키마 고정(`normalize_event`), health HTTP endpoint(`/health`,`/metrics`), examples 2종 추가
- `0.5.0`: 실부착 ingress 추가 — `HostEventIngress`, `JsonlTailIngress`, `UdpJsonIngress`
- `0.4.0`: 실행형 엣지 서비스 진입점 추가 — `runtime_profile`, `daemon_cli`, health/metrics JSON 출력, `sensory-edge-daemon` 스크립트
- `0.3.0`: 엣지 독립 실행 계층 추가 — `ingress`, `EdgeSensoryRuntime`, 큐 드롭 정책, trace TTL/cap
- `0.2.0`: 6-layer 파이프라인(MVP) 도입 — `SensoryFrame`, salience, multisensory binding, reflex gate, sensory trace, cognitive handoff
- `0.1.0`: 초기 릴리즈 (오감 채널, 반응 루프, 단/장기 기억, 5축 상황벡터)

## 변경 이력 / 무결성

- 변경 요약: [CHANGELOG.md](CHANGELOG.md)
- 무결성 설명: [BLOCKCHAIN_INFO.md](BLOCKCHAIN_INFO.md)
- 연속 기록 로그: [PHAM_BLOCKCHAIN_LOG.md](PHAM_BLOCKCHAIN_LOG.md)
- SHA-256 서명 매니페스트: [SIGNATURE.sha256](SIGNATURE.sha256)

중요:

- 여기서 말하는 블록체인은 분산 합의형 네트워크를 뜻하지 않는다.
- 이 저장소에서는 **파일 무결성과 변경 연속성**을 설명하는 문서 패턴을 의미한다.
- 실제 검증은 SHA-256 매니페스트와 검증 스크립트로 수행한다.

검증:

```bash
python3 scripts/verify_signature.py
```

서명 재생성:

```bash
python3 scripts/generate_signature.py
python3 scripts/verify_signature.py
```

## 감각 채널 우선 릴리즈 (6th_Sense)

감각 채널부터 공개할 때는 아래 순서를 권장한다.

1. 테스트 통과: `python3 -m pytest tests/ -q --tb=no`
2. 버전 동기화: `VERSION` / `pyproject.toml` / `sensory_input_kernel.__version__`
3. 서명 갱신: `python3 scripts/generate_signature.py`
4. 서명 검증: `python3 scripts/verify_signature.py`
5. README(한/영)와 CHANGELOG 동기화

## GitHub 업로드 가이드 (qquartsco-svg/6th_Sense)

현재 폴더에서 초기 업로드 시:

```bash
cd _staging/Sensory_Input_Kernel
git init
git add .
git commit -m "Release Sensory Input Kernel v0.9.2"
git branch -M main
git remote add origin https://github.com/qquartsco-svg/6th_Sense.git
git push -u origin main
```

이미 원격이 연결된 경우:

```bash
git add .
git commit -m "Update sensory channels and signature flow"
git push
```
