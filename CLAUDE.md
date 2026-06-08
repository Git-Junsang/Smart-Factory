# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

**Raspberry Pi 5** 기반 과일 분류 시스템. 사전학습된 COCO `yolo11n` 모델(NCNN 포맷)로 검사대 위 물체를 apple / banana / orange로 판별한다. 별도 학습 없이 COCO 클래스 ID 46(banana), 47(apple), 49(orange)만 사용한다.

**분류 메커니즘:** 검사대는 **앞으로만** 기울어지는 서보 1개를 갖는다. **카메라(YOLO)에 과일이 감지되면** 컨베이어(DC1)를 멈추고 추론한 뒤, **분류 레일(DC2)이 클래스에 맞는 바구니를 낙하 지점으로 이동**시키고, 검사대를 앞으로 기울여 과일을 굴려 떨어뜨린다. DC2는 위치 센서가 없어 **시간 기반 개루프**(`current_basket`를 소프트웨어로 추적, 시작 위치 = `HOME_BASKET`)로 제어한다. 분류 개수는 **OLED(SSD1306, I2C)**에 표시한다.

**입력/제어:** 푸시버튼1이 가동/중단을 **토글**(`hw.is_running` 플래그를 뒤집음)하고, 푸시버튼2가 OLED 카운트를 리셋한다. 상태 LED 3개는 **항상 하나만** 켜진다(가동중 / 검사·분류중 / 사용자 중단중).

**머신 간 작업 흐름:** 코드는 개발용 PC에서 편집·커밋하고, 라즈베리파이에서 pull 받아 실행한다. NCNN 모델은 PC에서 export(`scripts/export_ncnn.py`)한 뒤 생성된 `yolo11n_ncnn_model/` 폴더를 라파이의 `models/`로 복사한다 — 라파이에서 직접 export 하면 5~10분 걸린다. 하드웨어 의존 모듈(`picamera2`, `gpiozero`/`lgpio`, `luma.oled`)은 라파이에서만 해석되므로, `src.main`·`src.hardware`·`src.vision`·`src.display`는 PC에서 실행·import 할 수 없다.

## 명령어

```bash
# 시스템 실행 (라파이, venv 활성화 상태)
python -m src.main

# 하드웨어 점검 (라파이)
python -m scripts.test_hardware   # 컨베이어 / 분류레일 / 서보 / LED / IR / 버튼
python -m scripts.test_camera     # 카메라 + YOLO 추론 단독 점검

# 모델 export (PC에서 1회) → yolo11n_ncnn_model/ 를 models/ 로 복사
python scripts/export_ncnn.py
```

`picamera2`가 apt 전용이라 venv는 반드시 `--system-site-packages`로 생성:
```bash
python3 -m venv ~/venv-factory --system-site-packages
source ~/venv-factory/bin/activate && pip install -r requirements.txt
```

build / lint / 자동 테스트는 없다. `scripts/test_*`는 자동화 테스트가 아니라 수동 하드웨어 점검용 도구다.

## 아키텍처

`src/` 아래 4개 계층과 중앙 설정 파일로 구성:

- **[src/config.py](src/config.py)** — 모든 튜닝값의 단일 소스. 하드웨어 변경 대응은 *이 파일만* 수정한다. 포함: GPIO 핀 맵(`Pins`/`PINS`), COCO 클래스 ID + `CLASS_NAMES`, `BASKET_INDEX`(클래스 → 분류 레일 위 바구니 위치 0/1/2), 시간 기반 레일 상수(`RAIL_SPEED`, `RAIL_STEP_TIME`, `HOME_BASKET`), 서보 기울임 각도(`TILT_LEVEL_ANGLE`/`TILT_FORWARD_ANGLE`), OLED 설정(`OLED_*`, `COUNT_ORDER`), 타이밍/임계값 상수(`CONF_TH`, `N_FRAMES`, `VOTE_MIN` 등).
- **[src/hardware.py](src/hardware.py)** — `gpiozero`로 모든 GPIO 디바이스를 감싼 `Hardware` 클래스. Pi 5는 `lgpio` 핀 팩토리가 **필수**(모듈 로드 시 설정); `RPi.GPIO`/`pigpio`는 Pi 5에서 동작하지 않는다. 푸시버튼은 **활성 LOW**(풀업, 눌림=LOW) — 검사대 물체 감지는 IR이 아니라 카메라가 담당한다. 버튼1은 `when_pressed` 콜백으로 `is_running` 플래그를 **토글**한다. `move_rail_to(idx)`는 현재 위치와의 칸 차이만큼 DC2를 시간 구동하는 **개루프** 제어다. `set_status('run'|'inspect'|'stop')`는 상태 LED를 **배타 점등**한다. `reset()`/`cleanup()`은 모든 장치를 안전 정지 상태로 되돌린다.
- **[src/vision.py](src/vision.py)** — `Picamera2` + NCNN `YOLO` 모델을 감싼 `Vision` 클래스. NCNN 모델은 `task="detect"`를 명시해야 한다. 대상 클래스는 **이중 필터링**: `predict(classes=TARGET_CLASSES)`로 한 번, `detect_once()` 내부에서 다시 한 번(안전망). `detect()`는 단일 프레임 추론으로 **RUNNING 트리거**(검사대 물체 감지)에 쓰이고, `classify_stable()`은 정지 후 `N_FRAMES` 다수결 투표로 최종 분류하며 최다 득표가 `VOTE_MIN` 미만이면 `None`을 반환한다.
- **[src/display.py](src/display.py)** — `luma.oled`로 SSD1306(I2C)을 감싼 `Display` 클래스. 과일별 카운트를 보관하고 한 페이지에 그린다(`increment()`/`reset()`/`render()`). I2C 활성화 필요.
- **[src/main.py](src/main.py)** — `FruitSorter` 상태머신. 오케스트레이션 계층으로, GPIO/모델/OLED를 직접 다루지 않고 `self.hw`·`self.vision`·`self.display`만 호출한다. 생성 시 `hw.on_reset(display.reset)`로 버튼2를 카운트 리셋에 연결한다.

