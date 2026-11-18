"""Hardware-in-the-loop tests. Skipped unless LAB_HARDWARE=1.

They talk to the lab instrument (state file at ~/lab_instrument/state.json,
or wherever LAB_INSTRUMENT_STATE points).
"""

import json

import pytest

from payload_sim import Instrument
from payload_sim.instrument import state_file_path

pytestmark = pytest.mark.hardware


@pytest.fixture
def lab():
    inst = Instrument(seed=2024)
    inst.power_on()
    yield inst
    inst.power_off()


def test_lab_instrument_connects(lab):
    assert lab.mode == "hardware"
    assert lab.serial != "SIM-0001"


def test_lab_telemetry_matches_bench_state(lab):
    state = json.loads(state_file_path().read_text())
    frame = lab.read_telemetry()
    assert frame["serial"] == state["serial"]
    assert abs(frame["voltage_v"] - state.get("bus_voltage_v", 28.0)) < 0.5


def test_lab_self_test(lab):
    report = lab.self_test()
    assert report["passed"], json.dumps(report, indent=2)
