# Stub 示例

stub 展示五个能力域如何经配置、entry points 和工厂装配成 Job。它不创建仿真应用、不加载资产、不进行 play / step，也不生成图像、轨迹或数据集。

## 运行

在仓库根目录完成 `uv sync --locked --extra dev` 后执行：

```bash
uv run rsr list-backends
uv run rsr collect run -c configs/stub/default.toml
uv run rsr collect run -c configs/stub/debug.toml
./scripts/run.sh
```

配置按 `configs/<task>/` 组织，当前示例位于 `configs/stub/`。`default.toml` 显式将五个域的 `backend` 设为 `stub`。`debug.toml` 继承同目录的 `default.toml` 并覆盖日志级别，展示配置的相对继承。无需资产准备脚本，`assets/Stub/` 仅保留任务目录位置。

从其他工作目录调用时，使用 `scripts/run.sh` 的绝对路径；脚本会自动定位仓库和配置。通用 `scripts/rsr` 仍保留调用目录，因此手动传入相对 `-c` 路径时需自行注意其位置。

## 成功标准

- 后端列表包含五个类别，各有 `stub`。
- Job 按世界、场景、机器人、执行四个阶段运行并正常退出。
- 场景和机器人保存世界引用，规划器保存机器人引用及初始化状态。
- 正常结束和阶段异常都会进入世界清理；具体行为由自动化回归检查验证。

最短通路正常只说明包安装、配置和装配有效。新任务应另外定义物理行为、输出格式与验收标准，不能用这个示例替代真实后端验证。

## 相关入口

| 内容 | 位置 |
|---|---|
| 默认配置 | `configs/stub/default.toml` |
| 继承示例 | `configs/stub/debug.toml` |
| 运行包装 | `scripts/run.sh` |
| 任务骨架 | `real2sim2real/job/job_stub.py` |
| 生命周期 | `real2sim2real/job/base.py` |
| 新任务示例 | [创建新项目](new_project.md) |
