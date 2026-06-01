"""GPIO/PWM 하드웨어 제어 계층 (Raspberry Pi 5 + gpiozero + lgpio)."""
from gpiozero import (
    Motor, AngularServo, LED, Button, DigitalInputDevice, Device,
)
from gpiozero.pins.lgpio import LGPIOFactory

from src.config import (
    PINS, SERVO_ANGLE, CONVEYOR_SPEED,
    COCO_BANANA, COCO_APPLE, COCO_ORANGE,
)

# Pi 5는 lgpio 백엔드를 명시적으로 사용해야 함
# (RPi.GPIO 및 pigpio는 Pi 5에서 정상 동작하지 않음)
Device.pin_factory = LGPIOFactory()


class Hardware:
    """모든 GPIO 디바이스를 캡슐화하는 컨테이너."""

    def __init__(self):
        # ---------- DC 컨베이어 모터 (L298N) ----------
        self.conveyor = Motor(
            forward=PINS.DC_IN1,
            backward=PINS.DC_IN2,
            enable=PINS.DC_ENA,
            pwm=True,
        )

        # ---------- 서보 두 개 ----------
        # SG90 / MG90S 공통: pulse 0.5ms(0°) ~ 2.4ms(180°)
        self.servo1 = AngularServo(
            PINS.SERVO_S1,
            min_angle=0, max_angle=90,
            min_pulse_width=0.0005, max_pulse_width=0.0024,
            initial_angle=0,
        )
        self.servo2 = AngularServo(
            PINS.SERVO_S2,
            min_angle=0, max_angle=90,
            min_pulse_width=0.0005, max_pulse_width=0.0024,
            initial_angle=0,
        )

        # ---------- 토글 스위치 ----------
        # 풀업 — 스위치 ON 시 GND로 LOW → is_pressed=True
        self.toggle = Button(PINS.TOGGLE_SWITCH, pull_up=True, bounce_time=0.05)

        # ---------- IR proximity 센서 (활성 LOW) ----------
        self.ir_inspect = DigitalInputDevice(
            PINS.IR_INSPECT, pull_up=True, bounce_time=0.05,
        )
        self.ir_rails = {
            COCO_BANANA: DigitalInputDevice(PINS.IR_RAIL_BANANA, pull_up=True, bounce_time=0.05),
            COCO_APPLE:  DigitalInputDevice(PINS.IR_RAIL_APPLE,  pull_up=True, bounce_time=0.05),
            COCO_ORANGE: DigitalInputDevice(PINS.IR_RAIL_ORANGE, pull_up=True, bounce_time=0.05),
        }

        # ---------- LED ----------
        self.leds = {
            COCO_BANANA: LED(PINS.LED_BANANA),
            COCO_APPLE:  LED(PINS.LED_APPLE),
            COCO_ORANGE: LED(PINS.LED_ORANGE),
        }

        self.reset()

    # ===== 토글 스위치 =====
    @property
    def is_running(self) -> bool:
        """토글 스위치가 ON 상태인지."""
        return self.toggle.is_pressed

    # ===== 컨베이어 =====
    def conveyor_on(self, speed: float = CONVEYOR_SPEED):
        self.conveyor.forward(speed)

    def conveyor_off(self):
        self.conveyor.stop()

    # ===== 서보 =====
    def set_path(self, direction: str):
        """direction: 'neutral' | 'left' | 'right'"""
        a1, a2 = SERVO_ANGLE[direction]
        self.servo1.angle = a1
        self.servo2.angle = a2

    def reset_servos(self):
        self.set_path("neutral")

    # ===== IR (active LOW) =====
    def inspection_triggered(self) -> bool:
        """검사대 IR이 2cm 내 물체 감지 상태인지."""
        return not self.ir_inspect.value

    def rail_triggered(self, class_id: int) -> bool:
        """해당 도착 레일의 IR이 물체 감지 상태인지."""
        return not self.ir_rails[class_id].value

    # ===== LED =====
    def led_on(self, class_id: int):
        self.leds[class_id].on()

    def led_off(self, class_id: int):
        self.leds[class_id].off()

    def all_leds_off(self):
        for led in self.leds.values():
            led.off()

    # ===== 일괄 제어 =====
    def reset(self):
        """안전한 정지 상태로 복귀."""
        self.conveyor_off()
        self.reset_servos()
        self.all_leds_off()

    def cleanup(self):
        """프로그램 종료 시 모든 디바이스 정리."""
        self.reset()
        devices = [
            self.conveyor, self.servo1, self.servo2,
            self.toggle, self.ir_inspect,
            *self.ir_rails.values(),
            *self.leds.values(),
        ]
        for dev in devices:
            try:
                dev.close()
            except Exception:
                pass