### 상태머신 (src/main.py)

```
IDLE ──버튼1(RUN)──▶ RUNNING ──검사대 IR──▶ INSPECTING
        ▲                                       │
        │                            ┌──클래스 확정──▶ SORTING ──낙하·카운트──┐
        │                            └──불확실────▶ SKIP ────────────────┐   │
        └──────────── 버튼1(STOP, 어느 상태든) ──────────────────────────┘   │
                                                                             ▼
                                                                         RUNNING
```

버튼1은 누를 때마다 RUN↔STOP을 토글하며, 전 구간에서 `hw.is_running`으로 폴링된다. STOP이 되면 어느 상태에서든 IDLE로 복귀한다. `SORTING`은 **분류 레일을 알맞은 바구니로 이동(`move_rail_to`) → 검사대를 앞으로 기울여 낙하(`tilt_forward` → `TILT_HOLD_TIME` → `tilt_level`) → 카운트 +1(OLED 갱신)** 순으로 동작한다. 서보는 **세 과일 중 하나로 확정됐을 때만** 기울어진다 — `SKIP`(불확실)은 기울임·카운트 모두 하지 않고 넘어간다. 버튼2는 어느 때든 OLED 카운트를 0으로 리셋한다.

검사대 물체 감지는 **카메라(YOLO)**로 한다 — RUNNING 중 `vision.detect()`가 대상 과일을 감지하면 컨베이어를 멈추고 `CAMERA_STOP_TIME`(2초) 안정화 후 추론한다. 한 사이클을 처리하면 **카메라에서 과일이 사라질 때까지 대기**(`_wait_clear`)해 같은 과일 재감지를 막는다. (IR/PIR 근접센서는 쓰지 않는다.)

## 동작 변경 시 규칙

- 바구니 위치 재지정(예: 오렌지/사과 위치 교환): config의 `BASKET_INDEX`만 수정.
- 분류 레일 이동량 보정: config의 `RAIL_STEP_TIME`(한 칸 이동 시간), `RAIL_SPEED`.
- 검사대 기울임 정도: config의 `TILT_FORWARD_ANGLE`, `TILT_HOLD_TIME`.
- 핀 재배선: config의 `Pins` 데이터클래스만 수정.
- 인식 견고성 튜닝: config의 `CONF_TH`, `N_FRAMES`, `VOTE_MIN`, `IMG_SIZE`.
- 분류 레일은 위치 센서가 없는 **개루프**다 — 누적 오차가 생길 수 있으며, 시작 시 `HOME_BASKET`(기본 0)이 낙하 지점에 있다고 가정한다.

## README 참고사항

- 검사대 물체 감지는 **카메라(YOLO)**로 처리(IR/PIR 근접센서 미사용). 카메라가 정지 지점을 향하게 설치.
- 모터 전원과 라파이는 **공통 그라운드**를 공유해야 한다.
- OLED는 **I2C 활성화** 필요(`raspi-config` → Interface → I2C, 기본 주소 0x3C).
- gpiozero 기본 소프트웨어 PWM은 Pi 5에서 서보 지터를 유발할 수 있다; 심하면 PCA9685 컨트롤러로 업그레이드.
