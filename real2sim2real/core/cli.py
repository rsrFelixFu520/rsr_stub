"""Real2Sim2Real 统一 CLI 入口 (``rsr``).

设计约定:
- 本文件保持轻量; 业务子命令可通过 entry_points 注入.
- 入口负责: 挂载内建/插件命令 -> 交给 Typer 分发.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable
from importlib.metadata import entry_points
from typing import ClassVar

import typer
from typer.core import TyperGroup

from real2sim2real import __version__
from real2sim2real.core.registry import (
    JOB_REGISTRY,
    PLANNER_REGISTRY,
    ROBOT_REGISTRY,
    SCENE_REGISTRY,
    SIM_WORLD_REGISTRY,
    ensure_all_backends,
)

_PLATFORM_CLI_GROUP = "real2sim2real.cli.commands"  # 与 pyproject 组名一致

_BACKEND_KINDS = {
    "sim_world": SIM_WORLD_REGISTRY,
    "scene": SCENE_REGISTRY,
    "robot": ROBOT_REGISTRY,
    "planner": PLANNER_REGISTRY,
    "job": JOB_REGISTRY,
}


def load_cli_plugins(
    main_app: typer.Typer,
    group: str,
    fallback: Callable[[typer.Typer], None] | None = None,
) -> bool:
    """加载 ``group`` 下全部 CLI 插件; 若无一成功则调用 ``fallback``.

    遍历 ``importlib.metadata.entry_points`` 中指定 group 的插件,
    每个插件约定指向 ``register(main_app: typer.Typer) -> None``.
    单个插件加载失败只告警, 不中断整个 CLI.
    返回是否至少成功加载了一个插件.

    Args:
        main_app: 根 Typer app,插件在上面挂子命令.
        group: entry point 组名,须与 ``pyproject.toml`` 一致.
        fallback: 全部插件失败时的兜底注册函数;None 则不兜底.

    Returns:
        至少一个插件 ``register`` 成功则为 ``True``;否则 ``False``.
    """
    loaded = False  # 至少一个插件成功才算 True
    for ep in entry_points(group=group):
        try:
            ep.load()(main_app)  # register(app) 挂子命令
            loaded = True  # 至少一个成功,就不再走 fallback
        except Exception as exc:  # noqa: BLE001 - 单个插件失败不得中断整个 CLI
            warnings.warn(
                f"Failed to load CLI plugin '{ep.name}' (group '{group}'): {exc}",
                stacklevel=2,  # 指向 load_cli_plugins 的调用方
            )
    if not loaded and fallback is not None:  # 本包 collect 丢了也能手动挂
        fallback(main_app)  # 例如把内建 collect 命令挂上
    return loaded  # True 表示至少有一个插件的 register 成功


class ExtraHelpGroup(TyperGroup):
    """在标准 Typer help 之后追加 ``extra_help``."""

    extra_help: ClassVar[str] = ""  # 子类或运行时可改

    def format_help(self, ctx, formatter) -> None:  # noqa: ANN001
        """先输出 Typer 默认 help, 再追加类属性 ``extra_help`` (若非空).

        Args:
            ctx: Typer/Click 上下文.
            formatter: Click HelpFormatter,往里 write 文本.

        Returns:
            None.
        """
        super().format_help(ctx, formatter)  # 标准 Usage / Commands
        if self.extra_help:
            formatter.write(self.extra_help)  # 追加本仓库自定义尾注


app = typer.Typer(
    name="rsr",
    help="Real2Sim2Real 平台 CLI",
    cls=ExtraHelpGroup,
    no_args_is_help=True,  # 裸 rsr 打印 help 而不是报错
)


@app.command()
def version() -> None:
    """打印当前安装的 ``real2sim2real`` 包版本号.

    Returns:
        None.
    """
    typer.echo(__version__)  # 给脚本/CI 核对安装版本


@app.command("list-backends")
def list_backends(
    kind: str | None = typer.Option(
        None,
        "--kind",
        "-k",
        help="后端类别: sim_world/scene/robot/planner/job; 默认全部",
    ),
) -> None:
    """列出已注册的后端.

    未指定 ``--kind`` 时打印全部类别; 指定时只打印对应 registry 中的名称列表.

    Args:
        kind: 只列某一类后端;None 表示全部五类.

    Returns:
        None.
    """
    ensure_all_backends()  # 先扫 entry points,否则表是空的
    kinds = list(_BACKEND_KINDS) if kind is None else [kind]  # None → 五类全打
    for name in kinds:
        if name not in _BACKEND_KINDS:
            raise typer.BadParameter(
                f"Unknown kind '{name}'. Choose from: {', '.join(_BACKEND_KINDS)}"
            )  # 非法 --kind 走 Typer 参数错误,打印合法值
        names = _BACKEND_KINDS[name].list()  # 已注册后端名,排序过
        typer.echo(f"[{name}] {', '.join(names) if names else '(none)'}")  # 空表打 (none)


@app.command("settings")
def show_settings(
    section: str | None = typer.Option(
        None,
        "--section",
        "-s",
        help="只打印某个 section (如 logging / planner); 默认打印常用段",
    ),
) -> None:
    """打印合并后的统一 settings, 便于核对传参.

    未指定 ``--section`` 时打印常用段
    (logging / sim_world / scene / robot / planner / job).

    Args:
        section: 只打印这一段;None 则打印常用段列表.

    Returns:
        None.
    """
    from real2sim2real.core.config import get_settings  # 延迟 import,避免循环

    settings = get_settings()  # 含 -c / env 覆盖后的合并结果
    sections = (
        [section] if section else ["logging", "sim_world", "scene", "robot", "planner", "job"]
    )
    for name in sections:
        raw = settings.get(name, default=None)  # None 表示段缺失,不是空 dict
        typer.echo(f"[{name}]")  # 段标题,与 TOML 写法对齐
        if raw is None:
            typer.echo("  (missing)")  # 段不存在,与空 dict 区分
            continue
        data = dict(raw) if hasattr(raw, "items") else {"value": raw}  # Box 或标量
        for key, value in data.items():
            typer.echo(f"  {key} = {value!r}")  # repr 便于核对 Path / 列表


def _register_builtin_and_plugins() -> None:
    """加载 entry_points 插件 (如 ``real2sim2real.job.cli:register``).

    与参考项目一致: 在 ``main()`` 内挂载, 保证
    ``python -m real2sim2real.core.cli`` / VS Code ``module`` 调试时子命令可用.

    Returns:
        None.
    """
    load_cli_plugins(app, _PLATFORM_CLI_GROUP)  # collect 等业务命令走插件


def main() -> None:
    """``rsr`` 脚本入口: 挂载插件 -> Typer 分发.

    Returns:
        None.
    """
    _register_builtin_and_plugins()  # 先挂子命令再解析 argv
    app()  # 阻塞直到子命令结束


if __name__ == "__main__":
    main()  # python -m real2sim2real.core.cli
