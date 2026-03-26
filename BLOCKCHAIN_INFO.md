# BLOCKCHAIN_INFO

## 목적

`Sensory_Input_Kernel`의 핵심 파일 무결성과 변경 연속성을 기록하기 위한 문서입니다.

이 저장소에서 "블록체인"은 분산 합의형 퍼블릭 네트워크를 뜻하지 않습니다.
여기서는 다음 두 가지를 묶어 부르는 운영 표현입니다.

- `SIGNATURE.sha256` 기반 파일 무결성 확인
- `PHAM_BLOCKCHAIN_LOG.md` 기반 변경 연속성 기록

## 왜 필요한가

이 커널은 감각 입력을 상위 인지/보안 계층으로 전달하는 앞문 레이어입니다.
입력 경계가 흔들리면 이후의 salience, reflex, trace, MPK handoff 해석도 함께 흔들릴 수 있습니다.

그래서 최소한 아래는 명확해야 합니다.

- 어떤 파일이 현재 정본인가
- 어떤 버전 설명이 현재 코드와 맞는가
- 배포/검토 시 파일 변조가 없었는가

## 검증 방식

1. `SIGNATURE.sha256`에 파일별 SHA-256 해시를 기록한다.
2. `scripts/verify_signature.py`로 현재 파일과 매니페스트를 비교한다.
3. 결과를 `OK` / `MISMATCH` / `MISSING`으로 표시한다.
4. 릴리즈 직전에는 `scripts/generate_signature.py`로 매니페스트를 재생성한다.

## 범위

현재는 저장소 단위 무결성 확인이 목적입니다.

- 파일 존재 여부
- 파일 내용 해시 일치
- 릴리스 설명과 버전 정합성

아직 포함하지 않는 것:

- 원격 서명 인프라
- 외부 키 서버
- 분산 합의
- 하드웨어 루트 오브 트러스트

## 실행

```bash
python3 scripts/generate_signature.py
python3 scripts/verify_signature.py
```
