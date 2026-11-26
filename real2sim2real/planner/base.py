"""``BasePlanner``:可插拔运动规划后端基类接口.

Job 在 ``place_robot`` 末尾调用 ``init_planner``;
采集循环再 ``on_physics_step``.

"""

from __future__ import annotations

from abc import ABC
from typing import Any

from real2sim2real.core.config import BaseConfig
from real2sim2real.core.registry import PLANNER_REGISTRY, ensure_planner_backends


class BasePlanner(ABC):  # noqa: B024 - 生命周期提供可选空实现
    """运动规划后端接口.

    Job ``place_robot`` 固定先 ``init_planner``;采集循环再推进 / 落盘 / 复位.
    子类只覆盖钩子,不要改 ``init_planner`` / ``on_physics_step`` 的语义.
    """

    def __init__(self) -> None:
        """占位配置与执行状态;子类赋值 ``config``,``init_planner`` 再加载求解器.

        Returns:
            None.
        """
        super().__init__()  # 初始化 ABC
        self.config: BaseConfig | None = None
        self.robot: Any | None = None  # init_planner 时挂引用,子类可用
        self.state: dict[str, Any] = {}  # 额外状态,子类可用

        self.state["ready"] = False  # 求解器是否已加载成功
        self.state["timeout_s"] = 60.0  # Job 墙钟超时;后端可按自己的 Config 覆盖
        self.state["phase"] = "idle"  # 执行阶段名,recorder 落盘
        self.state["last_action"] = None  # 最近下发的动作

    def init_planner(self, robot: Any) -> None:  # noqa: B027
        """初始化运动规划后端.

        Args:
            robot: 已 ``arrange`` 的机器人(根位姿此时才有效).

        Returns:
            None.
        """

    def on_physics_step(self, robot: Any) -> bool:
        """每个物理步推进当前任务;返回 True 表示本episode已结束;默认立刻结束.

        Args:
            robot: 当前步要下发动作的机器人(读状态 / 写关节).

        Returns:
            True 表示本 episode 已结束;默认立刻结束.
        """
        del robot  # 基类不推进任务,参数仅满足签名;子类覆盖真正步进
        return True  # 立刻结束


class AutoPlanner:
    """规划器工厂:读 ``backend`` → 取实现类及其 ``config_cls`` → 实例化."""

    @classmethod
    def from_config(
        cls,
        backend: str | None = None,
        *,
        config: BaseConfig | None = None,
        **kwargs: Any,
    ) -> BasePlanner:
        """构造 stub / curobo 等规划器.

        Args:
            backend: 显式名;None 则读 config 或 ``[planner].backend``.
            config: 已构造配置;None 则 ``config_cls.from_settings("planner")``.
            **kwargs: 传给实现类构造函数.

        Returns:
            对应 backend 的规划器实例.
        """
        ensure_planner_backends()
        name = backend or (
            config.backend if config is not None else BaseConfig.peek_backend("planner")
        )
        impl_cls = PLANNER_REGISTRY.get(name)
        if config is None:
            cfg_cls = getattr(impl_cls, "config_cls", BaseConfig)
            config = cfg_cls.from_settings("planner")
        return impl_cls(config=config, **kwargs)
