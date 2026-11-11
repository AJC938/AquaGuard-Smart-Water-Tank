"""Threaded serial input and parser for AquaGuard's line-oriented Arduino output."""

from __future__ import annotations

from collections import deque
from datetime import datetime
import re
import threading
import time
import math
from typing import Any

import serial
from serial.tools import list_ports


_TEMP_RE = re.compile(r"^Temperature\s*:\s*(.*?)\s*(?:Celsius)?\s*$", re.I)
_DISTANCE_RE = re.compile(r"^Distance\s*:\s*(.*?)\s*(?:cm)?\s*$", re.I)
_WATER_RE = re.compile(r"^Water Sensor\s*:\s*(-?\d+)(?:\s*\|\s*Status\s*:\s*(WET|DRY))?\s*$", re.I)
_STATUS_RE = re.compile(r"^Status\s*:\s*(WET|DRY)\s*$", re.I)
_BUZZER_RE = re.compile(r"^Buzzer\s*:\s*(ON|OFF)\s*$", re.I)


def available_ports() -> list[dict[str, str]]:
    """Return currently enumerated serial ports in display-friendly form."""
    return [
        {"device": item.device, "description": item.description or item.device}
        for item in list_ports.comports()
    ]


class AquaGuardParser:
    """Assemble complete five-field readings from arbitrary serial line chunks."""

    def __init__(self) -> None:
        self._pending: dict[str, Any] = {}

    def feed_line(self, line: str) -> dict[str, Any] | None:
        line = line.strip().strip("- ")
        if not line:
            return None

        match = _TEMP_RE.match(line)
        if match:
            # A new cycle begins at Temperature, so stale partial fields cannot leak in.
            self._pending = {"temperature_raw": match.group(1).strip()}
            raw = self._pending["temperature_raw"]
            try:
                value = float(raw)
                if not math.isfinite(value):
                    raise ValueError
                self._pending["temperature_c"] = value
                self._pending["temperature_error"] = None
            except (TypeError, ValueError):
                self._pending["temperature_c"] = None
                self._pending["temperature_error"] = raw or "Sensor error"
            return self._complete_if_ready()

        match = _DISTANCE_RE.match(line)
        if match:
            raw = match.group(1).strip()
            if raw.upper() in {"NO ECHO", "NO_ECHO", "N/A"}:
                self._pending["distance_cm"] = None
                self._pending["distance_status"] = "NO ECHO"
            else:
                try:
                    value = float(raw)
                    if not math.isfinite(value):
                        raise ValueError
                    self._pending["distance_cm"] = value
                    self._pending["distance_status"] = "OK"
                except ValueError:
                    self._pending["distance_cm"] = None
                    self._pending["distance_status"] = raw or "Sensor error"
            return self._complete_if_ready()

        match = _WATER_RE.match(line)
        if match:
            self._pending["water_raw"] = int(match.group(1))
            if match.group(2):
                self._pending["water_status"] = match.group(2).upper()
            return self._complete_if_ready()

        match = _STATUS_RE.match(line)
        if match:
            self._pending["water_status"] = match.group(1).upper()
            return self._complete_if_ready()

        match = _BUZZER_RE.match(line)
        if match:
            self._pending["buzzer"] = match.group(1).upper()
            return self._complete_if_ready()

        return None

    def _complete_if_ready(self) -> dict[str, Any] | None:
        required = {"temperature_raw", "temperature_c", "temperature_error", "distance_cm",
                    "distance_status", "water_raw", "water_status", "buzzer"}
        if required.issubset(self._pending):
            reading = dict(self._pending)
            reading["timestamp"] = datetime.now().astimezone()
            self._pending = {}
            return reading
        return None


class SerialReader:
    """Own one serial port and read it on a daemon thread."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._serial: serial.Serial | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._state: dict[str, Any] = {
            "connected": False,
            "port": None,
            "error": None,
            "last_reading": None,
            "history": deque(maxlen=1800),
            "lines_received": 0,
        }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            data = dict(self._state)
            data["history"] = list(self._state["history"])
            data["last_reading"] = dict(self._state["last_reading"]) if self._state["last_reading"] else None
            return data

    def connect(self, port: str, baudrate: int = 9600) -> None:
        with self._lock:
            if self._state["connected"] or (self._thread and self._thread.is_alive()):
                raise RuntimeError("A serial reader is already active. Disconnect it before changing ports.")
            self._stop.clear()
            self._state.update(connected=False, port=port, error=None, last_reading=None,
                               history=deque(maxlen=1800), lines_received=0)
            try:
                self._serial = serial.Serial(port=port, baudrate=baudrate, timeout=0.25)
            except (serial.SerialException, OSError) as exc:
                self._serial = None
                self._state.update(port=None, error=str(exc))
                raise
            self._state["connected"] = True
            self._thread = threading.Thread(target=self._read_loop, name="aquaguard-serial", daemon=True)
            self._thread.start()

    def disconnect(self) -> None:
        with self._lock:
            self._stop.set()
            port = self._serial
            self._serial = None
            if port is not None:
                try:
                    port.close()
                except (serial.SerialException, OSError):
                    pass
            thread = self._thread
            self._state["connected"] = False
        if thread and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        with self._lock:
            if self._thread is thread:
                self._thread = None

    def _read_loop(self) -> None:
        parser = AquaGuardParser()
        while not self._stop.is_set():
            with self._lock:
                port = self._serial
            if port is None:
                break
            try:
                raw_line = port.readline()
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8", errors="replace").strip()
                with self._lock:
                    self._state["lines_received"] += 1
                reading = parser.feed_line(line)
                if reading is not None:
                    with self._lock:
                        self._state["last_reading"] = reading
                        self._state["history"].append(reading)
            except (serial.SerialException, OSError) as exc:
                if not self._stop.is_set():
                    with self._lock:
                        self._state.update(connected=False, error=f"Serial connection lost: {exc}")
                break
            except Exception as exc:  # Keep the UI alive if an unexpected device line triggers a parser issue.
                with self._lock:
                    self._state["error"] = f"Serial read error: {exc}"
                time.sleep(0.1)
        with self._lock:
            port = self._serial
            self._serial = None
            if self._state["connected"] and not self._stop.is_set():
                self._state.update(connected=False, error=self._state["error"] or "Serial connection closed.")
        if port is not None:
            try:
                port.close()
            except (serial.SerialException, OSError):
                pass
