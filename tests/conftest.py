"""Keep developer configuration and cached logging out of stub tests."""

import os

import pytest

from real2sim2real.core.config import reset_settings
from real2sim2real.core.logger import reset_logging


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch, tmp_path):
    for name in list(os.environ):
        if name.startswith("RSR_"):
            monkeypatch.delenv(name)
    monkeypatch.chdir(tmp_path)
    reset_settings()
    reset_logging()
    yield
    reset_logging()
    reset_settings()
