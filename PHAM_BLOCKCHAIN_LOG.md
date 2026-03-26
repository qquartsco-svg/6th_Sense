# PHAM_BLOCKCHAIN_LOG

## 2026-03-26

- established integrity documents for `Sensory_Input_Kernel`
- added SHA-256 manifest verification flow
- aligned README and README_EN with current test baseline and release scope
- fixed test bootstrap so `pytest` collection works outside the package root

## 2026-03-27

- added deterministic signature manifest generator (`scripts/generate_signature.py`)
- documented sensory-channel-first release sequence and GitHub publish runbook
- refreshed integrity workflow to require regenerate -> verify before release push
