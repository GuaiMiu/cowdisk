"""
@File: disk.py
@Author: GuaiMiu
@Date: 2025/4/5 20:26
@Version: 1.0
@Description:
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FileEntryOut(BaseModel):
    """
    文件或目录条目(DB 索引)
    """

    id: int
    user_id: int
    parent_id: int | None
    name: str
    path: str | None = None
    is_dir: bool
    size: int
    mime_type: str | None = None
    etag: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FileListOut(BaseModel):
    """
    目录列表输出(DB)
    """

    parent_id: int | None
    items: list[FileEntryOut]
    total: int
    page: int
    page_size: int


class FileMkdirIn(BaseModel):
    """
    创建目录输入模型(DB)
    """

    parent_id: int | None = None
    name: str


class FileUploadOut(BaseModel):
    """
    上传输出模型(DB)
    """

    items: list[FileEntryOut]


class FileDeleteFailure(BaseModel):
    """
    批量删除失败条目(DB)
    """

    file_id: int
    error: str


class FileDeleteIn(BaseModel):
    """
    删除输入模型(DB)
    """

    file_ids: list[int]


class FileDeleteBatchOut(BaseModel):
    """
    批量删除输出模型(DB)
    """

    success: list[int]
    failed: list[FileDeleteFailure]


class FileMoveIn(BaseModel):
    """
    移动输入模型(DB)
    """

    file_id: int
    target_parent_id: int | None = None
    new_name: str | None = None


class FileMoveBody(BaseModel):
    """
    移动请求体(新 API)
    """

    target_parent_id: int | None = None
    new_name: str | None = None


class FileRenameIn(BaseModel):
    """
    重命名输入模型(DB)
    """

    file_id: int
    new_name: str


class FileRenameBody(BaseModel):
    """
    重命名请求体(新 API)
    """

    new_name: str


class FileUpdateBody(BaseModel):
    """
    文件或目录更新请求体(新 API)
    """

    model_config = ConfigDict(populate_by_name=True)

    parent_id: int | None = Field(default=None, alias="parentId")
    name: str | None = None


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


class DiskUploadInitIn(BaseModel):
    """
    分片上传初始化
    """

    parent_id: int | None = None
    name: str
    size: int
    mime_type: str | None = None
    part_size: int
    overwrite: bool = False


class UploadConfigOut(BaseModel):
    chunk_size_mb: int
    chunk_upload_threshold_mb: int
    max_parallel_chunks: int
    enable_resumable: bool
    max_single_file_mb: int


class DiskUploadInitOut(BaseModel):
    """
    分片上传初始化输出
    """

    upload_id: str
    part_size: int
    total_parts: int
    expires_in: int
    upload_config: UploadConfigOut


class DiskUploadStatusOut(BaseModel):
    """
    分片上传状态
    """

    status: str
    total_parts: int
    uploaded_parts: list[int]
    missing_parts: list[int]
    uploaded_bytes: int
    expires_in: int


class DiskUploadFinalizeIn(BaseModel):
    """
    分片上传完成
    """

    parent_id: int | None = None
    name: str
    overwrite: bool = False
    mime_type: str | None = None
    total_parts: int | None = None


class DiskMkdirIn(BaseModel):
    """
    创建目录输入模型
    """

    path: str


class DiskDeleteIn(BaseModel):
    """
    删除输入模型
    """

    paths: list[str]
    recursive: bool = False


class DiskDeleteOut(BaseModel):
    """
    删除输出模型
    """

    path: str
    deleted: bool


class DiskDeleteFailure(BaseModel):
    """
    批量删除失败条目
    """

    path: str
    error: str


class DiskDeleteBatchOut(BaseModel):
    """
    批量删除输出模型
    """

    success: list[str]
    failed: list[DiskDeleteFailure]


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


class DiskTrashBatchIdsIn(BaseModel):
    """
    回收站批量操作输入模型
    """

    ids: list[str]


class DiskTrashBatchOut(BaseModel):
    """
    回收站批量操作输出模型
    """

    success: int
    failed: list[str]


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


class DiskRenameItem(BaseModel):
    """
    批量重命名输入条目
    """

    src: str
    dst: str
    overwrite: bool = False


class DiskRenameIn(BaseModel):
    """
    重命名输入模型
    """

    items: list[DiskRenameItem]


class DiskRenameFailure(BaseModel):
    """
    批量重命名失败条目
    """

    src: str
    dst: str
    error: str


class DiskRenameBatchOut(BaseModel):
    """
    批量重命名输出模型
    """

    success: list[DiskEntry]
    failed: list[DiskRenameFailure]


class DiskDownloadTokenIn(BaseModel):
    """
    下载令牌输入模型
    """

    file_id: int | None = None
    job_id: str | None = None


class DiskCompressIn(BaseModel):
    """
    压缩输入模型
    """

    file_id: int
    name: str | None = None


class DiskExtractIn(BaseModel):
    """
    解压输入模型
    """

    file_id: int


class DiskTextReadOut(BaseModel):
    """
    文本读取输出模型
    """

    file_id: int
    content: str
    size: int
    modified_time: datetime | None = None


class DiskTextSaveIn(BaseModel):
    """
    文本保存输入模型
    """

    file_id: int
    content: str
    overwrite: bool = False


class FileTextSaveBody(BaseModel):
    """
    文本保存请求体(新 API)
    """

    content: str
    overwrite: bool = False


class DiskDownloadPrepareIn(BaseModel):
    """
    打包下载准备输入模型(DB)
    """

    file_id: int
