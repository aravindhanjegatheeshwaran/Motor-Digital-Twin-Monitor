import os
import csv
import datetime

from config import (
    LIVE_LOG_PATH,
    TEMP_HIGH_LIMIT, HUMIDITY_LOW_LIMIT,
    CURRENT_ZERO_ALERT, VOLTAGE_LOW_LIMIT, VOLTAGE_HIGH_LIMIT,
)


class DataProcessor:

    def __init__(self) -> None:
        self.temp_high_limit: float    = TEMP_HIGH_LIMIT
        self.humidity_low_limit: float = HUMIDITY_LOW_LIMIT
        self.current_zero_alert: float = CURRENT_ZERO_ALERT
        self.voltage_low_limit: float  = VOLTAGE_LOW_LIMIT
        self.voltage_high_limit: float = VOLTAGE_HIGH_LIMIT
        self._init_log()

    def _init_log(self) -> None:
        try:
            with open(LIVE_LOG_PATH, "w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow([
                    "timestamp",
                    "temperature", "humidity", "motor_reported",
                    "current", "voltage",
                    "high_temp", "low_humidity",
                    "no_current", "low_voltage", "overvoltage",
                    "overall_status",
                ])
            print(f"[DataProcessor] Live log initialised: {LIVE_LOG_PATH}")
        except Exception as exc:
            print(f"[DataProcessor] Could not create log: {exc}")

    def parse(self, raw_line: str) -> tuple[float, float, int, float, float] | None:
        try:
            parts = [p.strip() for p in raw_line.strip().split(",")]
            if len(parts) != 7:
                return None
            if parts[0].upper() != "0XZZ" or parts[6].upper() != "0XFF":
                return None

            def _kv(token: str, key: str) -> str:
                k, _, v = token.partition("=")
                if k.strip().lower() != key.lower():
                    raise ValueError(f"expected key '{key}', got '{k}'")
                return v.strip()

            def _safe_float(s: str) -> float:
                s = s.strip()
                # Fix hardware formatting bug: "0.-3" → "-0.3"
                import re
                m = re.match(r'^(\d+)\.-(\d+)$', s)
                if m:
                    s = f"-{m.group(1)}.{m.group(2)}"
                return float(s)

            t = _safe_float(_kv(parts[1], "t"))
            h = _safe_float(_kv(parts[2], "h"))
            m = int(round(_safe_float(_kv(parts[3], "m"))))
            I = _safe_float(_kv(parts[4], "I"))
            V = _safe_float(_kv(parts[5], "V"))

            if m not in (0, 1):
                return None
            return t, h, m, I, V

        except (ValueError, IndexError):
            return None

    def evaluate(
        self,
        temperature: float,
        humidity: float,
        motor: int,
        current: float,
        voltage: float,
    ) -> dict:
        high_temp  = temperature > self.temp_high_limit
        low_hum    = humidity    < self.humidity_low_limit
        no_current = current    <= self.current_zero_alert
        low_volt   = voltage     < self.voltage_low_limit
        high_volt  = voltage     > self.voltage_high_limit
        motor_on   = motor == 1

        any_fault = high_temp or low_hum or no_current or low_volt or high_volt

        labels = []
        if high_temp:  labels.append("High Temp")
        if low_hum:    labels.append("Low Humidity")
        if no_current: labels.append("No Current")
        if low_volt:   labels.append("Low Voltage")
        if high_volt:  labels.append("Overvoltage")

        return {
            "temperature":    temperature,
            "humidity":       humidity,
            "motor":          motor,
            "motor_on":       motor_on,
            "current":        current,
            "voltage":        voltage,
            "high_temp":      high_temp,
            "low_humidity":   low_hum,
            "no_current":     no_current,
            "low_voltage":    low_volt,
            "overvoltage":    high_volt,
            "fault_label":    " + ".join(labels) if labels else "",
            "overall_fault":  any_fault,
            "overall_status": "FAULT" if any_fault else "NORMAL",
        }

    def log(self, result: dict) -> None:
        try:
            with open(LIVE_LOG_PATH, "a", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow([
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    result["temperature"],
                    result["humidity"],
                    result["motor"],
                    result["current"],
                    result["voltage"],
                    int(result["high_temp"]),
                    int(result["low_humidity"]),
                    int(result["no_current"]),
                    int(result["low_voltage"]),
                    int(result["overvoltage"]),
                    result["overall_status"],
                ])
        except Exception as exc:
            print(f"[DataProcessor] Log write error: {exc}")
