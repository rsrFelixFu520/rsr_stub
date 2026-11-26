"""无依赖的 SimWorld stub 后端,用于注册器与配置通路验证.

不启动 Kit;``init_world`` / ``destroy_world`` 为空操作.
``app`` / ``world`` / ``stage`` 由 ``BaseSimWorld`` 初始化为 None。
真实后端按需提供 play / step 等运行时接口，stub 不模拟物理步进。
"""

from __future__ import annotations

from typing import Any

from real2sim2real.core.config import BaseConfig
from real2sim2real.simworld.base import BaseSimWorld


class StubSimWorldConfig(BaseConfig):
    """``[sim_world]``:stub 仿真世界配置."""


class StubSimWorld(BaseSimWorld):
    """最小可实例化的仿真世界实现."""

    config_cls = StubSimWorldConfig  # AutoSimWorld 用此类拉 [sim_world]

    def __init__(self, config: StubSimWorldConfig | Any | None = None, **kwargs: Any) -> None:
        """保存配置;运行时句柄保持基类 ``None``.

        Args:
            config: stub 世界配置.
            **kwargs: 丢弃.

        Returns:
            None.
        """
        super().__init__()  # BaseSimWorld:app/world/stage 占位 None
        del kwargs  # AutoSimWorld 可能传入未知键
        self.config = config or self.config_cls.from_settings("sim_world")  # [sim_world] stub

    def init_world(self) -> None:
        """stub:不启动 SimulationApp.

        Returns:
            None.
        """

    def destroy_world(self) -> None:
        """stub:无运行时可销毁.

        Returns:
            None.
        """
