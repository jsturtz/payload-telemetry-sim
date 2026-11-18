import os

import pytest

from payload_sim import Instrument


def pytest_collection_modifyitems(config, items):
    if os.environ.get("LAB_HARDWARE") == "1":
        return
    skip_hw = pytest.mark.skip(reason="hardware test: set LAB_HARDWARE=1 to run")
    for item in items:
        if "hardware" in item.keywords:
            item.add_marker(skip_hw)


@pytest.fixture
def sim():
    """A powered-on, seeded, simulated instrument."""
    inst = Instrument(seed=1234, hardware=False)
    inst.power_on()
    yield inst
    inst.power_off()
