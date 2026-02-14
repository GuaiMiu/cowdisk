"""
@File: auth.py
@Author: GuaiMiu
@Date: 2025/3/16 00:31
@Version: 1.0
@Description:
"""

from fastapi import APIRouter, Depends
from fastapi_pagination import set_page, set_params
from fastapi_pagination.api import set_items_transformer
from fastapi_pagination.cursor import CursorPage, CursorParams
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.modules.admin.models.response import ResponseModel
from app.modules.admin.models.user import User
from app.modules.admin.schemas.user import UserAddIn, UserEditIn, UserOut, UsersDeleteIn
from app.shared.deps import require_permissions, require_user
from app.modules.admin.services.user import UserService
from app.core.database import get_async_session

user_router = APIRouter(
    prefix="/users",
    tags=["Admin - Users"],
    dependencies=[Depends(require_user)],
)


@user_router.get(
    "",
    summary="获取用户列表",
    response_model=ResponseModel[CursorPage[UserOut]],
    dependencies=[require_permissions(["system:user:list"])],
)
async def get_user_list(
    params: CursorParams = Depends(),
    db: AsyncSession = Depends(get_async_session),
):
    query = select(User).where(User.is_deleted == False).order_by(User.id.asc())
    with set_page(CursorPage[UserOut]), set_params(params), set_items_transformer(
        lambda items: [UserOut.model_validate(item) for item in items]
    ):
        page = await paginate(db, query)
    return ResponseModel.success(data=page)


@user_router.get(
    "/{user_id}",
    summary="获取用户信息",
    response_model=ResponseModel[UserOut],
    dependencies=[require_permissions(["system:user:list"])],
)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """
    获取用户信息
    :param user_id:
    :param db:
    :return:
    """
    user = await UserService.get_user(db=db, user_id=user_id)
    return ResponseModel.success(data=user)


@user_router.post(
    "",
    summary="添加用户",
    response_model=ResponseModel[UserOut],
    dependencies=[require_permissions(["system:user:create"])],
)
async def add_user(
    user: UserAddIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    """
    添加用户
    """
    role = await UserService.add_user(db=db, user=user, current_user=current_user)
    return ResponseModel.success(data=role)


@user_router.patch(
    "/{user_id}",
    summary="编辑用户",
    response_model=ResponseModel[UserOut],
    dependencies=[require_permissions(["system:user:update"])],
)
async def edit_user(
    user_id: int,
    user: UserEditIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    """
    编辑用户
    """
    user.id = user_id
    user = await UserService.edit_user(db=db, user=user, current_user=current_user)
    return ResponseModel.success(data=user)


@user_router.delete(
    "/{user_id}",
    summary="删除用户",
    response_model=ResponseModel[UsersDeleteIn],
    dependencies=[require_permissions(["system:user:delete"])],
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    """
    删除用户
    :param current_user:
    :param user_id:
    :param db:
    :return:
    """
    users = await UserService.delete_users(
        db=db, users=UsersDeleteIn(ids=[user_id]), current_user=current_user
    )
    return ResponseModel.success(data=users)


@user_router.delete(
    "",
    summary="批量删除用户",
    response_model=ResponseModel[UsersDeleteIn],
    dependencies=[require_permissions(["system:user:delete"])],
)
async def delete_users(
    users: UsersDeleteIn,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_user),
):
    """
    批量删除用户
    """
    users = await UserService.delete_users(
        db=db, users=users, current_user=current_user
    )
    return ResponseModel.success(data=users)




