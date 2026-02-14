from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from app.core.exception import PermissionException, ServiceException
from app.modules.admin.models.response import ResponseModel
from app.modules.admin.models.user import User
from app.modules.admin.services.auth import get_user_permissions
from app.modules.system.deps import get_config, get_config_service
from app.modules.system.permissions import build_config_permission
from app.modules.system.service.config import ConfigCenterService
from app.modules.system.schemas.config_center import (
    ConfigBatchErrorOut,
    ConfigBatchUpdateIn,
    ConfigBatchUpdateOut,
    ConfigGroupDetailOut,
    ConfigGroupListOut,
)
from app.modules.system.typed.specs import REGISTRY
from app.modules.system.typed.config import Config
from app.shared.permission_match import has_permission
from app.shared.deps import require_permissions, require_user

system_config_router = APIRouter(
    prefix="/admin/system/config",
    tags=["System - Config"],
    dependencies=[Depends(require_user)],
)


@system_config_router.get(
    "/groups",
    summary="列出配置分组",
    response_model=ResponseModel[ConfigGroupListOut],
)
async def list_config_groups(
    service: ConfigCenterService = Depends(get_config_service),
    current_user: User = Depends(require_user),
    user_permissions: list[str] = Depends(get_user_permissions),
):
    all_groups = await service.list_groups()
    if current_user.is_superuser:
        groups = all_groups
    else:
        groups = [
            group
            for group in all_groups
            if has_permission(user_permissions, build_config_permission(group, "read"))
        ]
    return ResponseModel.success(data=ConfigGroupListOut(groups=groups))


@system_config_router.get(
    "",
    summary="按分组获取配置",
    response_model=ResponseModel[ConfigGroupDetailOut],
)
async def get_group_config(
    service: ConfigCenterService = Depends(get_config_service),
    group: str = Query(..., description="配置分组"),
    current_user: User = Depends(require_user),
    user_permissions: list[str] = Depends(get_user_permissions),
):
    if not current_user.is_superuser:
        required = build_config_permission(group, "read")
        if not has_permission(user_permissions, required):
            raise PermissionException(msg="无权查看该配置分组")
    items = await service.list_group_specs_with_values(group)
    return ResponseModel.success(data=ConfigGroupDetailOut(group=group, items=items))


@system_config_router.put(
    "/batch",
    summary="批量更新配置",
    response_model=ResponseModel[ConfigBatchUpdateOut],
)
async def update_configs(
    payload: ConfigBatchUpdateIn,
    service: ConfigCenterService = Depends(get_config_service),
    current_user: User = Depends(require_user),
    user_permissions: list[str] = Depends(get_user_permissions),
):
    if not current_user.is_superuser:
        required_permissions: set[str] = set()
        for item in payload.items:
            key = item.key.strip()
            spec = REGISTRY.get(key)
            if not spec:
                continue
            required_permissions.add(build_config_permission(spec.group, "write"))
        for required in required_permissions:
            if not has_permission(user_permissions, required):
                raise PermissionException(msg="无权修改该配置分组")
    try:
        result = await service.update_batch(
            items=[item.model_dump() for item in payload.items],
            updated_by=current_user.id,
        )
    except ServiceException as exc:
        errors: list[ConfigBatchErrorOut] = []
        if exc.data:
            try:
                parsed = json.loads(exc.data)
            except json.JSONDecodeError:
                parsed = []
            if isinstance(parsed, list):
                errors = [ConfigBatchErrorOut.model_validate(item) for item in parsed]
        return ResponseModel.error(msg=exc.msg or "保存失败", data=errors)

    return ResponseModel.success(
        msg="保存成功",
        data=ConfigBatchUpdateOut(
            updated_keys=result.updated_keys,
            skipped_keys=result.skipped_keys,
            version=result.version,
            rollback_point=result.rollback_point,
        ),
    )


@system_config_router.get(
    "/upload",
    summary="获取上传相关配置",
    response_model=ResponseModel[dict],
    dependencies=[require_permissions(["cfg:core:read"])],
)
async def get_upload_config(config: Config = Depends(get_config)):
    data = {
        "chunk_size_mb": await config.upload.chunk_size_mb(),
        "chunk_upload_threshold_mb": await config.upload.chunk_upload_threshold_mb(),
        "max_parallel_chunks": await config.upload.max_parallel_chunks(),
        "enable_resumable": await config.upload.enable_resumable(),
        "max_single_file_mb": await config.upload.max_single_file_mb(),
    }
    return ResponseModel.success(data=data)
