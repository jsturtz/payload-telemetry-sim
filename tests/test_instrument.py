import pytest

from payload_sim import Instrument, InstrumentTimeoutError, LabNotConnectedError, PoweredOffError
from payload_sim.instrument import (
    MAX_OPERATING_TEMP_C,
    NOMINAL_READING,
    READING_RANGE,
    VOLTAGE_RANGE_V,
)

# ---- power ---------------------------------------------------------------


def test_starts_powered_off():
    assert Instrument(hardware=False).powered is False


def test_power_cycle(sim):
    assert sim.powered
    sim.power_off()
    assert not sim.powered


@pytest.mark.parametrize("command", ["read_telemetry", "self_test"])
def test_commands_rejected_when_powered_off(command):
    inst = Instrument(seed=1, hardware=False)
    with pytest.raises(PoweredOffError, match="powered off"):
        getattr(inst, command)()


# ---- telemetry -----------------------------------------------------------


def test_telemetry_has_expected_fields(sim):
    frame = sim.read_telemetry()
    assert set(frame) == {"serial", "mode", "temperature_c", "voltage_v", "reading", "timestamp"}
    assert frame["mode"] == "simulated"


def test_telemetry_values_in_range(sim):
    for _ in range(10):
        frame = sim.read_telemetry()
        assert READING_RANGE[0] <= frame["reading"] <= READING_RANGE[1]
        assert VOLTAGE_RANGE_V[0] <= frame["voltage_v"] <= VOLTAGE_RANGE_V[1]
        assert frame["temperature_c"] < MAX_OPERATING_TEMP_C


def test_same_seed_is_deterministic():
    def readings(seed):
        inst = Instrument(seed=seed, hardware=False)
        inst.power_on()
        return [inst.read_telemetry()["reading"] for _ in range(5)]

    assert readings(99) == readings(99)
    assert readings(99) != readings(100)


def test_reading_near_nominal():
    inst = Instrument(hardware=False)
    inst.power_on()
    reading = inst.read_telemetry()["reading"]
    assert abs(reading - NOMINAL_READING) < 6.5


def test_self_heating_raises_temperature(sim):
    first = sim.read_telemetry()["temperature_c"]
    for _ in range(20):
        last = sim.read_telemetry()["temperature_c"]
    assert last > first + 3


# ---- failure modes -------------------------------------------------------


def test_overheated_reading_out_of_range():
    inst = Instrument(seed=5, hardware=False, ambient_c=60.0)
    inst.power_on()
    frame = inst.read_telemetry()
    assert frame["temperature_c"] > MAX_OPERATING_TEMP_C
    assert frame["reading"] > READING_RANGE[1]


def test_timeout_raised():
    inst = Instrument(seed=3, hardware=False, timeout_rate=1.0)
    inst.power_on()
    with pytest.raises(InstrumentTimeoutError):
        inst.read_telemetry()


def test_occasional_timeouts_are_reproducible():
    def count_timeouts(seed):
        inst = Instrument(seed=seed, hardware=False, timeout_rate=0.1)
        inst.power_on()
        timeouts = 0
        for _ in range(200):
            try:
                inst.read_telemetry()
            except InstrumentTimeoutError:
                timeouts += 1
        return timeouts

    assert count_timeouts(11) == count_timeouts(11)
    assert 5 < count_timeouts(11) < 40


def test_hardware_mode_without_lab_fails(tmp_path):
    inst = Instrument(seed=1, hardware=True, state_file=tmp_path / "missing.json")
    with pytest.raises(LabNotConnectedError, match="not found"):
        inst.power_on()


def test_hardware_mode_disconnected(tmp_path):
    state = tmp_path / "state.json"
    state.write_text('{"connected": false}')
    inst = Instrument(seed=1, hardware=True, state_file=state)
    with pytest.raises(LabNotConnectedError, match="connected=false"):
        inst.power_on()


# ---- self test -----------------------------------------------------------


def test_self_test_passes_nominal(sim):
    report = sim.self_test()
    assert report["passed"] is True
    assert all(report["checks"].values())
    assert len(report["frames"]) == 3


def test_self_test_fails_when_overheated():
    inst = Instrument(seed=5, hardware=False, ambient_c=60.0)
    inst.power_on()
    report = inst.self_test()
    assert report["passed"] is False
    assert report["checks"]["temperature"] is False
    assert report["checks"]["reading"] is False


def test_self_test_fails_on_timeout():
    inst = Instrument(seed=3, hardware=False, timeout_rate=1.0)
    inst.power_on()
    report = inst.self_test()
    assert report["passed"] is False
    assert report["checks"]["responsive"] is False
    assert report["errors"]
