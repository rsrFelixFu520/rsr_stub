"""``BaseRobot``:在已有仿真环境中添加机器人.

SimWorld 负责环境 USD 与生命周期;Robot 不启停 App.
``init_robot`` 挂引用,``arrange`` 初始化 pose, ``adjust`` 调整 pose.
"""

from __future__ import annotations

from abc import ABC
from typing import Any

import numpy as np

from real2sim2real.core.config import BaseConfig
from real2sim2real.core.registry import ROBOT_REGISTRY, ensure_robot_backends
from real2sim2real.simworld.base import BaseSimWorld


class BaseRobot(ABC):  # noqa: B024 - 与 BaseScene 一致，生命周期提供可选空实现
    """机器人模块:在 simworld 已加载的环境中添加机器人.

    Job ``place_robot`` 中调用, 先 ``init_robot`` 再 ``arrange``;采集循环再读
    位姿 / 目标 / 图像.子类只覆盖钩子,不要改这些入口的语义.
    """

    def __init__(self) -> None:
        """占位配置与布局缓存.

        Returns:
            None.
        """
        super().__init__()
        self.config: BaseConfig | None = None

        self.sim_world: BaseSimWorld | None = None
        self.poses: dict[str, tuple[np.ndarray, np.ndarray]] = {}  # arrange 后的世界位姿
        self.poses_realtime: dict[str, tuple[np.ndarray, np.ndarray]] = {}  # play 中当前位姿
        self.sensors: dict[str, Any] = {}  # 相机名 → 传感器
        self.state: dict[str, Any] = {}  # 额外状态,子类可用

    def init_robot(self, sim_world: BaseSimWorld) -> None:  # noqa: B027
        """打开 USD 并添加到 sim world 对应 prim;不负责位姿编排.

        Args:
            sim_world: 已 ``init_world`` 的世界,须带可用 stage.

        Returns:
            None.
        """

    def arrange(self) -> None:  # noqa: B027
        """按配置把已加载机器人摆到 sim world 中的目标位姿.

        Returns:
            None.
        """

    def adjust(self) -> None:  # noqa: B027 - 可选扩展接口
        """摆放完成后的位姿调整接口，默认空。"""


class AutoRobot:
    """Robot 工厂:读 ``backend`` → 取实现类及其 ``config_cls`` → 实例化."""

    @classmethod
    def from_config(
        cls,
        backend: str | None = None,
        *,
        config: BaseConfig | None = None,
        **kwargs: Any,
    ) -> BaseRobot:
        """按配置构造机器人后端.

        Args:
            backend: 显式名;None 则读 ``[robot].backend``.
            config: 已构造配置;None 则 ``from_settings("robot")``.
            **kwargs: 传给实现类.

        Returns:
            已实例化的 Robot 后端.
        """
        ensure_robot_backends()
        name = backend or (config.backend if config else BaseConfig.peek_backend("robot"))
        impl_cls = ROBOT_REGISTRY.get(name)
        if config is None:
            cfg_cls = getattr(impl_cls, "config_cls", BaseConfig)
            config = cfg_cls.from_settings("robot")
        return impl_cls(config=config, **kwargs)
