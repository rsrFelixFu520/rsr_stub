"""无依赖的 Planner stub 后端.

供 Registry / Job 冒烟,不调用 GPU.
``ready`` / ``phase`` 等由 ``BasePlanner`` 提供默认.
"""

from __future__ import annotations

from typing import Any

from real2sim2real.core.config import BaseConfig
from real2sim2real.planner.base import BasePlanner
from real2sim2real.robot.base import BaseRobot


class StubPlannerConfig(BaseConfig):
    """``[planner]``:stub 规划器配置."""


class StubPlanner(BasePlanner):
    """最小可实例化的规划器实现."""

    config_cls = StubPlannerConfig  # AutoPlanner 用此类拉 [planner]

    def __init__(self, config: StubPlannerConfig | Any | None = None, **kwargs: Any) -> None:
        """读取配置;抓放状态保持基类默认(``ready=False``, ``phase=idle``).

        Args:
            config: stub 规划配置;None 则 from_settings("planner").
            **kwargs: 丢弃.

        Returns:
            None.
        """
        super().__init__()  # BasePlanner:ready=False, phase=idle
        del kwargs  # AutoPlanner 可能传入未知键
        self.config = config or self.config_cls.from_settings("planner")  # [planner] stub

    def init_planner(self, robot: BaseRobot) -> None:
        """标记就绪;不加载任何求解器.

        Args:
            robot: Job 传入的已放置机器人;stub 不读位姿,仅满足契约.

        Returns:
            None.
        """
        self.robot = robot
        self.state["ready"] = True
        self.state["phase"] = "idle"
