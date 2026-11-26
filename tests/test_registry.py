"""Installed entry points and resilient third-party plugin discovery."""

import tomllib
from importlib.metadata import distribution
from pathlib import Path
from types import SimpleNamespace

import pytest

from real2sim2real.core import registry


def test_template_registers_stub_in_each_domain():
    project_file = Path(__file__).resolve().parents[1] / "pyproject.toml"
    project = tomllib.loads(project_file.read_text())["project"]
    own = distribution(project["name"])
    installed = {(ep.group, ep.name): ep for ep in own.entry_points}
    domains = {
        "simworld": ("SIM_WORLD", "real2sim2real.simworld.stub:StubSimWorld"),
        "scene": ("SCENE", "real2sim2real.scene.scene_stub:StubScene"),
        "robot": ("ROBOT", "real2sim2real.robot.robot_stub:StubRobot"),
        "planner": ("PLANNER", "real2sim2real.planner.planner_stub:StubPlanner"),
        "job": ("JOB", "real2sim2real.job.job_stub:StubJob"),
    }
    registry.ensure_all_backends()
    for domain, (name, target) in domains.items():
        group = f"real2sim2real.{domain}.backends"
        assert project["entry-points"][group]["stub"] == target
        entry_point = installed[group, "stub"]
        assert entry_point.value == target
        registered = getattr(registry, f"{name}_REGISTRY")
        assert "stub" in registered.list()
        assert registered.get("stub") is entry_point.load()


def test_failed_plugin_does_not_hide_working_plugins(monkeypatch):
    def broken():
        raise ImportError("optional runtime is missing")

    class Working:
        pass

    plugins = [
        SimpleNamespace(name="broken", load=broken),
        SimpleNamespace(name="working", load=lambda: Working),
    ]
    monkeypatch.setattr(registry, "entry_points", lambda *, group: plugins)
    local = registry.Registry("test")
    with pytest.warns(UserWarning, match="broken"):
        local.load_entry_points("test.backends")
    assert local.get("working") is Working
    with pytest.raises(KeyError, match="Available backends: working"):
        local.get("missing")
