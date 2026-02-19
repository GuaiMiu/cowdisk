"""
@File: paths.py
@Author: GuaiMiu
@Date: 2026/2/7
@Version: 1.0
@Description: 路径规则与规范化
"""

from pathlib import PurePosixPath

from app.modules.disk.domain.errors import DiskError


def ensure_name(name: str) -> str:
    """
    校验并规范化文件/目录名。
    空字符串会被视为非法名称。
    禁止包含路径分隔符，避免路径穿越。
    仅处理单个段名，不负责拼接路径。
    权限假设：调用方已完成鉴权。
    并发：纯函数无状态。
    性能：字符串级操作开销极小。
    返回：清理后的安全名称。
    """
    safe = (name or "").strip()
    if not safe:
        raise DiskError(msg="名称不能为空")
    if "/" in safe or "\\" in safe:
        # 禁止路径分隔符，避免越权访问与路径拼接漏洞。
        raise DiskError(msg="名称不允许包含路径分隔符")
    return safe


def build_storage_path(user_id: int, parent_storage_path: str | None, name: str) -> str:
    """
    生成存储层的相对路径。
    根目录以 user_id 作为顶层隔离。
    目录树通过父存储路径拼接形成。
    不依赖用户输入 path，避免语义混乱。
    权限假设：调用方已验证 parent 属于用户。
    并发：纯函数无状态。
    性能：路径拼接开销可忽略。
    返回：Posix 风格存储路径。
    """
    if parent_storage_path:
        rel = PurePosixPath(parent_storage_path) / name
    else:
        rel = PurePosixPath(str(user_id)) / name
    return rel.as_posix()


def build_trash_path(user_id: int, file_id: int, name: str, deleted_at_token: str) -> str:
    """
    生成回收站存储路径。
    使用时间戳 + file_id 避免冲突。
    目录与文件统一落在 .trash 下隔离。
    回收站路径不暴露给用户作为访问路径。
    权限假设：调用方已确认用户归属。
    并发：纯函数无状态。
    性能：路径拼接开销可忽略。
    返回：Posix 风格回收站路径。
    """
    rel = PurePosixPath(".trash") / str(user_id) / f"{deleted_at_token}_{file_id}" / name
    return rel.as_posix()


def rel_path_from_storage(user_id: int, storage_path: str) -> str:
    """
    将存储路径转换为用户可见的相对路径。
    仅用于展示，不作为权限校验依据。
    去除 user_id 根前缀形成逻辑路径。
    不会解析或访问真实文件系统。
    权限假设：调用方仅用于展示。
    并发：纯函数无状态。
    性能：字符串处理开销极小。
    返回：Posix 风格逻辑路径。
    """
    rel = PurePosixPath(storage_path or "")
    parts = list(rel.parts)
    if parts and parts[0] == str(user_id):
        rel = PurePosixPath(*parts[1:])
    return rel.as_posix()

