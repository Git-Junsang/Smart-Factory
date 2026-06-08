"""GPIO/PWM 하드웨어 제어 계층 (Raspberry Pi 5 + gpiozero + lgpio).

구성:
  - DC 모터 1: 검사 컨베이어 (과일을 검사대로 이송)
  - DC 모터 2: 분류 레일 (바구니 3개를 시간 기반 개루프로 위치 이동)
  - 서보 1개: 검사대를 앞으로 기울여 과일을 낙하시킴
  - 푸시버튼 2개: 가동/중단 토글, 카운트 리셋
  - 상태 LED 3개: 가동중 / 검사·분류중 / 사용자 중단중 (항상 하나만 점등)
  - IR proximity 1개: 검사대 근접 감지
"""
import time

from gpiozero import Motor, AngularServo, LED, Button, DigitalInputDevice, Device
from gpiozero.pins.lgpio import LGPIOFactory

from src.config import (
    PINS, CONVEYOR_SPEED, RAIL_SPEED, RAIL_STEP_TIME, HOME_BASKET,
    TILT_LEVEL_ANGLE, TILT_FORWARD_ANGLE,
    SERVO_MIN_PULSE, SERVO_MAX_PULSE, SERVO_MAX_ANGLE,
    SERVO_SWEEP_SPEED, SERVO_STEP_DEG,
)

# Pi 5는 lgpio 백엔드를 명시적으로 사용해야 함
# (RPi.GPIO 및 pigpio는 Pi 5에서 정상 동작하지 않음)
Device.pin_factory = LGPIOFactory()


