"""OLED(SSD1306 128x64, I2C) 카운트 표시 계층.

과일 종류별 분류 개수를 카운트해 한 페이지에 표시한다:

    Banana: X
    Orange: X
    Apple : X

luma.oled 사용. I2C가 활성화돼 있어야 한다(raspi-config → Interface → I2C).
하드웨어 의존 모듈이므로 PC에서는 import할 수 없다(라파이 전용).
"""
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306

from src.config import (
    OLED_I2C_PORT, OLED_ADDR, OLED_WIDTH, OLED_HEIGHT,
    COUNT_ORDER, COCO_BANANA, COCO_APPLE, COCO_ORANGE,
)

# 표시용 라벨 (config의 CLASS_NAMES와 별개로 OLED 표기를 깔끔하게 고정)
_LABELS = {
    COCO_BANANA: "Banana",
    COCO_ORANGE: "Orange",
    COCO_APPLE:  "Apple",
}


class Display:
    """OLED 카운터 — 분류 개수를 보관하고 화면을 갱신한다."""

    def __init__(self):
        # 기여자: 서준상 1.0 | 기능: SSD1306 OLED(I2C) 초기화 및 카운트 0으로 첫 화면 렌더
        serial = i2c(port=OLED_I2C_PORT, address=OLED_ADDR)
        self.device = ssd1306(serial, width=OLED_WIDTH, height=OLED_HEIGHT)
        self.counts = {COCO_BANANA: 0, COCO_APPLE: 0, COCO_ORANGE: 0}
        self.render()
        print(f"[Display] OLED ready (I2C {OLED_I2C_PORT}, addr {hex(OLED_ADDR)})")

    def increment(self, cls_id: int):
        # 기여자: 서준상 1.0 | 기능: 해당 과일 카운트 +1 후 OLED 갱신
        """해당 클래스 카운트 +1 후 화면 갱신."""
        if cls_id in self.counts:
            self.counts[cls_id] += 1
            self.render()

    def reset(self):
        # 기여자: 서준상 1.0 | 기능: 버튼2 콜백 — 모든 카운트 0으로 리셋 후 OLED 갱신
        """모든 카운트를 0으로 리셋 후 화면 갱신 (버튼2 콜백)."""
        for cls in self.counts:
            self.counts[cls] = 0
        self.render()
        print("[Display] counts reset")

    def render(self):
        # 기여자: 서준상 1.0 | 기능: Banana/Orange/Apple 카운트를 한 페이지로 OLED에 그림
        """현재 카운트를 OLED에 그린다."""
        with canvas(self.device) as draw:
            y = 2
            for cls in COUNT_ORDER:
                draw.text((4, y), f"{_LABELS[cls]}: {self.counts[cls]}", fill="white")
                y += 20

    def close(self):
        # 기여자: 서준상 1.0 | 기능: 종료 시 OLED 화면 클리어
        try:
            self.device.clear()
        except Exception:
            pass
