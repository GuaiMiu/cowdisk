from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ConfigGroupItemOut(BaseModel):
    key: str
    group: str
    description: str
    value: Any
    default: Any
    value_type: str
    rules: dict[str, Any] = Field(default_factory=dict)
    is_secret: bool = False
    editable: bool = True
    source: str
    served_from: str | None = None


class ConfigGroupListOut(BaseModel):
    groups: list[str]


class ConfigGroupDetailOut(BaseModel):
    group: str
    items: list[ConfigGroupItemOut]


class ConfigBatchUpdateItemIn(BaseModel):
    key: str
    value: Any


class ConfigBatchUpdateIn(BaseModel):
    items: list[ConfigBatchUpdateItemIn] = Field(default_factory=list)


class ConfigBatchUpdateOut(BaseModel):
    updated_keys: list[str] = Field(default_factory=list)
    skipped_keys: list[str] = Field(default_factory=list)
    version: int
    rollback_point: str | None = None


class ConfigBatchErrorOut(BaseModel):
    key: str
    error: str
