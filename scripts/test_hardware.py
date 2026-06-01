"""하드웨어 개별 점검 — 키보드 입력으로 모터/서보/LED를 수동 제어.

비전 없이 GPIO 결선과 모터 방향, 서보 0°/45° 위치를 확인할 때 사용합니다.

사용:  python -m scripts.test_hardware
"""
import time
from src.hardware import Hardware
from src.config import COCO_BANANA, COCO_APPLE, COCO_ORANGE, CLASS_NAMES


MENU = """
========================================
  m: 컨베이어 ON
  s: 컨베이어 OFF
  1: 서보 → neutral (0,0)
  2: 서보 → left    (45,0)  [바나나]
  3: 서보 → right   (0,45)  [사과/오렌지]
  b: LED 바나나 토글
  a: LED 사과 토글
  o: LED 오렌지 토글
  i: 검사대 IR 상태 출력
  r: 도착 IR 상태 출력
  t: 토글 스위치 상태 출력
  q: 종료
========================================
"""


def main():
    hw = Hardware()
    led_state = {COCO_BANANA: False, COCO_APPLE: False, COCO_ORANGE: False}

    try:
        while True:
            print(MENU)
            cmd = input("> ").strip().lower()

            if cmd == "m":
                hw.conveyor_on()
                print("conveyor ON")
            elif cmd == "s":
                hw.conveyor_off()
                print("conveyor OFF")
            elif cmd == "1":
                hw.set_path("neutral");  print("servos → (0, 0)")
            elif cmd == "2":
                hw.set_path("left");     print("servos → (45, 0)")
            elif cmd == "3":
                hw.set_path("right");    print("servos → (0, 45)")
            elif cmd in ("b", "a", "o"):
                cls = {"b": COCO_BANANA, "a": COCO_APPLE, "o": COCO_ORANGE}[cmd]
                led_state[cls] = not led_state[cls]
                (hw.led_on if led_state[cls] else hw.led_off)(cls)
                print(f"LED {CLASS_NAMES[cls]} → {led_state[cls]}")
            elif cmd == "i":
                print(f"IR inspection triggered: {hw.inspection_triggered()}")
            elif cmd == "r":
                for cls in (COCO_BANANA, COCO_APPLE, COCO_ORANGE):
                    print(f"  rail {CLASS_NAMES[cls]:7s}: {hw.rail_triggered(cls)}")
            elif cmd == "t":
                print(f"toggle switch ON: {hw.is_running}")
            elif cmd == "q":
                break
            time.sleep(0.1)
    finally:
        hw.cleanup()
        print("cleaned up.")


if __name__ == "__main__":
    main()
