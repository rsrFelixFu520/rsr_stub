"""Configuration inheritance, validation and precedence contracts."""

import pytest
from pydantic import ValidationError

from real2sim2real.core.config import BaseConfig, apply_settings_file, reset_settings


class TaskConfig(BaseConfig):
    count: int = 1
    label: str = "default"


def test_defaults_work_without_project_file():
    assert BaseConfig.from_settings("job").backend == "stub"
    assert TaskConfig.from_settings("missing") == TaskConfig()


def test_relative_inheritance_and_precedence(monkeypatch, tmp_path):
    configs = tmp_path / "configs"
    configs.mkdir()
    (configs / "parent.toml").write_text('[job]\ncount = 2\nlabel = "parent"\n')
    child = configs / "child.toml"
    child.write_text('inherit = "parent.toml"\n[job]\ncount = 3\n')
    apply_settings_file(child)
    assert TaskConfig.from_settings("job") == TaskConfig(count=3, label="parent")

    (configs / ".secrets.toml").write_text("[job]\ncount = 4\n")
    reset_settings()
    assert TaskConfig.from_settings("job").count == 4

    monkeypatch.setenv("RSR_JOB__COUNT", "5")
    reset_settings()
    assert TaskConfig.from_settings("job").count == 5


def test_configuration_switch_drops_cache(tmp_path):
    first = tmp_path / "first.toml"
    second = tmp_path / "second.toml"
    first.write_text("[job]\ncount = 2\n")
    second.write_text("[job]\ncount = 8\n")
    apply_settings_file(first)
    assert TaskConfig.from_settings("job").count == 2
    apply_settings_file(second)
    assert TaskConfig.from_settings("job").count == 8


def test_unknown_fields_are_rejected(tmp_path):
    path = tmp_path / "settings.toml"
    path.write_text("[job]\ncoutn = 2\n")
    with pytest.raises(ValidationError, match="coutn"):
        TaskConfig.from_settings("job")


def test_missing_explicit_file_is_rejected(tmp_path):
    with pytest.raises(FileNotFoundError, match="missing.toml"):
        apply_settings_file(tmp_path / "missing.toml")


def test_yaml_roundtrip_creates_parent_directories(tmp_path):
    path = tmp_path / "nested" / "task.yaml"
    config = TaskConfig(count=7, label="测试")
    config.to_yaml(path)
    assert TaskConfig.from_yaml(path) == config
