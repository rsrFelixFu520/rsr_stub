"""统一配置系统:dynaconf 加载 settings + pydantic ``BaseConfig`` 校验.

查找与覆盖顺序(后者优先):

1. 包内 ``default_settings.toml``(零配置可用)
2. 项目文件通过顶层 ``inherit`` / ``dynaconf_include`` 展开的父配置(先父后子)
3. 项目 ``settings.toml``(cwd 或 ``RSR_SETTINGS_FILE``)
4. 同目录 ``.secrets.toml``(可选)
5. 环境变量前缀 ``RSR_``(嵌套用双下划线,优先级最高)
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any, TypeVar

import yaml
from dynaconf import Dynaconf
from dynaconf.base import LazySettings
from pydantic import BaseModel, ConfigDict

# dynaconf 段内标记,以及本仓库的 inherit;不得进入 pydantic Config
_RESERVED_SETTINGS_KEYS = frozenset(
    {"dynaconf_merge", "dynaconf_merge_unique", "dynaconf_include", "inherit"}
)

Settings = LazySettings  # get_settings() 的返回类型别名
"""``get_settings()`` 的返回类型."""

C = TypeVar("C", bound="BaseConfig")  # from_yaml/from_dict 的返回类型

_DEFAULT_SETTINGS_PATH = Path(__file__).parent / "default_settings.toml"  # 包内回退
_SETTINGS: Settings | None = None  # 进程内单例缓存;reset_settings 可清空


def _resolve_project_settings_file() -> str:
    """``RSR_SETTINGS_FILE`` 优先,否则 ``cwd/settings.toml``.

    CLI ``-c`` 会先把路径写入该环境变量,再 ``from_settings``.

    Returns:
        项目配置路径字符串(文件未必存在).
    """
    explicit = os.environ.get("RSR_SETTINGS_FILE")  # rsr -c 设置
    if explicit:
        return explicit  # CLI -c 已写入绝对路径
    return str(Path.cwd() / "settings.toml")  # 文件不存在 dynaconf 会跳过


def _parse_include_files(path: Path) -> list[str]:
    """读 TOML 顶层 ``inherit`` / ``dynaconf_include``;相对路径相对该文件所在目录.

    Args:
        path: 待解析的 TOML 路径;不是文件则返回空列表.

    Returns:
        待继承文件路径列表;缺文件/坏 TOML/无 inherit 则为 ``[]``.
    """
    if not path.is_file():
        return []  # 缺文件不报错,交给上层跳过
    try:
        with path.open("rb") as f:  # tomllib 要求二进制模式
            data = tomllib.load(f)  # 只取顶层 inherit,不做完整配置校验
    except (OSError, tomllib.TOMLDecodeError):
        return []  # 坏 TOML 当无 inherit,不阻断启动
    raw = data.get("inherit", data.get("dynaconf_include", []))  # inherit 优先
    if raw is None:
        return []  # 显式 null 视为不继承
    if isinstance(raw, str):
        return [raw]  # 单文件写成字符串
    if isinstance(raw, (list, tuple)):
        return [str(item) for item in raw if item]  # 丢掉空项
    return []  # 其它类型忽略,避免 dynaconf 吃到奇怪值


def _expand_settings_chain(project_file: str) -> list[str]:
    """展开 inherit 链:被继承文件在前,``project_file`` 在最后.

    循环引用会被跳过;缺失的 include 仍保留路径,交给 dynaconf 自行跳过.

    Args:
        project_file: 项目配置路径(``RSR_SETTINGS_FILE`` 或 cwd ``settings.toml``).

    Returns:
        先父后子的配置路径列表,末项为 ``project_file``.
    """
    chain: list[Path] = []  # 先父后子,后者覆盖
    seen: set[Path] = set()  # 打断 A→B→A 循环 inherit

    def walk(path: Path) -> None:
        """深度优先把被继承文件放进 ``chain``,自身最后追加.

        Args:
            path: 当前要展开的配置文件路径(可为 ``~`` 或相对路径).

        Returns:
            None.循环引用时提前返回.
        """
        resolved = path.expanduser()  # 支持 ~/...
        if resolved.exists():
            resolved = resolved.resolve()  # 真实路径去重,避免循环
        if resolved in seen:
            return  # 已访问,打断循环 inherit
        seen.add(resolved)  # 先标记再递归,防止自引用
        if resolved.is_file():
            for rel in _parse_include_files(resolved):
                walk(resolved.parent / rel)  # 相对路径相对该文件所在目录
        chain.append(resolved)  # 自身在祖先之后,优先级更高

    walk(Path(project_file))  # 从项目文件出发展开整条链
    return [str(p) for p in chain]  # Dynaconf settings_files 要 str


def _build_settings() -> Settings:
    """按优先级拼默认 + inherit 链 + 项目文件 + secrets + ``RSR_`` 环境变量.

    Returns:
        已合并各层与 ``RSR_`` 环境变量的 Dynaconf 对象.
    """
    project_file = _resolve_project_settings_file()  # -c 或 cwd settings.toml
    inherited = _expand_settings_chain(project_file)  # 含项目文件本身
    secrets_file = str(Path(project_file).parent / ".secrets.toml")  # 可选,gitignore
    return Dynaconf(
        envvar_prefix="RSR",  # 如 RSR_JOB__BACKEND=tabletop
        settings_files=[str(_DEFAULT_SETTINGS_PATH), *inherited, secrets_file],  # 后者覆盖
        merge_enabled=True,  # 后者覆盖前者,字典深合并
        environments=False,  # 不用 [default]/[production] 分段
    )


def get_settings(*, force_reload: bool = False) -> Settings:
    """返回全局唯一的 settings 对象.

    Args:
        force_reload: True 时丢弃缓存,重新读盘(测试或 -c 之后).

    Returns:
        进程单例 settings;``force_reload`` 时重新读盘后再返回.
    """
    global _SETTINGS  # 进程单例;测试用 reset_settings 清空
    if _SETTINGS is None or force_reload:
        _SETTINGS = _build_settings()  # 读盘 + env 合并,结果缓存
    return _SETTINGS  # 后续 from_settings 都读这份


def reset_settings() -> None:
    """清空缓存,使下次 ``get_settings()`` 重新加载.

    Returns:
        None.
    """
    global _SETTINGS  # 与 get_settings 同一缓存
    _SETTINGS = None  # 下次 get_settings 再 _build_settings


def apply_settings_file(path: str | Path) -> Path:
    """把 ``path`` 写入 ``RSR_SETTINGS_FILE`` 并清缓存,后续 ``get_settings`` 会合并该文件.

    Args:
        path: 项目 TOML/配置文件;相对路径相对 cwd,支持 ``~``.

    Returns:
        解析后的绝对路径.

    Raises:
        FileNotFoundError: 路径不是文件.
    """
    resolved = Path(path).expanduser().resolve()  # ~ 与相对路径都收成绝对
    if not resolved.is_file():
        raise FileNotFoundError(f"配置文件不存在: {resolved}")  # CLI -c 指错文件时应立刻失败
    os.environ["RSR_SETTINGS_FILE"] = str(resolved)  # 后续 _build_settings 读这个
    reset_settings()  # 丢掉旧单例
    return resolved  # 调用方可用来打印实际加载路径


def _to_plain(value: Any) -> Any:
    """递归将 dynaconf Box 转为普通 dict/list,供 pydantic 消费.

    Args:
        value: dynaconf Box / 嵌套容器 / 标量.

    Returns:
        普通 dict/list 或原样标量.
    """
    if isinstance(value, dict):
        return {k: _to_plain(v) for k, v in dict(value).items()}  # Box → 普通 dict
    if isinstance(value, (list, tuple)):
        return [_to_plain(v) for v in value]  # 列表元素同样拆 Box
    return value  # 标量原样返回


def _to_plain_dict(value: Any) -> dict[str, Any]:
    """section 不是 dict 时退回空配置,让字段走默认值.

    Args:
        value: settings 某一段的原始值(可能是 Box、标量或 None).

    Returns:
        普通 dict;非 dict 则 ``{}``.
    """
    plain = _to_plain(value)  # 先拆 Box
    if not isinstance(plain, dict):
        return {}  # 段写成字符串时不当字段,避免 extra=forbid 炸
    return plain  # 已是普通 dict,可给 pydantic


def _normalize_top_level_keys(cls: type[BaseModel], data: dict[str, Any]) -> dict[str, Any]:
    """大小写不敏感地对齐字段名,避免 env 覆盖产生的大写键被 ``extra=forbid`` 拒绝.

    Args:
        cls: 目标 pydantic 模型(用 ``model_fields`` 对齐键名).
        data: 已转成普通 dict 的 section 内容.

    Returns:
        键名对齐字段后的 dict;丢掉 reserved 键.
    """
    field_by_lower = {name.lower(): name for name in cls.model_fields}  # BACKEND → backend
    out: dict[str, Any] = {}  # 键名对齐后的 section
    for key, value in data.items():
        if key.lower() in _RESERVED_SETTINGS_KEYS:
            continue  # inherit / dynaconf_merge 不是业务字段
        out[field_by_lower.get(key.lower(), key)] = value  # 对上字段名,对不上原样保留
    return out  # 交给 from_dict 做 extra=forbid 校验


class BaseConfig(BaseModel):
    """所有 ``*Config`` 的基类:yaml/dict/settings section 统一入口."""

    model_config = ConfigDict(extra="forbid")  # 拼写错误的 toml 键直接报错

    backend: str = "stub"  # 选型字符串,与 entry point 名一致

    @classmethod
    def peek_backend(cls, section: str) -> str:
        """从 settings 读取 ``backend``,不做完整校验(避免专用字段阻塞选型).

        AutoX 先 peek 再选实现类,再用该类的 ``config_cls`` 做完整校验.

        Args:
            section: settings 段名(如 ``job`` / ``planner``).

        Returns:
            ``backend`` 字符串;缺段或空值则为 ``"stub"``.
        """
        raw = get_settings().get(section, default=None)  # 不做 pydantic,避免专用字段卡住选型
        if raw is None:  # 缺段则默认 stub,CI 零配置可跑
            return "stub"
        backend = getattr(raw, "backend", None)  # Dynaconf Box 属性访问
        if backend is None and isinstance(raw, dict):
            backend = raw.get("backend")  # 普通 dict(测试注入)走键访问
        return str(backend or "stub")  # 空字符串也回退 stub

    @classmethod
    def from_yaml(cls: type[C], path: str | Path) -> C:
        """从单个 YAML 文件构造(测试/脚本用,不走 dynaconf 合并).

        Args:
            path: YAML 文件路径.

        Returns:
            校验后的配置实例.

        Raises:
            FileNotFoundError: 文件不存在.
            ValueError: 字段校验失败.
        """
        path = Path(path)  # 统一成 Path
        if not path.exists():
            raise FileNotFoundError(f"Config file does not exist: {path}")  # 测试/脚本缺文件
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}  # 空文件当空 dict
        return cls.from_dict(data)  # 走同一套 pydantic 校验

    @classmethod
    def from_dict(cls: type[C], d: dict[str, Any]) -> C:
        """使用 pydantic 校验配置，失败时抛出原始 ValidationError.

        Args:
            d: 字段字典;未知键会被 ``extra=forbid`` 拒绝.

        Returns:
            校验后的配置实例.

        Raises:
            ValueError: pydantic 校验失败.
        """
        return cls.model_validate(d)

    @classmethod
    def from_settings(cls: type[C], section: str, *, settings: Settings | None = None) -> C:
        """从统一 settings 的某个 section 加载并校验.

        缺失 section 视为空配置(用字段默认值).

        Args:
            section: settings 段名(如 ``logging`` / ``job``).
            settings: 已加载的 Dynaconf 对象;None 则用进程单例.

        Returns:
            该 section 校验后的配置;缺段用字段默认值.
        """
        settings = settings or get_settings()  # 未传入则用进程单例
        raw = settings.get(section, default={})  # 缺段 → 空,字段走默认
        data = _normalize_top_level_keys(cls, _to_plain_dict(raw))  # Box + 大写键
        return cls.from_dict(data)  # 完整校验后再给 AutoX / 后端

    def to_yaml(self, path: str | Path) -> None:
        """把当前配置 dump 成 YAML,便于对照或生成模板.

        Args:
            path: 输出文件路径;父目录不存在时会创建.

        Returns:
            None.
        """
        path = Path(path)  # 统一成 Path,便于 mkdir
        path.parent.mkdir(parents=True, exist_ok=True)  # 目录不存在则创建
        with path.open("w", encoding="utf-8") as f:
            # mode=json 把 Path 等转成可 YAML 的基础类型;保留键序便于对照
            yaml.safe_dump(self.model_dump(mode="json"), f, allow_unicode=True, sort_keys=False)
