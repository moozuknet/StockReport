import time
import threading
from typing import Callable, Optional
from config import AppConfig

class ReportScheduler:
    def __init__(
        self, 
        config: AppConfig, 
        log_fn: Callable[[str], None], 
        runner_fn: Optional[Callable] = None,
        on_finished: Optional[Callable] = None
    ):
        self.config = config
        self.log_fn = log_fn
        self.runner_fn = runner_fn
        self.on_finished = on_finished
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.is_running = False

    def start(self):
        if self.is_running:
            return
        self.stop_event.clear()
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        if not self.is_running:
            return
        self.stop_event.set()
        self.is_running = False
        self.log_fn("수집 스케줄러가 중지되었습니다.")

    def join(self, timeout: Optional[float] = None):
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=timeout)

    def _run_loop(self):
        self.log_fn("수집 스케줄러가 시작되었습니다.")
        
        while not self.stop_event.is_set():
            try:
                if self.runner_fn:
                    self.runner_fn(self.config, self.log_fn)
            except Exception as e:
                self.log_fn(f"[스케줄러 예외 발생] {e}")

            if self.config.interval_minutes <= 0:
                # 1회성 실행 완료 후 탈출
                break

            # 주기적 반복: interval_minutes 초 단위 변환 후 분할 대기 (중지 이벤트 빠른 감지)
            total_seconds = self.config.interval_minutes * 60
            self.log_fn(f"다음 실행까지 {self.config.interval_minutes}분 대기합니다...")

            for _ in range(total_seconds):
                if self.stop_event.is_set():
                    break
                time.sleep(1)

        self.is_running = False
        if self.on_finished:
            try:
                self.on_finished()
            except Exception:
                pass
