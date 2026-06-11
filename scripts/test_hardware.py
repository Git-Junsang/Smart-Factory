"""하드웨어 개별 점검 — 키보드 입력으로 모터/서보/LED를 수동 제어.

비전 없이 GPIO 결선과 모터 방향, 분류 레일 이동, 검사대 기울임,
상태 LED를 확인할 때 사용합니다.

사용:  python -m scripts.test_hardware
"""
import time
from src.hardware import Hardware


MENU = """
========================================
  m: 컨베이어(DC1) ON
  s: 컨베이어(DC1) OFF
  0: 분류 레일 → 바구니 #0
  1: 분류 레일 → 바구니 #1
  2: 분류 레일 → 바구니 #2
  f: 검사대 앞으로 기울임
  l: 검사대 평평 복귀
  r: 상태 LED → 가동중(LED1)
  e: 상태 LED → 검사중(LED2)
  p: 상태 LED → 중단중(LED3)
  x: 상태 LED 모두 OFF
  b: 가동/중단 버튼(버튼1) 상태 출력
  q: 종료
========================================
"""


def main():
    # 기여자: 박준규 0.5, 이윤성 0.5 | 기능: 키보드 메뉴로 컨베이어/분류레일/서보/LED/버튼을 수동 점검(비전 없이 결선 확인)
    hw = Hardware()
    hw.on_reset(lambda: print("[Test] reset button pressed"))

    try:
        while True:
            print(MENU)
            cmd = input("> ").strip().lower()

            if cmd == "m":
                hw.conveyor_on();  print("conveyor ON")
            elif cmd == "s":
                hw.conveyor_off(); print("conveyor OFF")
            elif cmd in ("0", "1", "2"):
                hw.move_rail_to(int(cmd))
                print(f"rail → basket #{cmd} (current={hw.current_basket})")
            elif cmd == "f":
                hw.tilt_forward(); print("tilt → forward")
            elif cmd == "l":
                hw.tilt_level();   print("tilt → level")
            elif cmd == "r":
                hw.set_status("run");     print("LED → run")
            elif cmd == "e":
                hw.set_status("inspect"); print("LED → inspect")
            elif cmd == "p":
                hw.set_status("stop");    print("LED → stop")
            elif cmd == "x":
                hw.set_status(None);      print("LED → all off")
            elif cmd == "b":
                print(f"run button state (is_running): {hw.is_running}")
            elif cmd == "q":
                break
            time.sleep(0.1)
    finally:
        hw.cleanup()
        print("cleaned up.")


if __name__ == "__main__":
    main()
