"""任务命令插件：rsr collect run [-c CONFIG]。"""

from pathlib import Path
from typing import Annotated

import typer

from real2sim2real.core.config import apply_settings_file
from real2sim2real.core.logger import LogConfig, configure_logging, get_logger
from real2sim2real.job.base import AutoJob

app = typer.Typer(help="任务编排；stub 仅验证结构，不采集数据。", no_args_is_help=True)


@app.command()
def run(
    config: Annotated[
        Path | None, typer.Option("--config", "-c", help="任务 TOML 配置路径")
    ] = None,
) -> None:
    """通过 Job 工厂运行固定生命周期。"""
    if config is not None:
        try:
            path = apply_settings_file(config)
        except FileNotFoundError as exc:
            raise typer.BadParameter(str(exc), param_hint="--config") from exc
    configure_logging(LogConfig.from_settings("logging"), force=True)
    log = get_logger(__name__)
    if config is not None:
        log.info("加载配置文件", path=str(path))
    job = AutoJob.from_config()
    job.run()
    log.info("任务生命周期完成", backend=job.config.backend)


def register(main_app: typer.Typer) -> None:
    """由 real2sim2real.cli.commands entry point 挂载命令。"""
    main_app.add_typer(app, name="collect")