class Hardware:
    """모든 GPIO 디바이스를 캡슐화하는 컨테이너."""

    def __init__(self):
        # ---------- DC 모터 1: 검사 컨베이어 ----------
        self.conveyor = Motor(
            forward=PINS.DC1_IN1, backward=PINS.DC1_IN2,
            enable=PINS.DC1_ENA, pwm=True,
        )

        # ---------- DC 모터 2: 분류 레일 (바구니 위치) ----------
        self.rail = Motor(
            forward=PINS.DC2_IN3, backward=PINS.DC2_IN4,
            enable=PINS.DC2_ENB, pwm=True,
        )
        # 위치 센서가 없으므로 현재 바구니 위치를 소프트웨어로 추적
        self.current_basket = HOME_BASKET

        # ---------- 서보: 검사대 앞 기울임 ----------
        # 펄스폭/가동범위는 config에서 보정 (ES08MA2 등 9g 서보 과회전 방지)
        self.tilt_servo = AngularServo(
            PINS.SERVO_TILT,
            min_angle=0, max_angle=SERVO_MAX_ANGLE,
            min_pulse_width=SERVO_MIN_PULSE, max_pulse_width=SERVO_MAX_PULSE,
            initial_angle=TILT_LEVEL_ANGLE,
        )
        self._tilt_angle = TILT_LEVEL_ANGLE   # 현재 기울임 각도 추적(점진 스윕용)

        # ---------- 푸시버튼 (풀업, 눌림=LOW) ----------
        # 버튼1: 누를 때마다 가동/중단 토글
        self.btn_run = Button(PINS.BUTTON_RUN, pull_up=True, bounce_time=0.1)
        self._running_flag = False
        self.btn_run.when_pressed = self._toggle_running
        # 버튼2: 카운트 리셋 — 콜백은 main에서 on_reset()으로 연결
        self.btn_reset = Button(PINS.BUTTON_RESET, pull_up=True, bounce_time=0.1)

        # ---------- IR proximity 센서 (활성 LOW) ----------
        self.ir_inspect = DigitalInputDevice(
            PINS.IR_INSPECT, pull_up=True, bounce_time=0.05,
        )

        # ---------- 상태 LED ----------
        self.led_run     = LED(PINS.LED_RUN)
        self.led_inspect = LED(PINS.LED_INSPECT)
        self.led_stop    = LED(PINS.LED_STOP)

        self.reset()

    # ===== 가동/중단 버튼 (토글) =====
    def _toggle_running(self):
        """버튼1 눌림 콜백 — 가동/중단 플래그를 뒤집는다."""
        self._running_flag = not self._running_flag
        print(f"[HW] run button → {'RUN' if self._running_flag else 'STOP'}")

    @property
    def is_running(self) -> bool:
        """현재 가동 요청 상태(버튼1 토글)."""
        return self._running_flag

    def on_reset(self, callback):
        """버튼2(카운트 리셋) 눌림 콜백을 연결한다."""
        self.btn_reset.when_pressed = callback

    # ===== DC 모터 1: 컨베이어 =====
    def conveyor_on(self, speed: float = CONVEYOR_SPEED):
        self.conveyor.forward(speed)

    def conveyor_off(self):
        self.conveyor.stop()

    # ===== DC 모터 2: 분류 레일 (시간 기반 개루프) =====
    def move_rail_to(self, target_index: int):
        """분류 레일을 target_index 바구니가 낙하 지점에 오도록 이동.

        현재 위치와의 칸 차이만큼 RAIL_STEP_TIME 동안 구동한다(개루프).
        """
        delta = target_index - self.current_basket
        if delta == 0:
            return
        if delta > 0:
            self.rail.forward(RAIL_SPEED)
        else:
            self.rail.backward(RAIL_SPEED)
        time.sleep(abs(delta) * RAIL_STEP_TIME)
        self.rail.stop()
        self.current_basket = target_index

    def rail_stop(self):
        self.rail.stop()

    # ===== 서보: 검사대 기울임 =====
    def _sweep_tilt(self, target: float):
        """현재 각도에서 target까지 SERVO_SWEEP_SPEED(도/초)로 점진 이동.

        SERVO_SWEEP_SPEED가 0이면 즉시 이동(기존 동작).
        """
        cur = self._tilt_angle
        if SERVO_SWEEP_SPEED <= 0 or target == cur:
            self.tilt_servo.angle = target
            self._tilt_angle = target
            return
        step_delay = SERVO_STEP_DEG / SERVO_SWEEP_SPEED
        direction = 1 if target > cur else -1
        a = cur
        while a != target:
            a += direction * SERVO_STEP_DEG
            if (direction > 0 and a > target) or (direction < 0 and a < target):
                a = target
            self.tilt_servo.angle = a
            time.sleep(step_delay)
        self._tilt_angle = target

    def tilt_forward(self):
        """검사대를 앞으로 기울여 과일을 굴려 낙하시킨다(절반 속도 스윕)."""
        self._sweep_tilt(TILT_FORWARD_ANGLE)

    def tilt_level(self):
        """검사대를 다시 평평하게 복귀(절반 속도 스윕)."""
        self._sweep_tilt(TILT_LEVEL_ANGLE)

    # ===== IR (active LOW) =====
    def inspection_triggered(self) -> bool:
        """검사대 IR이 2cm 내 물체 감지 상태인지."""
        return not self.ir_inspect.value

    # ===== 상태 LED (배타 점등) =====
    def set_status(self, status):
        """status: 'run' | 'inspect' | 'stop' | None — 해당 LED만 켜고 나머지 OFF."""
        self.led_run.off()
        self.led_inspect.off()
        self.led_stop.off()
        if status == "run":
            self.led_run.on()
        elif status == "inspect":
            self.led_inspect.on()
        elif status == "stop":
            self.led_stop.on()

    # ===== 일괄 제어 =====
    def reset(self):
        """안전한 정지 상태로 복귀 (모터 정지, 검사대 평평, LED OFF)."""
        self.conveyor_off()
        self.rail_stop()
        self.tilt_level()
        self.set_status(None)

    def cleanup(self):
        """프로그램 종료 시 모든 디바이스 정리."""
        self.reset()
        devices = [
            self.conveyor, self.rail, self.tilt_servo,
            self.btn_run, self.btn_reset, self.ir_inspect,
            self.led_run, self.led_inspect, self.led_stop,
        ]
        for dev in devices:
            try:
                dev.close()
            except Exception:
                pass
