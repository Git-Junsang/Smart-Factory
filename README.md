# Fruit Sort — Raspberry Pi 5 + YOLO11n

COCO 사전학습 yolo11n.pt를 그대로 사용해 **apple / banana / orange** 세 클래스만
판별하고, 검사대를 앞으로 기울여 과일을 떨어뜨린 뒤 분류 레일이 알맞은 바구니를
받아내는 자동 분류 시스템. 분류 개수는 OLED에 표시한다.

## 동작 시퀀스

1. 푸시버튼1 누름 → 가동 시작(다시 누르면 중단). 가동중 LED1 ON
2. 검사대 IR(2cm 근접) 감지 → 컨베이어(DC1) 정지, LED2 ON, YOLO 추론
3. 추론 결과(다수결)에 따라 분류 레일(DC2)이 알맞은 바구니를 낙하 지점으로 이동
   - 바나나 → 바구니 #0
   - 오렌지 → 바구니 #1
   - 사과   → 바구니 #2
4. 검사대 서보가 앞으로 기울어짐 → 과일이 굴러 바구니로 낙하 → 검사대 평평 복귀
5. 해당 과일 카운트 +1, OLED 갱신 후 컨베이어 재가동
6. 불확실(신뢰도 부족) 시 → 카운트 없이 과일만 비우고 통과(SKIP)
7. 푸시버튼2 → OLED 카운트 전체 0으로 리셋
8. 푸시버튼1로 중단 시 어느 단계에서든 정지, LED3 ON

상태 LED는 항상 하나만 켜진다: **LED1=가동중 / LED2=검사·분류중 / LED3=중단중**.

## 설치

### 1) 시스템 패키지 (apt)
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv \
                    python3-picamera2 python3-libcamera \
                    python3-opencv \
                    python3-lgpio python3-gpiozero
