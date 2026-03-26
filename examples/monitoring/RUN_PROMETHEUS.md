# Run Prometheus Locally

## 1) Start sensory daemon

```bash
cd _staging/Sensory_Input_Kernel
sensory-edge-daemon \
  --forever \
  --profile balanced \
  --health-port 8088 \
  --metrics-jsonl-path ./runtime_metrics.jsonl \
  --metrics-flush-every 20 \
  --metrics-rotate-daily
```

## 2) Start Prometheus

```bash
prometheus --config.file=examples/monitoring/prometheus.yml
```

Open [http://localhost:9090/targets](http://localhost:9090/targets) and verify `sensory_input_kernel` is `UP`.
Open [http://localhost:9090/rules](http://localhost:9090/rules) and verify `sensory_input_kernel_alerts` is loaded.

## 3) Query metrics

- `rate(sensory_ticks_total[1m])`
- `sensory_queue_size`
- `increase(sensory_drop_total[5m])`
- `increase(sensory_ingress_errors_total[5m])`

## 4) Grafana dashboard

Use panel queries in `examples/monitoring/GRAFANA_QUERIES.md`.

Or import:

- `examples/monitoring/grafana_dashboard.json`

After import, set datasource UID from `PROMETHEUS_UID` to your Prometheus datasource UID.

## 5) Alert rules

Rule file:

- `examples/monitoring/alert_rules.yml`

Included alerts:

- `SensoryFeltWarningSpike`
- `SensoryHighGutRisk`
- `SensoryIngressErrorRatioHigh`
- `SensoryQueueBacklog`

