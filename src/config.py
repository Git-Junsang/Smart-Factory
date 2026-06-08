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
# 분류 메커니즘 (시간 기반 개루프)
# ------------------------------------------------------------
# 검사대는 "앞으로만" 기울어진다(서보 1개). 과일은 항상 같은 방향으로
# 굴러 떨어지고, 분류는 분류 레일(DC 모터 2)이 바구니 3개 중 알맞은
# 바구니를 낙하 지점으로 이동시켜서 처리한다.
#
# DC 모터는 위치 피드백이 없으므로 시간 기반 개루프로 제어한다:
#   - BASKET_INDEX: 클래스 → 레일 위 바구니 위치(0,1,2)
#   - 현재 위치는 소프트웨어로 추적(self.current_basket), 시작 위치 = HOME_BASKET
#   - 한 칸 이동 = RAIL_STEP_TIME 동안 RAIL_SPEED로 구동
#
# 바구니 재배치/오렌지·사과 위치 교환 등은 BASKET_INDEX만 수정.
# 리미트 스위치를 달면 정확도가 올라간다(개루프는 누적 오차 가능).
# ============================================================
BASKET_INDEX = {
    COCO_BANANA: 0,
    COCO_ORANGE: 1,
    COCO_APPLE:  2,
}
HOME_BASKET    = 0      # 시작 시 낙하 지점에 와 있다고 가정하는 바구니
RAIL_SPEED     = 0.6    # 분류 레일(DC2) 듀티 사이클
RAIL_STEP_TIME = 0.8    # 바구니 한 칸 이동 시간 (초) — 실측 후 보정

# 검사대 서보 (앞 기울임) — 펄스폭→각도 보정
# ES08MA2 같은 9g 서보는 가동범위가 ~90~120°라 0.5~2.4ms(180° 서보용)로 구동하면
# 기계 한계 너머로 밀려 과회전·스톨한다. 안전한 1.0~2.0ms로 좁히고, 그 범위가
# 만드는 실제 회전을 SERVO_MAX_ANGLE로 둔다. 여전히 과하면 TILT_FORWARD_ANGLE을
# 낮추거나 SERVO_MAX_PULSE를 줄여라.
SERVO_MIN_PULSE = 0.0010   # 1.0ms → 0°
SERVO_MAX_PULSE = 0.0020   # 2.0ms → SERVO_MAX_ANGLE
SERVO_MAX_ANGLE = 90       # 위 펄스폭이 만드는 가동 범위(도)
TILT_LEVEL_ANGLE   = 0     # 평평(과일 안착)
TILT_FORWARD_ANGLE = 60    # 앞으로 기울임(과일이 굴러 낙하) — 과회전 시 낮춰라

# ============================================================
# GPIO 핀 매핑 (BCM 번호)
# ------------------------------------------------------------
# Pi 5 하드웨어 PWM 가능 핀: GPIO12, 13, 18, 19
# 서보(SERVO_TILT)·모터 ENA/ENB를 HW PWM 핀에 배치해 지터를 줄였다.
# OLED는 하드웨어 I2C(SDA=GPIO2, SCL=GPIO3) 고정 핀 사용.
# ============================================================
@dataclass(frozen=True)
class Pins:
    # ----- 입력 (푸시버튼: 풀업, 눌림=LOW / IR: 활성 LOW) -----
    BUTTON_RUN:   int = 17   # 푸시버튼1: 가동/중단 토글
    BUTTON_RESET: int = 16   # 푸시버튼2: OLED 카운트 리셋
    IR_INSPECT:   int = 27   # 검사대 IR proximity (2cm 근접)

    # ----- DC 모터 1: 검사 컨베이어 (L298N ch.A) -----
    DC1_ENA: int = 12   # HW PWM
    DC1_IN1: int = 23
    DC1_IN2: int = 24

    # ----- DC 모터 2: 분류 레일 / 바구니 위치 (L298N ch.B) -----
    DC2_ENB: int = 18   # HW PWM
    DC2_IN3: int = 5
    DC2_IN4: int = 6

    # ----- 서보: 검사대 앞 기울임 (HW PWM) -----
    SERVO_TILT: int = 13

    # ----- 상태 LED (항상 하나만 점등) -----
    LED_RUN:     int = 20   # 가동중
    LED_INSPECT: int = 21   # 검사/분류중
    LED_STOP:    int = 26   # 사용자 중단중

PINS = Pins()

# ============================================================
# OLED (SSD1306 128x64, I2C)
# ============================================================
OLED_I2C_PORT = 1
OLED_ADDR     = 0x3C
OLED_WIDTH    = 128
OLED_HEIGHT   = 64
# OLED 표시 순서 (사용자 명세: Banana / Orange / Apple)
COUNT_ORDER   = [COCO_BANANA, COCO_ORANGE, COCO_APPLE]

# ============================================================
# 타이밍 / 임계값
# ============================================================
CONF_TH        = 0.60   # YOLO 신뢰도 임계값
N_FRAMES       = 10     # 다수결 투표 프레임 수
VOTE_MIN       = 6      # 신뢰 가능한 최소 동일 클래스 표 수 (N_FRAMES/2 이상)
TILT_HOLD_TIME = 1.5    # 앞으로 기울인 채 유지(과일 낙하 대기) 시간 (초)
DEBOUNCE_TIME  = 0.3    # 검사대 정지 후 흔들림 안정화 (초)
CONVEYOR_SPEED = 0.7    # DC 모터 1 듀티 사이클 (0.0 ~ 1.0)

# ============================================================
# 모델
# ============================================================
MODEL_PATH = "models/yolo11n_ncnn_model"
IMG_SIZE   = 320        # 검사대 ROI가 크면 320 충분, 인식률 낮으면 416/640
