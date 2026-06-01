# Fruit Sort — Raspberry Pi 5 + YOLO11n

COCO 사전학습 yolo11n.pt를 그대로 사용해 **apple / banana / orange** 세 클래스만
컨베이어 위에서 판별, 서보 분기로 자동 분류하는 시스템.

## 동작 시퀀스

1. 토글 스위치 ON → 컨베이어 가동
2. 검사대 IR(2cm 근접) 감지 → 컨베이어 정지, YOLO 추론
3. 추론 결과에 따라:
   - 바나나 → 서보1(S1) 45° 기울임 + LED1 ON
   - 사과   → 서보2(S2) 45° 기울임 + LED2 ON
   - 오렌지 → 서보2(S2) 45° 기울임 + LED3 ON
   - 그 외(apple/banana/orange 아님 또는 신뢰도 부족) → 통과
4. 도착 레일 IR 감지 → 서보·LED 복귀
5. 토글 OFF 전까지 반복

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
python3 -m venv ~/venv-fruit --system-site-packages
source ~/venv-fruit/bin/activate
pip install -r requirements.txt
```
`--system-site-packages` 플래그 필수 (picamera2는 apt 전용).

### 3) NCNN 모델 준비 (PC에서 1회)
```bash
python scripts/export_ncnn.py
# → yolo11n_ncnn_model/ 생성
# 이 폴더를 라파이의 fruit-sort/models/ 안으로 복사
```

## 실행
```bash
cd fruit-sort
source ~/venv-fruit/bin/activate
python -m src.main
```

## 점검 스크립트
```bash
python -m scripts.test_hardware   # 모터/서보/LED/IR/스위치 개별 점검
python -m scripts.test_camera     # 카메라+YOLO 단독 점검
```

## 핀 매핑 (BCM)

| 부품              | 핀         | 비고               |
|------------------|-----------|-------------------|
| 토글 스위치        | GPIO17    | 풀업, ON=LOW       |
| IR 검사대          | GPIO27    | 활성 LOW           |
| IR 바나나 레일     | GPIO5     |                   |
| IR 사과 레일       | GPIO6     |                   |
| IR 오렌지 레일     | GPIO16    |                   |
| DC 모터 ENA       | GPIO12    | HW PWM            |
| DC 모터 IN1       | GPIO23    |                   |
| DC 모터 IN2       | GPIO24    |                   |
| 서보 S1 (좌)      | GPIO13    | HW PWM            |
| 서보 S2 (우)      | GPIO18    | HW PWM            |
| LED 바나나         | GPIO20    |                   |
| LED 사과           | GPIO21    |                   |
| LED 오렌지         | GPIO26    |                   |

핀 변경은 `src/config.py`의 `Pins` 클래스만 수정.

## 주의사항

- **PIR이 아닌 IR proximity 모듈 사용 권장**. PIR(인체감지)은 2cm 근접 감지 불가.
- **공통 그라운드**: 모터 전원과 라파이 GND를 반드시 연결.
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
python3 -m venv ~/venv-fruit --system-site-packages
source ~/venv-fruit/bin/activate

ncnn포맷 변경
from ultralytics import YOLO
YOLO("yolo11n.pt").export(format="ncnn", imgsz=320)
# → yolo11n_ncnn_model/ 폴더 생성

pip install --upgrade pip
pip install ultralytics ncnn

2. 동작 원리
2.1. 동작 순서

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
├── requirements.txt
├── models/
│   ├── yolo11n.pt                    # 자동 다운로드된 PyTorch 가중치
│   └── yolo11n_ncnn_model/           # PC에서 변환 후 복사
│       ├── model.ncnn.bin
│       ├── model.ncnn.param
│       └── metadata.yaml
├── src/
│   ├── __init__.py
│   ├── config.py                     # 상수: CONF_TH, N_FRAMES, SERVO_ANGLE,
│   │                                 #       CLASS_TO_PATH, GPIO 핀 번호 등
│   ├── hardware.py                   # GPIO·PWM 초기화, 모터/서보/LED 제어
│   ├── vision.py                     # Picamera2 + YOLO 추론, classify_stable()
│   └── main.py                       # 상태머신 메인 루프
├── scripts/
│   ├── export_ncnn.py                # NCNN 변환 1회 실행 스크립트
│   ├── test_camera.py                # 카메라+YOLO 단독 점검
│   ├── test_conveyor.py              # DC 모터 단독 점검
│   ├── test_servo.py                 # 서보 S1/S2 단독 점검 및 0° 교정
│   ├── test_ir.py                    # IR 센서 4개 트리거 점검
│   └── test_led.py                   # LED 3개 점등 점검
├── logs/                             # 런타임 로그 (gitignore 대상)
│   └── .gitkeep
└── .gitignore

3.2. 상세 설명
- 사전학습 가중치 다운로드
from ultralytics import YOLO
model = YOLO("yolo11n.pt")  # 최초 1회 자동 다운로드

4. 참고문헌
Ultralytics 공식 RPi 가이드 — picamera2 + YOLO 연동 예제 코드
https://docs.ultralytics.com/guides/raspberry-pi

ejtech.io의 yolo_detect.py 튜토리얼 — off-the-shelf YOLO11n NCNN으로 RPi 5에서 약 8 FPS 달성
https://www.ejtech.io/learn/yolo-on-raspberry-pi
