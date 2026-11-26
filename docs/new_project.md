# 用模板创建新项目

## 1. 建立独立仓库与环境

使用托管平台的模板功能，或将本仓库文件复制到新目录（不复制 `.git/`、`.venv/`、缓存、`outputs/`、`dist/` 和本地环境文件），再在新目录初始化 Git。保留现有许可文件并记录新增代码、资产的来源。

先执行 README 的安装和 stub 通路，确认模板在新位置可独立运行，再加入业务内容。新项目不要引用原 `rsr` 的绝对路径。

需要替换或确认的内容：

| 位置 | 修改 |
|---|---|
| `pyproject.toml` | 项目发行名、描述、版本、依赖；新增后端 entry points |
| `real2sim2real/__init__.py` | 版本与包元数据保持一致 |
| `README.md` | 项目目标、真实支持的运行时、最短运行命令和验收入口 |
| `AGENTS.md` | 本项目的任务范围、目录约定、运行限制与检查方式 |
| `docs/` | 替换模板迁移背景，添加实际任务说明 |
| 环境示例和编辑器配置 | 本项目需要的变量和运行配置；不写个人机器路径 |

可以只改发行名并保留 `real2sim2real` Python 包与插件组，但必须使用独立环境。发行名不同仍可能共享同名模块、`rsr` 命令和 entry point 组，不能因此与旧 `rsr` 混装。

确需在同一环境并存时，同时重命名 Python 包目录、全部导入、CLI 入口、entry point 组及 `registry.py` / `core/cli.py` 中对应常量，并更新配置环境变量前缀和文档。完成后检查 wheel 内容和所有注册入口。

## 2. 按任务建立目录

以任务名 `demo` 为例，按实际需要增加组件，不要求机械复制所有域：

```text
real2sim2real/
├── scene/scene_demo.py
├── robot/robot_demo.py
├── planner/planner_demo.py
├── job/job_demo.py
└── utils/demo_utils.py
configs/demo/default.toml
scripts/demo/prepare_assets.py
scripts/demo/validate_demo.py
assets/Demo/
docs/demo.md
tests/test_demo.py
```

仅在需要新运行时时增加 `simworld/simworld_demo.py`。同一任务的相关后端和配置类放在相应域的一个文件里。共享能力应复用或提取为通用辅助，避免复制另一任务的整套代码。

任务资产及其 USD 引用、材质、贴图等依赖放进任务目录，记录获取或生成方式。输出使用 `outputs/demo/`；调试、失败与尚未验收的结果使用 `outputs/debug/demo/`。大资产与数据通过项目自己的下载或打包流程管理。

## 3. 先添加一个可运行的 Job

下面的例子只验证扩展路径，其余四个组件仍使用 stub。

创建 `real2sim2real/job/job_demo.py`：

```python
from pydantic import Field

from real2sim2real.core.config import BaseConfig
from real2sim2real.job.base import BaseJob


class DemoJobConfig(BaseConfig):
    backend: str = "demo"
    message: str = Field(default="demo completed", min_length=1)


class DemoJob(BaseJob):
    config_cls = DemoJobConfig

    def simulate(self) -> None:
        self.log.info("demo", message=self.config.message)
```

在 `pyproject.toml` 已有的 Job entry point 表内增加一项，不要重复创建同名 TOML 表：

```toml
[project.entry-points."real2sim2real.job.backends"]
stub = "real2sim2real.job.job_stub:StubJob"
demo = "real2sim2real.job.job_demo:DemoJob"
```

创建 `configs/demo/default.toml`：

```toml
[job]
backend = "demo"
message = "my first task"
```

重新安装使 entry points 生效，然后运行：

```bash
uv sync --extra dev
uv run rsr list-backends --kind job
uv run rsr collect run -c configs/demo/default.toml
./scripts/check
```

应能发现 `demo` 并输出配置中的消息。随后逐个替换 scene、robot、planner 或 simworld；每个域沿用“配置类 + 实现类 + `config_cls` + entry point + TOML backend”的完整路径。

## 4. 接入真实任务并验收

组件构造函数保持轻量，仿真器初始化放在 `init_world`，资产加载分别放在 `init_scene` / `init_robot`，求解器初始化放在 `init_planner`。由 Job 的钩子和 `simulate()` 组织执行，保留基类的异常清理。

真实任务需要明确开始、结束、超时和失败条件；独立验收应读取实际运行结果，不能仅检查“程序未报错”。添加与改动相关的回归测试，再记录实际运行时与验证结果。stub 测试只证明框架装配和生命周期可用。

可用下面的结构建立 `docs/demo.md`：

```markdown
# Demo 任务

## 目标与范围
任务输入、输出、成功和失败的定义。

## 环境与资产
运行时版本、硬件、依赖安装、资产来源和获取方法。

## 运行
从仓库根目录执行的准备、调试、正式运行命令。

## 验收
独立验收命令、指标、阈值、失败时的处理方式。

## 结果与限制
已验证的配置、结果位置、已知问题、尚未验证的部分。
```

完成后更新根 README 的任务入口和 AGENTS 的项目约定，使读者无需访问旧仓库即可安装、运行和判断结果。
