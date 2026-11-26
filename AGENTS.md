# AGENTS.md — rsr_stub

这是可复用的项目骨架。人类入门见 [README.md](README.md)，环境见 [docs/environment.md](docs/environment.md)，新任务流程见 [docs/new_project.md](docs/new_project.md)。

## 工作范围

- 默认交付可独立安装、无仿真器也能运行的 stub 通路。
- 原 `rsr` 仓库及其文档是迁移参考；旧任务、机器路径、资产和运行限制不自动成为新项目约定。
- 新项目应在本文写清自己的任务范围、运行时和验收标准，避免把多个无关项目继续堆进模板。
- 不在未被要求时创建 git commit 或 push；不提交密钥、本地环境、仿真器安装和生成数据。

## 仓库地图

| 路径 | 职责 |
|---|---|
| `real2sim2real/core/` | 配置、Registry、CLI、日志、`default_settings.toml` |
| `real2sim2real/{simworld,scene,robot,planner,job}/` | `base.py`、工厂、stub、任务后端 |
| `real2sim2real/utils/` | 任务共用辅助；任务专用逻辑用 `<task>_utils.py` |
| `configs/<task>/` | 按任务组织配置；stub 示例位于 `configs/stub/`，继承路径相对当前配置文件 |
| `scripts/<task>/` | 资产准备、运行包装、独立验收 |
| `assets/<Task>/` | 任务资产及其依赖、来源与许可说明 |
| `outputs/<task>/` | 任务结果；调试与失败结果用 `outputs/debug/<task>/` |
| `docs/<task>.md` | 任务目标、环境、命令、验收、结果与已知限制 |
| `tests/` | 普通 Python 可运行的回归测试 |

## 架构契约

1. 五个能力域通过 `Auto*.from_config()` 装配。工厂先读取 `backend`，再从对应 Registry 取实现类，使用该实现的 `config_cls` 校验配置。
2. 每个任务在每个能力域中最多维护一个实现文件：`<domain>_<task>.py`。确有需要才增加该域；允许复用现有组件。stub 的 simworld 文件沿用 `stub.py`。
3. 配置类继承 `BaseConfig`，保留 `extra="forbid"`。新增字段进入对应后端配置类，不把某个任务的字段塞进通用基类。
4. 后端通过 `pyproject.toml` entry points 注册。保持现有 `real2sim2real.*` 组名；后端名使用配置中的小写字符串。
5. 组件构造函数只保存配置和轻量状态。仿真资源在生命周期阶段初始化；模块顶层不导入 `isaacsim`、`omni`、`pxr`、Newton 等重型运行时。
6. `BaseJob.run()` 保持 `init_world → arrange_scene → place_robot → start_simulation`，并在 `finally` 中 `close()`。扩展阶段钩子或 `simulate()`，保留清理和异常传播行为。
7. 世界负责运行时和环境，Scene 添加场景资产，Robot 添加机器人，Planner 负责规划控制，Job 负责装配与顺序。任务循环、录制、重试、统计和验收由具体 Job 实现。
8. `adjust_scene()`、`adjust_robot()` 默认调用组件的 `adjust()`。细节及全部钩子顺序见 [架构说明](docs/architecture.md)。

## 环境与检查

模板使用 Python 3.12、`uv` 和独立 `.venv`。真实仿真任务使用目标仿真器支持的运行时；不要把模板的开发环境直接视为仿真环境。

```bash
uv sync --locked --extra dev
./scripts/check
uv run rsr list-backends
uv run rsr collect run -c configs/stub/default.toml
```

修改依赖时更新 `pyproject.toml`，运行 `uv lock`，再 `uv sync --locked --extra dev`。将 `uv.lock` 一并纳入版本控制。改变 entry points 后重新安装项目（`uv sync`），再检查后端可发现性。

使用类型标注和简短公共 API docstring；Ruff 行宽 100，规则以 `pyproject.toml` 为准。日志使用 `get_logger` / `LoggerMixin`。插件加载失败应给出可定位告警，并允许其他插件继续加载。

## 修改联动

- 改基类接口：同步 stub、任务实现、架构文档和相关回归测试。
- 加后端：同步 entry points、配置示例、任务说明，并验证 `list-backends` 和最短运行通路。
- 加配置字段：同步后端 `config_cls` 与对应示例；只有通用默认值才进入 `default_settings.toml`。
- 移动文件：检查导入、entry points、配置继承和文档链接。
- 依赖真实运行时的变更：记录实际安装版本和执行过的验证；无法执行时明确说明，不能以 stub 通过代替物理验收。

提交前至少确认适用检查通过、文档命令与当前实现一致，且没有原项目绝对路径、旧业务注册项或未经说明的大文件。
