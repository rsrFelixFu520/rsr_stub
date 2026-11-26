"""文本日志：控制台输出与可选的文件保存，异常堆栈保留多行。"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, ClassVar

import structlog
from pydantic import field_validator

from real2sim2real.core.config import BaseConfig

__all__ = ["LogConfig", "LoggerMixin", "configure_logging", "get_logger", "reset_logging"]


class LogConfig(BaseConfig):
    """统一使用 level 过滤日志; log_file 未设置时只输出到控制台。"""

    level: str = "INFO"
    console: bool = True
    log_file: Path | None = None

    @field_validator("level")
    @classmethod
    def _validate_level(cls, value: str) -> str:
        level = value.upper()
        if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"Unsupported log level: {value!r}")
        return level


def _render_text(_logger: Any, _name: str, event: dict[str, Any]) -> str:
    """普通事件写一行，附加字段跟随内容，异常堆栈另起多行。"""

    def single_line(value: Any) -> str:
        return str(value).replace("\r", "\\r").replace("\n", "\\n")

    timestamp = event.pop("timestamp")
    level = event.pop("level").upper()
    message = single_line(event.pop("event", ""))
    exception = event.pop("exception", None)
    event.pop("logger", None)
    fields = " ".join(f"{key}={single_line(value)}" for key, value in event.items())
    text = f"{timestamp} [{level}] {message}"
    if fields:
        text += f" {fields}"
    if exception:
        text += f"\n{exception}"
    return text


_config: LogConfig | None = None
_handlers: list[logging.Handler] = []


def configure_logging(config: LogConfig | None = None, *, force: bool = False) -> LogConfig:
    """配置项目日志；省略 config 时读取 settings 的 logging 段。"""
    global _config
    if _config is not None and not force:
        return _config.model_copy(deep=True)
    config = config if config is not None else LogConfig.from_settings("logging")
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.ExtraAdder(),
            structlog.processors.TimeStamper(fmt="iso", utc=True),
        ],
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.format_exc_info,
            _render_text,
        ],
    )
    handlers: list[logging.Handler] = []
    if config.console:
        handlers.append(logging.StreamHandler(sys.stdout))
    if config.log_file is not None:
        path = config.log_file.expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))
    if not handlers:
        handlers.append(logging.NullHandler())
    logger = logging.getLogger("real2sim2real")
    for handler in _handlers:
        logger.removeHandler(handler)
        handler.close()
    for handler in handlers:
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(config.level)
    logger.propagate = False
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )
    _handlers[:] = handlers
    _config = config.model_copy(deep=True)
    return _config.model_copy(deep=True)


def reset_logging() -> None:
    """关闭项目创建的日志句柄，使下次获取 logger 时重新配置。"""
    global _config
    logger = logging.getLogger("real2sim2real")
    for handler in _handlers:
        logger.removeHandler(handler)
        handler.close()
    _handlers.clear()
    _config = None


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """获取 logger, 例如 log.info('scene_loaded', scene_id='demo')。"""
    if _config is None:
        configure_logging()
    name = name or "real2sim2real"
    if name != "real2sim2real" and not name.startswith("real2sim2real."):
        name = f"real2sim2real.{name}"
    return structlog.stdlib.get_logger(name)


class LoggerMixin:
    """为业务类提供绑定 component 字段的 self.log。"""

    log_component: ClassVar[str | None] = None

    @property
    def log(self) -> structlog.stdlib.BoundLogger:
        cls = type(self)
        return get_logger(f"{cls.__module__}.{cls.__qualname__}").bind(
            component=self.log_component or cls.__qualname__
        )
