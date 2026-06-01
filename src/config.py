"""GPIO 핀 매핑 및 시스템 상수.

이 파일만 수정하면 하드웨어 변경에 대응 가능합니다.
"""
from dataclasses import dataclass

# ============================================================
# COCO 클래스 ID (yolo11n.pt 사전학습 모델 기준)
# ============================================================
COCO_BANANA = 46
COCO_APPLE  = 47
COCO_ORANGE = 49
TARGET_CLASSES = [COCO_BANANA, COCO_APPLE, COCO_ORANGE]

CLASS_NAMES = {
    COCO_BANANA: "banana",
    COCO_APPLE:  "apple",
    COCO_ORANGE: "orange",
}

# ============================================================
# 분류 경로 매핑
# ------------------------------------------------------------
# "left"    → 서보1(S1)만 45° 회전 (모터1 앞으로 기울어짐)
# "right"   → 서보2(S2)만 45° 회전 (모터2 앞으로 기울어짐)
# "neutral" → 두 서보 모두 0° (직진)
#
# 사용자 명세:
#   - 바나나  → 모터1 앞으로 기울어짐  → "left"
#   - 사과    → 모터2 앞으로 기울어짐  → "right"
#   - 오렌지  → 모터2 앞으로 기울어짐  → "right"
#
# ※ 사과와 오렌지가 같은 도착점이라는 의미입니다.
#    분리가 필요하면 아래 PATH_MAP만 수정하세요. 예: 오렌지를 직진으로 보내려면
#    COCO_ORANGE: "neutral" 로 변경.
# ============================================================
PATH_MAP = {
    COCO_BANANA: "left",
    COCO_APPLE:  "right",
    COCO_ORANGE: "right",
}

# 경로별 (S1, S2) 각도 조합
SERVO_ANGLE = {
    "neutral": (0,  0),
    "left":    (45, 0),
    "right":   (0,  45),
}

# ============================================================
# GPIO 핀 매핑 (BCM 번호)
# ------------------------------------------------------------
# Pi 5 하드웨어 PWM 가능 핀: GPIO12, 13, 18, 19
# 서보의 안정성을 위해 SERVO_S1/S2를 HW PWM 핀에 배치.
# ============================================================
@dataclass(frozen=True)
class Pins:
    # ----- 입력 -----
    TOGGLE_SWITCH:   int = 17   # 토글 스위치 (풀업, ON=LOW)

    # IR proximity 센서 (활성 LOW — 일반 IR 장애물 모듈 기준)
    # ※ 'PIR'은 인체감지용이라 2cm 근접 감지 불가. IR proximity 모듈 사용 가정.
    IR_INSPECT:      int = 27   # 검사대 (분기점 직전)
    IR_RAIL_BANANA:  int = 5    # 바나나 도착 레일
    IR_RAIL_APPLE:   int = 6    # 사과 도착 레일
    IR_RAIL_ORANGE:  int = 16   # 오렌지 도착 레일

    # ----- DC 모터 (L298N) -----
    DC_ENA: int = 12   # HW PWM
    DC_IN1: int = 23
    DC_IN2: int = 24

    # ----- 서보 (HW PWM 권장) -----
    SERVO_S1: int = 13
    SERVO_S2: int = 18

    # ----- 결과 알림 LED -----
    LED_BANANA: int = 20
    LED_APPLE:  int = 21
    LED_ORANGE: int = 26

PINS = Pins()

# ============================================================
# 타이밍 / 임계값
# ============================================================
CONF_TH        = 0.60   # YOLO 신뢰도 임계값
N_FRAMES       = 10     # 다수결 투표 프레임 수
VOTE_MIN       = 6      # 신뢰 가능한 최소 동일 클래스 표 수 (N_FRAMES/2 이상)
TILT_HOLD_TIME = 2.0    # 서보 기울임 후 추가 대기 (초)
DEBOUNCE_TIME  = 0.3    # 검사대 정지 후 흔들림 안정화 (초)
DROP_TIMEOUT   = 10.0   # 도착 IR 감지 타임아웃 (초)
CONVEYOR_SPEED = 0.7    # DC 모터 듀티 사이클 (0.0 ~ 1.0)

# ============================================================
# 모델
# ============================================================
MODEL_PATH = "models/yolo11n_ncnn_model"
IMG_SIZE   = 320        # 검사대 ROI가 크면 320 충분, 인식률 낮으면 416/640
