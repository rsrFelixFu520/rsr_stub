"""完整经过各阶段钩子的 stub Job, 不启动 Isaac、不录制数据。"""

from __future__ import annotations

from typing import Any

from real2sim2real.core.config import BaseConfig
from real2sim2real.job.base import BaseJob


class StubJobConfig(BaseConfig):
    """``[job]``:stub 任务编排配置."""


class StubJob(BaseJob):
    """使用基类生命周期，任务执行接口保持空实现。"""

    config_cls = StubJobConfig

    def __init__(self, config: StubJobConfig | None = None, **kwargs: Any) -> None:
        """由基类加载配置并创建四个组件。"""
        del kwargs
        super().__init__(config=config)
