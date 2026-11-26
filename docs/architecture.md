# 架构与配置

## 模块职责

| 能力域 | 负责 | 不负责 |
|---|---|---|
| simworld | 创建与销毁仿真运行时、加载基础环境、提供运行时句柄 | 具体任务编排 |
| scene | 在已有世界中添加场景资产，摆放与调整 | 启停仿真应用 |
| robot | 添加机器人、摆放与调整、维护机器人位姿和状态 | 启停仿真应用 |
| planner | 初始化规划控制逻辑，按具体后端推进动作 | 全局任务生命周期 |
| job | 选择并装配四个组件，按阶段执行任务 | 把特定任务语义塞入所有组件基类 |

`Base*` 提供通用接口及空实现，stub 是可实例化的最小后端。涉及真实运行时的 `play`、步进、相机采集和任务终止条件由具体后端与 Job 定义，模板不假设所有仿真器具有同一套方法。

## 工厂与插件

```text
settings[section].backend
  → Auto*.from_config()
  → ensure_*_backends()
  → Registry.get(backend)
  → 实现类.config_cls.from_settings(section)
  → 实现类(config=...)
```

工厂也支持显式传入后端名及已构造的配置。配置类与实现类放在一起，通过 `config_cls` 关联；Registry 注册实现类，不注册配置类。

| 配置 section | 工厂 | entry point 组 |
|---|---|---|
| `sim_world` | `AutoSimWorld` | `real2sim2real.simworld.backends` |
| `scene` | `AutoScene` | `real2sim2real.scene.backends` |
| `robot` | `AutoRobot` | `real2sim2real.robot.backends` |
| `planner` | `AutoPlanner` | `real2sim2real.planner.backends` |
| `job` | `AutoJob` | `real2sim2real.job.backends` |

CLI 插件组为 `real2sim2real.cli.commands`，插件入口是 `register(main_app: typer.Typer) -> None`。根 CLI 保持通用，业务命令通过插件添加；模板的 `collect` 由 `real2sim2real.job.cli:register` 提供。

entry points 来自安装后的包元数据，因此仅添加源码文件不能完成注册。外部插件使用同一组名即可接入。单个插件加载失败会告警并跳过，其他插件仍可使用；后续选择失败的后端会报未知后端错误。

## Job 生命周期

`BaseJob.__init__()` 读取 Job 配置并通过四个组件工厂创建实例。构造阶段不分配仿真资源。`run()` 的顺序固定：

```text
init_world
  → arrange_scene
  → place_robot
  → start_simulation
finally: close
```

| 阶段 | 内部顺序 |
|---|---|
| `init_world` | `before_init_world_hook` → `sim_world.init_world` → GUI 检查 → `after_init_world_hook` |
| `arrange_scene` | `before_arrange_scene_hook` → `build_occ` → `scene.init_scene` → `scene.arrange` → `adjust_scene` → GUI 检查 → `after_arrange_scene_hook` |
| `place_robot` | `before_place_robot_hook` → `robot.init_robot` → `robot.arrange` → `adjust_robot` → `planner.init_planner` → GUI 检查 → `after_place_robot_hook` |
| `start_simulation` | `before_start_simulation_hook` → `setup_gui_hook` → GUI 检查 → `simulate` → `after_start_simulation_hook` |

`build_occ` 是默认空的建图扩展点。`adjust_scene` / `adjust_robot` 默认调用对应组件的 `adjust()`。GUI 检查只在 Job 配置提供并启用 `inspect_gui`，且世界后端支持 `wait_for_gui_edit` 时执行。

`simulate()` 默认为空，stub 复用整个流程。具体 Job 在这里实现仿真循环、录制和验收。各 after 钩子只在该阶段正常完成时调用；异常向上传播，`finally` 仍尝试清理世界。`close()` 在成功销毁后清空世界引用，重复调用不再销毁。同一个 Job 实例按一次运行使用，需要重跑时创建新实例。

## 配置层次

后者覆盖前者：

1. 包内 `core/default_settings.toml`。
2. 项目配置顶层 `inherit` / `dynaconf_include` 展开的父配置，先父后子。
3. `RSR_SETTINGS_FILE` 指定文件；未设置时使用调用目录的 `settings.toml`。
4. 项目配置同目录的 `.secrets.toml`。
5. `RSR_*` 环境变量，嵌套字段使用 `__`。

`collect run -c` 会设置 `RSR_SETTINGS_FILE` 并清理进程内配置缓存。`settings` 命令使用环境变量选择配置文件，没有 `-c` 参数。

```toml
# configs/my_task/debug.toml
inherit = "default.toml"

[logging]
level = "DEBUG"
```

继承文件相对当前 TOML 所在目录解析；它不改变后端中资产或输出路径的含义。`BaseConfig.from_settings(section)` 读取并用 Pydantic 校验该段，未知业务字段会被拒绝。`from_yaml()` / `from_dict()` 是直接构造配置的入口，不自动应用 TOML 继承、secrets 或环境变量层。

配置默认使用全部 stub。真实项目应显式配置需要替换的域，其余域可继续使用 stub；未提供文件的零配置回退适合骨架验证，不能据此判断实际任务配置已经正确加载。
