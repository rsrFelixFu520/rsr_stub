"""通用后端注册表.

- :class:`Registry` — ``{名称: 实现类}``,支持装饰器注册与 entry_points 插件发现
- ``*_REGISTRY`` — 仿真后端注册表
- ``ensure_*`` — 惰性从 ``pyproject.toml`` entry points 加载后端

选型:``peek_backend`` → ``ensure_*`` → ``REGISTRY.get(name)``.
"""

from __future__ import annotations

from collections.abc import Callable
from importlib.metadata import entry_points
from typing import Any


class Registry[T]:
    """某项能力(例如 ``"planner"``)的后端注册表."""

    def __init__(self, kind: str) -> None:
        """创建注册表.

        Args:
            kind: 能力类别名,出现在错误信息里(如 ``Unknown planner backend``).

        Returns:
            None.
        """
        self.kind = kind  # 出现在 Unknown {kind} backend 错误里
        self._impls: dict[str, type[T]] = {}  # 配置字符串 → 实现类

    def register(self, name: str) -> Callable[[type[T]], type[T]]:
        """返回装饰器,将类注册为名为 ``name`` 的后端.

        Args:
            name: 后端名称(配置里写的字符串,如 ``"stub"``).

        Returns:
            装饰器 ``_wrap``,将类登记为 ``name``.

        Example::

            PLANNER_REGISTRY = Registry("planner")

            @PLANNER_REGISTRY.register("stub")
            class StubPlanner: ...
        """

        def _wrap(cls: type[T]) -> type[T]:
            """把 ``cls`` 登记为 ``name``,并原样返回该类.

            Args:
                cls: 被装饰的后端实现类.

            Returns:
                原样返回的 ``cls``.
            """
            self._impls[name] = cls  # 同名后注册覆盖前者
            return cls  # 原样返回,类定义不受影响

        return _wrap  # 给 @REGISTRY.register("stub") 用

    def register_class(self, name: str, cls: type[T]) -> None:
        """非装饰器场景的直接注册(例如 entry_points 自动加载).

        Args:
            name: 后端名称(entry point 的 name).
            cls: 实现类.

        Returns:
            None.
        """
        self._impls[name] = cls  # 与 @register 同一张表,后者覆盖

    def get(self, name: str) -> type[T]:
        """按名称取实现类;未注册时抛 ``KeyError``.

        Args:
            name: 后端名称.

        Returns:
            已注册的实现类.

        Raises:
            KeyError: 名称未注册.
        """
        if name not in self._impls:  # 未 ensure_* 或拼错 backend 名
            # 空表时给出明确提示,避免拼出空 Available 列表
            available = ", ".join(sorted(self._impls)) or "(no backends registered)"
            # 把已注册名带进异常,AutoX / CLI 才能提示改配置
            raise KeyError(
                f"Unknown {self.kind} backend: '{name}'. Available backends: {available}"
            )
        return self._impls[name]  # AutoX 拿到类后再实例化

    def list(self) -> list[str]:
        """返回已注册后端名称的排序列表(``rsr list-backends`` 用).

        Returns:
            已注册后端名称,按字母排序.
        """
        return sorted(self._impls)  # 稳定顺序,rsr list-backends 直接打印

    def is_registered(self, name: str) -> bool:
        """判断 ``name`` 是否已注册.

        Args:
            name: 后端名称.

        Returns:
            ``True`` 如果 ``name`` 已注册,否则 ``False``.
        """
        return name in self._impls  # 不触发加载;ensure_* 之后再问才准

    def load_entry_points(self, group: str) -> None:
        """扫描 entry_points group,自动注册 ``pyproject.toml`` 声明的实现.

        本包与第三方插件均在 ``pyproject.toml`` 中声明::

            [project.entry-points."real2sim2real.planner.backends"]
            stub = "real2sim2real.planner.planner_stub:StubPlanner"

        单个插件 import 失败只 warn,不阻断 CLI/Registry.

        Args:
            group: entry point 组名,须与 ``pyproject.toml`` 一致.

        Returns:
            None.单个插件失败只 warn.
        """
        for ep in entry_points(group=group):
            try:
                impl_cls = ep.load()  # import 实现模块并取出类
            except Exception as exc:  # noqa: BLE001 - 插件加载失败不得中止启动
                import warnings  # 延迟 import,避免顶层依赖 warnings

                warnings.warn(
                    f"Failed to load plugin '{ep.name}' (from entry_points group '{group}'): {exc}",
                    stacklevel=2,
                )
                continue  # 跳过坏插件,继续扫其余
            self.register_class(ep.name, impl_cls)  # name 即配置里的 backend 字符串


# 五个能力域各一张表,与 pyproject entry point 组一一对应
SIM_WORLD_REGISTRY: Registry[Any] = Registry("sim_world")
SCENE_REGISTRY: Registry[Any] = Registry("scene")
ROBOT_REGISTRY: Registry[Any] = Registry("robot")
PLANNER_REGISTRY: Registry[Any] = Registry("planner")
JOB_REGISTRY: Registry[Any] = Registry("job")

_SIM_WORLD_EP = "real2sim2real.simworld.backends"  # 与 pyproject.toml 组名必须一致
_SCENE_EP = "real2sim2real.scene.backends"
_ROBOT_EP = "real2sim2real.robot.backends"
_PLANNER_EP = "real2sim2real.planner.backends"
_JOB_EP = "real2sim2real.job.backends"

_sim_world_loaded = False  # 惰性加载开关,避免 import 时就拉 Isaac
_scene_loaded = False
_robot_loaded = False
_planner_loaded = False
_job_loaded = False


def ensure_sim_world_backends() -> None:
    """惰性从 entry points 加载 SimWorld 后端.

    Returns:
        None.
    """
    global _sim_world_loaded
    if not _sim_world_loaded:
        SIM_WORLD_REGISTRY.load_entry_points(_SIM_WORLD_EP)  # 只扫一次
        _sim_world_loaded = True  # 重复调用不再扫盘


def ensure_scene_backends() -> None:
    """惰性从 entry points 加载 Scene 后端.

    Returns:
        None.
    """
    global _scene_loaded
    if not _scene_loaded:
        SCENE_REGISTRY.load_entry_points(_SCENE_EP)  # 只扫一次
        _scene_loaded = True  # 重复调用不再扫盘


def ensure_robot_backends() -> None:
    """惰性从 entry points 加载 Robot 后端.

    Returns:
        None.
    """
    global _robot_loaded
    if not _robot_loaded:
        ROBOT_REGISTRY.load_entry_points(_ROBOT_EP)  # 只扫一次
        _robot_loaded = True  # 重复调用不再扫盘


def ensure_planner_backends() -> None:
    """惰性从 entry points 加载 Planner 后端.

    Returns:
        None.
    """
    global _planner_loaded
    if not _planner_loaded:
        PLANNER_REGISTRY.load_entry_points(_PLANNER_EP)  # 只扫一次
        _planner_loaded = True  # 重复调用不再扫盘


def ensure_job_backends() -> None:
    """惰性从 entry points 加载 Job 后端.

    Returns:
        None.
    """
    global _job_loaded
    if not _job_loaded:
        JOB_REGISTRY.load_entry_points(_JOB_EP)  # 只扫一次
        _job_loaded = True  # 重复调用不再扫盘


def ensure_all_backends() -> None:
    """加载全部后端注册表(``rsr list-backends`` 用).

    Returns:
        None.
    """
    ensure_sim_world_backends()  # 各表惰性,内部有 loaded 开关
    ensure_scene_backends()
    ensure_robot_backends()
    ensure_planner_backends()
    ensure_job_backends()
