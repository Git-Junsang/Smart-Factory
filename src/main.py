"""상태머신 메인 루프.

가동/중단은 푸시버튼1(토글)로 제어한다. 누를 때마다 RUN ↔ STOP이 뒤집힌다.

상태 전이:
  IDLE  (중단중, LED3 ON)
    └─(버튼1 → RUN)──→ RUNNING
  RUNNING  (컨베이어 가동, LED1 ON)
    ├─(카메라에 과일 감지 → 컨베이어 정지·2초 안정화)──→ INSPECTING
    └─(버튼1 → STOP)────→ IDLE
  INSPECTING  (컨베이어 정지, N프레임 YOLO 추론, LED2 ON)
    ├─(클래스 확정)─────→ SORTING
    └─(불확실)──────────→ SKIP
  SORTING  (분류 레일 이동 → 검사대 앞으로 기울임 → 과일 낙하 → 카운트, LED2 ON)
    └─→ RUNNING
  버튼1로 STOP 시 어느 상태에서든 IDLE로 복귀.
  버튼2는 어느 때든 OLED 카운트를 0으로 리셋.

분류 메커니즘:
  검사대는 앞으로만 기울어진다. 과일은 항상 같은 방향으로 굴러 떨어지고,
  분류 레일(DC2)이 클래스에 맞는 바구니를 낙하 지점으로 이동시켜 받아낸다.

실행:  python -m src.main
"""
import signal
import time

from src.config import (
    BASKET_INDEX, CLASS_NAMES,
    TILT_HOLD_TIME, CAMERA_STOP_TIME,
)
from src.hardware import Hardware
from src.vision import Vision
from src.display import Display


