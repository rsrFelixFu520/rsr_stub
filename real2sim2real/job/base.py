"""任务编排基础接口：组件构造、生命周期与阶段扩展钩子。"""

from __future__ import annotations

from typing import Any

from real2sim2real.core.config import BaseConfig
from real2sim2real.core.logger import LoggerMixin
from real2sim2real.core.registry import JOB_REGISTRY, ensure_job_backends
from real2sim2real.planner.base import AutoPlanner, BasePlanner
from real2sim2real.robot.base import AutoRobot, BaseRobot
from real2sim2real.scene.base import AutoScene, BaseScene
from real2sim2real.simworld.base import AutoSimWorld, BaseSimWorld


class BaseJob(LoggerMixin):
    """构造时创建组件，运行时按固定顺序初始化和执行任务。

    ``run``:init_world → arrange_scene → place_robot → start_simulation。
    无论成功或失败，最终都会调用 ``close``。
    子类通过阶段钩子及 ``simulate`` 扩展具体任务，不在基类实现采集和录制。
    """

    config_cls = BaseConfig

    def __init__(self, config: BaseConfig | None = None) -> None:
        """读取任务配置并创建组件，不启动仿真运行时。"""
        super().__init__()
        self.config = config if config is not None else self.config_cls.from_settings("job")

        self.sim_world: BaseSimWorld | None = AutoSimWorld.from_config()
        self.scene: BaseScene = AutoScene.from_config()
        self.robot: BaseRobot = AutoRobot.from_config()
        self.planner: BasePlanner = AutoPlanner.from_config()

        self.state: dict[str, Any] = {}

    def run(self) -> None:
        """顺序执行四个阶段，异常向上传播并确保关闭世界。"""
        try:
            self.log.info("(1) 初始化世界阶段......")
            self.init_world()
            self.log.info("(2) 摆放场景阶段......")
            self.arrange_scene()
            self.log.info("(3) 放置机器人阶段......")
            self.place_robot()
            self.log.info("(4) 启动仿真阶段......")
            self.start_simulation()
        finally:
            self.close()

    def init_world(self) -> None:
        """前置钩子 → 初始化世界 → GUI 检查 → 后置钩子。"""
        self.before_init_world_hook()
        self.sim_world.init_world()
        self.gui_inspect("after_init_world")
        self.after_init_world_hook()

    def arrange_scene(self) -> None:
        """前置钩子 → 建图接口 → 场景初始化 → 摆放 → 调整 → GUI检查 → 后置钩子。"""
        self.before_arrange_scene_hook()
        self.build_occ()
        self.scene.init_scene(self.sim_world)
        self.scene.arrange()
        self.adjust_scene()
        self.gui_inspect("after_arrange_scene")
        self.after_arrange_scene_hook()

    def place_robot(self) -> None:
        """前置钩子 → 机器人初始化 → 摆放 → 调整 → 规划器初始化 → GUI检查 → 后置钩子。"""
        self.before_place_robot_hook()
        self.robot.init_robot(self.sim_world)
        self.robot.arrange()
        self.adjust_robot()
        self.planner.init_planner(self.robot)
        self.gui_inspect("after_place_robot")
        self.after_place_robot_hook()

    def start_simulation(self) -> None:
        """前置钩子 → GUI 准备与检查 → 执行任务 → 后置钩子。"""
        self.before_start_simulation_hook()
        self.setup_gui_hook()
        self.gui_inspect("before_simulation")
        self.simulate()
        self.after_start_simulation_hook()

    def close(self) -> None:
        """销毁世界，重复关闭时不再销毁。"""
        if self.sim_world is not None:
            self.sim_world.destroy_world()
            self.sim_world = None

    def build_occ(self) -> None:
        """挂载场景前的建图扩展接口，默认空。"""

    def adjust_scene(self) -> None:
        """调用场景的位姿调整接口。"""
        self.scene.adjust()

    def adjust_robot(self) -> None:
        """调用机器人的位姿调整接口。"""
        self.robot.adjust()

    def simulate(self) -> None:
        """任务执行接口，默认空；具体仿真循环由子类实现。"""

    def gui_inspect(self, reason: str) -> None:
        """按 inspect_gui 配置调用支持 GUI 检查的世界后端。"""
        if not getattr(self.config, "inspect_gui", False):
            return
        inspect = getattr(self.sim_world, "wait_for_gui_edit", None)
        if callable(inspect):
            inspect(reason=reason)

    def before_init_world_hook(self) -> None:
        """初始化世界之前，默认空。"""

    def after_init_world_hook(self) -> None:
        """世界初始化和 GUI 检查完成后，默认空。"""

    def before_arrange_scene_hook(self) -> None:
        """建图和场景挂载之前，默认空。"""

    def after_arrange_scene_hook(self) -> None:
        """场景摆放、调整和 GUI 检查完成后，默认空。"""

    def before_place_robot_hook(self) -> None:
        """机器人挂载之前，默认空。"""

    def after_place_robot_hook(self) -> None:
        """机器人、规划器初始化和 GUI 检查完成后，默认空。"""

    def before_start_simulation_hook(self) -> None:
        """任务执行准备之前，默认空。"""

    def setup_gui_hook(self) -> None:
        """任务执行前的 GUI 准备接口，默认空。"""

    def after_start_simulation_hook(self) -> None:
        """任务正常完成后，默认空；异常时不调用。"""


class AutoJob:
    """Job 工厂:读 ``[job].backend`` → 取 Job 类及其 ``config_cls`` → 实例化."""

    @classmethod
    def from_config(
        cls,
        backend: str | None = None,
        *,
        config: BaseConfig | None = None,
        **kwargs: Any,
    ) -> BaseJob:
        """构造已选型的 Job 实例.

        Args:
            backend: 显式后端名;None 则从 config 或 settings ``[job]`` 读.
            config: 已构造的 Job 配置;None 则用实现类 ``config_cls``.
            **kwargs: 传给 Job 构造函数(一般为空).

        Returns:
            已选型的 ``BaseJob`` 实例.
        """
        ensure_job_backends()
        name = backend or (config.backend if config is not None else BaseConfig.peek_backend("job"))
        job_cls = JOB_REGISTRY.get(name)
        if config is None:
            cfg_cls = getattr(job_cls, "config_cls", BaseConfig)
            config = cfg_cls.from_settings("job")
        return job_cls(config=config, **kwargs)
