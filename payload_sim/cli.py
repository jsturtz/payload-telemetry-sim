"""Command line entry point: `python -m payload_sim selftest`.

Exit codes: 0 = self test passed, 1 = self test failed, 2 = could not run.
"""

from __future__ import annotations

import argparse
import json
import sys

from payload_sim.instrument import Instrument, InstrumentError, hardware_mode_enabled


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="payload_sim", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    selftest = sub.add_parser("selftest", help="power on, run a self test, print a JSON report")
    selftest.add_argument(
        "--seed",
        type=int,
        default=None,
        help="RNG seed (default: 42 in simulated mode, unseeded in hardware mode)",
    )
    selftest.add_argument("--samples", type=int, default=3, help="readings to take")
    selftest.add_argument(
        "--ambient", type=float, default=None, help="ambient temp in C (simulated mode)"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    seed = args.seed
    if seed is None and not hardware_mode_enabled():
        seed = 42
    kwargs = {"seed": seed}
    if args.ambient is not None:
        kwargs["ambient_c"] = args.ambient
    instrument = Instrument(**kwargs)

    try:
        instrument.power_on()
        report = instrument.self_test(samples=args.samples)
    except InstrumentError as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, indent=2))
        return 2
    finally:
        instrument.power_off()

    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
