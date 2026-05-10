import threading
import time
import queue
import random

from config import (
    SERIAL_PORT, BAUD_RATE, SERIAL_TIMEOUT,
    RECONNECT_DELAY, DEMO_MODE,
)


class SerialReader:

    def __init__(
        self,
        port: str = SERIAL_PORT,
        baud_rate: int = BAUD_RATE,
        demo_mode: bool = DEMO_MODE,
    ) -> None:
        self.port       = port
        self.baud_rate  = baud_rate
        self.demo_mode  = demo_mode

        self._serial_conn   = None
        self._data_queue: queue.Queue = queue.Queue(maxsize=500)
        self._running: bool = False
        self._thread: threading.Thread | None = None

        self.connected: bool     = False
        self.status_message: str = "Initializing..."
        self._reconnect_event: threading.Event = threading.Event()

    def start(self) -> None:
        self._running = True
        if self.demo_mode:
            target = self._demo_loop
            self.connected = True
            self.status_message = "DEMO MODE - Simulated data active"
        else:
            target = self._serial_loop

        self._thread = threading.Thread(target=target, daemon=True, name="SerialReader")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._reconnect_event.set()
        self._close_connection()

    def reconnect(self) -> None:
        if self.demo_mode:
            return
        self._close_connection()
        self.status_message = "Manual reconnect requested..."
        self._reconnect_event.set()

    def get_data(self) -> str | None:
        try:
            return self._data_queue.get_nowait()
        except queue.Empty:
            return None

    def _open_connection(self) -> bool:
        try:
            import serial
            self._serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=SERIAL_TIMEOUT,
            )
            self.connected = True
            self.status_message = f"Connected to {self.port} @ {self.baud_rate} baud"
            print(f"[SerialReader] {self.status_message}")
            return True
        except Exception as exc:
            self.connected = False
            self.status_message = f"Cannot open {self.port}: {exc}"
            print(f"[SerialReader] {self.status_message}")
            return False

    def _close_connection(self) -> None:
        if self._serial_conn is not None:
            try:
                if self._serial_conn.is_open:
                    self._serial_conn.close()
            except Exception:
                pass
        self.connected = False

    def _serial_loop(self) -> None:
        import serial

        while self._running:
            if not self.connected:
                if not self._open_connection():
                    self._reconnect_event.wait(timeout=RECONNECT_DELAY)
                    self._reconnect_event.clear()
                    continue

            try:
                raw: bytes = self._serial_conn.readline()
                if raw:
                    line = raw.decode("utf-8", errors="ignore").strip()
                    if line and not self._data_queue.full():
                        self._data_queue.put(line)

            except serial.SerialException as exc:
                print(f"[SerialReader] Serial error: {exc}")
                self._close_connection()
                self.status_message = f"Disconnected - retrying in {RECONNECT_DELAY:.0f}s..."
                self._reconnect_event.wait(timeout=RECONNECT_DELAY)
                self._reconnect_event.clear()

            except Exception as exc:
                print(f"[SerialReader] Unexpected error: {exc}")
                time.sleep(0.1)

    def _demo_loop(self) -> None:
        scenarios = [
            ("NORMAL",       (25, 38), (50, 75), 0, (0.5, 2.0), (11.0, 13.0)),
            ("HIGH TEMP",    (41, 50), (50, 75), 0, (0.5, 2.0), (11.0, 13.0)),
            ("LOW HUMIDITY", (25, 38), (5,  28), 0, (0.5, 2.0), (11.0, 13.0)),
            ("NO CURRENT",   (25, 38), (50, 75), 1, (0.0, 0.0), (11.0, 13.0)),
            ("LOW VOLTAGE",  (25, 38), (50, 75), 0, (0.5, 2.0), (0.0,  8.0)),
        ]

        FAULT_SAMPLES  = 10
        NORMAL_SAMPLES = 8

        scenario_idx = 0
        phase        = "fault"
        count        = 0

        while self._running:
            name, t_r, h_r, m, i_r, v_r = scenarios[scenario_idx]

            if phase == "fault":
                t       = round(random.uniform(*t_r), 1)
                h       = round(random.uniform(*h_r), 1)
                current = 0.0 if i_r == (0.0, 0.0) else round(random.uniform(*i_r), 2)
                voltage = round(random.uniform(*v_r), 2)
            else:
                t       = round(random.uniform(25, 38), 1)
                h       = round(random.uniform(50, 75), 1)
                m       = 0
                current = round(random.uniform(0.5, 2.0), 2)
                voltage = round(random.uniform(11.0, 13.0), 2)

            line = f"0XZZ,t={t},h={h},m={m},I={current},V={voltage},0XFF"
            if not self._data_queue.full():
                self._data_queue.put(line)

            count += 1
            limit = FAULT_SAMPLES if phase == "fault" else NORMAL_SAMPLES

            if count >= limit:
                count = 0
                if phase == "fault":
                    phase = "normal"
                else:
                    phase = "fault"
                    scenario_idx = (scenario_idx + 1) % len(scenarios)

            time.sleep(0.3)
