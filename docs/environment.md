# 环境配置

本项目 `rsr_stub` 可以不使用 Isaac Sim 中的 Python，默认使用普通 Python 3.12 和项目独立 `.venv`。参考本项目新增的项目必须使用 Isaac Sim 自带的 Python 环境，通过 `python.sh` 完成项目安装、测试和任务运行；初始 stub 验证也必须使用该环境。新项目步骤见 [创建新项目](new_project.md)。

## 普通 Python：开发和运行 stub

模板的默认开发版本为 Python 3.12，版本提示在 `.python-version`。需要已安装 `uv`，在仓库根目录运行：

```bash
uv sync --locked --extra dev
uv run rsr list-backends
uv run rsr collect run -c configs/stub/default.toml
./scripts/check
```

`uv sync` 创建本仓库的 `.venv` 并安装项目，entry points 随安装生效。无需激活环境；`uv run` 使用仓库环境。此通路不需要 GPU、Isaac Sim、CUDA。

如使用已有 Python 环境，也可执行：

```bash
python -m pip install -e '.[dev]'
python -m real2sim2real.core.cli collect run -c configs/stub/default.toml
```

这条 pip 路径使用 `pyproject.toml` 的版本约束，不会自动遵循 `uv.lock`。需要可复现的模板开发环境时使用上面的 uv 流程。

## Isaac Sim 环境：本模板可选，新项目必须使用

模板只附带 stub 后端。新项目应先设置 Isaac Sim 环境并在其中验证 stub 通路，再实现或安装实际的 simworld / scene / robot / planner 后端。仅切换解释器不会获得仿真能力。

```bash
# 替换成目标机器真实安装位置
export RSR_ISAACSIM_HOME=/path/to/isaacsim
"$RSR_ISAACSIM_HOME/python.sh" -m pip install -e '.[dev]'
./scripts/rsr list-backends
./scripts/rsr collect run -c configs/stub/default.toml
```

这只验证目标解释器可以加载骨架；实际仿真还需执行新后端的最短场景和独立验收。使用目标安装版本自带的 Python 及其 CUDA、USD、Kit 依赖，记录安装版本和硬件条件。不要直接复制旧机器的 `app` 链接、扩展缓存路径或整份编辑器搜索路径。

## 包装入口与本地配置

`./scripts/rsr` 在设置 `RSR_ISAACSIM_HOME` 时优先使用其 `python.sh`，并检查它是否可执行；未设置时使用 `uv run --project <仓库根> --locked rsr`。它设置默认 `RSR_ASSETS_ROOT` 为仓库 `assets/`，保留调用者的工作目录，因此一般相对 `-c` 路径仍相对调用目录。

`./scripts/run.sh` 自动传入 stub 配置的绝对路径，可从任意目录启动。`./scripts/check` 则切换到仓库根，用 uv 环境执行开发检查，不随 `RSR_ISAACSIM_HOME` 切换成仿真器检查。

以上回退到 uv 的行为仅供本模板使用。新项目必须调整运行包装，使未设置有效 Isaac Sim 路径时明确报错，并将检查脚本中的 Python 工具改为通过 `python.sh -m ...` 执行，避免静默使用普通 `.venv`。

`.env.example` 只列出变量示例，复制为 `.env` 后按本机需要填写。CLI 与 shell 包装脚本不自动加载 dotenv 文件；在当前 shell 显式 `export` 变量，或由编辑器的环境配置载入。模板环境变量包括 `RSR_SETTINGS_FILE`、`RSR_ISAACSIM_HOME`、`RSR_ASSETS_ROOT` 和 `RSR_LOGGING__LEVEL`。

## 依赖维护与打包

```bash
# 修改依赖后更新锁定并安装
uv lock
uv sync --locked --extra dev

# 构建 wheel 和源码包
uv build
```

模板只锁定骨架所需依赖。真实后端的重依赖优先放入独立插件包或可选依赖，并根据目标运行时解决版本兼容。普通 Python 的 `uv.lock` 不替代仿真器自身的依赖管理。

`uv.lock` 需要提交；`.venv/`、本地 `.env` / `.secrets.toml`、仿真器安装、构建产物和 `outputs/` 不提交。生成正式结果时记录代码版本、配置、运行时版本和验收结论。

## 常见问题

| 现象 | 处理 |
|---|---|
| 后端列表为空或没有新后端 | 确认在当前解释器安装项目；修改 entry points 后重新 `uv sync` 或 `pip install -e .` |
| 看到旧 `rsr` 的业务后端或导入旧路径 | 使用独立环境；检查当前解释器和 `real2sim2real.__file__`，不要在同一环境混装两份骨架 |
| 指定配置后仍是旧值 | 检查 `RSR_*` 环境变量覆盖；进程内切换配置使用 `apply_settings_file()` 或 `reset_settings()` |
| `-c` 报文件不存在 | 相对路径基于调用目录；切换到仓库根或使用绝对路径 |
| 未知配置字段 | 对照当前后端的 `config_cls`，修正拼写或选用正确后端；不要删除 `extra="forbid"` 绕过问题 |
| CLI 里没有 `collect` | 检查当前环境已安装 `real2sim2real.cli.commands` entry point；通过 `rsr` 或模块 `main()` 启动 |
