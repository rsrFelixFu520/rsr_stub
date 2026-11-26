"""``BaseSimWorld``:仿真世界运行时基类接口.

负责仿真应用生命周期、环境 USD 加载与跨对象步进同步:

- ``init_world`` — 建立仿真运行时(App / World)并加载环境 USD
- ``destroy_world`` — 销毁仿真运行时(App/World)

场景和机器人资产不在此加载,由 Scene / Robot 后续挂入.
"""

from __future__ import annotations

from abc import ABC
from typing import Any

from real2sim2real.core.config import BaseConfig
from real2sim2real.core.registry import SIM_WORLD_REGISTRY, ensure_sim_world_backends


class BaseSimWorld(ABC):  # noqa: B024 - 生命周期提供可选空实现
    """仿真世界基类:App/World 生命周期、环境 USD 与步进同步."""

    def __init__(self) -> None:
        """占位配置与运行时句柄;子类赋值 ``config``,``init_world`` 再填 App/World.

        Returns:
            None.
        """
        super().__init__()
        self.config: BaseConfig | None = None

        self.app: Any | None = None
        self.world: Any | None = None
        self.stage: Any | None = None

    def init_world(self) -> None:  # noqa: B027
        """建立仿真运行时(App / World)并加载环境 USD.

        Returns:
            None.
        """

    def destroy_world(self) -> None:  # noqa: B027
        """销毁仿真运行时(App/World).

        Returns:
            None.
        """


class AutoSimWorld:
    """SimWorld 工厂:读 ``backend`` → 取实现类及其 ``config_cls`` → 实例化."""

    @classmethod
    def from_config(
        cls,
        backend: str | None = None,
        *,
        config: BaseConfig | None = None,
        **kwargs: Any,
    ) -> BaseSimWorld:
        """构造仿真世界后端.

        Args:
            backend: 显式名;None 则读 ``[sim_world].backend``.
            config: 已构造配置;None 则 ``from_settings("sim_world")``.
            **kwargs: 传给实现类.

        Returns:
            已实例化的仿真世界后端.
        """
        ensure_sim_world_backends()
        name = backend or (config.backend if config else BaseConfig.peek_backend("sim_world"))
        impl_cls = SIM_WORLD_REGISTRY.get(name)
        if not config:
            cfg_cls = getattr(impl_cls, "config_cls", BaseConfig)
            config = cfg_cls.from_settings("sim_world")
        return impl_cls(config=config, **kwargs)
