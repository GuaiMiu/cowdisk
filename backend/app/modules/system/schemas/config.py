"""
@File: config.py
@Author: GuaiMiu
@Date: 2026/02/10
@Version: 1.0
@Description: 配置中心 Schema
"""

from typing import Any

from pydantic import BaseModel, Field


class ConfigItemOut(BaseModel):
    key: str
    value: Any
    default: Any
    value_type: str
    description: str | None = None
    rules: dict[str, Any] | None = None
    is_secret: bool = False


class ConfigGroupOut(BaseModel):
    items: list[ConfigItemOut] = Field(default_factory=list)


class ConfigUpdateItem(BaseModel):
    key: str
    value: Any


class ConfigUpdateIn(BaseModel):
    items: list[ConfigUpdateItem] = Field(default_factory=list)
