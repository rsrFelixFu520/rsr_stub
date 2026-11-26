"""无依赖的 Scene stub 后端."""

from __future__ import annotations

from typing import Any

from real2sim2real.core.config import BaseConfig
from real2sim2real.scene.base import BaseScene
from real2sim2real.simworld.base import BaseSimWorld


class StubSceneConfig(BaseConfig):
    """``[scene]``:stub 场景配置."""


class StubScene(BaseScene):
    """最小可实例化的场景实现."""

    config_cls = StubSceneConfig

    def __init__(
        self,
        config: StubSceneConfig | Any | None = None,
        **kwargs: Any,
    ) -> None:
        """只保存配置;布局缓存保持基类空默认.

        Args:
            config: stub 场景配置.
            **kwargs: 丢弃.

        Returns:
            None.
        """
        super().__init__()  # poses / poses_realtime / sensors / sim_world 保持基类空默认
        del kwargs
        self.config = config or self.config_cls.from_settings("scene")

    def init_scene(self, sim_world: BaseSimWorld | None = None) -> None:
        """stub:不挂 USD.

        Args:
            sim_world: 已 ``init_world`` 的世界;stub 只保存引用,不访问 stage.

        Returns:
            None.
        """
        self.sim_world = sim_world

    def arrange(self) -> None:
        """stub:不摆位.

        Returns:
            None.
        """
