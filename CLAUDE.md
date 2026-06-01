# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

**Raspberry Pi 5** 기반 과일 분류 컨베이어 시스템. 사전학습된 COCO `yolo11n` 모델(NCNN 포맷)로 컨베이어 위 물체를 apple / banana / orange로 판별하고, 서보 분기로 각 레일에 분류한다. 별도 학습 없이 COCO 클래스 ID 46(banana), 47(apple), 49(orange)만 사용한다.

**머신 간 작업 흐름:** 코드는 개발용 PC에서 편집·커밋하고, 라즈베리파이에서 pull 받아 실행한다. NCNN 모델은 PC에서 export(`scripts/export_ncnn.py`)한 뒤 생성된 `yolo11n_ncnn_model/` 폴더를 라파이의 `models/`로 복사한다 — 라파이에서 직접 export 하면 5~10분 걸린다. 하드웨어 의존 모듈(`picamera2`, `gpiozero`/`lgpio`)은 라파이에서만 해석되므로, `src.main`·`src.hardware`·`src.vision`은 PC에서 실행·import 할 수 없다.

## 명령어

```bash
# 시스템 실행 (라파이, venv 활성화 상태)
python -m src.main

# 하드웨어 점검 (라파이)
python -m scripts.test_hardware   # 모터 / 서보 / LED / IR / 스위치
python -m scripts.test_camera     # 카메라 + YOLO 추론 단독 점검

# 모델 export (PC에서 1회) → yolo11n_ncnn_model/ 를 models/ 로 복사
python scripts/export_ncnn.py
```

`picamera2`가 apt 전용이라 venv는 반드시 `--system-site-packages`로 생성:
```bash
python3 -m venv ~/venv-fruit --system-site-packages
source ~/venv-fruit/bin/activate && pip install -r requirements.txt
```

build / lint / 자동 테스트는 없다. `scripts/test_*`는 자동화 테스트가 아니라 수동 하드웨어 점검용 도구다.

## 아키텍처

`src/` 아래 3개 계층과 중앙 설정 파일로 구성:

- **[src/config.py](src/config.py)** — 모든 튜닝값의 단일 소스. 하드웨어 변경 대응은 *이 파일만* 수정한다. 포함: GPIO 핀 맵(`Pins`/`PINS`), COCO 클래스 ID + `CLASS_NAMES`, `PATH_MAP`(클래스 → `"left"`/`"right"`/`"neutral"`), `SERVO_ANGLE`(방향 → `(S1, S2)` 각도쌍), 타이밍/임계값 상수(`CONF_TH`, `N_FRAMES`, `VOTE_MIN` 등).
- **[src/hardware.py](src/hardware.py)** — `gpiozero`로 모든 GPIO 디바이스를 감싼 `Hardware` 클래스. Pi 5는 `lgpio` 핀 팩토리가 **필수**(모듈 로드 시 설정); `RPi.GPIO`/`pigpio`는 Pi 5에서 동작하지 않는다. IR 센서와 토글 스위치는 **활성 LOW**(`triggered = not device.value`). `reset()`/`cleanup()`은 모든 장치를 안전 정지 상태로 되돌린다.
- **[src/vision.py](src/vision.py)** — `Picamera2` + NCNN `YOLO` 모델을 감싼 `Vision` 클래스. NCNN 모델은 `task="detect"`를 명시해야 한다. 대상 클래스는 **이중 필터링**: `predict(classes=TARGET_CLASSES)`로 한 번, `detect_once()` 내부에서 다시 한 번(안전망). `classify_stable()`은 `N_FRAMES` 다수결 투표를 하며, 최다 득표가 `VOTE_MIN` 미만이면 `None`을 반환한다.
- **[src/main.py](src/main.py)** — `FruitSorter` 상태머신. 오케스트레이션 계층으로, GPIO나 모델을 직접 다루지 않고 `self.hw`·`self.vision`만 호출한다.

### 상태머신 (src/main.py)

```
IDLE ──토글 ON──▶ RUNNING ──검사대 IR──▶ INSPECTING
        ▲                                     │
        │                          ┌──클래스 확정──▶ SORTING ──도착 IR / 타임아웃──┐
        │                          └──불확실────▶ SKIP ──────────────────────┐  │
        └──────────── 토글 OFF (어느 상태든) ──────────────────────────────┘  │
                                                                              ▼
                                                                          RUNNING
```

토글 스위치는 전 구간에서 `hw.is_running`으로 폴링되며, OFF로 내리면 어느 상태에서든 IDLE로 복귀한다. `SORTING`은 컨베이어를 재가동해 물체를 분기 플랩 너머로 밀고, 도착 레일 IR을 기다린 뒤(`DROP_TIMEOUT` 한도), 서보/LED를 neutral로 복귀시킨다.

## 동작 변경 시 규칙

- 과일 경로 재지정(예: 오렌지를 직진으로): config의 `PATH_MAP`만 수정.
- 핀 재배선: config의 `Pins` 데이터클래스만 수정.
- 인식 견고성 튜닝: config의 `CONF_TH`, `N_FRAMES`, `VOTE_MIN`, `IMG_SIZE`.
- 기본값에서 apple과 orange는 같은 `"right"` 경로(동일 도착점)를 공유한다 — 명세에 따른 의도된 동작이며 버그가 아니다.

## README 참고사항

- 2cm 검사대 트리거에는 **IR proximity** 모듈 사용(인체감지용 PIR 아님).
- 모터 전원과 라파이는 **공통 그라운드**를 공유해야 한다.
- gpiozero 기본 소프트웨어 PWM은 Pi 5에서 서보 지터를 유발할 수 있다; 심하면 PCA9685 컨트롤러로 업그레이드.
