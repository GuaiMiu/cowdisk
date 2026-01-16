"""
@File: disk.py
@Author: GuaiMiu
@Date: 2025/4/5 20:26
@Version: 1.0
@Description:
"""

from datetime import datetime

from pydantic import BaseModel


class DiskEntry(BaseModel):
    """
    文件或目录信息
    """

    name: str
    path: str
    is_dir: bool
    size: int
    modified_time: datetime | None = None


class DiskListOut(BaseModel):
    """
    目录列表输出模型
    """

    path: str
    items: list[DiskEntry]


class DiskUploadOut(BaseModel):
    """
    上传输出模型
    """

    items: list[DiskEntry]


class DiskUploadInitIn(BaseModel):
    """
    分片上传初始化
    """

    path: str
    filename: str
    size: int
    total_chunks: int
    overwrite: bool = False


class DiskUploadCompleteIn(BaseModel):
    """
    分片上传完成
    """

    upload_id: str


class DiskMkdirIn(BaseModel):
    """
    创建目录输入模型
    """

    path: str


class DiskDeleteIn(BaseModel):
    """
    删除输入模型
    """

    path: str
    recursive: bool = False


class DiskDeleteOut(BaseModel):
    """
    删除输出模型
    """

    path: str
    deleted: bool


class DiskTrashEntry(BaseModel):
    """
    回收站条目
    """

    id: str
    name: str
    path: str
    is_dir: bool
    size: int
    deleted_at: datetime


class DiskTrashListOut(BaseModel):
    """
    回收站列表输出模型
    """

    items: list[DiskTrashEntry]


class DiskTrashRestoreIn(BaseModel):
    """
    回收站恢复输入模型
    """

    id: str


class DiskTrashDeleteIn(BaseModel):
    """
    回收站删除输入模型
    """

    id: str


class DiskShareCreateIn(BaseModel):
    """
    分享创建输入模型
    """

    path: str
    expires_hours: int | None = 72


class DiskShareEntry(BaseModel):
    """
    分享条目
    """

    id: str
    name: str
    path: str
    is_dir: bool
    created_at: datetime
    expires_at: datetime | None = None


class DiskShareListOut(BaseModel):
    """
    分享列表输出模型
    """

    items: list[DiskShareEntry]


class DiskRenameIn(BaseModel):
    """
    重命名输入模型
    """

    src: str
    dst: str
    overwrite: bool = False


class DiskDownloadTokenIn(BaseModel):
    """
    下载令牌输入模型
    """

    path: str | None = None
    job_id: str | None = None
