# Changelog

## 0.9.2

- added `scripts/generate_signature.py` for deterministic SHA-256 manifest generation
- added release/publish runbook to README and README_EN (sensory-channel-first rollout)
- kept blockchain-style integrity flow explicit: regenerate then verify before push

## 0.9.1

- added `tests/conftest.py` so the suite can be collected from outside the package root
- clarified current local verification result in Korean and English READMEs
- added integrity documentation and SHA-256 verification workflow
- synchronized runtime package version marker (`sensory_input_kernel.__version__`) with release version
- added `SIK -> MPK` bridge payload example and refreshed verification baseline notes

## 0.9.0

- added `FeltSenseState` and sixth-sense style handoff expansion
- added `build_mpk_channel_scores()` and SIK -> MPK session example
- hardened socket-restricted runtime behavior for UDP ingress and health server startup
- clarified real channels vs proxy channels in documentation
