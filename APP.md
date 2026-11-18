# payload-sim

A simulated spacecraft payload instrument (a spectrometer) that a test lab would validate.

## Layout

```
payload_sim/
  instrument.py   Instrument class, failure modes, simulated + "hardware" modes
  cli.py          `python -m payload_sim selftest`
tests/
  conftest.py         skips @hardware tests unless LAB_HARDWARE=1; `sim` fixture
  test_instrument.py  unit tests: behaviour + every failure mode
  test_cli.py         CLI exit codes and JSON output
  test_hardware.py    hardware-in-the-loop tests (@pytest.mark.hardware)
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Run it

```bash
python -m payload_sim selftest              # JSON report, exit 0
python -m payload_sim selftest --ambient 70 # overheated -> exit 1
```

Exit codes: `0` passed, `1` self-test failed, `2` could not run (e.g. lab not connected).

## Test and lint

```bash
pytest                      # unit tests; hardware tests are skipped
pytest -m "not hardware"    # explicitly only the fast tests
ruff check .                # lint
ruff format --check .       # formatting
python -m build             # builds dist/*.whl (and an sdist)
```

## Failure modes

| Failure | How to trigger | What you see |
|---|---|---|
| Command while powered off | call `read_telemetry()` / `self_test()` before `power_on()` | `PoweredOffError` |
| Timeout | `timeout_rate=` (0 simulated by default, 5% in hardware mode) | `InstrumentTimeoutError`; `self_test` retries once, then marks `responsive: false` |
| Overheated | ambient above ~50 °C | `reading` jumps out of range (400–600); self test fails |
| Lab not connected | hardware mode with no/invalid state file, or `"connected": false` | `LabNotConnectedError`, CLI exit 2 |

## Simulated vs. hardware mode

- **Simulated** (default): fast; deterministic when you pass `seed=`.
- **Hardware** (`LAB_HARDWARE=1`): pretends to talk to bench equipment. It is slower (50–200 ms per read), noisier, has occasional timeouts, and reads its state from a JSON file:

  - default path: `~/lab_instrument/state.json`
  - override: `LAB_INSTRUMENT_STATE=/some/other/path.json`

  Example state file:

  ```json
  {
    "serial": "SPEC-LAB-07",
    "ambient_c": 22.5,
    "bus_voltage_v": 28.1,
    "connected": true
  }
  ```

  Then:

  ```bash
  LAB_HARDWARE=1 pytest -m hardware
  LAB_HARDWARE=1 python -m payload_sim selftest
  ```

  Try editing the file while you test (set `"ambient_c": 60` or `"connected": false`) to watch the lab "break."
