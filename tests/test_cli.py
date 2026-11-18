import json

from payload_sim.cli import main


def run(capsys, *args):
    code = main(["selftest", *args])
    return code, json.loads(capsys.readouterr().out)


def test_selftest_passes(capsys, monkeypatch):
    monkeypatch.delenv("LAB_HARDWARE", raising=False)
    code, report = run(capsys)
    assert code == 0
    assert report["passed"] is True
    assert report["mode"] == "simulated"


def test_selftest_fails_when_overheated(capsys, monkeypatch):
    monkeypatch.delenv("LAB_HARDWARE", raising=False)
    code, report = run(capsys, "--ambient", "75")
    assert code == 1
    assert report["passed"] is False


def test_selftest_reports_missing_lab(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("LAB_HARDWARE", "1")
    monkeypatch.setenv("LAB_INSTRUMENT_STATE", str(tmp_path / "nope.json"))
    code, report = run(capsys)
    assert code == 2
    assert "not found" in report["error"]
