"""无依赖的 Robot stub 后端。"""

from __future__ import annotations

from typing import Any

from real2sim2real.core.config import BaseConfig
from real2sim2real.robot.base import BaseRobot
from real2sim2real.simworld.base import BaseSimWorld


class StubRobotConfig(BaseConfig):
    """``[robot]``:stub 机器人配置."""


class StubRobot(BaseRobot):
    """最小可实例化的机器人实现。"""

    config_cls = StubRobotConfig

    def __init__(self, config: StubRobotConfig | None = None, **kwargs: Any) -> None:
        """只保存配置；布局缓存保持基类空默认。"""
        super().__init__()
        del kwargs
        self.config = config if config is not None else self.config_cls.from_settings("robot")

    def init_robot(self, sim_world: BaseSimWorld) -> None:
        """stub 不挂 USD，只保存世界引用。"""
        self.sim_world = sim_world

    def arrange(self) -> None:
        """stub 不摆位。"""

    def adjust(self) -> None:
        """stub 不调整位姿。"""