class FruitSorter:
    def __init__(self):
        # 기여자: 서준상 1.0 | 기능: 하드웨어·비전·OLED 계층 생성 및 버튼2(리셋) 연결, 종료 시그널 등록
        self.hw = Hardware()
        self.vision = Vision()
        self.display = Display()
        # 버튼2(리셋) → OLED 카운트 0으로
        self.hw.on_reset(self.display.reset)
        self.alive = True
        signal.signal(signal.SIGINT, self._on_sigint)
        signal.signal(signal.SIGTERM, self._on_sigint)

    def _on_sigint(self, *_):
        # 기여자: 서준상 1.0 | 기능: SIGINT/SIGTERM 수신 시 메인 루프 종료 플래그를 내려 안전 종료
        print("\n[Main] Stop signal received.")
        self.alive = False

    def _sleep_interruptible(self, duration: float):
        """duration초 대기하되, 종료/STOP되면 즉시 빠져나온다(블로킹 최소화)."""
        t0 = time.time()
        while time.time() - t0 < duration:
            if not (self.alive and self.hw.is_running):
                return
            time.sleep(0.02)

    # ============================================================
    # 상태 핸들러
    # ============================================================
    def _idle(self):
        # 기여자: 서준상 1.0 | 기능: 사용자 중단(IDLE) 상태 처리 — 전 장치 정지 후 버튼1 RUN 대기
        """중단 상태에서 대기 (버튼1로 RUN 될 때까지). LED3 ON."""
        self.hw.reset()
        self.hw.set_status("stop")
        print("[Main] IDLE — press run button to start.")
        while self.alive and not self.hw.is_running:
            time.sleep(0.1)

    def _running(self) -> bool:
        # 기여자: 서준상 1.0 | 기능: 컨베이어 가동 후 카메라가 과일을 감지할 때까지 폴링, 감지 시 정지·안정화
        """컨베이어 가동 → 카메라에 대상 과일이 감지될 때까지 대기. LED1 ON.
        감지되면 컨베이어를 멈추고 CAMERA_STOP_TIME(2초) 안정화한다.
        Return: True=감지됨, False=버튼1로 STOP."""
        print("[Main] RUNNING — conveyor on.")
        self.hw.set_status("run")
        self.hw.conveyor_on()
        while self.alive and self.hw.is_running:
            if self.vision.detect() is not None:   # 카메라에 대상 과일 감지
                print(f"[Main] 카메라 감지 — 컨베이어 정지 {CAMERA_STOP_TIME}s.")
                self.hw.conveyor_off()
                time.sleep(CAMERA_STOP_TIME)       # 정지 후 안정화
                return True
            time.sleep(0.02)
        # 버튼1로 STOP된 경우
        self.hw.conveyor_off()
        return False

    def _inspecting(self):
        # 기여자: 서준상 1.0 | 기능: 정지된 과일을 N프레임 다수결 YOLO 추론으로 분류(확정 클래스 또는 None)
        """N프레임 다수결 추론. 확정 클래스 반환 또는 None. LED2 ON."""
        print("[Main] INSPECTING — running YOLO.")
        self.hw.set_status("inspect")
        return self.vision.classify_stable()

    def _sorting(self, cls_id: int):
        # 기여자: 서준상 1.0 | 기능: 분류 레일 정렬 → 검사대 앞 기울임으로 과일 낙하 → OLED 카운트 +1
        """분류 레일로 알맞은 바구니를 낙하 지점에 정렬 → 검사대를 앞으로
        기울여 과일 낙하 → 검사대 복귀 → 카운트 +1 (OLED 갱신). LED2 유지."""
        name = CLASS_NAMES[cls_id]
        target = BASKET_INDEX[cls_id]
        print(f"[Main] SORTING — {name} → basket #{target}")
        self.hw.set_status("inspect")

        # 1) 분류 레일을 알맞은 바구니로 이동 (STOP 시 즉시 중단)
        self.hw.move_rail_to(target)
        if not self.hw.is_running:
            return   # 사용자가 중단 — 기울임·카운트 생략

        # 2) 검사대 앞으로 기울임 → 과일이 굴러 바구니로 낙하
        self.hw.tilt_forward()
        self._sleep_interruptible(TILT_HOLD_TIME)
        self.hw.tilt_level()
        if not self.hw.is_running:
            return   # 사용자가 중단 — 카운트 생략

        # 3) 카운트 +1 → OLED 갱신
        self.display.increment(cls_id)
        print(f"[Main] counted {name}: {self.display.counts[cls_id]}")

    def _skip(self):
        # 기여자: 서준상 1.0 | 기능: 분류 불확실 시 기울임·카운트 없이 통과(오분류 방지)
        """분류 실패(불확실) 시 — 서보를 움직이지 않고 넘어간다.

        세 과일(apple/banana/orange) 중 하나로 확정됐을 때만 검사대가
        기울어지도록, 여기서는 기울임·카운트 모두 하지 않는다.
        """
        print("[Main] SKIP — no confident class. (서보 미동작)")

    def _wait_clear(self):
        # 기여자: 서준상 1.0 | 기능: 검사대가 비워질 때까지 대기해 같은 과일 재감지·재처리 방지
        """다음 사이클 전, 카메라에 대상 과일이 더는 안 보일 때까지 대기.

        분류돼 낙하한 과일은 화면에서 즉시 사라지고, 미분류로 남은 과일은
        치워질 때까지 대기한다 — 같은 과일로 즉시 재감지·재처리되는 것을 막는다.
        """
        if self.vision.detect() is None:
            return
        print("[Main] 화면이 비워지길 대기 중...")
        while self.alive and self.hw.is_running:
            if self.vision.detect() is None:
                print("[Main] 화면 비워짐 — 다음 사이클.")
                return
            time.sleep(0.1)

    # ============================================================
    # 메인 루프
    # ============================================================
    def run(self):
        # 기여자: 서준상 0.4, 박준규 0.2, 이용희 0.2, 이윤성 0.2 | 기능: 상태머신 메인 루프 — IDLE→RUNNING→INSPECTING→SORTING/SKIP 순환 및 종료 시 정리
        try:
            while self.alive:
                # 버튼1이 STOP이면 IDLE로
                if not self.hw.is_running:
                    self._idle()
                    continue

                # 컨베이어 가동 → 검사대 도달 대기
                inspected = self._running()
                if not inspected:
                    continue   # 버튼1로 STOP됨

                # YOLO 추론
                cls_id = self._inspecting()
                if cls_id is None:
                    self._skip()
                else:
                    # 세 과일 중 하나로 확정됐을 때만 분류 레일 이동 + 기울여 낙하 + 카운트
                    self._sorting(cls_id)

                # 다음 사이클 전 검사대가 비워질 때까지 대기 (상시감지 재트리거 방지)
                self._wait_clear()

        finally:
            print("[Main] Cleaning up.")
            self.hw.cleanup()
            self.vision.close()
            self.display.close()


if __name__ == "__main__":
    FruitSorter().run()
