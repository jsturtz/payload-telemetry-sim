"""The payload instrument model.

Two modes:
  * simulated (default): pure Python, fast, deterministic when given a seed.
  * hardware (LAB_HARDWARE=1): pretends to talk to a lab instrument whose
    state lives in a JSON file (default ~/lab_instrument/state.json). Slower,
    noisier, and occasionally times out, like real bench equipment.
"""

from __future__ import annotations

import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

# Nominal values and limits for the instrument.
NOMINAL_READING = 500.0  # detector counts at the reference wavelength
NOMINAL_BUS_VOLTAGE_V = 28.0
DEFAULT_AMBIENT_C = 20.0
SELF_HEATING_C_PER_READ = 0.2

READING_RANGE = (400.0, 600.0)
VOLTAGE_RANGE_V = (27.0, 29.0)
MAX_OPERATING_TEMP_C = 50.0

SIM_NOISE_SIGMA = 5.0
HW_NOISE_SIGMA = 8.0
HW_LATENCY_S = (0.05, 0.2)
HW_DEFAULT_TIMEOUT_RATE = 0.05

DEFAULT_STATE_FILE = Path.home() / "lab_instrument" / "state.json"


class InstrumentError(Exception):
    """Base class for instrument failures."""


class PoweredOffError(InstrumentError):
    """A command was sent while the instrument was powered off."""


class InstrumentTimeoutError(InstrumentError):
    """The instrument did not respond in time."""


class LabNotConnectedError(InstrumentError):
    """Hardware mode was requested but the lab instrument is unavailable."""


def hardware_mode_enabled() -> bool:
    return os.environ.get("LAB_HARDWARE") == "1"


def state_file_path() -> Path:
    override = os.environ.get("LAB_INSTRUMENT_STATE")
    return Path(override) if override else DEFAULT_STATE_FILE


class Instrument:
    """A spectrometer payload.

    Args:
        seed: RNG seed. Pass one for reproducible simulated behaviour;
            None means unseeded (different every run).
        hardware: force hardware mode on/off. None reads LAB_HARDWARE.
        timeout_rate: probability that any single read times out.
            None picks the mode default (0 simulated, 5% hardware).
        ambient_c: starting ambient temperature (simulated mode only;
            hardware mode reads it from the state file).
        state_file: path to the lab state file (hardware mode only).
    """

    def __init__(
        self,
        seed: int | None = None,
        hardware: bool | None = None,
        timeout_rate: float | None = None,
        ambient_c: float = DEFAULT_AMBIENT_C,
        state_file: Path | str | None = None,
    ) -> None:
        self.hardware = hardware_mode_enabled() if hardware is None else hardware
        if timeout_rate is None:
            timeout_rate = HW_DEFAULT_TIMEOUT_RATE if self.hardware else 0.0
        self.timeout_rate = timeout_rate
        self.ambient_c = ambient_c
        self.state_file = Path(state_file) if state_file else state_file_path()
        self.serial = "SIM-0001"
        self.powered = False
        self.reads = 0
        self.bus_voltage_v = NOMINAL_BUS_VOLTAGE_V
        self._rng = random.Random(seed)

    @property
    def mode(self) -> str:
        return "hardware" if self.hardware else "simulated"

    # ---- power ---------------------------------------------------------

    def power_on(self) -> None:
        if self.hardware:
            self._load_lab_state()
        self.powered = True
        self.reads = 0

    def power_off(self) -> None:
        self.powered = False

    # ---- telemetry -----------------------------------------------------

    def read_telemetry(self) -> dict:
        """Return one telemetry frame.

        Note: when overheated the detector returns garbage readings rather
        than raising. Catching that is the job of self_test() and the tests.
        """
        self._require_power("read_telemetry")

        if self.hardware:
            time.sleep(self._rng.uniform(*HW_LATENCY_S))
            self._load_lab_state()

        if self._rng.random() < self.timeout_rate:
            raise InstrumentTimeoutError("no response from instrument")

        self.reads += 1
        sigma = HW_NOISE_SIGMA if self.hardware else SIM_NOISE_SIGMA
        temperature = (
            self.ambient_c + SELF_HEATING_C_PER_READ * self.reads + self._rng.gauss(0, 0.1)
        )
        voltage = self.bus_voltage_v + self._rng.gauss(0, 0.05)
        reading = NOMINAL_READING + self._rng.gauss(0, sigma)
        if temperature > MAX_OPERATING_TEMP_C:
            # Thermal runaway in the detector: counts saturate.
            reading *= 2.5

        return {
            "serial": self.serial,
            "mode": self.mode,
            "temperature_c": round(temperature, 2),
            "voltage_v": round(voltage, 3),
            "reading": round(reading, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ---- self test -----------------------------------------------------

    def self_test(self, samples: int = 3) -> dict:
        """Take a few readings and check every value against its limits."""
        self._require_power("self_test")

        frames: list[dict] = []
        errors: list[str] = []
        for _ in range(samples):
            frame = self._read_with_retry(errors)
            if frame is not None:
                frames.append(frame)

        checks = {
            "responsive": len(frames) == samples,
            "temperature": all(f["temperature_c"] <= MAX_OPERATING_TEMP_C for f in frames),
            "voltage": all(_in_range(f["voltage_v"], VOLTAGE_RANGE_V) for f in frames),
            "reading": all(_in_range(f["reading"], READING_RANGE) for f in frames),
        }
        return {
            "serial": self.serial,
            "mode": self.mode,
            "passed": bool(frames) and all(checks.values()),
            "checks": checks,
            "errors": errors,
            "frames": frames,
        }

    # ---- internals -----------------------------------------------------

    def _read_with_retry(self, errors: list[str], attempts: int = 2) -> dict | None:
        """Like a real driver: retry a timed-out read once before giving up."""
        for attempt in range(1, attempts + 1):
            try:
                return self.read_telemetry()
            except InstrumentTimeoutError as exc:
                errors.append(f"timeout (attempt {attempt}/{attempts}): {exc}")
        return None

    def _require_power(self, command: str) -> None:
        if not self.powered:
            raise PoweredOffError(f"command '{command}' rejected: instrument is powered off")

    def _load_lab_state(self) -> None:
        try:
            state = json.loads(self.state_file.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise LabNotConnectedError(
                f"lab instrument state file not found: {self.state_file}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise LabNotConnectedError(f"lab state file is not valid JSON: {exc}") from exc

        if not state.get("connected", True):
            raise LabNotConnectedError("lab instrument reports connected=false")
        self.serial = state.get("serial", "LAB-UNKNOWN")
        self.ambient_c = float(state.get("ambient_c", DEFAULT_AMBIENT_C))
        self.bus_voltage_v = float(state.get("bus_voltage_v", NOMINAL_BUS_VOLTAGE_V))


def _in_range(value: float, bounds: tuple[float, float]) -> bool:
    low, high = bounds
    return low <= value <= high
