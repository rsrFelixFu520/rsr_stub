# rsr stub

虚实闭环平台：**场景重建与数字孪生 → 仿真数据采集 → 策略训练 → 真机评测回流**。

本仓库是可插拔的仿真编排框架：抽象基类 + 配置 / Registry + stub 后端。每个任务的场景、机器人、规划器、Job、SimWorld 都是独立注册的后端。

**本项目（`rsr_stub`）可以不使用 Isaac Sim 中的 Python**，开发、检查和 stub 运行默认使用 `uv` 管理的 Python 3.12 独立 `.venv`。
**参考本项目新增的项目必须使用 Isaac Sim 自带的 Python 环境**（通过安装目录中的 `python.sh`），包括项目安装、测试和任务运行；该要求从新项目的 stub 验证阶段开始适用。具体命令见 [创建新项目](docs/new_project.md)。

> Agent / 贡献者：先读 [`AGENTS.md`](AGENTS.md)（目录约定、扩展后端、配置与 CLI 约定）。

## 快速开始

需要 Python 3.12 和 `uv`。在本仓库根目录执行：

```bash
uv sync --locked --extra dev
uv run rsr version
uv run rsr list-backends
uv run rsr collect run -c configs/stub/default.toml
./scripts/check
```

`list-backends` 应显示 `sim_world`、`scene`、`robot`、`planner`、`job` 五类，每类均有 `stub`。`collect run` 应依次经过世界初始化、场景摆放、机器人放置、任务执行，并清理世界；正常退出表示骨架通路可用。stub 的任务执行是空实现，不代表任何物理任务已经完成。

也可以使用仓库包装入口：

```bash
./scripts/rsr collect run -c configs/stub/default.toml
uv run python -m real2sim2real.core.cli list-backends
```

包装入口在设置 `RSR_ISAACSIM_HOME` 时使用该目录的 `python.sh`，否则使用 `uv run --project <仓库> --locked`；环境准备见 [环境配置](docs/environment.md)。从其他目录启动示例可用 `./scripts/run.sh` 的绝对路径。

## 项目结构

```text
rsr_stub/
├── AGENTS.md                 # Agent 与贡献者的开发约定
├── README.md                 # 人类入门入口
├── pyproject.toml            # 包元数据、依赖、entry points、检查配置
├── uv.lock                   # 可复现依赖锁定
├── .python-version           # 默认开发 Python 版本
├── real2sim2real/
│   ├── core/                 # 配置、Registry、CLI、日志、默认配置
│   ├── simworld/             # 仿真运行时与环境
│   ├── scene/                # 场景资产
│   ├── robot/                # 机器人资产与状态
│   ├── planner/              # 规划与控制
│   ├── job/                  # 任务装配、生命周期、collect 命令
│   └── utils/                # 共用辅助；新增任务按任务名分文件
├── configs/<task>/           # 按任务组织配置；示例为 stub/
├── scripts/                  # 运行包装和检查入口
├── tests/                    # 不依赖仿真器的回归测试
├── assets/                   # 任务资产目录；大资产按项目单独管理
├── outputs/                  # 本地生成结果，不提交
└── docs/                     # 文档说明
```

## 配置与扩展

配置使用 TOML，按能力域设置 `backend`。后端名对应 `pyproject.toml` 中的 entry point 名称。零配置时使用包内默认值；显式配置推荐使用 `collect run -c <文件>`。

```bash
# 查看某个配置实际合并后的段；settings 命令通过环境变量选择文件
RSR_SETTINGS_FILE=configs/stub/default.toml uv run rsr settings --section job

# 环境变量覆盖嵌套字段，使用双下划线
RSR_LOGGING__LEVEL=DEBUG uv run rsr collect run
```

新项目通常保留这套骨架，只添加任务后端、配置、资产准备脚本与验收说明。真实仿真依赖由后端按需加载；

## 文档入口

- [AGENTS.md](AGENTS.md)：修改代码前阅读的结构与开发约定。
- [环境配置](docs/environment.md)：安装、锁文件、运行入口、Isaac 接入和排错。
- [Stub 示例](docs/stub.md)：最短通路、配置继承和成功标准。
- [架构与配置](docs/architecture.md)：模块职责、生命周期、工厂与插件协议。
- [创建新项目](docs/new_project.md)：复制模板、重命名、添加可运行的任务后端。
- [迁移说明](docs/migration.md)：提取范围、修正内容及与原仓库的边界。

仓库保留现有 [LICENSE](LICENSE)。正式分发新增代码和资产前，记录各自来源与许可。
