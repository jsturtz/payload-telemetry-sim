"""Simulated spacecraft payload instrument (a spectrometer)."""

from payload_sim.instrument import (
    Instrument,
    InstrumentError,
    InstrumentTimeoutError,
    LabNotConnectedError,
    PoweredOffError,
)

__all__ = [
    "Instrument",
    "InstrumentError",
    "InstrumentTimeoutError",
    "LabNotConnectedError",
    "PoweredOffError",
]
__version__ = "0.1.0"