```

### 2) Python 가상환경
```bash
python3 -m venv ~/venv-factory --system-site-packages
source ~/venv-factory/bin/activate
pip install -r requirements.txt
```
`--system-site-packages` 플래그 필수 (picamera2는 apt 전용).

### 3) NCNN 모델 준비 (PC에서 1회)
```bash
python scripts/export_ncnn.py
# → yolo11n_ncnn_model/ 생성
# 이 폴더를 라파이의 Smart-Factory/models/ 안으로 복사
```

## 실행
```bash
cd Smart-Factory
source ~/venv-factory/bin/activate
python -m src.main
```

## 점검 스크립트
```bash
python -m scripts.test_hardware   # 컨베이어/분류레일/서보/LED/IR/버튼 개별 점검
python -m scripts.test_camera     # 카메라+YOLO 단독 점검
```

## 핀 매핑 (BCM)

| 부품 | 핀 | 비고 |
| --- | --- | --- |
| 푸시버튼1 (가동/중단) | GPIO17 | 풀업, 눌림=LOW |
| 푸시버튼2 (카운트 리셋) | GPIO16 | 풀업, 눌림=LOW |
| IR 검사대 | GPIO27 | 활성 LOW |
| DC1 컨베이어 ENA/IN1/IN2 | GPIO12 / 23 / 24 | ENA=HW PWM |
| DC2 분류 레일 ENB/IN3/IN4 | GPIO18 / 5 / 6 | ENB=HW PWM |
| 서보 (검사대 기울임) | GPIO13 | HW PWM |
| LED1 가동중 | GPIO20 | |
| LED2 검사·분류중 | GPIO21 | |
| LED3 중단중 | GPIO26 | |
| OLED (SSD1306 128×64) | I2C SDA=GPIO2, SCL=GPIO3 | addr 0x3C |

핀 변경은 `src/config.py`의 `Pins` 클래스만 수정.

## 주의사항

- **PIR이 아닌 IR proximity 모듈 사용 권장**. PIR(인체감지)은 2cm 근접 감지 불가.
- **공통 그라운드**: 모터 전원과 라파이 GND를 반드시 연결.
- **분류 레일은 시간 기반 개루프**: 위치 센서가 없어 `config.py`의 `RAIL_STEP_TIME`을
  실측해 보정해야 한다. 시작 시 바구니 #0이 낙하 지점에 와 있다고 가정하며,
  누적 오차가 신경 쓰이면 리미트 스위치로 홈 위치를 보강하는 것을 권장.
- **OLED I2C 활성화**: `sudo raspi-config` → Interface Options → I2C 켜기.
  `i2cdetect -y 1`로 주소 확인(기본 0x3C).
- **서보 지터**: gpiozero 기본 SW PWM은 Pi 5에서 지터가 있을 수 있음.
  심하면 PCA9685 PWM 컨트롤러로 업그레이드 권장.
- **NCNN export는 PC에서**: 라파이에서 직접 export는 매우 느림.



<중간 보고서>

1. 작업 환경
1.1. 라즈베리파이 외부 환경에서 소스코드, 빌드 작업 후 git을 통해 라즈베리파이 내에서 run할 예정

1.2. 작업 디렉토리
smart-factory/
├── README.md
├── requirements.txt
├── models/
│   └── yolo11n_ncnn_model/    # PC에서 export 후 복사
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── hardware.py
│   ├── vision.py
│   └── main.py
└── scripts/
    ├── export_ncnn.py
    ├── test_camera.py
    └── test_hardware.py

1.3. 사용한 라이브러리, 패키지
sudo apt update
sudo apt install -y python3-pip python3-venv \
                    python3-picamera2 python3-libcamera \
                    python3-opencv \
                    python3-lgpio python3-gpiozero

requirements.txt에 버전 정보 담겨 있음.

1.4. 가상환경, ncnn
python3 -m venv ~/venv-factory --system-site-packages
source ~/venv-factory/bin/activate

ncnn포맷 변경
from ultralytics import YOLO
YOLO("yolo11n.pt").export(format="ncnn", imgsz=320)
# → yolo11n_ncnn_model/ 폴더 생성

pip install --upgrade pip
pip install ultralytics ncnn

2. 동작 원리
2.1. 동작 순서
① 토글 스위치를 ON으로 올리면 DC 모터가 회전해 컨베이어가 가동된다.
② 물체가 분기점 직전 검사대로 이동하면 IR proximity 센서(2cm 근접)가 감지하고,
   컨베이어를 정지시킨 뒤 흔들림 안정화(DEBOUNCE_TIME)를 거친다.
③ 정지 상태에서 카메라로 N_FRAMES(기본 10) 장을 연속 추론하고, 프레임별 최고
   신뢰도 클래스를 다수결 투표한다. 최다 득표가 VOTE_MIN(기본 6) 이상이면 클래스
   확정, 미만이면 "불확실"로 처리한다.
④ 확정 시: 해당 클래스의 결과 LED를 켜고, PATH_MAP에 따라 서보를 기울여 분기
   레일을 연 뒤 컨베이어를 재가동해 물체를 밀어낸다.
     - 바나나 → S1 45° + LED1   (왼쪽 레일)
     - 사과   → S2 45° + LED2   (오른쪽 레일)
     - 오렌지 → S2 45° + LED3   (오른쪽 레일, 사과와 동일 도착점)
⑤ 도착 레일 IR이 낙하를 확인하면(또는 DROP_TIMEOUT 초과 시) 서보와 LED를
   neutral/OFF로 복귀시키고 다음 사이클을 준비한다.
⑥ 불확실 시: 분기 없이 컨베이어로 물체를 그대로 통과시킨다(SKIP).
⑦ 토글을 OFF로 내리면 어느 단계에서든 모든 장치를 안전 정지하고 IDLE로 돌아간다.

2.2. main.py 상태머신
IDLE ──토글ON──▶ RUNNING ──검사대IR──▶ INSPECTING
                  ▲                       │
                  │                       ├─확정──▶ SORTING ──도착IR──▶ (다시 RUNNING)
                  │                       └─실패──▶ SKIP ───────────────┘
                  └────────────────── 토글OFF ─────────────────────────────────▶ IDLE

3. 소프트웨어
3.1. 파일별 역할
smart-factory/
├── README.md
├── requirements.txt                  # ultralytics, ncnn, numpy<2.0
├── CLAUDE.md                          # 프로젝트 가이드
├── .gitignore
├── logs/                             # 런타임 로그(gitignore 대상)
├── models/
│   └── yolo11n_ncnn_model/           # PC에서 변환 후 복사
│       ├── model.ncnn.bin            # NCNN 가중치(바이너리)
│       ├── model.ncnn.param          # NCNN 네트워크 구조
│       └── metadata.yaml             # 클래스명·imgsz 등 메타정보
├── src/
│   ├── __init__.py
│   ├── config.py                     # 단일 설정 소스: 핀 맵, 클래스 ID,
│   │                                 #   PATH_MAP, SERVO_ANGLE, CONF_TH,
│   │                                 #   N_FRAMES, VOTE_MIN 등 상수 전부
│   ├── hardware.py                   # GPIO·PWM 초기화, 모터/서보/LED/IR 제어
│   ├── vision.py                     # Picamera2 + YOLO 추론, classify_stable()
│   └── main.py                       # FruitSorter 상태머신 메인 루프
└── scripts/
    ├── export_ncnn.py                # yolo11n.pt → NCNN 1회 변환(PC)
    ├── test_camera.py                # 카메라+YOLO 단독 점검
    └── test_hardware.py              # 모터/서보/LED/IR/스위치 수동 점검

  ※ 코드는 PC에서 편집·커밋 → 라즈베리파이에서 git pull 후 실행한다.
    하드웨어 의존 모듈(picamera2, gpiozero/lgpio)은 라파이에서만 import되므로
    src.main / src.hardware / src.vision은 PC에서 실행할 수 없다.

3.2. 상세 설명

(1) config.py — 모든 튜닝값의 단일 소스
  - 하드웨어/동작 변경은 이 파일만 수정하면 된다.
  - COCO 클래스 ID: banana=46, apple=47, orange=49 (TARGET_CLASSES).
    별도 학습 없이 사전학습 COCO 가중치의 이 세 ID만 사용한다.
  - PATH_MAP: 클래스 → "left"/"right"/"neutral" 분기 방향 매핑.
    (예) 오렌지를 직진시키려면 COCO_ORANGE: "neutral" 한 줄만 바꾸면 된다.
  - SERVO_ANGLE: 방향 → (S1, S2) 각도쌍.
    neutral=(0,0), left=(45,0), right=(0,45).
  - Pins(frozen dataclass): BCM 핀 번호. 재배선 시 이 클래스만 수정.
    서보·DC ENA는 Pi 5의 HW PWM 가능 핀(GPIO12/13/18)에 배치해 지터를 줄였다.
  - 임계값: CONF_TH=0.60(YOLO 신뢰도), N_FRAMES=10(투표 프레임 수),
    VOTE_MIN=6(확정 최소 득표), DEBOUNCE/TILT_HOLD/DROP_TIMEOUT(타이밍),
    CONVEYOR_SPEED=0.7(모터 듀티), IMG_SIZE=320(추론 해상도).

(2) hardware.py — GPIO 추상화 계층 (Hardware 클래스)
  - gpiozero로 DC 모터(Motor, PWM)·서보 2개(AngularServo)·LED 3개·토글
    스위치(Button)·IR 4개(DigitalInputDevice)를 객체로 감싼다.
  - Pi 5는 lgpio 핀 팩토리가 필수다. 모듈 로드 시
    Device.pin_factory = LGPIOFactory()로 지정한다.
    (RPi.GPIO·pigpio는 Pi 5에서 동작하지 않음)
  - IR proximity와 토글 스위치는 활성 LOW이므로 triggered = not device.value
    로 판정한다. 토글은 pull_up=True, ON 시 GND로 떨어져 is_pressed=True.
  - 서보는 SG90/MG90S 기준 펄스폭 0.5ms(0°)~2.4ms(90°)로 매핑.
  - 주요 메서드: conveyor_on/off, set_path(direction), led_on/off,
    inspection_triggered(), rail_triggered(class_id),
    reset()(전 장치 안전 정지), cleanup()(종료 시 모든 핸들 close).

(3) vision.py — 카메라 + 추론 계층 (Vision 클래스)
  - Picamera2를 640×480 RGB888로 구성·시작하고 AE/AWB 1초 안정화 후 사용.
  - NCNN 모델은 task를 자동 추론하지 못하므로 YOLO(path, task="detect")로
    명시 로딩한다.
  - 대상 클래스 이중 필터링: ① predict(classes=TARGET_CLASSES)로 추론 단계
    차단, ② detect_once() 내부에서 cls_id·conf를 한 번 더 검증(안전망).
  - detect_once(): 한 프레임에서 최고 신뢰도 박스의 class_id 반환(없으면 None).
  - classify_stable(): N_FRAMES 연속 추론 → Counter 다수결.
    최다 득표가 VOTE_MIN 미만이면 None을 반환해 오분류를 억제한다.

(4) main.py — 상태머신 오케스트레이션 (FruitSorter 클래스)
  - GPIO나 모델을 직접 다루지 않고 self.hw / self.vision만 호출하는 상위 계층.
  - 상태 핸들러: _idle / _running / _inspecting / _sorting / _skip.
    토글 스위치를 전 구간에서 hw.is_running으로 폴링하여, OFF가 되면 어느
    상태에서든 즉시 컨베이어를 멈추고 IDLE로 복귀한다(2.2 상태머신 참고).
  - _sorting(): LED 점등 → 서보 기울임 → 컨베이어 재가동 → 도착 IR 대기
    (DROP_TIMEOUT 한도) → TILT_HOLD_TIME 후 neutral·LED OFF 복귀.
  - SIGINT/SIGTERM 핸들러로 안전 종료, finally 블록에서 hw.cleanup()·
    vision.close()를 보장한다.

(5) scripts/ — 보조 도구
  - export_ncnn.py: PC에서 yolo11n.pt를 NCNN(imgsz=320)으로 1회 변환.
    생성된 yolo11n_ncnn_model/ 폴더를 라파이의 models/로 복사한다.
    (라파이에서 직접 export 시 5~10분 소요)
  - test_camera.py: 컨베이어·서보 없이 비전 모듈만 검증. 검사대 위치에
    과일 사진을 두고 classify_stable() 결과를 반복 출력한다.
  - test_hardware.py: 키보드 입력으로 모터/서보(0°·45°)/LED/IR/스위치를
    개별 수동 점검한다. (자동화 테스트가 아닌 결선 확인용 도구)

  ※ 빌드/lint/자동 테스트는 없으며, test_* 스크립트는 수동 하드웨어 점검용이다.

4. 참고문헌
Ultralytics 공식 RPi 가이드 — picamera2 + YOLO 연동 예제 코드
https://docs.ultralytics.com/guides/raspberry-pi

ejtech.io의 yolo_detect.py 튜토리얼 — off-the-shelf YOLO11n NCNN으로 RPi 5에서 약 8 FPS 달성
https://www.ejtech.io/learn/yolo-on-raspberry-pi
