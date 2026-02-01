"""
@File: share.py
@Author: GuaiMiu
@Date: 2025/4/5 20:26
@Version: 1.0
@Description: 分享相关模型
"""

from pydantic import BaseModel


class Share(BaseModel):
    id: str
    resourceType: str
    path: str
    token: str
    name: str
    createdAt: int
    expiresAt: int | None = None
    hasCode: bool
    code: str | None = None
    status: int
    missing: bool | None = None


class ShareCreateIn(BaseModel):
    resourceType: str
    path: str
    expiresInDays: int | None = None
    expiresAt: int | None = None
    code: str | None = None


class ShareUpdateIn(BaseModel):
    expiresInDays: int | None = None
    expiresAt: int | None = None
    code: str | None = None
    status: int | None = None


class ShareBatchIdsIn(BaseModel):
    ids: list[str]


class ShareBatchStatusIn(BaseModel):
    ids: list[str]
    status: int


class ShareBatchOut(BaseModel):
    success: int
    failed: list[str]


class ShareListOut(BaseModel):
    items: list[Share]
    total: int
    page: int
    size: int
    pages: int


class ShareLockedOut(BaseModel):
    locked: bool = True
    share: dict


class ShareUnlockedOut(BaseModel):
    locked: bool = False
    share: Share
    listing: list[dict] | None = None
    fileMeta: dict | None = None


class ShareUnlockIn(BaseModel):
    code: str


class ShareListQueryOut(BaseModel):
    items: list[dict]
    nextCursor: str | None = None


class ShareSaveIn(BaseModel):
    targetPath: str
