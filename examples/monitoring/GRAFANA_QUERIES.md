# Sensory Input Kernel - Grafana PromQL Queries

## Core runtime

- Tick rate (per second):
  - `rate(sensory_ticks_total[1m])`
- Queue size:
  - `sensory_queue_size`
- Dropped events (per minute):
  - `increase(sensory_drop_total[1m])`

## Ingress reliability

- Ingress errors (per minute):
  - `increase(sensory_ingress_errors_total[1m])`
- Ingress reads (per minute):
  - `increase(sensory_ingress_reads_total[1m])`
- Error ratio:
  - `increase(sensory_ingress_errors_total[5m]) / clamp_min(increase(sensory_ingress_reads_total[5m]), 1)`

## Ingress latency histogram buckets

- <=1ms:
  - `sensory_ingress_latency_bucket{bucket="le_1ms"}`
- <=5ms:
  - `sensory_ingress_latency_bucket{bucket="le_5ms"}`
- <=10ms:
  - `sensory_ingress_latency_bucket{bucket="le_10ms"}`
- <=50ms:
  - `sensory_ingress_latency_bucket{bucket="le_50ms"}`
- >50ms:
  - `sensory_ingress_latency_bucket{bucket="gt_50ms"}`

## Sixth-sense (felt) metrics

- Gut risk:
  - `sensory_felt_gut_risk`
- Coherence:
  - `sensory_felt_coherence`
- Confidence:
  - `sensory_felt_confidence`
- Felt tag counters:
  - `sensory_felt_tag_total{tag="premonition_warning"}`
  - `sensory_felt_tag_total{tag="premonition_clear"}`
  - `sensory_felt_tag_total{tag="premonition_ambiguous"}`

## Recommended alert examples

- Queue buildup:
  - `sensory_queue_size > 0`
- Sustained drops:
  - `increase(sensory_drop_total[5m]) > 0`
- Ingress unstable:
  - `increase(sensory_ingress_errors_total[5m]) > 0`

