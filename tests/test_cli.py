"""Exercise the installed command plugin through a fresh interpreter."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "real2sim2real.core.cli", *args],
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "NO_COLOR": "1", "TERM": "dumb"},
    )


@pytest.mark.parametrize("config", [None, ROOT / "configs/stub/debug.toml"])
def test_collect_runs_with_default_and_explicit_config(config):
    args = ["collect", "run"]
    if config is not None:
        args += ["-c", str(config)]
    result = run_cli(*args)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "任务生命周期完成" in result.stdout
    assert "backend=stub" in result.stdout


def test_backend_listing_and_help_load_without_simulator():
    result = run_cli("list-backends")
    assert result.returncode == 0, result.stderr
    listed = dict(line.removeprefix("[").split("] ", 1) for line in result.stdout.splitlines())
    assert set(listed) == {"sim_world", "scene", "robot", "planner", "job"}
    assert all("stub" in backends.split(", ") for backends in listed.values())
    result = run_cli("--help")
    assert result.returncode == 0
    assert "collect" in result.stdout


def test_invalid_backend_fails(monkeypatch):
    monkeypatch.setenv("RSR_JOB__BACKEND", "does_not_exist")
    result = run_cli("collect", "run")
    assert result.returncode != 0
    assert "does_not_exist" in result.stdout + result.stderr


def test_missing_config_is_cli_parameter_error(tmp_path):
    result = run_cli("collect", "run", "-c", str(tmp_path / "missing.toml"))
    assert result.returncode == 2
    assert "missing.toml" in result.stdout + result.stderr


def test_stub_does_not_import_simulator_modules():
    code = """
import sys
from real2sim2real.job.base import AutoJob
AutoJob.from_config().run()
for name in sys.modules:
    assert name.split('.')[0] not in {'isaacsim', 'omni', 'pxr', 'newton', 'warp'}
"""
    result = subprocess.run(
        [sys.executable, "-c", code], text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
